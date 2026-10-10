"""
Gọi Moodle Web Service (giao thức REST) – dùng NGUYÊN mã này cho Moodle thật của trường và Moodle mô phỏng.

    POST {MOODLE_WS_URL}/webservice/rest/server.php
         wstoken, wsfunction, moodlewsrestformat=json, tham số mảng dạng messages[0][touserid]=...

Hàm dùng (Moodle 3.9):
    core_webservice_get_site_info        kiểm tra kết nối, tên site, phiên bản, các hàm được cấp quyền
    core_message_send_instant_messages   gửi tin nhắn cá nhân; mỗi tin trả msgid (= mdl_messages.id) hoặc -1 kèm lỗi
Lỗi cấp lời gọi: {"exception": ..., "errorcode": "invalidtoken" | "accessexception" | "invalidparameter", "message": ...}
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx

from common.messaging.config import MessagingSettings
from common.messaging.email import DeliveryError

FORMAT_PLAIN = 2                       # FORMAT_PLAIN của Moodle
REST_PATH = "/webservice/rest/server.php"
REQUIRED_FUNCTIONS = ("core_webservice_get_site_info", "core_message_send_instant_messages")
# errorcode coi là lỗi cấu hình (không thử lại từng tin, báo quản trị)
CONFIG_ERRORS = {"invalidtoken": "Token web service không hợp lệ",
                 "accessexception": "Tài khoản dịch vụ chưa được cấp quyền gọi hàm này",
                 "servicenotavailable": "Dịch vụ web chưa bật",
                 "webservicesnotenabled": "Moodle chưa bật web service"}


class MoodleError(DeliveryError):
    pass


def flatten(params: Mapping, prefix: str = "") -> dict[str, str]:
    """{'messages': [{'touserid': 5}]} -> {'messages[0][touserid]': '5'} (cách Moodle REST nhận mảng)."""
    out: dict[str, str] = {}
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, Mapping):
            out.update(flatten(value, name))
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                if isinstance(item, Mapping):
                    out.update(flatten(item, f"{name}[{i}]"))
                else:
                    out[f"{name}[{i}]"] = str(item)
        elif isinstance(value, bool):
            out[name] = "1" if value else "0"
        elif value is not None:
            out[name] = str(value)
    return out


@dataclass(frozen=True)
class SentMessage:
    msgid: int
    conversationid: int | None
    clientmsgid: str | None
    errormessage: str | None


class MoodleClient:
    def __init__(self, settings: MessagingSettings, transport: httpx.BaseTransport | None = None):
        if not settings.moodle_ws_url or not settings.moodle_ws_token:
            raise MoodleError("Chưa cấu hình MOODLE_WS_URL / MOODLE_WS_TOKEN", permanent=True, code="not_configured")
        self.url = settings.moodle_ws_url + REST_PATH
        self.token = settings.moodle_ws_token
        self.timeout = settings.moodle_ws_timeout
        self.transport = transport

    def call(self, function: str, params: Mapping | None = None):
        data = {"wstoken": self.token, "wsfunction": function, "moodlewsrestformat": "json", **flatten(params or {})}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(self.url, data=data)
        except httpx.TimeoutException as exc:
            raise MoodleError("Moodle không phản hồi (quá thời gian chờ)", permanent=False, code="timeout") from exc
        except httpx.HTTPError as exc:
            raise MoodleError(f"Không kết nối được Moodle: {type(exc).__name__}", permanent=False, code="network") from exc
        if response.status_code >= 500:
            raise MoodleError(f"Moodle lỗi máy chủ HTTP {response.status_code}", permanent=False,
                              code=f"http_{response.status_code}")
        if response.status_code >= 400:
            raise MoodleError(f"Moodle từ chối yêu cầu HTTP {response.status_code}", permanent=True,
                              code=f"http_{response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise MoodleError("Moodle trả về dữ liệu không phải JSON (kiểm tra MOODLE_WS_URL)", permanent=True,
                              code="bad_response") from exc
        if isinstance(payload, Mapping) and "exception" in payload:
            code = str(payload.get("errorcode") or "exception")
            message = CONFIG_ERRORS.get(code) or str(payload.get("message") or code)
            raise MoodleError(f"Moodle báo lỗi: {message} ({code})", permanent=True, code=code)
        return payload

    def site_info(self) -> dict:
        info = self.call("core_webservice_get_site_info")
        functions = {f.get("name") for f in info.get("functions", [])}
        info["missing_functions"] = [f for f in REQUIRED_FUNCTIONS if f not in functions]
        return info

    def send_instant_messages(self, messages: Sequence[Mapping]) -> list[SentMessage]:
        """messages: [{touserid, text, clientmsgid}] – văn bản thuần (FORMAT_PLAIN)."""
        payload = {"messages": [dict(touserid=int(m["touserid"]), text=m["text"], textformat=FORMAT_PLAIN,
                                     clientmsgid=m.get("clientmsgid") or "") for m in messages]}
        result = self.call("core_message_send_instant_messages", payload)
        if not isinstance(result, list) or len(result) != len(messages):
            raise MoodleError("Phản hồi gửi tin không đúng định dạng của Moodle", permanent=False, code="bad_response")
        return [SentMessage(int(r.get("msgid", -1)), r.get("conversationid"), r.get("clientmsgid"),
                            r.get("errormessage")) for r in result]

    def send_one(self, touserid: int, text: str, clientmsgid: str) -> SentMessage:
        [sent] = self.send_instant_messages([dict(touserid=touserid, text=text, clientmsgid=clientmsgid)])
        if sent.msgid <= 0:
            # Moodle trả -1 khi không thể gửi cho người này (vd sinh viên chỉ nhận tin từ liên hệ)
            raise MoodleError(f"Moodle không gửi được: {sent.errormessage or 'không rõ lý do'}", permanent=True,
                              code="cannot_message")
        return sent
