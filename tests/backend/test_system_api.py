"""
Kiểm thử nhánh Hệ thống / Danh mục / Tài khoản: đổi mật khẩu (thu hồi token cũ), quản lý người dùng,
nhật ký ETL, danh mục môn học, các ràng buộc của API sao lưu.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.core.security import hash_password, token_revoked, validate_new_password
from tests.backend.conftest import (ADMIN_ID, ADMIN_PASSWORD, ADMIN_USERNAME, API, INACTIVE_ID, INACTIVE_USERNAME,
                                    bearer)


@pytest.fixture()
def restore_admin_password(db, accounts):
    yield
    db.execute("UPDATE analytics.app_user SET password_hash = %s, password_changed_at = NULL WHERE user_id = %s",
               (hash_password(ADMIN_PASSWORD), ADMIN_ID))


def _login(client, username=ADMIN_USERNAME, password=ADMIN_PASSWORD):
    return client.post(f"{API}/auth/login", json={"username": username, "password": password})


# ----------------------------------------------------------------------------- chính sách mật khẩu
@pytest.mark.parametrize("password, ok", [
    ("abc123", False),            # ngắn
    ("abcdefgh", False),          # không có số
    ("12345678", False),          # không có chữ
    ("Matkhau2026", True),
    ("mậtkhẩu99", True),          # chữ có dấu vẫn là chữ
])
def test_password_policy(password, ok):
    assert (validate_new_password(password) is None) is ok


def test_token_revoked_compares_whole_seconds():
    changed = datetime(2026, 10, 1, 8, 0, 0, 750_000, tzinfo=timezone.utc)
    same_second = int(changed.replace(microsecond=0).timestamp())
    assert not token_revoked({"iat": same_second}, changed)          # token cấp ngay sau khi đổi (cùng giây)
    assert token_revoked({"iat": same_second - 1}, changed)
    assert not token_revoked({"iat": 0}, None)


# ----------------------------------------------------------------------------- đổi mật khẩu
def test_login_records_last_login(client, db, accounts):
    before = datetime.now(timezone.utc) - timedelta(seconds=5)
    assert _login(client).status_code == 200
    last = db.execute("SELECT last_login_at FROM analytics.app_user WHERE user_id = %s", (ADMIN_ID,)).fetchone()[0]
    assert last is not None and last >= before


def test_change_password_rejects_wrong_current_and_weak_password(client, admin_headers, restore_admin_password):
    wrong = client.post(f"{API}/auth/change-password", headers=admin_headers,
                        json={"current_password": "khong-dung-123", "new_password": "MatKhauMoi2026"})
    assert wrong.status_code == 400 and "hiện tại" in wrong.json()["detail"]
    weak = client.post(f"{API}/auth/change-password", headers=admin_headers,
                       json={"current_password": ADMIN_PASSWORD, "new_password": "abcdefgh"})
    assert weak.status_code == 400 and "chữ và số" in weak.json()["detail"]
    same = client.post(f"{API}/auth/change-password", headers=admin_headers,
                       json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD})
    assert same.status_code == 400


def test_change_password_revokes_old_tokens(client, restore_admin_password):
    # token cũ được cấp ở giây TRƯỚC lần đổi mật khẩu
    old_token = bearer(ADMIN_ID, "ADMIN", now=datetime.now(timezone.utc) - timedelta(seconds=10))
    changed = client.post(f"{API}/auth/change-password", headers=old_token,
                          json={"current_password": ADMIN_PASSWORD, "new_password": "MatKhauMoi2026"})
    assert changed.status_code == 200
    new_token = {"Authorization": f"Bearer {changed.json()['access_token']}"}

    assert client.get(f"{API}/auth/me", headers=old_token).status_code == 401
    assert client.get(f"{API}/auth/me", headers=new_token).status_code == 200
    assert _login(client).status_code == 401
    assert _login(client, password="MatKhauMoi2026").status_code == 200


def test_change_password_requires_login(client):
    r = client.post(f"{API}/auth/change-password", json={"current_password": "a", "new_password": "b"})
    assert r.status_code == 401


# ----------------------------------------------------------------------------- quản lý người dùng
@pytest.mark.parametrize("method, path", [
    ("get", "/admin/users"), ("get", "/admin/etl/runs"), ("get", "/admin/catalog/courses"), ("get", "/admin/backups"),
    ("post", "/admin/backups"), ("post", f"/admin/users/{INACTIVE_ID}/reset-password"),
])
def test_system_endpoints_are_admin_only(client, teacher_headers, method, path):
    assert getattr(client, method)(f"{API}{path}", headers=teacher_headers).status_code == 403
    assert getattr(client, method)(f"{API}{path}").status_code == 401


def test_list_users(client, admin_headers, accounts):
    rows = client.get(f"{API}/admin/users", headers=admin_headers).json()
    by_id = {r["user_id"]: r for r in rows}
    assert by_id[ADMIN_ID]["role"] == "ADMIN" and by_id[ADMIN_ID]["course_count"] == 0
    assert by_id[INACTIVE_ID]["is_active"] is False
    teacher = by_id[accounts["teacher"]]
    assert teacher["course_count"] == len(accounts["teacher_courses"])
    assert "password_hash" not in teacher


def test_lock_and_unlock_user(client, db, admin_headers, accounts):
    try:
        r = client.post(f"{API}/admin/users/{INACTIVE_ID}/active", headers=admin_headers, json={"is_active": True})
        assert r.status_code == 200 and r.json()["is_active"] is True
        # đã mở khóa -> token của tài khoản đó dùng được
        assert client.get(f"{API}/auth/me", headers=bearer(INACTIVE_ID, "ADMIN")).status_code == 200
        r = client.post(f"{API}/admin/users/{INACTIVE_ID}/active", headers=admin_headers, json={"is_active": False})
        assert r.json()["is_active"] is False
        assert client.get(f"{API}/auth/me", headers=bearer(INACTIVE_ID, "ADMIN")).status_code == 401
    finally:
        db.execute("UPDATE analytics.app_user SET is_active = FALSE WHERE user_id = %s", (INACTIVE_ID,))


def test_admin_cannot_lock_self_or_reset_own_password(client, admin_headers):
    assert client.post(f"{API}/admin/users/{ADMIN_ID}/active", headers=admin_headers,
                       json={"is_active": False}).status_code == 409
    assert client.post(f"{API}/admin/users/{ADMIN_ID}/reset-password", headers=admin_headers).status_code == 409


def test_unknown_user_returns_404(client, admin_headers):
    assert client.post(f"{API}/admin/users/987654/active", headers=admin_headers,
                       json={"is_active": True}).status_code == 404
    assert client.post(f"{API}/admin/users/987654/reset-password", headers=admin_headers).status_code == 404


def test_reset_password_issues_usable_temporary_password(client, db, admin_headers, accounts):
    try:
        db.execute("UPDATE analytics.app_user SET is_active = TRUE WHERE user_id = %s", (INACTIVE_ID,))
        r = client.post(f"{API}/admin/users/{INACTIVE_ID}/reset-password", headers=admin_headers)
        assert r.status_code == 200
        temp = r.json()["temporary_password"]
        assert validate_new_password(temp) is None and len(temp) == 12
        assert _login(client, INACTIVE_USERNAME, temp).status_code == 200
    finally:
        db.execute("UPDATE analytics.app_user SET is_active = FALSE WHERE user_id = %s", (INACTIVE_ID,))


# ----------------------------------------------------------------------------- nhật ký ETL, danh mục
def test_etl_runs(client, db, admin_headers):
    body = client.get(f"{API}/admin/etl/runs", params={"limit": 5}, headers=admin_headers).json()
    total = db.execute("SELECT COUNT(*) FROM analytics.etl_run_log").fetchone()[0]
    assert body["total"] == total and len(body["items"]) == min(5, total)
    started = [r["started_at"] for r in body["items"]]
    assert started == sorted(started, reverse=True)
    ok = client.get(f"{API}/admin/etl/runs", params={"status": "SUCCESS"}, headers=admin_headers).json()
    assert all(r["status"] == "SUCCESS" for r in ok["items"])
    assert client.get(f"{API}/admin/etl/runs", params={"status": "DONE"}, headers=admin_headers).status_code == 422


def test_catalog_lists_every_course_with_teacher_names(client, admin_headers, courses):
    body = client.get(f"{API}/admin/catalog/courses", headers=admin_headers).json()
    assert {c["course_id"] for c in body["items"]} == {c["course_id"] for c in courses}
    by_id = {c["course_id"]: c for c in body["items"]}
    for course in courses:
        item = by_id[course["course_id"]]
        assert [t["user_id"] for t in item["teachers"]] == list(course["teacher_ids"])
        assert item["enrolled"] == course["enrolled"]


# ----------------------------------------------------------------------------- API sao lưu: ràng buộc đầu vào
@pytest.mark.parametrize("name", ["..%2F.env", "lms_analytics_x.zip", "bao_cao.zip", "lms_analytics_20260101_000000.zip"])
def test_backup_names_outside_pattern_or_missing_are_404(client, admin_headers, name):
    assert client.get(f"{API}/admin/backups/{name}/download", headers=admin_headers).status_code == 404
    assert client.delete(f"{API}/admin/backups/{name}", headers=admin_headers).status_code == 404


def test_restore_requires_exact_confirmation(client, admin_headers):
    r = client.post(f"{API}/admin/backups/lms_analytics_20260101_000000.zip/restore", headers=admin_headers,
                    json={"confirm_name": "lms_analytics_20260101_000001.zip"})
    assert r.status_code == 422
