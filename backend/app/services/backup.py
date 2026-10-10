"""
Sao lưu và phục hồi dữ liệu CSDL phân tích (schema analytics).

Định dạng bản sao lưu: một file zip gồm
  - manifest.json: phiên bản định dạng, thời điểm tạo, người tạo, AS_OF, lịch sử migration, số dòng từng bảng;
  - <bảng>.csv: dữ liệu từng bảng xuất bằng COPY ... TO STDOUT (CSV có dòng tiêu đề).

Chỉ sao lưu DỮ LIỆU. Cấu trúc bảng do migration quản lý, nên chỉ phục hồi khi lịch sử migration
của bản sao lưu trùng khớp với CSDL hiện tại (cùng phiên bản, cùng checksum).

Không dùng pg_dump để không phụ thuộc phiên bản công cụ dòng lệnh của PostgreSQL trên máy chạy API.

Phục hồi chạy trong MỘT giao dịch: TRUNCATE mọi bảng -> COPY FROM theo thứ tự bảng cha trước
-> đối chiếu số dòng với manifest -> đặt lại sequence của cột identity. Lỗi ở bất kỳ bước nào thì
ROLLBACK, dữ liệu cũ giữ nguyên.
"""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg import sql

from backend.app.core.config import TZ, as_of, get_settings
from database.config import load_db_config

FORMAT_VERSION = 1
SCHEMA = "analytics"
# Thứ tự nạp khi phục hồi: bảng được tham chiếu (khóa ngoại) đứng trước. Khi phục hồi, khóa ngoại và chỉ mục phụ được
# tạm bỏ rồi tạo lại sau khi nạp (xem _restore_tables), nên cả cặp tham chiếu chéo intervention_log <-> outbound_message
# cũng nạp được.
BACKUP_TABLES = (
    "app_user",
    "academic_term",
    "risk_rule_set",
    "etl_run_log",
    "etl_watermark",
    "etl_online_snapshot",
    "fact_server_traffic_hourly",
    "fact_course_progress_daily",
    "fact_student_risk_summary",
    "message_template",
    "auto_prompt_rule",
    "intervention_log",
    "outbound_message",
    "channel_check",
)
NAME_PATTERN = re.compile(r"^lms_analytics_\d{8}_\d{6}(_\d{1,3})?\.zip$")
# Khóa advisory riêng cho sao lưu/phục hồi: hai thao tác không chạy chồng lên nhau (kể cả giữa nhiều worker)
ADVISORY_KEY = 7_420_001
COPY_CHUNK = 1 << 20


class BackupError(RuntimeError):
    """Bản sao lưu không hợp lệ hoặc không phục hồi được."""


class BackupBusy(BackupError):
    """Đang có thao tác sao lưu/phục hồi khác."""


class BackupNotFound(BackupError):
    """Không có file sao lưu với tên đã cho."""


@dataclass(frozen=True)
class BackupInfo:
    name: str
    size_bytes: int
    created_at: str
    created_by: str | None
    as_of: str | None
    migration_version: int | None
    total_rows: int
    tables: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------------------- tiện ích
def backup_dir() -> Path:
    path = Path(get_settings().backup_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_path(name: str) -> Path:
    """Đường dẫn file sao lưu; chỉ chấp nhận tên đúng mẫu (chặn ../ và tên tùy ý)."""
    if not NAME_PATTERN.fullmatch(name):
        raise BackupNotFound("Tên file sao lưu không hợp lệ")
    path = backup_dir() / name
    if not path.is_file():
        raise BackupNotFound(f"Không tìm thấy bản sao lưu {name}")
    return path


def _connect() -> psycopg.Connection:
    cfg = load_db_config("ANALYTICS_DB")
    return psycopg.connect(**cfg.conninfo(application_name="lms-backup"),
                           options="-c statement_timeout=0 -c lock_timeout=30000")


def _columns(conn: psycopg.Connection, table: str) -> list[str]:
    """Cột ghi được (bỏ cột GENERATED ... STORED), theo thứ tự định nghĩa."""
    rows = conn.execute("""
        SELECT a.attname FROM pg_attribute a
        WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped AND a.attgenerated = ''
        ORDER BY a.attnum""", (f"{SCHEMA}.{table}",)).fetchall()
    return [r[0] for r in rows]


def _migrations(conn: psycopg.Connection) -> list[list]:
    rows = conn.execute("SELECT version, checksum FROM public.schema_migrations ORDER BY version").fetchall()
    return [[int(v), c] for v, c in rows]


def _schema_tables(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute("""SELECT table_name FROM information_schema.tables
                           WHERE table_schema = %s AND table_type = 'BASE TABLE'""", (SCHEMA,)).fetchall()
    return {r[0] for r in rows}


def _lock(conn: psycopg.Connection) -> None:
    if not conn.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_KEY,)).fetchone()[0]:
        raise BackupBusy("Đang có một thao tác sao lưu hoặc phục hồi khác, vui lòng thử lại sau")


def _unlock(conn: psycopg.Connection) -> None:
    conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_KEY,))


def _reset(conn: psycopg.Connection) -> None:
    """Đưa kết nối về chế độ autocommit (hủy giao dịch dở dang nếu có) để mở khóa advisory."""
    if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
        conn.rollback()
    conn.read_only = None
    conn.isolation_level = None
    conn.autocommit = True


def _new_name(directory: Path, now: datetime) -> str:
    base = f"lms_analytics_{now:%Y%m%d_%H%M%S}"
    name, n = f"{base}.zip", 1
    while (directory / name).exists():
        n += 1
        name = f"{base}_{n}.zip"
    return name


def _read_manifest(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as zf:
            return json.loads(zf.read("manifest.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BackupError(f"File {path.name} không phải bản sao lưu hợp lệ") from exc


def _info(path: Path, manifest: dict) -> BackupInfo:
    tables = {t: int(meta["rows"]) for t, meta in manifest.get("tables", {}).items()}
    migrations = manifest.get("migrations") or []
    return BackupInfo(name=path.name, size_bytes=path.stat().st_size, created_at=manifest.get("created_at", ""),
                      created_by=manifest.get("created_by"), as_of=manifest.get("as_of"),
                      migration_version=migrations[-1][0] if migrations else None,
                      total_rows=sum(tables.values()), tables=tables)


# ----------------------------------------------------------------------------- nghiệp vụ
def list_backups() -> list[BackupInfo]:
    """Các bản sao lưu trong thư mục, mới nhất trước. File hỏng bị bỏ qua."""
    items = []
    for path in backup_dir().glob("lms_analytics_*.zip"):
        if not NAME_PATTERN.fullmatch(path.name):
            continue
        try:
            items.append(_info(path, _read_manifest(path)))
        except BackupError:
            continue
    return sorted(items, key=lambda i: (i.created_at, i.name), reverse=True)


def create_backup(created_by: str) -> BackupInfo:
    """Xuất toàn bộ bảng của schema analytics trong một ảnh chụp nhất quán (REPEATABLE READ)."""
    directory = backup_dir()
    now = datetime.now(TZ)
    name = _new_name(directory, now)
    final, partial = directory / name, directory / f"{name}.part"

    with _connect() as conn:
        conn.autocommit = True
        _lock(conn)
        try:
            missing = _schema_tables(conn) - set(BACKUP_TABLES)
            if missing:
                raise BackupError(f"Bảng chưa được khai báo trong danh sách sao lưu: {', '.join(sorted(missing))}")
            conn.autocommit = False
            conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            conn.read_only = True
            tables: dict[str, dict] = {}
            with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                for table in BACKUP_TABLES:
                    columns = _columns(conn, table)
                    query = sql.SQL("COPY {}.{} ({}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
                        sql.Identifier(SCHEMA), sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)))
                    with zf.open(f"{table}.csv", "w", force_zip64=True) as out, conn.cursor().copy(query) as copy:
                        # COPY trả từng dòng; gom thành khối ~1 MB rồi mới nén (nén từng dòng tốn gấp ~3 lần CPU)
                        buffer = bytearray()
                        for chunk in copy:
                            buffer += chunk
                            if len(buffer) >= COPY_CHUNK:
                                out.write(buffer)
                                buffer.clear()
                        if buffer:
                            out.write(buffer)
                    rows = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier(SCHEMA), sql.Identifier(table))).fetchone()[0]
                    tables[table] = {"rows": int(rows), "columns": columns}
                manifest = {
                    "format_version": FORMAT_VERSION,
                    "created_at": now.isoformat(timespec="seconds"),
                    "created_by": created_by,
                    "database": conn.info.dbname,
                    "as_of": as_of().isoformat(timespec="seconds"),
                    "migrations": _migrations(conn),
                    "tables": tables,
                }
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            conn.rollback()
            partial.replace(final)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        finally:
            _reset(conn)
            _unlock(conn)
    return _info(final, manifest)


def delete_backup(name: str) -> None:
    backup_path(name).unlink()


def restore_backup(name: str) -> dict:
    """Thay toàn bộ dữ liệu schema analytics bằng dữ liệu trong bản sao lưu. Trả về số dòng đã nạp từng bảng."""
    path = backup_path(name)
    manifest = _read_manifest(path)
    if manifest.get("format_version") != FORMAT_VERSION:
        raise BackupError("Bản sao lưu được tạo bởi phiên bản định dạng khác, không phục hồi được")
    if list(manifest.get("tables", {})) != list(BACKUP_TABLES):
        raise BackupError("Danh sách bảng trong bản sao lưu không khớp với hệ thống hiện tại")

    with _connect() as conn:
        conn.autocommit = True
        _lock(conn)
        try:
            current = _migrations(conn)
            if manifest.get("migrations") != current:
                backup_version = (manifest.get("migrations") or [[None]])[-1][0]
                raise BackupError(f"Bản sao lưu thuộc cấu trúc CSDL phiên bản V{backup_version:03d}, hệ thống "
                                  f"hiện tại là V{current[-1][0]:03d}; không phục hồi được"
                                  if backup_version is not None and current else
                                  "Lịch sử migration của bản sao lưu không khớp với CSDL hiện tại")
            loaded: dict[str, int] = {}
            conn.autocommit = False
            try:
                _restore_tables(conn, path, manifest, loaded)
            except psycopg.errors.LockNotAvailable as exc:
                raise BackupBusy("Dữ liệu đang được một tiến trình khác sử dụng (ví dụ ETL đang chạy), "
                                 "vui lòng thử lại sau ít phút") from exc
        finally:
            _reset(conn)
            _unlock(conn)
    return {"name": name, "tables": loaded, "total_rows": sum(loaded.values())}


def _deferred_structure(conn: psycopg.Connection) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """
    Khóa ngoại [(bảng, tên, định nghĩa)] và chỉ mục phụ [(tên đầy đủ, câu tạo)] (không gắn PRIMARY KEY/UNIQUE) của schema,
    đọc từ catalog PostgreSQL – để tạm bỏ khi nạp dữ liệu và tạo lại ĐÚNG như cũ (tên, điều kiện, DEFERRABLE…).
    """
    fks = conn.execute("""
        SELECT c.conrelid::regclass::text, c.conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c WHERE c.contype = 'f' AND c.connamespace = %s::regnamespace
        ORDER BY 1, 2""", (SCHEMA,)).fetchall()
    indexes = [(r[0], r[1]) for r in conn.execute("""
        SELECT i.indexrelid::regclass::text, pg_get_indexdef(i.indexrelid)
        FROM pg_index i JOIN pg_class t ON t.oid = i.indrelid
        WHERE t.relnamespace = %s::regnamespace AND t.relkind = 'r'
          AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = i.indexrelid)
        ORDER BY i.indexrelid""", (SCHEMA,)).fetchall()]
    return fks, indexes


def _restore_tables(conn: psycopg.Connection, path: Path, manifest: dict, loaded: dict[str, int]) -> None:
    """
    Một giao dịch (lỗi ở bất kỳ bước nào -> hoàn tác toàn bộ, dữ liệu cũ giữ nguyên):
      tạm bỏ khóa ngoại + chỉ mục phụ -> TRUNCATE -> COPY từng bảng -> đối chiếu số dòng -> tạo lại chỉ mục ->
      thêm lại khóa ngoại (PostgreSQL kiểm tra toàn vẹn của TOÀN BỘ dữ liệu vừa nạp) -> đặt lại sequence.
    Nạp rồi mới dựng chỉ mục/kiểm tra khóa ngoại một lần nhanh hơn nhiều so với cập nhật từng dòng (cách pg_restore làm);
    đo trên dữ liệu 5 khoa: xem docs/KET_QUA_KIEM_THU.md.
    """
    with zipfile.ZipFile(path) as zf, conn.transaction():
        fks, indexes = _deferred_structure(conn)
        for table, name, _ in fks:
            conn.execute(sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(sql.SQL(table), sql.Identifier(name)))
        for name, _ in indexes:
            conn.execute(sql.SQL("DROP INDEX {}").format(sql.SQL(name)))
        conn.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY").format(sql.SQL(", ").join(
            sql.SQL("{}.{}").format(sql.Identifier(SCHEMA), sql.Identifier(t)) for t in BACKUP_TABLES)))
        for table in BACKUP_TABLES:
            columns = manifest["tables"][table]["columns"]
            if columns != _columns(conn, table):
                raise BackupError(f"Cột của bảng {table} trong bản sao lưu không khớp với CSDL hiện tại")
            query = sql.SQL("COPY {}.{} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
                sql.Identifier(SCHEMA), sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)))
            with zf.open(f"{table}.csv") as src, conn.cursor().copy(query) as copy:
                while chunk := src.read(COPY_CHUNK):
                    copy.write(chunk)
            rows = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                sql.Identifier(SCHEMA), sql.Identifier(table))).fetchone()[0]
            if rows != manifest["tables"][table]["rows"]:
                raise BackupError(f"Bảng {table}: nạp {rows} dòng, bản sao lưu ghi {manifest['tables'][table]['rows']} dòng")
            loaded[table] = int(rows)
        for _, ddl in indexes:
            conn.execute(ddl)
        for table, name, definition in fks:
            try:
                conn.execute(sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} {}").format(
                    sql.SQL(table), sql.Identifier(name), sql.SQL(definition)))
            except psycopg.errors.ForeignKeyViolation as exc:
                raise BackupError(f"Dữ liệu trong bản sao lưu vi phạm ràng buộc {name} của bảng {table}") from exc
        # Cột identity: sequence tiếp tục sau giá trị lớn nhất vừa nạp
        identity = conn.execute("""SELECT table_name, column_name FROM information_schema.columns
                                   WHERE table_schema = %s AND is_identity = 'YES' ORDER BY 1""", (SCHEMA,)).fetchall()
        for table, column in identity:
            conn.execute(sql.SQL(
                "SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(MAX({}), 0) + 1, false) FROM {}.{}"
            ).format(sql.Identifier(column), sql.Identifier(SCHEMA), sql.Identifier(table)),
                (f"{SCHEMA}.{table}", column))
