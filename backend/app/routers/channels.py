"""
Hệ thống › Kênh gửi tin (quản trị viên): cấu hình hiện hành (đã che bí mật), chế độ gửi hiệu lực, kiểm tra kết nối
(kết quả được lưu – là điều kiện 3 của chốt chặn gửi thật), gửi thử email, thống kê gửi.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Connection

from backend.app.core.db import fetch_all, get_conn
from backend.app.core.security import CurrentUser
from backend.app.routers.deps import admin_user
from common.messaging.config import CHANNEL_EMAIL, CHANNEL_MOODLE, MODE_FILE, MessagingConfigError, load_settings
from common.messaging.email import DeliveryError, check_smtp, send_email
from common.messaging.moodle import MoodleClient
from common.messaging.outbox import effective_modes, record_check

router = APIRouter(prefix="/admin/channels", tags=["Kênh gửi tin"], dependencies=[Depends(admin_user)])


def _settings():
    try:
        return load_settings()
    except MessagingConfigError as exc:
        raise HTTPException(503, f"Cấu hình kênh gửi tin chưa đúng: {exc}") from exc


@router.get("", summary="Cấu hình kênh gửi tin, chế độ hiệu lực, lần kiểm tra gần nhất, thống kê 30 ngày")
def status(conn: Connection = Depends(get_conn)) -> dict:
    settings = _settings()
    modes = effective_modes(conn, settings)
    checks = {r["channel"]: r for r in fetch_all(conn, """
        SELECT c.channel, c.ok, c.detail, c.checked_at, u.full_name AS checked_by_name,
               c.config_fingerprint = :fe AS email_current, c.config_fingerprint = :fm AS moodle_current
        FROM analytics.channel_check c LEFT JOIN analytics.app_user u ON u.user_id = c.checked_by""",
        {"fe": settings.fingerprint(CHANNEL_EMAIL), "fm": settings.fingerprint(CHANNEL_MOODLE)})}
    stats = fetch_all(conn, """
        SELECT channel, origin, status, COUNT(*) AS n FROM analytics.outbound_message
        WHERE created_at > now() - interval '30 days' GROUP BY channel, origin, status ORDER BY 1, 2, 3""")
    for ch, c in checks.items():
        email_current, moodle_current = c.pop("email_current"), c.pop("moodle_current")
        c["current_config"] = email_current if ch == CHANNEL_EMAIL else moodle_current
    return {"config": settings.describe(),
            "channels": {ch: {"mode": m, "warnings": w, "last_check": checks.get(ch)} for ch, (m, w) in modes.items()},
            "stats": stats}


@router.post("/test-moodle", summary="Kiểm tra Moodle Web Service (core_webservice_get_site_info)")
def test_moodle(user: CurrentUser = Depends(admin_user), conn: Connection = Depends(get_conn)) -> dict:
    settings = _settings()
    try:
        info = MoodleClient(settings).site_info()
    except DeliveryError as exc:
        record_check(conn, settings, CHANNEL_MOODLE, False, {"error": str(exc)}, user.user_id)
        conn.commit()
        return {"ok": False, "error": str(exc)}
    ok = not info["missing_functions"]
    detail = {k: info.get(k) for k in ("sitename", "release", "version", "username", "userid", "siteurl")}
    detail["missing_functions"] = info["missing_functions"]
    record_check(conn, settings, CHANNEL_MOODLE, ok, detail, user.user_id)
    conn.commit()
    return {"ok": ok, **detail,
            "error": None if ok else "Thiếu quyền gọi hàm: " + ", ".join(info["missing_functions"])}


class TestEmailIn(BaseModel):
    to: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/test-email", summary="Kiểm tra máy chủ thư và gửi một email thử (theo đúng chế độ đang hiệu lực)")
def test_email(body: TestEmailIn, user: CurrentUser = Depends(admin_user), conn: Connection = Depends(get_conn)) -> dict:
    settings = _settings()
    if settings.mail_transport == "off":
        return {"ok": False, "error": "Kênh email đang tắt (MAIL_TRANSPORT=off)"}
    try:
        detail = check_smtp(settings) if settings.mail_transport == "smtp" else {"transport": "file"}
        # Email thử gửi thẳng tới địa chỉ quản trị nhập (không phải sinh viên) – chế độ FILE vẫn ghi file
        mode = MODE_FILE if settings.mail_transport == "file" else "LIVE"
        delivery = send_email(settings, mode, to=str(body.to), to_name=user.full_name or "", reply_to=None,
                              subject="[LMS Analytics] Email thử kênh gửi tin",
                              body=f"Email thử do {user.full_name or user.username} gửi từ trang Hệ thống › Kênh gửi tin.\n"
                                   "Nếu bạn nhận được email này, cấu hình máy chủ thư của LMS Analytics hoạt động.",
                              tracking_id=f"test-{uuid.uuid4().hex[:12]}")
    except DeliveryError as exc:
        record_check(conn, settings, CHANNEL_EMAIL, False, {"error": str(exc)}, user.user_id)
        conn.commit()
        return {"ok": False, "error": str(exc)}
    detail.update(message_id=delivery.provider_ref, delivered_to=delivery.delivered_to, **delivery.meta)
    record_check(conn, settings, CHANNEL_EMAIL, True, detail, user.user_id)
    conn.commit()
    return {"ok": True, **detail}
