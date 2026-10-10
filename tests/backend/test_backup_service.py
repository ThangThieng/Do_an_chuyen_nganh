"""
Kiểm thử sao lưu/phục hồi trên CSDL phân tích thật (khứ hồi đầy đủ ~ 40 giây).

Phục hồi thay dữ liệu bằng bản sao lưu vừa tạo trong cùng test, nên dữ liệu sau khi chạy giống hệt trước khi chạy.
Không chạy song song với ETL scheduler.
"""
from __future__ import annotations

import json
import zipfile

import psycopg
import pytest

from backend.app.services import backup as backup_service
from database.config import load_db_config
from tests.backend.conftest import API, TEST_MARK


@pytest.fixture()
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "backup_dir", lambda: tmp_path)
    return tmp_path


def _fingerprints(db) -> dict[str, str]:
    """md5 nội dung từng bảng (băm từng dòng rồi băm chuỗi mã đã sắp xếp – tránh giới hạn chuỗi 1 GB) + giá trị kế tiếp của sequence identity."""
    result = {}
    for table in backup_service.BACKUP_TABLES:
        result[table] = db.execute(
            f"SELECT md5(COALESCE(string_agg(md5(t::text), '' ORDER BY md5(t::text)), '')) FROM analytics.{table} t").fetchone()[0]
    return result


def test_backup_covers_every_table_of_schema(db):
    tables = {r[0] for r in db.execute("""SELECT table_name FROM information_schema.tables
                                          WHERE table_schema = 'analytics' AND table_type = 'BASE TABLE'""")}
    assert tables == set(backup_service.BACKUP_TABLES)


def _structure(db) -> tuple[set, set]:
    fks = set(db.execute("""SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint
                            WHERE contype IN ('f', 'p', 'u', 'c') AND connamespace = 'analytics'::regnamespace""").fetchall())
    indexes = set(db.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'analytics'").fetchall())
    return fks, indexes


def test_backup_and_restore_round_trip(db, backup_dir, accounts):
    before = _fingerprints(db)
    info = backup_service.create_backup("pytest")
    assert backup_service.NAME_PATTERN.fullmatch(info.name)
    assert not list(backup_dir.glob("*.part"))

    with zipfile.ZipFile(backup_dir / info.name) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert set(zf.namelist()) == {"manifest.json", *(f"{t}.csv" for t in backup_service.BACKUP_TABLES)}
    for table in backup_service.BACKUP_TABLES:
        rows = db.execute(f"SELECT COUNT(*) FROM analytics.{table}").fetchone()[0]
        assert manifest["tables"][table]["rows"] == rows == info.tables[table]
    assert "stat_date" not in manifest["tables"]["fact_server_traffic_hourly"]["columns"]   # cột sinh tự động

    # Làm bẩn dữ liệu sau khi sao lưu: thêm một can thiệp, xóa một dòng lưu lượng
    teacher = accounts["teacher"]
    course = accounts["course"]["course_id"]
    db.execute("""INSERT INTO analytics.intervention_log (course_id, user_id, teacher_id, action_type, content)
                  VALUES (%s, 1, %s, 'NOTE', %s)""", (course, teacher, f"{TEST_MARK} sẽ bị phục hồi xóa"))
    db.execute("DELETE FROM analytics.fact_server_traffic_hourly WHERE stat_hour = "
               "(SELECT MIN(stat_hour) FROM analytics.fact_server_traffic_hourly)")
    assert _fingerprints(db) != before

    structure = _structure(db)
    result = backup_service.restore_backup(info.name)
    assert result["total_rows"] == info.total_rows
    assert _fingerprints(db) == before
    # Phục hồi tạm bỏ rồi dựng lại khóa ngoại + chỉ mục phụ: cấu trúc phải giống hệt (tên, định nghĩa, DEFERRABLE…)
    assert _structure(db) == structure

    # Sequence identity tiếp tục sau giá trị lớn nhất: chèn mới không trùng khóa
    max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM analytics.intervention_log").fetchone()[0]
    new_id = db.execute("""INSERT INTO analytics.intervention_log (course_id, user_id, teacher_id, action_type, content)
                           VALUES (%s, 1, %s, 'NOTE', %s) RETURNING id""",
                        (course, teacher, f"{TEST_MARK} sau phục hồi")).fetchone()[0]
    assert new_id > max_id


def _rewrite_manifest(path, change) -> None:
    with zipfile.ZipFile(path) as zf:
        members = {n: zf.read(n) for n in zf.namelist()}
    manifest = json.loads(members["manifest.json"])
    change(manifest)
    members["manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_restore_refuses_other_schema_version_and_keeps_data(db, backup_dir):
    info = backup_service.create_backup("pytest")
    _rewrite_manifest(backup_dir / info.name, lambda m: m["migrations"].pop())
    before = db.execute("SELECT COUNT(*) FROM analytics.fact_course_progress_daily").fetchone()[0]
    with pytest.raises(backup_service.BackupError, match="phiên bản"):
        backup_service.restore_backup(info.name)
    assert db.execute("SELECT COUNT(*) FROM analytics.fact_course_progress_daily").fetchone()[0] == before


def test_restore_rolls_back_when_row_count_differs(db, backup_dir):
    info = backup_service.create_backup("pytest")
    _rewrite_manifest(backup_dir / info.name,
                      lambda m: m["tables"]["fact_student_risk_summary"].update(rows=m["tables"]["fact_student_risk_summary"]["rows"] + 1))
    before = _fingerprints(db)
    with pytest.raises(backup_service.BackupError, match="fact_student_risk_summary"):
        backup_service.restore_backup(info.name)
    assert _fingerprints(db) == before


def test_second_operation_is_rejected_while_one_is_running(backup_dir):
    cfg = load_db_config("ANALYTICS_DB")
    with psycopg.connect(**cfg.conninfo(application_name="pytest-lock"), autocommit=True) as holder:
        holder.execute("SELECT pg_advisory_lock(%s)", (backup_service.ADVISORY_KEY,))
        try:
            with pytest.raises(backup_service.BackupBusy):
                backup_service.create_backup("pytest")
        finally:
            holder.execute("SELECT pg_advisory_unlock(%s)", (backup_service.ADVISORY_KEY,))
    assert not list(backup_dir.iterdir())


def test_list_skips_corrupt_files(backup_dir):
    (backup_dir / "lms_analytics_20260101_000000.zip").write_bytes(b"not a zip")
    (backup_dir / "ghi_chu.zip").write_bytes(b"x")
    assert backup_service.list_backups() == []


def test_backup_api_create_list_download_delete(client, admin_headers, backup_dir):
    created = client.post(f"{API}/admin/backups", headers=admin_headers)
    assert created.status_code == 201
    name = created.json()["name"]
    assert created.json()["created_by"] == "test.admin"
    listed = client.get(f"{API}/admin/backups", headers=admin_headers).json()
    assert [i["name"] for i in listed["items"]] == [name]
    download = client.get(f"{API}/admin/backups/{name}/download", headers=admin_headers)
    assert download.status_code == 200 and download.headers["content-type"] == "application/zip"
    assert download.content[:2] == b"PK"
    assert client.delete(f"{API}/admin/backups/{name}", headers=admin_headers).status_code == 204
    assert client.get(f"{API}/admin/backups", headers=admin_headers).json()["items"] == []


def test_restore_via_api(client, admin_headers, backup_dir, db):
    """Phục hồi qua API: giao dịch đọc của bước xác thực (app_user) phải đã kết thúc, nếu không TRUNCATE
    sẽ chờ khóa tới lock_timeout (lỗi phát hiện khi chạy trên Docker)."""
    info = backup_service.create_backup("pytest")
    before = db.execute("SELECT COUNT(*) FROM analytics.fact_student_risk_summary").fetchone()[0]
    r = client.post(f"{API}/admin/backups/{info.name}/restore", headers=admin_headers,
                    json={"confirm_name": info.name})
    assert r.status_code == 200, r.text
    assert r.json()["total_rows"] == info.total_rows
    assert db.execute("SELECT COUNT(*) FROM analytics.fact_student_risk_summary").fetchone()[0] == before
