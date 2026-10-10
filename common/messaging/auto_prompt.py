"""
Nhắc tự động (chức năng 2): đánh giá quy tắc trên snapshot rủi ro mới nhất và tạo tin trong hàng đợi.

    INACTIVE_DAYS    {"days": n}        không vào môn từ n ngày hoặc chưa từng vào
    BECAME_RED       {}                 Nguy cơ cao ở snapshot mới nhất, khác Nguy cơ cao ở snapshot liền trước
    MISSED_DEADLINE  {"days_after": n}  có bài đã tới hạn chưa nộp, hạn nộp đúng n ngày trước ngày snapshot

Chống gửi dồn: mỗi sinh viên nhận tối đa 1 tin của cùng quy tắc trong cooldown_days (tính theo thời gian thực);
khóa chống trùng auto:{quy tắc}:{SV}:{kênh}:{ngày snapshot} bảo đảm chạy lại job không tạo tin lặp.
Chế độ AUTO: tin vào hàng đợi (QUEUED, hẹn qua giờ yên lặng); REVIEW: chờ giảng viên duyệt (PENDING_REVIEW).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy import Connection, text

from common.messaging import compose
from common.messaging.config import CHANNEL_EMAIL, MessagingSettings
from common.messaging.outbox import enqueue, next_allowed_time, now

TRIGGERS = {
    "INACTIVE_DAYS": dict(name="Không truy cập quá n ngày", param="days", lo=3, hi=30, default=7),
    "BECAME_RED": dict(name="Vừa chuyển sang Nguy cơ cao", param=None),
    "MISSED_DEADLINE": dict(name="Quá hạn nộp bài chưa nộp", param="days_after", lo=0, hi=7, default=1),
}


def _due_date(value) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date() if isinstance(value, str) else value.date()


def matching(conn: Connection, rule: dict, snapshot_date: date) -> list[dict]:
    """Sinh viên khớp điều kiện của quy tắc tại snapshot (chưa xét thời gian chờ)."""
    rows = compose.students(conn, rule["course_id"], snapshot_date)
    params = rule.get("params") or {}
    trig = rule["trigger_type"]
    if trig == "INACTIVE_DAYS":
        days = int(params.get("days", 7))
        return [r for r in rows if r["days_since_last_access"] is None or r["days_since_last_access"] >= days]
    if trig == "BECAME_RED":
        prev_date = conn.execute(text("""SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary
                                         WHERE course_id = :c AND snapshot_date < :d"""),
                                 {"c": rule["course_id"], "d": snapshot_date}).scalar()
        prev = {} if prev_date is None else dict(conn.execute(text(
            """SELECT user_id, risk_level FROM analytics.fact_student_risk_summary
               WHERE course_id = :c AND snapshot_date = :d"""), {"c": rule["course_id"], "d": prev_date}).all())
        return [r for r in rows if r["risk_level"] == "RED" and prev.get(r["user_id"]) != "RED"]
    if trig == "MISSED_DEADLINE":
        target = snapshot_date - timedelta(days=int(params.get("days_after", 1)))
        return [r for r in rows if any(a.get("status") == "missing" and _due_date(a.get("duedate")) == target
                                       for a in r["assignment_detail"])]
    raise ValueError(f"Loại quy tắc không hỗ trợ: {trig}")


def recently_sent(conn: Connection, rule: dict) -> set[int]:
    since = now() - timedelta(days=int(rule["cooldown_days"]))
    return {int(u) for (u,) in conn.execute(text("""
        SELECT DISTINCT user_id FROM analytics.outbound_message
        WHERE rule_id = :r AND created_at >= :since AND status NOT IN ('CANCELLED', 'FAILED')"""),
        {"r": rule["rule_id"], "since": since}).all()}


def sent_today(conn: Connection, course_id: int) -> int:
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(conn.execute(text("""SELECT COUNT(*) FROM analytics.outbound_message
                                    WHERE course_id = :c AND origin = 'AUTO' AND created_at >= :start"""),
                            {"c": course_id, "start": start}).scalar())


def evaluate(conn: Connection, rule: dict, today: date, settings: MessagingSettings, *, dry_run: bool) -> dict:
    """Đánh giá một quy tắc. dry_run=True: chỉ trả danh sách, không tạo tin."""
    snapshot = compose.latest_snapshot(conn, rule["course_id"], today)
    if snapshot is None:
        return dict(snapshot_date=None, matched=0, skipped_cooldown=0, created=0, recipients=[])
    matched = matching(conn, rule, snapshot)
    cooldown = recently_sent(conn, rule)
    targets = [r for r in matched if r["user_id"] not in cooldown]
    recipients = [dict(user_id=r["user_id"], student_code=r["student_code"], student_name=r["student_name"],
                       risk_level=r["risk_level"]) for r in targets]
    result = dict(snapshot_date=snapshot, matched=len(matched), skipped_cooldown=len(matched) - len(targets),
                  created=0, recipients=recipients)
    if dry_run or not targets:
        return result

    tpl = compose.template(conn, rule["template_id"])
    sender = compose.teacher(conn, rule["created_by"])
    course = dict(shortname=targets[0]["course_shortname"], fullname=targets[0]["course_fullname"])
    budget = max(0, settings.daily_limit_per_course - sent_today(conn, rule["course_id"]))
    status = "QUEUED" if rule["send_mode"] == "AUTO" else "PENDING_REVIEW"
    when = next_allowed_time(now(), settings) if status == "QUEUED" else None
    created = 0
    for d in compose.drafts_for(targets, rule["channels"], tpl["subject"], tpl["body"], course=course, sender=sender,
                                today=today):
        if d.error or created >= budget:
            continue
        body = d.body if d.channel == CHANNEL_EMAIL else compose.moodle_text(d.subject, d.body)
        mid = enqueue(conn, course_id=rule["course_id"], user_id=d.user_id, sender_id=rule["created_by"],
                      origin="AUTO", channel=d.channel, recipient=d.recipient, recipient_name=d.student_name,
                      subject=d.subject, body=body, status=status, rule_id=rule["rule_id"],
                      template_id=rule["template_id"], risk_level=d.risk_level, snapshot_date=d.snapshot_date,
                      next_attempt_at=when,
                      idempotency_key=f"auto:{rule['rule_id']}:{d.user_id}:{d.channel}:{d.snapshot_date}")
        created += mid is not None
    result["created"] = created
    conn.execute(text("""UPDATE analytics.auto_prompt_rule SET last_run_at = now(), last_run_summary = CAST(:s AS jsonb)
                         WHERE rule_id = :r"""),
                 {"r": rule["rule_id"], "s": json.dumps({k: v for k, v in result.items() if k != "recipients"},
                                                       default=str)})
    return result


def active_rules(conn: Connection, course_id: int | None = None) -> list[dict]:
    only = "AND course_id = :c" if course_id is not None else ""
    rows = conn.execute(text(f"""SELECT * FROM analytics.auto_prompt_rule WHERE is_active {only} ORDER BY rule_id"""),
                        {"c": course_id} if course_id is not None else {}).mappings().all()
    return [dict(r) for r in rows]
