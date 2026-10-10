"""Truy vấn cho Trung tâm can thiệp (chức năng 2): danh sách cần liên hệ, mẫu tin, lịch sử gửi, quy tắc nhắc tự động."""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import Connection, text

from backend.app.core.db import fetch_all, fetch_one, fetch_value
from backend.app.repositories._sql import LEVEL_RANK, offset, where

OUTBOX_COLUMNS = """o.message_id, o.course_id, o.user_id, o.sender_id, su.full_name AS sender_name, o.origin, o.rule_id,
       pr.name AS rule_name, o.template_id, o.channel, o.recipient, o.recipient_name, o.subject, o.body, o.status,
       o.attempts, o.next_attempt_at, o.last_error, o.delivery_mode, o.delivered_to, o.provider_ref, o.provider_meta,
       o.risk_level_at_time, o.snapshot_date, o.created_at, o.sent_at, o.intervention_id"""


def contact_list(conn: Connection, course_id: int, snapshot_date: date, levels: list[str], since: datetime,
                 include_contacted: bool) -> list[dict]:
    """SV Đỏ/Vàng của snapshot + lần liên hệ gần nhất (mọi giảng viên của môn); mặc định ẩn SV đã liên hệ từ `since`."""
    rows = fetch_all(conn, f"""
        WITH last_contact AS (
            SELECT DISTINCT ON (user_id) user_id, created_at, action_type, origin
            FROM analytics.intervention_log WHERE course_id = :c
            ORDER BY user_id, created_at DESC)
        SELECT r.user_id, r.student_code, r.student_name, r.email, r.risk_level, r.risk_score, r.risk_reasons,
               r.days_since_last_access, r.absent_sessions, r.total_sessions, r.missing_assignments_count,
               r.total_assignments, lc.created_at AS last_contact_at, lc.action_type AS last_contact_action,
               lc.origin AS last_contact_origin
        FROM analytics.fact_student_risk_summary r
        LEFT JOIN last_contact lc ON lc.user_id = r.user_id
        WHERE r.course_id = :c AND r.snapshot_date = :d AND r.risk_level = ANY(CAST(:levels AS text[]))
          AND (:all_rows OR lc.created_at IS NULL OR lc.created_at < :since)
        ORDER BY {LEVEL_RANK}, r.risk_score DESC, r.student_code""",
        {"c": course_id, "d": snapshot_date, "levels": levels, "since": since, "all_rows": include_contacted})
    for r in rows:
        reasons = r["risk_reasons"] if not isinstance(r["risk_reasons"], str) else json.loads(r["risk_reasons"])
        r["main_reason"] = "; ".join(reasons[:2]) if reasons else ""
    return rows


# ----------------------------------------------------------------------------- mẫu tin
def templates(conn: Connection, owner_id: int) -> list[dict]:
    return fetch_all(conn, """
        SELECT template_id, owner_id, code, name, purpose, subject, body, is_active, updated_at,
               owner_id IS NULL AS is_system
        FROM analytics.message_template
        WHERE is_active AND (owner_id IS NULL OR owner_id = :u)
        ORDER BY owner_id NULLS FIRST, template_id""", {"u": owner_id})


def template_of(conn: Connection, template_id: int) -> dict | None:
    return fetch_one(conn, "SELECT * FROM analytics.message_template WHERE template_id = :t", {"t": template_id})


def create_template(conn: Connection, owner_id: int, name: str, purpose: str, subject: str, body: str) -> int:
    code = f"U{owner_id}_{int(datetime.now().timestamp() * 1000)}"
    return int(fetch_value(conn, """
        INSERT INTO analytics.message_template (owner_id, code, name, purpose, subject, body)
        VALUES (:o, :code, :name, :purpose, :subject, :body) RETURNING template_id""",
        {"o": owner_id, "code": code, "name": name, "purpose": purpose, "subject": subject, "body": body}))


def update_template(conn: Connection, template_id: int, name: str, purpose: str, subject: str, body: str) -> None:
    conn.execute(text("""UPDATE analytics.message_template SET name = :name, purpose = :purpose, subject = :subject,
                         body = :body WHERE template_id = :t"""),
                 {"t": template_id, "name": name, "purpose": purpose, "subject": subject, "body": body})


def deactivate_template(conn: Connection, template_id: int) -> None:
    conn.execute(text("UPDATE analytics.message_template SET is_active = FALSE WHERE template_id = :t"),
                 {"t": template_id})


# ----------------------------------------------------------------------------- tin đã gửi
def messages(conn: Connection, course_id: int, *, status: str | None, origin: str | None, channel: str | None,
             user_id: int | None, page: int, page_size: int) -> tuple[list[dict], int]:
    conditions = ["o.course_id = :c"]
    params: dict = {"c": course_id}
    for key, value in (("status", status), ("origin", origin), ("channel", channel), ("user_id", user_id)):
        if value is not None:
            conditions.append(f"o.{key} = :{key}")
            params[key] = value
    cond = where(conditions)
    total = int(fetch_value(conn, f"SELECT COUNT(*) FROM analytics.outbound_message o WHERE {cond}", params))
    items = fetch_all(conn, f"""
        SELECT {OUTBOX_COLUMNS}
        FROM analytics.outbound_message o
        JOIN analytics.app_user su ON su.user_id = o.sender_id
        LEFT JOIN analytics.auto_prompt_rule pr ON pr.rule_id = o.rule_id
        WHERE {cond}
        ORDER BY o.created_at DESC, o.message_id DESC
        LIMIT :limit OFFSET :offset""", {**params, "limit": page_size, "offset": offset(page, page_size)})
    return items, total


def message_counts(conn: Connection, course_id: int) -> dict:
    rows = fetch_all(conn, """SELECT status, COUNT(*) AS n FROM analytics.outbound_message WHERE course_id = :c
                              GROUP BY status""", {"c": course_id})
    return {r["status"]: int(r["n"]) for r in rows}


def message_of(conn: Connection, course_id: int, message_id: int) -> dict | None:
    return fetch_one(conn, """SELECT * FROM analytics.outbound_message WHERE course_id = :c AND message_id = :m""",
                     {"c": course_id, "m": message_id})


def set_status(conn: Connection, message_id: int, from_statuses: tuple[str, ...], status: str,
               reset_attempts: bool = False) -> bool:
    extra = ", attempts = 0, last_error = NULL" if reset_attempts else ""
    return conn.execute(text(f"""
        UPDATE analytics.outbound_message SET status = :s, next_attempt_at = NULL{extra}
        WHERE message_id = :m AND status = ANY(CAST(:f AS text[]))"""),
        {"s": status, "m": message_id, "f": list(from_statuses)}).rowcount > 0


# ----------------------------------------------------------------------------- quy tắc nhắc tự động
def prompt_rules(conn: Connection, course_id: int) -> list[dict]:
    return fetch_all(conn, """
        SELECT r.*, t.name AS template_name, u.full_name AS created_by_name,
               (SELECT COUNT(*) FROM analytics.outbound_message o WHERE o.rule_id = r.rule_id AND o.status = 'SENT') AS sent,
               (SELECT COUNT(*) FROM analytics.outbound_message o
                WHERE o.rule_id = r.rule_id AND o.status = 'PENDING_REVIEW') AS pending_review
        FROM analytics.auto_prompt_rule r
        JOIN analytics.message_template t ON t.template_id = r.template_id
        JOIN analytics.app_user u ON u.user_id = r.created_by
        WHERE r.course_id = :c AND (r.is_active OR r.updated_at > now() - interval '30 days')
        ORDER BY r.rule_id""", {"c": course_id})


def prompt_rule(conn: Connection, course_id: int, rule_id: int) -> dict | None:
    return fetch_one(conn, "SELECT * FROM analytics.auto_prompt_rule WHERE course_id = :c AND rule_id = :r",
                     {"c": course_id, "r": rule_id})


def save_prompt_rule(conn: Connection, course_id: int, user_id: int, data: dict, rule_id: int | None = None) -> int:
    params = {"c": course_id, "u": user_id, "name": data["name"], "trigger": data["trigger_type"],
              "params": json.dumps(data.get("params") or {}), "channels": list(data["channels"]),
              "tpl": data["template_id"], "mode": data["send_mode"], "cooldown": data["cooldown_days"],
              "active": data.get("is_active", True), "r": rule_id}
    if rule_id is None:
        return int(fetch_value(conn, """
            INSERT INTO analytics.auto_prompt_rule (course_id, created_by, name, trigger_type, params, channels,
                                                    template_id, send_mode, cooldown_days, is_active)
            VALUES (:c, :u, :name, :trigger, CAST(:params AS jsonb), CAST(:channels AS text[]), :tpl, :mode, :cooldown,
                    :active)
            RETURNING rule_id""", params))
    conn.execute(text("""
        UPDATE analytics.auto_prompt_rule
        SET name = :name, trigger_type = :trigger, params = CAST(:params AS jsonb), channels = CAST(:channels AS text[]),
            template_id = :tpl, send_mode = :mode, cooldown_days = :cooldown, is_active = :active
        WHERE rule_id = :r AND course_id = :c"""), params)
    return rule_id
