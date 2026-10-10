"""Tài khoản Dashboard (analytics.app_user)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Connection, text

from backend.app.core.db import fetch_all, fetch_one


def find_by_username(conn: Connection, username: str) -> dict | None:
    return fetch_one(conn, """
        SELECT user_id, username, full_name, email, role, password_hash, is_active
        FROM analytics.app_user WHERE lower(username) = lower(:username)""", {"username": username})


def find_by_id(conn: Connection, user_id: int) -> dict | None:
    return fetch_one(conn, """
        SELECT user_id, username, full_name, email, role, password_hash, is_active
        FROM analytics.app_user WHERE user_id = :user_id""", {"user_id": user_id})


def record_login(conn: Connection, user_id: int) -> None:
    conn.execute(text("UPDATE analytics.app_user SET last_login_at = now() WHERE user_id = :id"), {"id": user_id})
    conn.commit()


def set_password_hash(conn: Connection, user_id: int, password_hash: str) -> None:
    """Đổi mật khẩu và đánh dấu thời điểm đổi -> mọi token cấp trước đó mất hiệu lực."""
    conn.execute(text("""UPDATE analytics.app_user SET password_hash = :hash, password_changed_at = now()
                          WHERE user_id = :id"""), {"hash": password_hash, "id": user_id})
    conn.commit()


def set_active(conn: Connection, user_id: int, active: bool) -> dict | None:
    row = fetch_one(conn, """
        UPDATE analytics.app_user SET is_active = :active WHERE user_id = :user_id
        RETURNING user_id, username, is_active""", {"user_id": user_id, "active": active})
    conn.commit()
    return row


def list_users(conn: Connection, today: date) -> list[dict]:
    """Mọi tài khoản kèm số môn giảng viên đang phụ trách (theo dòng tiến độ mới nhất của từng môn)."""
    return fetch_all(conn, """
        WITH latest AS (
            SELECT DISTINCT ON (course_id) course_id, teacher_ids
            FROM analytics.fact_course_progress_daily
            WHERE stat_date <= :today
            ORDER BY course_id, stat_date DESC)
        SELECT u.user_id, u.username, u.full_name, u.email, u.role, u.is_active,
               u.last_login_at, u.password_changed_at, u.created_at,
               (SELECT COUNT(*) FROM latest l WHERE u.user_id = ANY(l.teacher_ids)) AS course_count
        FROM analytics.app_user u
        ORDER BY u.role, u.user_id""", {"today": today})
