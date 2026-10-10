"""
Máy chủ Moodle 3.9 MÔ PHỎNG ở mức Web Service – để mã gửi tin nhắn của LMS Analytics là mã thật, chỉ đổi địa chỉ.

Giống Moodle 3.9:
  - Đường dẫn POST/GET /webservice/rest/server.php; tham số wstoken, wsfunction, moodlewsrestformat=json,
    mảng dạng messages[0][touserid]=...
  - core_webservice_get_site_info: thông tin site, người dùng của token, danh sách hàm được cấp quyền.
  - core_message_send_instant_messages: với mỗi tin kiểm tra người nhận (tồn tại, chưa xóa/khóa), quyền nhắn
    (moodle/site:messageanyuser hoặc chung khóa học, tôn trọng tùy chọn message_blocknoncontacts), tìm/tạo hội thoại
    cá nhân (type = 1, convhash = sha1 của 2 user id đã sắp xếp nối bằng "-"), ghi mdl_messages; trả msgid hoặc -1.
  - Lỗi cấp lời gọi: {"exception", "errorcode", "message"} với invalidtoken / accessexception / invalidparameter.
Thêm cho trình diễn: /stub/inbox?userid=... (hộp tin của một người), /stub/messages?userid=... (JSON).

Ghi trực tiếp vào moodle_src (các bảng mdl_* theo lược đồ Moodle 3.9 – migration moodle V005).

Chạy:  python -m tools.moodle_ws_stub            (mặc định http://127.0.0.1:8091)
Biến:  MOODLE_STUB_TOKENS="token1:username1,token2:username2" (mặc định lms-analytics-demo-token:lmsanalytics)
       MOODLE_STUB_MESSAGEANYUSER=true|false        (tài khoản gửi có moodle/site:messageanyuser – mặc định true)
       MOODLE_STUB_PORT=8091
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import time
from contextlib import contextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from database.config import load_db_config

DEFAULT_TOKENS = "lms-analytics-demo-token:lmsanalytics"
SITE_NAME = "Hệ thống LMS – Trường Đại học Đà Lạt (Moodle mô phỏng)"
RELEASE = "3.9.25 (Build: 20231009) – mô phỏng Web Service của LMS Analytics"
VERSION = "2020061525"
SERVICE_FUNCTIONS = ("core_webservice_get_site_info", "core_message_send_instant_messages")
ARRAY_KEY = re.compile(r"^(\w+)((?:\[[^\]]*\])+)$")
FORMAT_HTML, FORMAT_PLAIN = 1, 2
PRIVACY_ONLYCONTACTS, PRIVACY_COURSEMEMBER = 0, 1

app = FastAPI(title="Moodle 3.9 Web Service (mô phỏng)", docs_url=None, redoc_url=None)


def tokens() -> dict[str, str]:
    pairs = (os.getenv("MOODLE_STUB_TOKENS") or DEFAULT_TOKENS).split(",")
    return {p.split(":", 1)[0].strip(): p.split(":", 1)[1].strip() for p in pairs if ":" in p}


def can_message_any() -> bool:
    return (os.getenv("MOODLE_STUB_MESSAGEANYUSER") or "true").lower() in ("1", "true", "yes")


@contextmanager
def db():
    cfg = load_db_config("MOODLE_DB")
    with psycopg.connect(**cfg.conninfo(application_name="moodle-ws-stub")) as conn:
        yield conn


def error(errorcode: str, message: str, exception: str = "moodle_exception") -> JSONResponse:
    # Moodle trả HTTP 200 kèm đối tượng exception (không dùng mã HTTP lỗi)
    return JSONResponse({"exception": exception, "errorcode": errorcode, "message": message})


def _set_path(root: dict, parts: list[str], value: str) -> None:
    node = root
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        container = (lambda: []) if not last and parts[i + 1].isdigit() else (lambda: {})
        if isinstance(node, list):
            idx = int(part)
            while len(node) <= idx:
                node.append(None)
            if last:
                node[idx] = value
            else:
                if node[idx] is None:
                    node[idx] = container()
                node = node[idx]
        else:
            if last:
                node[part] = value
            else:
                node = node.setdefault(part, container())


def parse_params(form: dict[str, str]) -> dict:
    """messages[0][touserid]=5 -> {'messages': [{'touserid': '5'}]} (cách Moodle REST nhận mảng)."""
    out: dict = {}
    for key, value in form.items():
        m = ARRAY_KEY.match(key)
        parts = [m.group(1)] + re.findall(r"\[([^\]]*)\]", m.group(2)) if m else [key]
        _set_path(out, parts, value)
    return out


def user_by_username(conn, username: str):
    return conn.execute("SELECT id, username, firstname, lastname, deleted, suspended FROM mdl_user "
                        "WHERE username = %s AND mnethostid = 1", (username,)).fetchone()


def share_course(conn, a: int, b: int) -> bool:
    return conn.execute("""
        SELECT EXISTS (SELECT 1 FROM mdl_user_enrolments ua JOIN mdl_enrol ea ON ea.id = ua.enrolid
                       JOIN mdl_enrol eb ON eb.courseid = ea.courseid
                       JOIN mdl_user_enrolments ub ON ub.enrolid = eb.id
                       WHERE ua.userid = %s AND ub.userid = %s AND ua.status = 0 AND ub.status = 0)""",
        (a, b)).fetchone()[0]


def privacy(conn, userid: int) -> int:
    row = conn.execute("SELECT value FROM mdl_user_preferences WHERE userid = %s AND name = 'message_blocknoncontacts'",
                       (userid,)).fetchone()
    return int(row[0]) if row else PRIVACY_COURSEMEMBER


def conversation_for(conn, a: int, b: int, now: int) -> int:
    convhash = hashlib.sha1("-".join(str(x) for x in sorted((a, b))).encode()).hexdigest()
    row = conn.execute("SELECT id FROM mdl_message_conversations WHERE type = 1 AND convhash = %s", (convhash,)).fetchone()
    if row:
        conn.execute("UPDATE mdl_message_conversations SET timemodified = %s WHERE id = %s", (now, row[0]))
        return int(row[0])
    cid = conn.execute("""INSERT INTO mdl_message_conversations (type, convhash, enabled, timecreated, timemodified)
                          VALUES (1, %s, 1, %s, %s) RETURNING id""", (convhash, now, now)).fetchone()[0]
    for uid in sorted({a, b}):
        conn.execute("INSERT INTO mdl_message_conversation_members (conversationid, userid, timecreated) "
                     "VALUES (%s, %s, %s)", (cid, uid, now))
    return int(cid)


def site_info(conn, sender) -> dict:
    return {
        "sitename": SITE_NAME, "username": sender[1], "firstname": sender[2], "lastname": sender[3],
        "fullname": f"{sender[3]} {sender[2]}", "lang": "vi", "userid": int(sender[0]),
        "siteurl": os.getenv("MOODLE_STUB_PUBLIC_URL", "http://127.0.0.1:8091"), "userpictureurl": "",
        "functions": [{"name": f, "version": VERSION} for f in SERVICE_FUNCTIONS],
        "downloadfiles": 0, "uploadfiles": 0, "release": RELEASE, "version": VERSION, "mobilecssurl": "",
        "advancedfeatures": [{"name": "usecomments", "value": 1}, {"name": "messaging", "value": 1}],
        "usercanmanageownfiles": False, "userquota": 0, "usermaxuploadfilesize": -1, "userhomepage": 1,
        "siteid": 1, "sitecalendartype": "gregorian", "usercalendartype": "gregorian", "theme": "boost",
    }


def send_instant_messages(conn, sender, messages: list) -> list[dict] | JSONResponse:
    if not isinstance(messages, list) or not messages:
        return error("invalidparameter", "Invalid parameter value detected (Missing required key in single structure: messages)",
                     "invalid_parameter_exception")
    results = []
    now = int(time.time())
    sender_id = int(sender[0])
    for m in messages:
        try:
            touserid = int(m["touserid"])
            text = str(m["text"])
            fmt = int(m.get("textformat", 0) or 0)
        except (KeyError, TypeError, ValueError):
            return error("invalidparameter", "Invalid parameter value detected", "invalid_parameter_exception")
        base = {"clientmsgid": m.get("clientmsgid") or None, "text": text, "timecreated": now,
                "useridfrom": sender_id, "candeletemessagesforallusers": False}
        target = conn.execute("SELECT id, firstname, lastname, deleted, suspended FROM mdl_user WHERE id = %s",
                              (touserid,)).fetchone()
        reason = None
        if target is None or target[3] == 1:
            reason = "Người dùng không tồn tại"
        elif not text.strip():
            reason = "Nội dung tin nhắn trống"
        elif not can_message_any():
            pref = privacy(conn, touserid)
            if pref == PRIVACY_ONLYCONTACTS or (pref == PRIVACY_COURSEMEMBER and not share_course(conn, sender_id, touserid)):
                reason = f"Bạn không thể nhắn tin cho {target[2]} {target[1]}"
        if reason:
            results.append({**base, "msgid": -1, "conversationid": 0, "errormessage": reason})
            continue
        conversation = conversation_for(conn, sender_id, touserid, now)
        fullhtml = text if fmt == FORMAT_HTML else "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"
        msgid = conn.execute("""
            INSERT INTO mdl_messages (useridfrom, conversationid, subject, fullmessage, fullmessageformat,
                                      fullmessagehtml, smallmessage, timecreated, fullmessagetrust, customdata)
            VALUES (%s, %s, NULL, %s, %s, %s, %s, %s, 0, NULL) RETURNING id""",
            (sender_id, conversation, text, fmt, fullhtml, text, now)).fetchone()[0]
        results.append({**base, "msgid": int(msgid), "conversationid": conversation})
    conn.commit()
    return results


@app.api_route("/webservice/rest/server.php", methods=["GET", "POST"])
async def rest(request: Request):
    form = dict(request.query_params)
    if request.method == "POST":
        form.update({k: str(v) for k, v in (await request.form()).items()})
    params = parse_params(form)
    token, function = params.pop("wstoken", None), params.pop("wsfunction", None)
    params.pop("moodlewsrestformat", None)
    username = tokens().get(token or "")
    if not username:
        return error("invalidtoken", "Invalid token - token not found", "moodle_exception")
    with db() as conn:
        sender = user_by_username(conn, username)
        if sender is None or sender[4] == 1 or sender[5] == 1:
            return error("invalidtoken", "Invalid token - token not found")
        if function not in SERVICE_FUNCTIONS:
            return error("accessexception", "Access control exception", "webservice_access_exception")
        if function == "core_webservice_get_site_info":
            return JSONResponse(site_info(conn, sender))
        result = send_instant_messages(conn, sender, params.get("messages"))
        return result if isinstance(result, JSONResponse) else JSONResponse(result)


@app.get("/stub/messages")
def messages_json(userid: int, limit: int = 50):
    with db() as conn:
        rows = conn.execute("""
            SELECT m.id, m.useridfrom, uf.lastname || ' ' || uf.firstname, m.conversationid, m.fullmessage, m.timecreated
            FROM mdl_messages m
            JOIN mdl_message_conversation_members cm ON cm.conversationid = m.conversationid AND cm.userid = %s
            JOIN mdl_user uf ON uf.id = m.useridfrom
            ORDER BY m.timecreated DESC, m.id DESC LIMIT %s""", (userid, limit)).fetchall()
    return [dict(msgid=r[0], useridfrom=r[1], from_name=r[2], conversationid=r[3], text=r[4], timecreated=r[5])
            for r in rows]


@app.get("/stub/inbox", response_class=HTMLResponse)
def inbox(userid: int):
    with db() as conn:
        user = conn.execute("SELECT lastname || ' ' || firstname, username FROM mdl_user WHERE id = %s", (userid,)).fetchone()
    items = messages_json(userid)
    cards = "".join(
        f"<div class='m'><div class='h'><b>{html.escape(i['from_name'])}</b>"
        f"<span>{time.strftime('%d/%m/%Y %H:%M', time.localtime(i['timecreated']))} · mã tin {i['msgid']}</span></div>"
        f"<div class='t'>{html.escape(i['text']).replace(chr(10), '<br>')}</div></div>" for i in items
    ) or "<p class='e'>Chưa có tin nhắn nào.</p>"
    name = html.escape(user[0]) if user else f"#{userid}"
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Tin nhắn – {name}</title>
<style>body{{font:15px/1.5 system-ui,Segoe UI,Arial;background:#f3f4f6;margin:0}}
.top{{background:#0f6cbf;color:#fff;padding:12px 20px;font-weight:600}}
.w{{max-width:760px;margin:20px auto;padding:0 16px}}.m{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;
padding:12px 14px;margin-bottom:10px}}.h{{display:flex;justify-content:space-between;color:#374151;margin-bottom:6px}}
.h span{{color:#6b7280;font-size:13px}}.e{{color:#6b7280}}</style></head><body>
<div class="top">{html.escape(SITE_NAME)}</div><div class="w"><h2>Tin nhắn của {name}</h2>
<p class="e">Trang mô phỏng hộp tin nhắn Moodle – dữ liệu đọc từ mdl_messages, mdl_message_conversation_members.</p>
{cards}</div></body></html>"""
