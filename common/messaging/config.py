"""
Cấu hình kênh gửi tin (email, tin nhắn Moodle) và CHỐT CHẶN chế độ gửi thật.

Cùng một mã nguồn cho mọi môi trường – chỉ khác biến môi trường:
    MAIL_TRANSPORT      file | smtp | off          (mặc định file: ghi .eml, không cần máy chủ thư)
    MAIL_FILE_DIR       thư mục ghi .eml           (mặc định var/mail_outbox)
    SMTP_HOST, SMTP_PORT, SMTP_SECURITY (starttls | ssl | none), SMTP_USERNAME, SMTP_PASSWORD, SMTP_TIMEOUT
    MAIL_FROM, MAIL_FROM_NAME
    MAIL_DELIVERY       redirect | live            (mặc định redirect: mọi email về MAIL_REDIRECT_TO)
    MAIL_REDIRECT_TO    hộp thư kiểm thử
    MOODLE_WS_URL       gốc Moodle, vd https://lms.dlu.edu.vn hoặc http://127.0.0.1:8091 (Moodle mô phỏng)
    MOODLE_WS_TOKEN     token web service của tài khoản dịch vụ
    MOODLE_WS_ENV       stub | live                (Moodle mô phỏng hay Moodle thật của trường)
    MESSAGING_ALLOW_LIVE  true | false             (mặc định false)
    MESSAGING_QUIET_HOURS 22-6                     (không gửi TỰ ĐỘNG trong khung giờ này)
    MESSAGING_DAILY_LIMIT_PER_COURSE 300           (giới hạn tin tự động mỗi môn mỗi ngày)

Gửi tới người nhận THẬT (email sinh viên, Moodle của trường) chỉ khi đủ 3 điều kiện:
    1) MESSAGING_ALLOW_LIVE=true; 2) LMS_AS_OF trống (dữ liệu thật, thời gian thực);
    3) kết nối kênh đó đã được kiểm tra thành công với ĐÚNG cấu hình hiện tại (bảng analytics.channel_check).
Thiếu điều kiện nào: email tự hạ về chế độ chuyển hướng / ghi file; Moodle thật bị từ chối (Moodle mô phỏng vẫn dùng được).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from common.settings import PROJECT_ROOT, is_clock_frozen

MODE_FILE, MODE_REDIRECT, MODE_LIVE, MODE_STUB = "FILE", "REDIRECT", "LIVE", "STUB"
CHANNEL_EMAIL, CHANNEL_MOODLE = "EMAIL", "MOODLE"


class MessagingConfigError(RuntimeError):
    """Cấu hình kênh gửi tin sai hoặc thiếu – thông báo tiếng Việt, không chứa bí mật."""


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    return default if not raw else raw.lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise MessagingConfigError(f"{name} phải là số nguyên, nhận được {raw!r}") from exc


@dataclass(frozen=True)
class MessagingSettings:
    mail_transport: str = "file"
    mail_file_dir: str = str(PROJECT_ROOT / "var" / "mail_outbox")
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "starttls"
    smtp_username: str = ""
    smtp_password: str = field(default="", repr=False)
    smtp_timeout: int = 20
    mail_from: str = "canhbao.lms@dlu.edu.vn"
    mail_from_name: str = "Hệ thống cảnh báo học tập"
    mail_delivery: str = "redirect"
    mail_redirect_to: str = ""
    moodle_ws_url: str = ""
    moodle_public_url: str = ""      # địa chỉ Moodle mà TRÌNH DUYỆT mở được (liên kết hộp tin); mặc định = moodle_ws_url
    moodle_ws_token: str = field(default="", repr=False)
    moodle_ws_env: str = "stub"
    moodle_ws_timeout: int = 15
    allow_live: bool = False
    quiet_hours: tuple[int, int] = (22, 6)
    daily_limit_per_course: int = 300

    # ------------------------------------------------------------------ dấu vân tay cấu hình (không chứa bí mật)
    def fingerprint(self, channel: str) -> str:
        if channel == CHANNEL_EMAIL:
            raw = f"{self.mail_transport}|{self.smtp_host}|{self.smtp_port}|{self.smtp_security}|{self.smtp_username}|{self.mail_from}"
        else:
            raw = f"{self.moodle_ws_url}|{self.moodle_ws_env}|{hashlib.sha256(self.moodle_ws_token.encode()).hexdigest()[:12]}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def describe(self) -> dict:
        """Cấu hình hiện hành đã che bí mật (dùng cho trang Kênh gửi tin và lệnh messaging-check)."""
        return dict(
            mail_transport=self.mail_transport, mail_file_dir=self.mail_file_dir if self.mail_transport == "file" else None,
            smtp=(f"{self.smtp_host}:{self.smtp_port} ({self.smtp_security})" if self.mail_transport == "smtp" else None),
            smtp_username=_mask(self.smtp_username), smtp_password_set=bool(self.smtp_password),
            mail_from=f"{self.mail_from_name} <{self.mail_from}>", mail_delivery=self.mail_delivery,
            mail_redirect_to=self.mail_redirect_to or None,
            moodle_ws_url=self.moodle_ws_url or None, moodle_ws_env=self.moodle_ws_env,
            moodle_ws_token_set=bool(self.moodle_ws_token), allow_live=self.allow_live,
            clock_frozen=is_clock_frozen(), quiet_hours=f"{self.quiet_hours[0]:02d}:00–{self.quiet_hours[1]:02d}:00",
            daily_limit_per_course=self.daily_limit_per_course,
        )


def _mask(value: str) -> str | None:
    if not value:
        return None
    if "@" in value:
        name, domain = value.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return value[:2] + "***"


def load_settings() -> MessagingSettings:
    transport = _env("MAIL_TRANSPORT", "file").lower()
    if transport not in ("file", "smtp", "off"):
        raise MessagingConfigError("MAIL_TRANSPORT phải là file, smtp hoặc off")
    security = _env("SMTP_SECURITY", "starttls").lower()
    if security not in ("starttls", "ssl", "none"):
        raise MessagingConfigError("SMTP_SECURITY phải là starttls, ssl hoặc none")
    delivery = _env("MAIL_DELIVERY", "redirect").lower()
    if delivery not in ("redirect", "live"):
        raise MessagingConfigError("MAIL_DELIVERY phải là redirect hoặc live")
    moodle_env = _env("MOODLE_WS_ENV", "stub").lower()
    if moodle_env not in ("stub", "live"):
        raise MessagingConfigError("MOODLE_WS_ENV phải là stub hoặc live")
    quiet = _env("MESSAGING_QUIET_HOURS", "22-6")
    try:
        q_start, q_end = (int(x) for x in quiet.split("-"))
        assert 0 <= q_start <= 23 and 0 <= q_end <= 23
    except (ValueError, AssertionError) as exc:
        raise MessagingConfigError("MESSAGING_QUIET_HOURS dạng 22-6 (giờ bắt đầu-giờ kết thúc)") from exc
    file_dir = _env("MAIL_FILE_DIR") or str(PROJECT_ROOT / "var" / "mail_outbox")
    if not Path(file_dir).is_absolute():
        file_dir = str(PROJECT_ROOT / file_dir)
    settings = MessagingSettings(
        mail_transport=transport, mail_file_dir=file_dir,
        smtp_host=_env("SMTP_HOST"), smtp_port=_int("SMTP_PORT", 465 if security == "ssl" else 587),
        smtp_security=security, smtp_username=_env("SMTP_USERNAME"), smtp_password=os.getenv("SMTP_PASSWORD") or "",
        smtp_timeout=_int("SMTP_TIMEOUT", 20),
        mail_from=_env("MAIL_FROM", "canhbao.lms@dlu.edu.vn"),
        mail_from_name=_env("MAIL_FROM_NAME", "Hệ thống cảnh báo học tập"),
        mail_delivery=delivery, mail_redirect_to=_env("MAIL_REDIRECT_TO"),
        moodle_ws_url=_env("MOODLE_WS_URL").rstrip("/"), moodle_ws_token=_env("MOODLE_WS_TOKEN"),
        moodle_public_url=_env("MOODLE_WS_PUBLIC_URL", _env("MOODLE_WS_URL")).rstrip("/"),
        moodle_ws_env=moodle_env, moodle_ws_timeout=_int("MOODLE_WS_TIMEOUT", 15),
        allow_live=_bool("MESSAGING_ALLOW_LIVE"), quiet_hours=(q_start, q_end),
        daily_limit_per_course=_int("MESSAGING_DAILY_LIMIT_PER_COURSE", 300),
    )
    if transport == "smtp" and not settings.smtp_host:
        raise MessagingConfigError("MAIL_TRANSPORT=smtp nhưng chưa đặt SMTP_HOST")
    return settings


def live_blockers(settings: MessagingSettings, channel: str, check_ok: bool) -> list[str]:
    """Lý do (tiếng Việt) khiến kênh KHÔNG được gửi tới người nhận thật. Rỗng = được phép."""
    reasons = []
    if not settings.allow_live:
        reasons.append("MESSAGING_ALLOW_LIVE chưa bật")
    if is_clock_frozen():
        reasons.append("hệ thống đang chạy dữ liệu demo (LMS_AS_OF đang đặt)")
    if not check_ok:
        reasons.append("chưa kiểm tra kết nối thành công với cấu hình hiện tại (Hệ thống › Kênh gửi tin)")
    return reasons


def email_mode(settings: MessagingSettings, check_ok: bool) -> tuple[str | None, list[str]]:
    """(chế độ gửi email hiệu lực, cảnh báo). None = kênh tắt hoặc không dùng được."""
    if settings.mail_transport == "off":
        return None, ["Kênh email đang tắt (MAIL_TRANSPORT=off)"]
    if settings.mail_transport == "file":
        return MODE_FILE, []
    if settings.mail_delivery == "live":
        blockers = live_blockers(settings, CHANNEL_EMAIL, check_ok)
        if not blockers:
            return MODE_LIVE, []
        warn = ["Email được chuyển hướng tới hộp thư kiểm thử vì: " + "; ".join(blockers)]
    else:
        warn = []
    if not settings.mail_redirect_to:
        return None, warn + ["Chế độ chuyển hướng cần MAIL_REDIRECT_TO (hộp thư kiểm thử)"]
    return MODE_REDIRECT, warn


def moodle_mode(settings: MessagingSettings, check_ok: bool) -> tuple[str | None, list[str]]:
    """(chế độ gửi tin nhắn Moodle hiệu lực, cảnh báo). Moodle thật chỉ dùng khi đủ điều kiện gửi thật."""
    if not settings.moodle_ws_url or not settings.moodle_ws_token:
        return None, ["Chưa cấu hình MOODLE_WS_URL / MOODLE_WS_TOKEN"]
    if settings.moodle_ws_env == "stub":
        return MODE_STUB, []
    blockers = live_blockers(settings, CHANNEL_MOODLE, check_ok)
    if blockers:
        return None, ["Không gửi tới Moodle thật vì: " + "; ".join(blockers)]
    return MODE_LIVE, []
