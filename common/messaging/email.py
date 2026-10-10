"""
Gửi email can thiệp – một cài đặt duy nhất cho mọi chế độ:
    FILE      ghi file .eml chuẩn RFC 5322 (mở bằng Outlook/Thunderbird) – demo offline, kiểm thử
    REDIRECT  gửi qua SMTP thật nhưng người nhận là hộp thư kiểm thử (tiêu đề ghi rõ người nhận gốc)
    LIVE      gửi qua SMTP thật tới người nhận thật (chỉ khi chốt chặn ở config.py cho phép)
Mã xác nhận (provider_ref) là Message-ID – tra được trong hộp thư người nhận, file .eml, nhật ký máy chủ SMTP.
"""
from __future__ import annotations

import smtplib
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path

from common.messaging.config import MODE_FILE, MODE_LIVE, MODE_REDIRECT, MessagingSettings
from common.messaging.templates import text_to_html
from common.settings import TZ

MESSAGE_ID_DOMAIN = "lms-analytics.local"


class DeliveryError(RuntimeError):
    """Gửi thất bại. permanent=True: không thử lại (địa chỉ sai, bị từ chối vĩnh viễn)."""

    def __init__(self, message: str, *, permanent: bool, code: str | None = None):
        super().__init__(message)
        self.permanent = permanent
        self.code = code


@dataclass(frozen=True)
class Delivery:
    mode: str
    provider_ref: str
    delivered_to: str
    meta: dict


def build_message(settings: MessagingSettings, *, to: str, to_name: str, subject: str, body: str,
                  reply_to: str | None, reply_to_name: str | None, original_to: str | None,
                  tracking_id: str | None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = Address(display_name=settings.mail_from_name, addr_spec=settings.mail_from)
    msg["To"] = Address(display_name=to_name or "", addr_spec=to)
    if reply_to:
        msg["Reply-To"] = Address(display_name=reply_to_name or "", addr_spec=reply_to)
    msg["Subject"] = subject if original_to is None else f"{subject} [Gửi thay cho: {original_to}]"
    msg["Date"] = format_datetime(datetime.now(TZ))
    msg["Message-ID"] = make_msgid(idstring=tracking_id, domain=MESSAGE_ID_DOMAIN)
    msg["X-Mailer"] = "LMS Analytics"
    if tracking_id:
        msg["X-LMS-Message-Id"] = tracking_id
    if original_to:
        msg["X-LMS-Original-Recipient"] = original_to
    note = (f"\n\n---\n[Chế độ kiểm thử] Email này lẽ ra gửi tới {original_to}." if original_to else "")
    msg.set_content(body + note)
    msg.add_alternative(text_to_html(body + note), subtype="html")
    return msg


def _smtp_send(settings: MessagingSettings, msg: EmailMessage, recipient: str) -> dict:
    context = ssl.create_default_context()
    try:
        if settings.smtp_security == "ssl":
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout,
                                      context=context)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout)
        with server:
            server.ehlo()
            if settings.smtp_security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            refused = server.send_message(msg, from_addr=settings.mail_from, to_addrs=[recipient])
            if refused:
                code, reason = refused[recipient]
                raise DeliveryError(f"Máy chủ thư từ chối người nhận ({code})", permanent=code >= 500, code=str(code))
            return {"smtp_host": settings.smtp_host}
    except DeliveryError:
        raise
    except smtplib.SMTPRecipientsRefused as exc:
        code, _ = next(iter(exc.recipients.values()))
        raise DeliveryError(f"Địa chỉ người nhận bị từ chối ({code})", permanent=code >= 500, code=str(code)) from exc
    except smtplib.SMTPAuthenticationError as exc:
        raise DeliveryError("Đăng nhập máy chủ thư thất bại – kiểm tra SMTP_USERNAME/SMTP_PASSWORD",
                            permanent=False, code=str(exc.smtp_code)) from exc
    except smtplib.SMTPResponseException as exc:
        raise DeliveryError(f"Máy chủ thư trả lỗi {exc.smtp_code}", permanent=exc.smtp_code >= 500,
                            code=str(exc.smtp_code)) from exc
    except (smtplib.SMTPException, OSError, socket.timeout) as exc:
        raise DeliveryError(f"Không kết nối được máy chủ thư: {type(exc).__name__}", permanent=False) from exc


def send_email(settings: MessagingSettings, mode: str, *, to: str, to_name: str, subject: str, body: str,
               reply_to: str | None = None, reply_to_name: str | None = None,
               tracking_id: str | None = None) -> Delivery:
    """Gửi một email theo chế độ đã được chốt chặn quyết định (FILE / REDIRECT / LIVE)."""
    if not to or "@" not in to:
        raise DeliveryError("Sinh viên không có địa chỉ email hợp lệ", permanent=True, code="no_email")
    if mode == MODE_REDIRECT:
        recipient, original = settings.mail_redirect_to, to
    elif mode in (MODE_FILE, MODE_LIVE):
        recipient, original = to, None
    else:
        raise DeliveryError(f"Chế độ gửi email không hợp lệ: {mode}", permanent=True)
    msg = build_message(settings, to=recipient, to_name=to_name, subject=subject, body=body, reply_to=reply_to,
                        reply_to_name=reply_to_name, original_to=original, tracking_id=tracking_id)
    message_id = msg["Message-ID"]

    if mode == MODE_FILE:
        folder = Path(settings.mail_file_dir)
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{datetime.now(TZ):%Y%m%d_%H%M%S}_{tracking_id or 'mail'}.eml"
        path = folder / name
        path.write_bytes(bytes(msg))
        return Delivery(MODE_FILE, message_id, recipient, {"file": str(path)})
    meta = _smtp_send(settings, msg, recipient)
    return Delivery(mode, message_id, recipient, meta)


def check_smtp(settings: MessagingSettings) -> dict:
    """Kiểm tra kết nối + đăng nhập SMTP (không gửi thư)."""
    context = ssl.create_default_context()
    try:
        server = (smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout, context=context)
                  if settings.smtp_security == "ssl"
                  else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout))
        with server:
            code, banner = server.ehlo()
            if settings.smtp_security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            return {"ehlo": code, "server": banner.decode(errors="replace")[:120] if isinstance(banner, bytes) else str(banner)}
    except smtplib.SMTPAuthenticationError as exc:
        raise DeliveryError("Đăng nhập máy chủ thư thất bại – kiểm tra SMTP_USERNAME/SMTP_PASSWORD",
                            permanent=False) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise DeliveryError(f"Không kết nối được máy chủ thư {settings.smtp_host}:{settings.smtp_port}: "
                            f"{type(exc).__name__}", permanent=False) from exc
