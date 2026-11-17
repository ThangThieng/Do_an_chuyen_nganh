"""
Nạp CSV Moodle thật vào CSDL nguồn theo hai bước:

  1. stage     : đọc CSV (UTF-8, không dòng tiêu đề) -> COPY vào stg.<bảng> (mọi cột kiểu text, giữ nguyên toàn
                 bộ dữ liệu của file). Dòng sai số cột bị loại và ghi vào stg.reject (chỉ số dòng, không lưu nội dung).
  2. transform : trong MỘT transaction, xóa các bảng mdl_* đích rồi INSERT ... SELECT từ stg có ép kiểu, lọc phạm vi
                 (stg.scope_course) và bỏ cột nhạy cảm. Lỗi ở bất kỳ bảng nào -> rollback toàn bộ.

Ánh xạ cột theo TÊN: chỉ nạp các cột mà bảng đích có; cột đích không có trong file dùng giá trị mặc định
hoặc biểu thức ghi đè trong manifest.
"""
from __future__ import annotations

import csv
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

from ingest.manifest import DERIVED_CATEGORIES, ORPHAN_CHECKS, SCOPE_FILE, SOURCES, Source
from ingest.moodle311 import COLUMNS

log = logging.getLogger("ingest")
csv.field_size_limit(2**31 - 1)

NULL_TOKENS = ("NULL", "\\N")
NUMERIC_TYPES = {"bigint", "integer", "smallint", "numeric", "double precision", "real"}


class IngestError(RuntimeError):
    """Lỗi nạp dữ liệu (thiếu file bắt buộc, sai cấu trúc, CSDL đích được bảo vệ...)."""


@dataclass
class StageResult:
    table: str
    file: str
    rows_read: int = 0
    rows_staged: int = 0
    rows_rejected: int = 0
    skipped: bool = False          # file tùy chọn chưa có
    reused: bool = False           # đã nạp đúng file này ở lần trước


def source_columns(src: Source) -> tuple[str, ...]:
    return src.columns if src.columns is not None else COLUMNS[src.table]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(value: str) -> str | None:
    return None if value in NULL_TOKENS else value


# ----------------------------------------------------------------------------- bước 1: stage
def stage_file(conn: psycopg.Connection, data_dir: Path, src: Source, batch: str, force: bool = False) -> StageResult:
    path = data_dir / src.file
    result = StageResult(table=src.stage_name, file=src.file)
    if not path.is_file():
        if src.optional:
            result.skipped = True
            return result
        raise IngestError(f"Thiếu file bắt buộc: {path}")

    columns = source_columns(src)
    checksum = file_sha256(path)
    stage_table = sql.Identifier("stg", src.stage_name)
    previous = conn.execute(
        "SELECT rows_staged, rows_rejected, rows_read FROM stg.ingest_batch "
        "WHERE table_name = %s AND file_sha256 = %s AND status = 'STAGED' ORDER BY batch_id DESC LIMIT 1",
        (src.stage_name, checksum)).fetchone()
    exists = conn.execute("SELECT to_regclass(%s)", (f"stg.{src.stage_name}",)).fetchone()[0] is not None
    if previous and exists and not force:
        result.rows_staged, result.rows_rejected, result.rows_read = previous
        result.reused = True
        return result

    with conn.transaction():
        conn.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(stage_table))
        conn.execute(sql.SQL("CREATE UNLOGGED TABLE {} ({})").format(
            stage_table, sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in columns)))
        batch_id = conn.execute(
            "INSERT INTO stg.ingest_batch (batch, table_name, file_name, file_sha256, file_bytes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING batch_id",
            (batch, src.stage_name, src.file, checksum, path.stat().st_size)).fetchone()[0]
        rejects: list[tuple[int, int, int, str]] = []
        with path.open(encoding="utf-8-sig", newline="") as fh, conn.cursor() as cur:
            reader = csv.reader(fh)
            with cur.copy(sql.SQL("COPY {} FROM STDIN").format(stage_table)) as copy:
                for row in reader:
                    result.rows_read += 1
                    if len(row) != len(columns):
                        rejects.append((batch_id, reader.line_num, len(row),
                                        f"sai số cột: {len(row)} thay vì {len(columns)}"))
                        continue
                    copy.write_row([_clean(v) for v in row])
                    result.rows_staged += 1
        result.rows_rejected = len(rejects)
        if rejects:
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO stg.reject (batch_id, line_no, field_count, reason) "
                                "VALUES (%s, %s, %s, %s)", rejects)
        conn.execute(
            "UPDATE stg.ingest_batch SET rows_read = %s, rows_staged = %s, rows_rejected = %s, "
            "status = 'STAGED', finished_at = clock_timestamp() WHERE batch_id = %s",
            (result.rows_read, result.rows_staged, result.rows_rejected, batch_id))
    return result


def stage_scope(conn: psycopg.Connection, data_dir: Path) -> int:
    """Nạp danh sách môn trong phạm vi (cột đầu tiên của SCOPE_FILE) vào stg.scope_course."""
    path = data_dir / SCOPE_FILE
    if not path.is_file():
        raise IngestError(f"Thiếu file phạm vi: {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        ids = sorted({int(row[0]) for row in csv.reader(fh) if row and row[0].strip().isdigit()})
    with conn.transaction():
        conn.execute("TRUNCATE stg.scope_course")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO stg.scope_course (id) VALUES (%s)", [(i,) for i in ids])
    return len(ids)


# ----------------------------------------------------------------------------- bước 2: transform
def _target_columns(conn: psycopg.Connection, table: str) -> list[tuple[str, str, bool, str | None]]:
    rows = conn.execute(
        "SELECT column_name, data_type, is_nullable = 'NO', column_default FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position", (f"mdl_{table}",)).fetchall()
    if not rows:
        raise IngestError(f"Bảng đích mdl_{table} chưa tồn tại – hãy chạy migration cho CSDL nguồn trước.")
    return rows


def build_insert(conn: psycopg.Connection, src: Source) -> str:
    """Sinh câu INSERT INTO mdl_<bảng> (...) SELECT ... FROM stg.<bảng> s WHERE <phạm vi>."""
    staged = set(source_columns(src)) - set(src.skip)
    names, exprs = [], []
    for name, data_type, not_null, default in _target_columns(conn, src.table):
        if name in src.overrides:
            expr = src.overrides[name]
        elif name in staged:
            column = f's."{name}"'
            if data_type in NUMERIC_TYPES:
                expr = f"NULLIF({column}, '')::{data_type}"
                if not_null:
                    expr = f"COALESCE({expr}, 0)"
            else:
                expr = f"COALESCE({column}, '')" if not_null else column
        elif not_null and default is None:
            raise IngestError(f"mdl_{src.table}.{name} bắt buộc nhưng file không có và manifest không ghi đè.")
        else:
            continue                                   # dùng giá trị mặc định / NULL của bảng đích
        names.append(f'"{name}"')
        exprs.append(expr)
    where = f"\nWHERE {src.scope}" if src.scope else ""
    return (f"INSERT INTO mdl_{src.table} ({', '.join(names)})\nSELECT {', '.join(exprs)}\n"
            f"FROM stg.\"{src.stage_name}\" s{where}")


def transform(conn: psycopg.Connection, staged: dict[str, StageResult]) -> dict[str, int]:
    """Chuyển toàn bộ stg -> mdl_* trong một transaction. Trả về số dòng đã nạp của từng bảng."""
    loaded: dict[str, int] = {}
    with conn.transaction():
        targets = list(dict.fromkeys(f"mdl_{s.table}" for s in SOURCES))
        conn.execute("TRUNCATE " + ", ".join(targets) + " RESTART IDENTITY")
        for src in SOURCES:
            key = src.stage_name
            if staged[key].skipped:
                loaded[key] = 0
                continue
            started = time.perf_counter()
            loaded[key] = conn.execute(build_insert(conn, src)).rowcount
            if src.table == "course_categories":
                loaded[key] += _insert_derived_categories(conn)
            log.info("  mdl_%-26s %9d dòng (%.1fs) <- stg.%s", src.table, loaded[key], time.perf_counter() - started, key)
        for src in SOURCES:                            # số tự tăng tiếp nối id lớn nhất đã nạp
            conn.execute(sql.SQL(
                "SELECT setval(pg_get_serial_sequence({}, 'id'), GREATEST((SELECT MAX(id) FROM {}), 1))"
            ).format(sql.Literal(f"mdl_{src.table}"), sql.Identifier(f"mdl_{src.table}")))
        conn.execute("UPDATE stg.ingest_batch SET status = 'LOADED' WHERE status = 'STAGED'")
    for src in SOURCES:
        conn.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(f"mdl_{src.table}")))
    return loaded


def _insert_derived_categories(conn: psycopg.Connection) -> int:
    """Bổ sung danh mục cha không có trong file (Khoa và chuyên ngành) nếu chưa có."""
    added = 0
    for cat_id, name, parent, depth, path in DERIVED_CATEGORIES:
        added += conn.execute(
            "INSERT INTO mdl_course_categories (id, name, idnumber, description, parent, depth, path, timemodified) "
            "SELECT %s, %s, 'derived', '', %s, %s, %s, 0 "
            "WHERE NOT EXISTS (SELECT 1 FROM mdl_course_categories WHERE id = %s)",
            (cat_id, name, parent, depth, path, cat_id)).rowcount
    return added


# ----------------------------------------------------------------------------- kiểm tra sau nạp
def orphan_report(conn: psycopg.Connection) -> list[tuple[str, str, str, int]]:
    out = []
    for child, column, parent, condition in ORPHAN_CHECKS:
        count = conn.execute(
            f"SELECT COUNT(*) FROM mdl_{child} c WHERE ({condition}) "
            f"AND NOT EXISTS (SELECT 1 FROM mdl_{parent} p WHERE p.id = c.{column})").fetchone()[0]
        out.append((child, column, parent, count))
    return out


def epoch_ranges(conn: psycopg.Connection) -> list[tuple[str, str, int | None, int | None]]:
    checks = (("assign_submission", "timemodified"), ("grade_grades", "timemodified"), ("quiz_attempts", "timestart"),
              ("logstore_standard_log", "timecreated"), ("user_enrolments", "timemodified"),
              ("notifications", "timecreated"), ("sessions", "timemodified"))
    return [(t, c, *conn.execute(f"SELECT MIN({c}), MAX({c}) FROM mdl_{t} WHERE {c} > 0").fetchone())
            for t, c in checks]
