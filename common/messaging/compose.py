"""
Soạn tin cho một nhóm sinh viên của một môn từ snapshot rủi ro mới nhất – dùng chung cho giảng viên gửi tay
(backend) và nhắc tự động (ETL). Người nhận lấy từ dữ liệu Moodle đã nạp: email = mdl_user.email,
Moodle = mdl_user.id (user_id trong bảng fact) – nên dữ liệu thật dùng được ngay.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, text

from common.messaging.config import CHANNEL_EMAIL, CHANNEL_MOODLE
from common.messaging.templates import Rendered, TemplateError, build_context, render

STUDENT_COLUMNS = """r.user_id, r.student_code, r.student_name, r.email, r.risk_level, r.risk_score, r.risk_reasons,
       r.score_attendance, r.score_inactivity, r.score_assignment, r.total_sessions, r.absent_sessions,
       r.absence_rate, r.days_since_last_access, r.total_assignments, r.missing_assignments_count,
       r.assignment_detail, r.snapshot_date, r.course_shortname, r.course_fullname"""


def _json(value):
    return value if not isinstance(value, str) else json.loads(value)


def latest_snapshot(conn: Connection, course_id: int, today: date) -> date | None:
    return conn.execute(text("""SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary
                                WHERE course_id = :c AND snapshot_date <= :today"""),
                        {"c": course_id, "today": today}).scalar()


def students(conn: Connection, course_id: int, snapshot_date: date, user_ids: Iterable[int] | None = None) -> list[dict]:
    params: dict = {"c": course_id, "d": snapshot_date}
    only = ""
    if user_ids is not None:
        params["ids"] = [int(u) for u in user_ids]
        only = "AND r.user_id = ANY(CAST(:ids AS integer[]))"
    rows = [dict(r) for r in conn.execute(text(f"""
        SELECT {STUDENT_COLUMNS} FROM analytics.fact_student_risk_summary r
        WHERE r.course_id = :c AND r.snapshot_date = :d {only}
        ORDER BY r.student_code NULLS LAST, r.user_id"""), params).mappings()]
    for r in rows:
        r["risk_reasons"] = _json(r["risk_reasons"])
        r["assignment_detail"] = _json(r["assignment_detail"])
    return rows


def teacher(conn: Connection, user_id: int) -> dict:
    row = conn.execute(text("SELECT user_id, full_name, email, salutation FROM analytics.app_user WHERE user_id = :u"),
                       {"u": user_id}).mappings().first()
    if row is None:
        raise TemplateError("Không tìm thấy tài khoản người gửi")
    return dict(row)


def template(conn: Connection, template_id: int) -> dict | None:
    row = conn.execute(text("""SELECT template_id, owner_id, code, name, purpose, subject, body, is_active
                               FROM analytics.message_template WHERE template_id = :t"""),
                       {"t": template_id}).mappings().first()
    return dict(row) if row else None


@dataclass
class Draft:
    user_id: int
    student_code: str | None
    student_name: str
    channel: str
    recipient: str | None
    subject: str | None
    body: str
    risk_level: str
    snapshot_date: date
    error: str | None = None


def recipient_of(student: dict, channel: str) -> str | None:
    if channel == CHANNEL_EMAIL:
        email = (student.get("email") or "").strip()
        return email if "@" in email else None
    return str(student["user_id"])


def drafts_for(students_rows: list[dict], channels: Iterable[str], subject: str, body: str, *, course: dict,
               sender: dict, today: date, contact_days: int = 7) -> list[Draft]:
    """Bản tin cho từng (sinh viên, kênh). Lỗi điền mẫu/thiếu địa chỉ được ghi vào Draft.error, không ném."""
    out: list[Draft] = []
    for s in students_rows:
        try:
            rendered: Rendered | None = render(subject, body, build_context(s, course, sender, today=today,
                                                                            contact_days=contact_days))
            err = None
        except TemplateError as exc:
            rendered, err = None, str(exc)
        for ch in channels:
            recipient = recipient_of(s, ch)
            error = err or (None if recipient else "Sinh viên chưa có địa chỉ email trong Moodle")
            out.append(Draft(user_id=int(s["user_id"]), student_code=s.get("student_code"),
                             student_name=s["student_name"], channel=ch, recipient=recipient,
                             subject=(rendered.subject if rendered else None),
                             body=(rendered.body if rendered else ""), risk_level=s["risk_level"],
                             snapshot_date=s["snapshot_date"], error=error))
    return out


def moodle_text(subject: str | None, body: str) -> str:
    """Tin nhắn Moodle không có tiêu đề – đưa tiêu đề email (nếu có) lên dòng đầu."""
    return f"{subject}\n\n{body}" if subject else body


CHANNELS = (CHANNEL_MOODLE, CHANNEL_EMAIL)
