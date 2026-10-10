"""
Hàng đợi gửi tin (analytics.outbound_message) – dùng chung cho backend (giảng viên bấm gửi: gửi ngay) và
ETL scheduler (job message_dispatch mỗi phút: gửi tin đến hạn, thử lại lỗi tạm thời).

Vòng đời: PENDING_REVIEW (chờ GV duyệt) -> QUEUED -> SENDING -> SENT | FAILED (| CANCELLED)
- Khóa chống trùng idempotency_key UNIQUE: tạo lại cùng khóa không sinh tin mới.
- Lấy việc bằng FOR UPDATE SKIP LOCKED nên nhiều tiến trình gửi song song không gửi trùng.
- Lỗi tạm thời thử lại sau 1, 5, 15 phút; lỗi vĩnh viễn (địa chỉ sai, Moodle từ chối) -> FAILED ngay.
- Gửi thành công: lưu mã xác nhận (Message-ID / msgid) và ghi một mục nhật ký can thiệp liên kết với tin.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import Connection, Engine, text

from common.messaging.config import (CHANNEL_EMAIL, CHANNEL_MOODLE, MODE_STUB, MessagingSettings, email_mode,
                                     moodle_mode)
from common.messaging.email import Delivery, DeliveryError, send_email
from common.messaging.moodle import MoodleClient
from common.settings import TZ

log = logging.getLogger("messaging")
RETRY_DELAYS = (60, 300, 900)
ACTION_OF_CHANNEL = {CHANNEL_MOODLE: "MESSAGE", CHANNEL_EMAIL: "EMAIL"}
CHANNEL_LABEL = {CHANNEL_MOODLE: "tin nhắn Moodle", CHANNEL_EMAIL: "email"}


def now() -> datetime:
    """Gửi tin luôn theo thời gian thực (không theo AS_OF của dữ liệu demo)."""
    return datetime.now(TZ)


# ----------------------------------------------------------------------------- trạng thái kênh
def channel_check_ok(conn: Connection, settings: MessagingSettings, channel: str) -> bool:
    row = conn.execute(text("SELECT ok, config_fingerprint FROM analytics.channel_check WHERE channel = :c"),
                       {"c": channel}).first()
    return bool(row and row.ok and row.config_fingerprint == settings.fingerprint(channel))


def effective_modes(conn: Connection, settings: MessagingSettings) -> dict[str, tuple[str | None, list[str]]]:
    return {CHANNEL_EMAIL: email_mode(settings, channel_check_ok(conn, settings, CHANNEL_EMAIL)),
            CHANNEL_MOODLE: moodle_mode(settings, channel_check_ok(conn, settings, CHANNEL_MOODLE))}


def record_check(conn: Connection, settings: MessagingSettings, channel: str, ok: bool, detail: dict,
                 checked_by: int | None) -> None:
    conn.execute(text("""
        INSERT INTO analytics.channel_check (channel, ok, config_fingerprint, detail, checked_by, checked_at)
        VALUES (:c, :ok, :fp, CAST(:detail AS jsonb), :by, now())
        ON CONFLICT (channel) DO UPDATE SET ok = EXCLUDED.ok, config_fingerprint = EXCLUDED.config_fingerprint,
            detail = EXCLUDED.detail, checked_by = EXCLUDED.checked_by, checked_at = EXCLUDED.checked_at"""),
        {"c": channel, "ok": ok, "fp": settings.fingerprint(channel),
         "detail": json.dumps(detail, ensure_ascii=False, default=str), "by": checked_by})


# ----------------------------------------------------------------------------- tạo tin
def in_quiet_hours(moment: datetime, settings: MessagingSettings) -> bool:
    start, end = settings.quiet_hours
    h = moment.hour
    return (start <= h or h < end) if start > end else (start <= h < end)


def next_allowed_time(moment: datetime, settings: MessagingSettings) -> datetime:
    """Tin TỰ ĐỘNG tạo trong giờ yên lặng được hẹn gửi 1 giờ sau khi khung yên lặng kết thúc (kế hoạch v1.2 Mục 5.7:
    khung 22-6 -> hẹn 07:00), để sinh viên không nhận tin ngay lúc 06:00."""
    if not in_quiet_hours(moment, settings):
        return moment
    target = moment.replace(hour=settings.quiet_hours[1], minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return target if target > moment else target + timedelta(days=1)


def enqueue(conn: Connection, *, course_id: int, user_id: int, sender_id: int, origin: str, channel: str,
            recipient: str, recipient_name: str | None, subject: str | None, body: str, status: str,
            idempotency_key: str, rule_id: int | None = None, template_id: int | None = None,
            risk_level: str | None = None, snapshot_date=None, next_attempt_at: datetime | None = None) -> int | None:
    """Tạo một tin; trả về message_id, hoặc None nếu khóa chống trùng đã tồn tại."""
    return conn.execute(text("""
        INSERT INTO analytics.outbound_message
            (course_id, user_id, sender_id, origin, rule_id, template_id, channel, recipient, recipient_name,
             subject, body, status, idempotency_key, risk_level_at_time, snapshot_date, next_attempt_at)
        VALUES (:course_id, :user_id, :sender_id, :origin, :rule_id, :template_id, :channel, :recipient,
                :recipient_name, :subject, :body, :status, :key, :risk_level, :snapshot_date, :next_attempt_at)
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING message_id"""),
        dict(course_id=course_id, user_id=user_id, sender_id=sender_id, origin=origin, rule_id=rule_id,
             template_id=template_id, channel=channel, recipient=recipient, recipient_name=recipient_name,
             subject=subject, body=body, status=status, key=idempotency_key, risk_level=risk_level,
             snapshot_date=snapshot_date, next_attempt_at=next_attempt_at)).scalar()


# ----------------------------------------------------------------------------- gửi
CLAIM_SQL = """
    UPDATE analytics.outbound_message o
    SET status = 'SENDING', updated_at = now()
    FROM analytics.app_user u
    WHERE o.message_id IN (
        SELECT message_id FROM analytics.outbound_message
        WHERE status = 'QUEUED' AND (next_attempt_at IS NULL OR next_attempt_at <= :now) {only}
        ORDER BY next_attempt_at NULLS FIRST, message_id
        FOR UPDATE SKIP LOCKED
        LIMIT :limit)
      AND u.user_id = o.sender_id
    RETURNING o.*, u.full_name AS sender_name, u.email AS sender_email"""


def claim(engine: Engine, *, limit: int = 50, message_ids: Iterable[int] | None = None) -> list:
    ids = list(message_ids) if message_ids is not None else None
    only = "AND message_id = ANY(CAST(:ids AS bigint[]))" if ids is not None else ""
    with engine.begin() as conn:
        return conn.execute(text(CLAIM_SQL.format(only=only)),
                            {"now": now(), "limit": limit, **({"ids": ids} if ids is not None else {})}).all()


def _deliver_one(row, settings: MessagingSettings, modes: dict) -> Delivery:
    mode, warnings = modes[row.channel]
    if mode is None:
        raise DeliveryError("Kênh " + CHANNEL_LABEL[row.channel] + " không dùng được: " + "; ".join(warnings),
                            permanent=True, code="channel_unavailable")
    tracking = f"lms-{row.message_id}"
    if row.channel == CHANNEL_EMAIL:
        return send_email(settings, mode, to=row.recipient, to_name=row.recipient_name or "", subject=row.subject or "",
                          body=row.body, reply_to=row.sender_email or None, reply_to_name=row.sender_name,
                          tracking_id=tracking)
    client = MoodleClient(settings)
    sent = client.send_one(int(row.recipient), row.body, tracking)
    meta = {"conversationid": sent.conversationid, "moodle_url": settings.moodle_public_url or settings.moodle_ws_url}
    base = meta["moodle_url"]
    # Liên kết xem tin như sinh viên thấy: hộp tin của máy chủ mô phỏng, hoặc trang hội thoại của Moodle thật
    meta["view_url"] = (f"{base}/stub/inbox?userid={row.recipient}" if mode == MODE_STUB
                        else f"{base}/message/index.php?id={row.recipient}")
    return Delivery(mode, str(sent.msgid), f"mdl_user.id={row.recipient}", meta)


def _intervention_text(row, delivery: Delivery) -> str:
    head = f"Đã gửi {CHANNEL_LABEL[row.channel]}"
    if row.subject:
        head += f": {row.subject}"
    return f"{head}\n{row.body}"[:2000]


def _record_success(conn: Connection, row, delivery: Delivery) -> None:
    intervention_id = conn.execute(text("""
        INSERT INTO analytics.intervention_log
            (course_id, user_id, teacher_id, action_type, content, risk_level_at_time, origin, outbound_id)
        VALUES (:course_id, :user_id, :teacher_id, :action, :content, :risk, :origin, :mid)
        RETURNING id"""),
        dict(course_id=row.course_id, user_id=row.user_id, teacher_id=row.sender_id,
             action=ACTION_OF_CHANNEL[row.channel], content=_intervention_text(row, delivery),
             risk=row.risk_level_at_time, origin=row.origin, mid=row.message_id)).scalar_one()
    conn.execute(text("""
        UPDATE analytics.outbound_message
        SET status = 'SENT', sent_at = now(), attempts = attempts + 1, provider_ref = :ref, delivery_mode = :mode,
            delivered_to = :to, provider_meta = CAST(:meta AS jsonb), last_error = NULL, next_attempt_at = NULL,
            intervention_id = :iid
        WHERE message_id = :mid"""),
        dict(ref=delivery.provider_ref[:255], mode=delivery.mode, to=delivery.delivered_to[:255],
             meta=json.dumps(delivery.meta, ensure_ascii=False, default=str), iid=intervention_id, mid=row.message_id))


def _record_failure(conn: Connection, row, error: DeliveryError) -> str:
    attempts = int(row.attempts) + 1
    retry = (not error.permanent) and attempts <= len(RETRY_DELAYS)
    status = "QUEUED" if retry else "FAILED"
    conn.execute(text("""
        UPDATE analytics.outbound_message
        SET status = :status, attempts = :attempts, last_error = :error,
            next_attempt_at = :next, provider_meta = CAST(:meta AS jsonb)
        WHERE message_id = :mid"""),
        dict(status=status, attempts=attempts, error=str(error)[:1000],
             next=now() + timedelta(seconds=RETRY_DELAYS[attempts - 1]) if retry else None,
             meta=json.dumps({"code": error.code, "permanent": error.permanent}), mid=row.message_id))
    return status


def deliver(engine: Engine, settings: MessagingSettings, rows: list) -> dict:
    """Gửi các tin đã được claim (trạng thái SENDING). Trả về thống kê và kết quả từng tin."""
    summary = {"sent": 0, "retry": 0, "failed": 0, "results": []}
    if not rows:
        return summary
    with engine.connect() as conn:
        modes = effective_modes(conn, settings)
    for row in rows:
        try:
            delivery = _deliver_one(row, settings, modes)
        except DeliveryError as exc:
            with engine.begin() as conn:
                status = _record_failure(conn, row, exc)
            summary["retry" if status == "QUEUED" else "failed"] += 1
            summary["results"].append(dict(message_id=row.message_id, status=status, error=str(exc)))
            log.warning("Gửi tin %s (%s) thất bại: %s", row.message_id, row.channel, exc)
            continue
        except Exception as exc:          # lỗi lập trình/không lường trước: coi là tạm thời, không làm sập job
            err = DeliveryError(f"Lỗi không xác định: {type(exc).__name__}", permanent=False)
            with engine.begin() as conn:
                status = _record_failure(conn, row, err)
            log.exception("Gửi tin %s lỗi không xác định", row.message_id)
            summary["retry" if status == "QUEUED" else "failed"] += 1
            summary["results"].append(dict(message_id=row.message_id, status=status, error=str(err)))
            continue
        with engine.begin() as conn:
            _record_success(conn, row, delivery)
        summary["sent"] += 1
        summary["results"].append(dict(message_id=row.message_id, status="SENT", provider_ref=delivery.provider_ref,
                                       delivery_mode=delivery.mode, delivered_to=delivery.delivered_to))
    return summary


def dispatch_due(engine: Engine, settings: MessagingSettings, *, limit: int = 100) -> dict:
    """Job message_dispatch: gửi các tin QUEUED đến hạn."""
    return deliver(engine, settings, claim(engine, limit=limit))


def send_now(engine: Engine, settings: MessagingSettings, message_ids: Iterable[int]) -> dict:
    """Giảng viên bấm gửi: gửi ngay các tin vừa tạo (tin lỗi tạm thời sẽ được job thử lại)."""
    ids = list(message_ids)
    return deliver(engine, settings, claim(engine, limit=len(ids) or 1, message_ids=ids)) if ids else \
        {"sent": 0, "retry": 0, "failed": 0, "results": []}
