"""
Hàng đợi gửi tin trên CSDL phân tích thật (kế hoạch v1.2 Mục 5.12): chống trùng, thử lại theo lịch 1–5–15 phút rồi
thành công, dừng sau số lần thử tối đa, lỗi vĩnh viễn FAILED ngay, ghi nhật ký can thiệp liên kết với tin.

Lỗi được giả lập ở đúng hàm gửi email của hệ thống (common.messaging.outbox.send_email); lần gửi thành công đi qua
đường gửi thật ở chế độ FILE (ghi file .eml). Mọi tin do kiểm thử tạo có khóa bắt đầu bằng "pytest-queue-" và được dọn.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import psycopg
import pytest

from backend.app.core.db import get_engine
from common.messaging import outbox
from common.messaging.config import MessagingSettings
from common.messaging.email import DeliveryError
from common.settings import resolve_as_of
from database.config import load_db_config

KEY = "pytest-queue-"


@pytest.fixture(scope="module")
def db():
    with psycopg.connect(**load_db_config("ANALYTICS_DB").conninfo(application_name="lms-outbox-tests"),
                         autocommit=True) as conn:
        yield conn
        conn.execute("""DELETE FROM analytics.intervention_log WHERE outbound_id IN
                        (SELECT message_id FROM analytics.outbound_message WHERE idempotency_key LIKE %s)""", (KEY + "%",))
        conn.execute("DELETE FROM analytics.outbound_message WHERE idempotency_key LIKE %s", (KEY + "%",))


@pytest.fixture(scope="module")
def target(db):
    """Một sinh viên có email trong snapshot mới nhất và giảng viên của môn (người gửi)."""
    row = db.execute("""
        SELECT r.course_id, r.user_id, r.email, r.student_name, r.teacher_ids[1]
        FROM analytics.fact_student_risk_summary r
        WHERE r.snapshot_date = %s AND r.email IS NOT NULL AND cardinality(r.teacher_ids) > 0
          AND EXISTS (SELECT 1 FROM analytics.app_user u WHERE u.user_id = r.teacher_ids[1])
        ORDER BY r.course_id, r.user_id LIMIT 1""", (resolve_as_of().date(),)).fetchone()
    assert row, "Cần dữ liệu ETL tại AS_OF và tài khoản giảng viên (cli sync-users)"
    return dict(course_id=row[0], user_id=row[1], email=row[2], name=row[3], sender=row[4])


@pytest.fixture()
def settings(tmp_path):
    return MessagingSettings(mail_transport="file", mail_file_dir=str(tmp_path))


def _enqueue(target, key: str) -> int | None:
    with get_engine().begin() as conn:
        return outbox.enqueue(conn, course_id=target["course_id"], user_id=target["user_id"],
                              sender_id=target["sender"], origin="MANUAL", channel="EMAIL", recipient=target["email"],
                              recipient_name=target["name"], subject="[pytest] hàng đợi", body="Nội dung kiểm thử",
                              status="QUEUED", idempotency_key=key)


def _row(db, mid):
    return db.execute("""SELECT status, attempts, next_attempt_at, last_error, provider_ref, intervention_id,
                                (next_attempt_at - now()) AS wait
                         FROM analytics.outbound_message WHERE message_id = %s""", (mid,)).fetchone()


def _make_due(db, mid):
    db.execute("UPDATE analytics.outbound_message SET next_attempt_at = now() - interval '1 second' "
               "WHERE message_id = %s", (mid,))


def test_same_idempotency_key_creates_one_message(db, target):
    key = KEY + uuid.uuid4().hex
    first = _enqueue(target, key)
    assert first is not None
    assert _enqueue(target, key) is None
    db.execute("UPDATE analytics.outbound_message SET status = 'CANCELLED' WHERE message_id = %s", (first,))


def test_temporary_error_is_retried_on_schedule_then_sent(db, target, settings, monkeypatch, tmp_path):
    real_send = outbox.send_email
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise DeliveryError("Máy chủ thư tạm thời không nhận (451 4.3.0 thử lại sau)", permanent=False, code="451")
        return real_send(*args, **kwargs)

    monkeypatch.setattr(outbox, "send_email", flaky)
    mid = _enqueue(target, KEY + uuid.uuid4().hex)
    first = outbox.send_now(get_engine(), settings, [mid])
    assert (first["sent"], first["retry"], first["failed"]) == (0, 1, 0)
    status, attempts, next_at, error, ref, _, wait = _row(db, mid)
    assert (status, attempts, ref) == ("QUEUED", 1, None) and "451" in error
    assert timedelta(seconds=50) < wait <= timedelta(seconds=outbox.RETRY_DELAYS[0])   # hẹn thử lại sau 1 phút

    # Chưa tới hạn: job message_dispatch không lấy tin này
    assert mid not in [r["message_id"] for r in outbox.dispatch_due(get_engine(), settings)["results"]]
    _make_due(db, mid)
    second = outbox.dispatch_due(get_engine(), settings)
    assert any(r["message_id"] == mid and r["status"] == "SENT" for r in second["results"])
    status, attempts, next_at, error, ref, intervention_id, _ = _row(db, mid)
    assert (status, attempts, next_at, error) == ("SENT", 2, None, None)
    assert ref and any(ref in f.read_text(encoding="utf-8", errors="replace") for f in tmp_path.glob("*.eml"))
    action = db.execute("SELECT action_type, outbound_id FROM analytics.intervention_log WHERE id = %s",
                        (intervention_id,)).fetchone()
    assert action == ("EMAIL", mid)


def test_retries_stop_after_schedule_is_exhausted(db, target, settings, monkeypatch):
    def always_down(*args, **kwargs):
        raise DeliveryError("Không kết nối được máy chủ thư", permanent=False, code="connect")

    monkeypatch.setattr(outbox, "send_email", always_down)
    mid = _enqueue(target, KEY + uuid.uuid4().hex)
    waits = []
    for attempt in range(1, len(outbox.RETRY_DELAYS) + 2):
        if attempt > 1:
            _make_due(db, mid)
        outbox.send_now(get_engine(), settings, [mid])
        status, attempts, _, _, _, _, wait = _row(db, mid)
        assert attempts == attempt
        if attempt <= len(outbox.RETRY_DELAYS):
            assert status == "QUEUED"
            waits.append(round(wait.total_seconds() / 60))
    assert waits == [1, 5, 15]
    assert status == "FAILED"


def test_permanent_error_fails_immediately_without_retry(db, target, settings, monkeypatch):
    def rejected(*args, **kwargs):
        raise DeliveryError("Địa chỉ người nhận không tồn tại (550 5.1.1)", permanent=True, code="550")

    monkeypatch.setattr(outbox, "send_email", rejected)
    mid = _enqueue(target, KEY + uuid.uuid4().hex)
    result = outbox.send_now(get_engine(), settings, [mid])
    assert (result["sent"], result["retry"], result["failed"]) == (0, 0, 1)
    status, attempts, next_at, error, *_ = _row(db, mid)
    assert (status, attempts, next_at) == ("FAILED", 1, None) and "không tồn tại" in error
