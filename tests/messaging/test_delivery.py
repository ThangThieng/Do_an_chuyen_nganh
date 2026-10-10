"""
Chứng minh mức 1–2 (kế hoạch Mục 5.11): gửi bằng ĐÚNG mã dùng khi vận hành.

- Email: máy chủ SMTP cục bộ thật (aiosmtpd) nhận thư qua giao thức SMTP; kiểm tra người nhận, tiêu đề, Reply-To,
  nội dung tiếng Việt, Message-ID; chế độ chuyển hướng đổi đúng người nhận; chế độ file ghi .eml đọc lại được.
- Moodle: phản hồi mẫu theo định dạng Moodle 3.9 (thành công, msgid = -1, invalidtoken) qua httpx.MockTransport.
"""
from __future__ import annotations

import email
import json
import socket
from email import policy

import httpx
import pytest
from aiosmtpd.controller import Controller

from common.messaging.config import MODE_FILE, MODE_LIVE, MODE_REDIRECT, MessagingSettings
from common.messaging.email import DeliveryError, send_email
from common.messaging.moodle import MoodleClient, MoodleError, flatten


class Inbox:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):         # noqa: N802 – API của aiosmtpd
        self.messages.append(envelope)
        return "250 Message accepted for delivery"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def smtp():
    inbox, port = Inbox(), free_port()
    controller = Controller(inbox, hostname="127.0.0.1", port=port)
    controller.start()
    try:
        yield inbox, port
    finally:
        controller.stop()


def smtp_settings(port: int, **kw) -> MessagingSettings:
    return MessagingSettings(mail_transport="smtp", smtp_host="127.0.0.1", smtp_port=port, smtp_security="none",
                             mail_from="canhbao.lms@dlu.edu.vn", mail_from_name="Hệ thống cảnh báo học tập", **kw)


def test_smtp_live_delivers_vietnamese_mail_with_reply_to_teacher(smtp):
    inbox, port = smtp
    d = send_email(smtp_settings(port), MODE_LIVE, to="2212032@student.dlu.edu.vn", to_name="Bùi Mai Oanh",
                   subject="[IT004] Thầy cần trao đổi với em", body="Chào em Oanh,\n\nEm đã vắng 4/18 buổi.",
                   reply_to="lequocbao@dlu.edu.vn", reply_to_name="Lê Quốc Bảo", tracking_id="lms-1")
    [env] = inbox.messages
    assert env.rcpt_tos == ["2212032@student.dlu.edu.vn"] and env.mail_from == "canhbao.lms@dlu.edu.vn"
    msg = email.message_from_bytes(env.content, policy=policy.default)
    assert msg["Subject"] == "[IT004] Thầy cần trao đổi với em"
    assert msg["Reply-To"].addresses[0].addr_spec == "lequocbao@dlu.edu.vn"
    assert msg["Message-ID"].strip() == d.provider_ref and msg["X-LMS-Message-Id"] == "lms-1"
    assert "Em đã vắng 4/18 buổi." in msg.get_body(("plain",)).get_content()
    assert "<p>Chào em Oanh,</p>" in msg.get_body(("html",)).get_content()
    assert d.mode == MODE_LIVE and d.delivered_to == "2212032@student.dlu.edu.vn"


def test_smtp_redirect_sends_to_test_mailbox_and_keeps_original_recipient(smtp):
    inbox, port = smtp
    d = send_email(smtp_settings(port, mail_redirect_to="lms.test@example.com"), MODE_REDIRECT,
                   to="2212032@student.dlu.edu.vn", to_name="Bùi Mai Oanh", subject="Nhắc nhở", body="Nội dung")
    [env] = inbox.messages
    assert env.rcpt_tos == ["lms.test@example.com"]
    msg = email.message_from_bytes(env.content, policy=policy.default)
    assert msg["X-LMS-Original-Recipient"] == "2212032@student.dlu.edu.vn"
    assert "Gửi thay cho: 2212032@student.dlu.edu.vn" in msg["Subject"]
    assert d.delivered_to == "lms.test@example.com"


def test_smtp_permanent_rejection_is_not_retried():
    class Reject(Inbox):
        async def handle_RCPT(self, server, session, envelope, address, rcpt_options):  # noqa: N802
            return "550 5.1.1 Mailbox does not exist"
    port = free_port()
    controller = Controller(Reject(), hostname="127.0.0.1", port=port)
    controller.start()
    try:
        with pytest.raises(DeliveryError) as exc:
            send_email(smtp_settings(port), MODE_LIVE, to="x@example.com",
                       to_name="", subject="s", body="b")
        assert exc.value.permanent and exc.value.code == "550"
    finally:
        controller.stop()


def test_unreachable_smtp_is_temporary_error():
    with pytest.raises(DeliveryError) as exc:
        send_email(smtp_settings(1, smtp_timeout=2), MODE_LIVE, to="x@example.com", to_name="", subject="s", body="b")
    assert not exc.value.permanent


def test_file_mode_writes_rfc5322_message(tmp_path):
    settings = MessagingSettings(mail_transport="file", mail_file_dir=str(tmp_path))
    d = send_email(settings, MODE_FILE, to="2212032@student.dlu.edu.vn", to_name="Bùi Mai Oanh", subject="Tiêu đề",
                   body="Nội dung tiếng Việt", tracking_id="lms-9")
    msg = email.message_from_bytes(open(d.meta["file"], "rb").read(), policy=policy.default)
    assert msg["To"].addresses[0].addr_spec == "2212032@student.dlu.edu.vn"
    assert msg["Message-ID"].strip() == d.provider_ref
    assert msg.get_body(("plain",)).get_content().strip() == "Nội dung tiếng Việt"


def test_missing_email_is_permanent():
    with pytest.raises(DeliveryError) as exc:
        send_email(MessagingSettings(), MODE_FILE, to="", to_name="", subject="s", body="b")
    assert exc.value.permanent


# ----------------------------------------------------------------------------- Moodle Web Service (định dạng 3.9)
def moodle(handler) -> MoodleClient:
    s = MessagingSettings(moodle_ws_url="https://lms.example", moodle_ws_token="tok")
    return MoodleClient(s, transport=httpx.MockTransport(handler))


def test_flatten_matches_moodle_rest_array_syntax():
    assert flatten({"messages": [{"touserid": 5, "text": "hi"}]}) == {"messages[0][touserid]": "5",
                                                                     "messages[0][text]": "hi"}


def test_send_instant_message_success_returns_msgid():
    def handler(request: httpx.Request):
        form = dict(httpx.QueryParams(request.content.decode()))
        assert request.url.path == "/webservice/rest/server.php"
        assert form["wsfunction"] == "core_message_send_instant_messages" and form["wstoken"] == "tok"
        assert form["messages[0][touserid]"] == "42" and form["messages[0][textformat]"] == "2"
        return httpx.Response(200, json=[{"msgid": 1532, "clientmsgid": "lms-7", "text": "x", "timecreated": 1,
                                          "conversationid": 88, "useridfrom": 31,
                                          "candeletemessagesforallusers": False}])
    sent = moodle(handler).send_one(42, "Chào em", "lms-7")
    assert (sent.msgid, sent.conversationid) == (1532, 88)


def test_recipient_refused_is_permanent_error():
    def handler(request):
        return httpx.Response(200, json=[{"msgid": -1, "clientmsgid": "c", "errormessage": "Bạn không thể nhắn tin cho A"}])
    with pytest.raises(MoodleError) as exc:
        moodle(handler).send_one(42, "x", "c")
    assert exc.value.permanent and "không thể nhắn tin" in str(exc.value)


def test_invalid_token_is_reported_as_configuration_error():
    def handler(request):
        return httpx.Response(200, json={"exception": "moodle_exception", "errorcode": "invalidtoken",
                                         "message": "Invalid token - token not found"})
    with pytest.raises(MoodleError) as exc:
        moodle(handler).site_info()
    assert exc.value.code == "invalidtoken" and "Token web service không hợp lệ" in str(exc.value)


def test_timeout_and_5xx_are_temporary():
    def timeout(request):
        raise httpx.ConnectTimeout("t", request=request)
    with pytest.raises(MoodleError) as exc:
        moodle(timeout).site_info()
    assert not exc.value.permanent
    with pytest.raises(MoodleError) as exc:
        moodle(lambda r: httpx.Response(503, text="busy")).site_info()
    assert not exc.value.permanent


def test_site_info_reports_missing_functions():
    payload = {"sitename": "LMS", "functions": [{"name": "core_webservice_get_site_info", "version": "1"}]}
    info = moodle(lambda r: httpx.Response(200, content=json.dumps(payload))).site_info()
    assert info["missing_functions"] == ["core_message_send_instant_messages"]
