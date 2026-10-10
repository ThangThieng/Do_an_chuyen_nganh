"""
API phiên bản 1.2: so sánh khoa, xu hướng rủi ro, minh bạch (/meta), luật cảnh báo theo môn, trung tâm can thiệp,
kênh gửi tin. Gửi tin chạy THẬT qua HTTP tới máy chủ Moodle 3.9 mô phỏng (luồng uvicorn trong kiểm thử) và ghi email
ra file .eml – cùng mã nguồn dùng khi vận hành (chứng minh mức 2–3 của kế hoạch Mục 5.11).

Tiền điều kiện: dữ liệu 5 khoa đã backfill tới LMS_AS_OF. Mọi dữ liệu do kiểm thử tạo đều được dọn khi xong.
"""
from __future__ import annotations

import socket
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.types.json import Jsonb
import pytest
import uvicorn

from database.config import load_db_config
from etl.config import RISK_THRESHOLDS, RISK_WEIGHTS
from etl.rules import PRESETS
from etl.transform.risk_rules import score_student
from tests.backend.conftest import API, bearer

STARTED = datetime.now(timezone.utc)


# ----------------------------------------------------------------------------- hạ tầng: Moodle mô phỏng, kênh gửi
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def moodle_stub():
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config("tools.moodle_ws_stub.app:app", host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture()
def channels(monkeypatch, tmp_path, moodle_stub):
    """Kênh gửi ở chế độ demo an toàn: email ghi file, Moodle mô phỏng."""
    monkeypatch.setenv("MAIL_TRANSPORT", "file")
    monkeypatch.setenv("MAIL_FILE_DIR", str(tmp_path))
    monkeypatch.setenv("MOODLE_WS_URL", moodle_stub)
    monkeypatch.setenv("MOODLE_WS_TOKEN", "lms-analytics-demo-token")
    monkeypatch.setenv("MOODLE_WS_ENV", "stub")
    monkeypatch.setenv("MESSAGING_ALLOW_LIVE", "false")
    monkeypatch.setenv("MOODLE_STUB_MESSAGEANYUSER", "true")
    return tmp_path


@pytest.fixture(scope="module")
def moodle_db():
    with psycopg.connect(**load_db_config("MOODLE_DB").conninfo(application_name="lms-v12-tests"), autocommit=True) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def cleanup(db, moodle_db):
    """Dọn theo thứ tự khóa ngoại; kết quả kiểm tra kênh của môi trường thật được khôi phục nguyên trạng."""
    saved_checks = db.execute("SELECT channel, ok, config_fingerprint, detail, checked_by, checked_at "
                              "FROM analytics.channel_check").fetchall()
    yield
    db.execute("""DELETE FROM analytics.intervention_log WHERE outbound_id IN
                  (SELECT message_id FROM analytics.outbound_message WHERE created_at >= %s)""", (STARTED,))
    db.execute("DELETE FROM analytics.outbound_message WHERE created_at >= %s", (STARTED,))
    db.execute("DELETE FROM analytics.auto_prompt_rule WHERE name LIKE '[pytest]%%'")
    db.execute("DELETE FROM analytics.channel_check")
    for row in saved_checks:
        db.execute("""INSERT INTO analytics.channel_check (channel, ok, config_fingerprint, detail, checked_by, checked_at)
                      VALUES (%s, %s, %s, %s, %s, %s)""", (*row[:3], Jsonb(row[3]), *row[4:]))
    # Tin do Moodle mô phỏng ghi trong lúc kiểm thử (người gửi = tài khoản dịch vụ lmsanalytics)
    moodle_db.execute("""DELETE FROM mdl_messages WHERE timecreated >= %s
                         AND useridfrom = (SELECT id FROM mdl_user WHERE username = 'lmsanalytics')""",
                      (int(STARTED.timestamp()) - 5,))


@pytest.fixture()
def course(accounts):
    return accounts["course"]


def teacher_base(course) -> str:
    return f"{API}/teacher/courses/{course['course_id']}"


# ----------------------------------------------------------------------------- góp ý 1 & 2: so sánh, xu hướng
def test_faculty_comparison_reconciles_with_kpis(client, admin_headers):
    cmp = client.get(f"{API}/admin/compare/faculties", headers=admin_headers).json()
    kpi = client.get(f"{API}/admin/overview/kpis", headers=admin_headers).json()
    assert len(cmp["items"]) == 5
    assert sum(i["enrolled"] for i in cmp["items"]) == cmp["school"]["enrolled"] == kpi["total_enrolled"]
    assert sum(i["red"] for i in cmp["items"]) == kpi["red_students"]
    assert sum(i["active"] for i in cmp["items"]) == kpi["total_active"]
    assert kpi["unique_students"] == cmp["school"]["unique_students"] <= sum(i["unique_students"] for i in cmp["items"])
    for i in cmp["items"]:
        assert i["red"] + i["yellow"] + i["green"] == i["enrolled"]
        assert abs(i["red_rate"] + i["yellow_rate"] + i["green_rate"] - 100) < 0.05


def test_school_trend_ends_at_current_distribution(client, admin_headers):
    cmp = client.get(f"{API}/admin/compare/faculties", headers=admin_headers).json()["school"]
    trend = client.get(f"{API}/admin/risk-trend", headers=admin_headers).json()
    last = trend["series"][-1]
    assert trend["scope"] == "school" and trend["series"][0]["period"] == "T1"
    assert (last["red"], last["yellow"], last["green"]) == (cmp["red"], cmp["yellow"], cmp["green"])
    daily = client.get(f"{API}/admin/risk-trend", params={"granularity": "day"}, headers=admin_headers).json()["series"]
    assert len(daily) > len(trend["series"]) and daily[-1]["red"] == last["red"]


def test_faculty_page_summary_and_course_rates(client, admin_headers, course):
    body = client.get(f"{API}/admin/enrollment/faculties/{course['faculty_id']}/courses", headers=admin_headers).json()
    s = body["summary"]
    assert s["enrolled"] == sum(c["enrolled"] for c in body["items"])
    for c in body["items"]:
        assert c["rule_scope"] in ("GLOBAL", "COURSE")
        if c["enrolled"]:
            assert abs(c["red_rate"] - 100 * c["red_count"] / c["enrolled"]) < 0.01
    faculty_trend = client.get(f"{API}/admin/risk-trend", params={"faculty_id": course["faculty_id"]},
                               headers=admin_headers).json()["series"][-1]
    assert faculty_trend["red"] == s["red"]


def test_teacher_trend_matches_summary_and_is_protected(client, teacher_headers, other_teacher_headers, course):
    summary = client.get(teacher_base(course) + "/risk-summary", headers=teacher_headers).json()
    trend = client.get(teacher_base(course) + "/risk-trend", headers=teacher_headers).json()
    assert trend["series"][-1]["red"] == summary["red"]
    assert summary["prev_week"]["total"] > 0 and summary["rule"]["scope"] in ("GLOBAL", "COURSE")
    assert client.get(teacher_base(course) + "/risk-trend", headers=other_teacher_headers).status_code == 403


def test_admin_course_page_is_read_only_view(client, admin_headers, teacher_headers, course):
    summary = client.get(f"{API}/admin/courses/{course['course_id']}/risk-summary", headers=admin_headers).json()
    assert summary["red"] == course["red_count"]
    students = client.get(f"{API}/admin/courses/{course['course_id']}/risk-students", headers=admin_headers).json()
    uid = students["items"][0]["user_id"]
    detail = client.get(f"{API}/admin/courses/{course['course_id']}/students/{uid}", headers=admin_headers).json()
    assert detail["user_id"] == uid and isinstance(detail["attendance_detail"], list)
    # So sánh với trung bình lớp: cùng số liệu với giảng viên (chỉ đọc)
    admin_cmp = client.get(f"{API}/admin/courses/{course['course_id']}/students/{uid}/compare", headers=admin_headers).json()
    teacher_cmp = client.get(teacher_base(course) + f"/students/{uid}/compare", headers=teacher_headers).json()
    assert admin_cmp["metrics"] == teacher_cmp["metrics"] and len(admin_cmp["metrics"]) == 5
    assert client.get(f"{API}/admin/courses/{course['course_id']}/students/{uid}/compare",
                      headers=teacher_headers).status_code == 403
    assert client.get(f"{API}/admin/courses/{course['course_id']}/risk-summary", headers=teacher_headers).status_code == 403


# ----------------------------------------------------------------------------- góp ý 4: minh bạch
def test_meta_rule_equals_etl_configuration(client, admin_headers):
    rule = client.get(f"{API}/meta/risk-rule", headers=admin_headers).json()
    assert rule["scope"] == "GLOBAL"
    assert rule["thresholds"] == pytest.approx(dict(RISK_THRESHOLDS))
    assert rule["weights"] == pytest.approx(dict(RISK_WEIGHTS))
    metrics = client.get(f"{API}/meta/metrics", headers=admin_headers).json()
    keys = {m["key"] for m in metrics["items"]}
    assert {"risk_level", "risk_score", "active_rate", "risk_trend"} <= keys
    assert any("mdl_logstore_standard_log" in m["moodle_tables"] for m in metrics["items"])
    fresh = client.get(f"{API}/meta/freshness", headers=admin_headers).json()
    assert fresh["clock_frozen"] and fresh["latest_snapshot_date"]


def test_every_stored_score_is_reproducible_from_its_rule(db, snapshot):
    """Σ đóng góp == risk_score và mức suy ra == risk_level cho MỌI dòng snapshot hôm nay (theo rule_set_id đã lưu)."""
    rules = {r[0]: r[1] for r in db.execute("SELECT rule_set_id, params FROM analytics.risk_rule_set").fetchall()}
    global_levels = next(p["level_rules"] for i, p in rules.items() if i == 1)
    rows = db.execute("""SELECT course_id, total_sessions, absent_sessions, days_since_last_access, access_count_14d,
                                total_assignments, missing_assignments_count, max_consecutive_missing, attendance_detail,
                                risk_score, risk_level, rule_set_id
                         FROM analytics.fact_student_risk_summary WHERE snapshot_date = %s""", (snapshot,)).fetchall()
    by_course: dict[int, list] = {}
    for r in rows:
        by_course.setdefault(r[0], []).append(r)
    checked = 0
    for course_rows in by_course.values():
        median = float(statistics.median(r[4] for r in course_rows))
        for r in course_rows:
            p = rules[r[11]]
            res = score_student(dict(total_sessions=r[1], absent_sessions=r[2], days_since_last_access=r[3],
                                     access_count_14d=r[4], total_assignments=r[5], missing_assignments_count=r[6],
                                     max_consecutive_missing=r[7], attendance_detail=r[8]), median,
                                p["thresholds"], p["weights"], global_levels, p["extra_rules"])
            assert (res["risk_score"], res["risk_level"]) == (r[9], r[10])
            checked += 1
    assert checked > 10_000


# ----------------------------------------------------------------------------- chức năng 1: luật theo môn
def test_course_rule_preview_save_apply_and_reset(client, teacher_headers, other_teacher_headers, course, db, snapshot):
    url = teacher_base(course) + "/risk-rules"
    state = client.get(url, headers=teacher_headers).json()
    assert state["can_edit"] and len(state["presets"]) == 4 and state["attendance_activities"]
    before = client.get(teacher_base(course) + "/risk-summary", headers=teacher_headers).json()
    params = PRESETS["PROJECT"]["params"]
    body = {"preset": "PROJECT", "params": params, "note": "[pytest] thử luật đồ án"}
    preview = client.post(url + "/preview", json=body, headers=teacher_headers).json()
    assert preview["before"] == {"RED": before["red"], "YELLOW": before["yellow"], "GREEN": before["green"]}
    assert client.put(url, json=body, headers=other_teacher_headers).status_code == 403
    try:
        saved = client.put(url, json=body, headers=teacher_headers)
        assert saved.status_code == 200, saved.text
        after = client.get(teacher_base(course) + "/risk-summary", headers=teacher_headers).json()
        assert {"RED": after["red"], "YELLOW": after["yellow"], "GREEN": after["green"]} == preview["after"]
        assert after["rule"]["scope"] == "COURSE" and after["rule"]["preset"] == "PROJECT"
        assert after["rule"]["differs_from_default"]
        progress = db.execute("""SELECT red_count, rule_set_id FROM analytics.fact_course_progress_daily
                                 WHERE course_id = %s AND stat_date = %s""", (course["course_id"], snapshot)).fetchone()
        assert progress[0] == after["red"] and progress[1] == saved.json()["rule_set_id"]
        trend = client.get(teacher_base(course) + "/risk-trend", params={"granularity": "day"}, headers=teacher_headers).json()
        assert any(c["date"] == snapshot.isoformat() for c in trend["rule_changes"])
    finally:
        reset = client.delete(url, headers=teacher_headers)
        assert reset.status_code == 200
        db.execute("DELETE FROM analytics.risk_rule_set WHERE note LIKE '[pytest]%%'")
    restored = client.get(teacher_base(course) + "/risk-summary", headers=teacher_headers).json()
    assert (restored["red"], restored["yellow"], restored["green"]) == (before["red"], before["yellow"], before["green"])


def test_rule_outside_safe_bounds_is_rejected_with_reasons(client, teacher_headers, course):
    params = {**PRESETS["DEFAULT"]["params"], "weights": {"attendance": 0.9, "inactivity": 0.05, "assignment": 0.05}}
    res = client.post(teacher_base(course) + "/risk-rules/preview", json={"params": params}, headers=teacher_headers)
    assert res.status_code == 422
    fields = {e["field"] for e in res.json()["detail"]["errors"]}
    assert {"attendance", "inactivity"} <= fields


# ----------------------------------------------------------------------------- chức năng 2: gửi tin
def _red_students(client, headers, course, n=2):
    items = client.get(teacher_base(course) + "/contact-list", params={"not_contacted_days": 0},
                       headers=headers).json()["items"]
    return items[:n]


def test_preview_fills_template_from_snapshot(client, teacher_headers, course, channels):
    students = _red_students(client, teacher_headers, course)
    body = client.post(teacher_base(course) + "/messages/preview",
                       json={"user_ids": [s["user_id"] for s in students], "channels": ["MOODLE", "EMAIL"], "template_id": 1},
                       headers=teacher_headers).json()
    assert body["channels"]["EMAIL"]["mode"] == "FILE" and body["channels"]["MOODLE"]["mode"] == "STUB"
    assert len(body["drafts"]) == 2 * len(students)
    d = body["drafts"][0]
    assert d["error"] is None and "{" not in d["body"] and d["student_name"].split()[-1] in d["body"]


def test_send_email_and_moodle_message_end_to_end(client, teacher_headers, course, channels, moodle_db, db):
    [student] = _red_students(client, teacher_headers, course, 1)
    request_id = uuid.uuid4().hex
    items = [{"user_id": student["user_id"], "channel": ch, "subject": "[pytest] Thầy cần trao đổi",
              "body": "Chào em, đây là tin kiểm thử."} for ch in ("EMAIL", "MOODLE")]
    res = client.post(teacher_base(course) + "/messages", json={"request_id": request_id, "items": items},
                      headers=teacher_headers).json()
    assert res["sent"] == 2 and res["failed"] == 0, res
    refs = {r["delivery_mode"]: r["provider_ref"] for r in res["results"]}
    # Email: file .eml có đúng Message-ID
    eml = list(channels.glob("*.eml"))
    assert len(eml) == 1 and refs["FILE"] in eml[0].read_text(encoding="utf-8", errors="replace")
    # Moodle: tin nằm trong mdl_messages, hội thoại cá nhân có sinh viên là thành viên
    msg = moodle_db.execute("""SELECT m.fullmessage, cm.userid FROM mdl_messages m
                               JOIN mdl_message_conversation_members cm ON cm.conversationid = m.conversationid
                               WHERE m.id = %s AND cm.userid = %s""", (int(refs["STUB"]), student["user_id"])).fetchone()
    assert msg and "tin kiểm thử" in msg[0]
    # Nhật ký can thiệp được ghi, liên kết với tin
    logs = db.execute("""SELECT action_type FROM analytics.intervention_log i JOIN analytics.outbound_message o
                         ON o.message_id = i.outbound_id WHERE o.user_id = %s AND i.created_at >= %s""",
                      (student["user_id"], STARTED)).fetchall()
    assert sorted(r[0] for r in logs) == ["EMAIL", "MESSAGE"]
    # Gửi lại cùng request_id: không tạo tin trùng
    again = client.post(teacher_base(course) + "/messages", json={"request_id": request_id, "items": items},
                        headers=teacher_headers).json()
    assert again["created"] == 0
    history = client.get(teacher_base(course) + "/messages", params={"status": "SENT"}, headers=teacher_headers).json()
    assert {m["provider_ref"] for m in history["items"]} >= set(refs.values())


def test_moodle_refusal_is_permanent_failure(client, teacher_headers, course, channels, monkeypatch, moodle_db):
    """Không có quyền messageanyuser + SV chỉ nhận tin từ liên hệ -> Moodle trả msgid = -1 -> FAILED, không thử lại."""
    monkeypatch.setenv("MOODLE_STUB_MESSAGEANYUSER", "false")
    [student] = _red_students(client, teacher_headers, course, 1)
    res = client.post(teacher_base(course) + "/messages", json={"request_id": uuid.uuid4().hex, "items": [
        {"user_id": student["user_id"], "channel": "MOODLE", "subject": "x", "body": "[pytest] tin bị từ chối"}]},
        headers=teacher_headers).json()
    assert res["failed"] == 1 and "không thể nhắn tin" in res["results"][0]["error"].lower()


def test_demo_data_cannot_reach_real_mailboxes(client, teacher_headers, course, channels, monkeypatch):
    monkeypatch.setenv("MAIL_TRANSPORT", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("MAIL_DELIVERY", "live")
    monkeypatch.setenv("MESSAGING_ALLOW_LIVE", "true")
    monkeypatch.delenv("MAIL_REDIRECT_TO", raising=False)
    [student] = _red_students(client, teacher_headers, course, 1)
    res = client.post(teacher_base(course) + "/messages", json={"request_id": uuid.uuid4().hex, "items": [
        {"user_id": student["user_id"], "channel": "EMAIL", "subject": "x", "body": "y"}]}, headers=teacher_headers)
    assert res.status_code == 409 and "demo" in res.json()["detail"]


def test_auto_prompt_dry_run_run_cooldown_and_approve(client, teacher_headers, course, channels):
    base = teacher_base(course) + "/auto-prompts"
    tpl = next(t for t in client.get(f"{API}/teacher/message-templates", headers=teacher_headers).json()["items"]
               if t["code"] == "INACTIVE")
    rid = client.post(base, json={"name": "[pytest] không truy cập", "trigger_type": "INACTIVE_DAYS", "params": {"days": 7},
                                  "channels": ["MOODLE"], "template_id": tpl["template_id"], "send_mode": "REVIEW",
                                  "cooldown_days": 7}, headers=teacher_headers).json()["rule_id"]
    dry = client.post(f"{base}/{rid}/dry-run", headers=teacher_headers).json()
    assert dry["matched"] > 0 and dry["created"] == 0
    run = client.post(f"{base}/{rid}/run", headers=teacher_headers).json()
    assert run["created"] == len(dry["recipients"])
    assert client.post(f"{base}/{rid}/run", headers=teacher_headers).json()["created"] == 0   # thời gian chờ
    pending = client.get(teacher_base(course) + "/messages", params={"status": "PENDING_REVIEW"},
                         headers=teacher_headers).json()["items"]
    assert pending and all(m["origin"] == "AUTO" for m in pending)
    approved = client.post(teacher_base(course) + f"/messages/{pending[0]['message_id']}/approve",
                           headers=teacher_headers).json()
    assert approved["sent"] == 1


def test_intervention_center_permissions(client, other_teacher_headers, admin_headers, course):
    for suffix in ("/contact-list", "/messages", "/auto-prompts", "/risk-rules"):
        assert client.get(teacher_base(course) + suffix, headers=other_teacher_headers).status_code == 403
        assert client.get(teacher_base(course) + suffix, headers=admin_headers).status_code == 403


def test_admin_channel_check_against_moodle_stub(client, admin_headers, teacher_headers, channels):
    res = client.post(f"{API}/admin/channels/test-moodle", headers=admin_headers).json()
    assert res["ok"] and "mô phỏng" in res["sitename"]
    status = client.get(f"{API}/admin/channels", headers=admin_headers).json()
    assert status["channels"]["MOODLE"]["last_check"]["ok"]
    assert "password" not in str(status["config"]).lower() or status["config"]["smtp_password_set"] in (True, False)
    assert client.get(f"{API}/admin/channels", headers=teacher_headers).status_code == 403



# ----------------------------------------------------------------------------- Mục 4.9: quyền, phiên bản, chấm lại = ETL
def _assistant_of(db, course_id: int, snapshot) -> int:
    """Trợ giảng (vai trò Moodle teacher) của môn – có trong teacher_ids nhưng không trong editing_teacher_ids."""
    row = db.execute("""SELECT ARRAY(SELECT unnest(teacher_ids) EXCEPT SELECT unnest(editing_teacher_ids))
                        FROM analytics.fact_course_progress_daily WHERE course_id = %s AND stat_date = %s""",
                     (course_id, snapshot)).fetchone()
    if not row or not row[0]:
        pytest.skip("Môn kiểm thử không có trợ giảng")
    return int(row[0][0])


def test_teaching_assistant_can_view_and_preview_but_not_save(client, db, snapshot, course):
    assistant = _assistant_of(db, course["course_id"], snapshot)
    if db.execute("SELECT 1 FROM analytics.app_user WHERE user_id = %s AND is_active", (assistant,)).fetchone() is None:
        pytest.skip("Trợ giảng chưa có tài khoản (python -m backend.app.cli sync-users)")
    headers = bearer(assistant, "TEACHER")
    url = teacher_base(course) + "/risk-rules"
    state = client.get(url, headers=headers)
    assert state.status_code == 200 and state.json()["can_edit"] is False
    body = {"preset": "PRACTICE", "params": PRESETS["PRACTICE"]["params"], "note": "[pytest] trợ giảng"}
    assert client.post(url + "/preview", json=body, headers=headers).status_code == 200
    saved = client.put(url, json=body, headers=headers)
    assert saved.status_code == 403 and "giảng viên chính" in saved.json()["detail"]
    assert client.delete(url, headers=headers).status_code == 403


def test_two_saves_make_two_versions_and_history_is_not_rewritten(client, teacher_headers, course, db, snapshot):
    url = teacher_base(course) + "/risk-rules"
    yesterday_sql = """SELECT rule_set_id, red_count, yellow_count FROM analytics.fact_course_progress_daily
                       WHERE course_id = %s AND stat_date = %s::date - 1"""
    yesterday = db.execute(yesterday_sql, (course["course_id"], snapshot)).fetchone()
    try:
        ids = []
        for preset in ("THEORY", "PROJECT"):
            res = client.put(url, json={"preset": preset, "params": PRESETS[preset]["params"],
                                        "note": f"[pytest] {preset}"}, headers=teacher_headers)
            assert res.status_code == 200, res.text
            ids.append(res.json()["rule_set_id"])
        history = client.get(url, headers=teacher_headers).json()["history"]
        mine = sorted((h for h in history if h["rule_set_id"] in ids), key=lambda h: h["rule_set_id"])
        assert [h["is_active"] for h in mine] == [False, True]
        versions = [r[0] for r in db.execute(
            "SELECT version_no FROM analytics.risk_rule_set WHERE rule_set_id = ANY(%s) ORDER BY rule_set_id", (ids,))]
        assert versions[1] == versions[0] + 1
        # Snapshot các ngày trước giữ nguyên bộ luật và số liệu cũ (không "viết lại lịch sử")
        assert db.execute(yesterday_sql, (course["course_id"], snapshot)).fetchone() == yesterday
        assert db.execute("""SELECT COUNT(*) FROM analytics.fact_student_risk_summary
                             WHERE course_id = %s AND snapshot_date < %s AND rule_set_id = ANY(%s)""",
                          (course["course_id"], snapshot, ids)).fetchone()[0] == 0
    finally:
        assert client.delete(url, headers=teacher_headers).status_code == 200
        db.execute("DELETE FROM analytics.risk_rule_set WHERE note LIKE '[pytest]%%'")


RESCORE_SQL = """SELECT user_id, score_attendance, score_inactivity, score_assignment, risk_score, risk_level,
                        risk_reasons, attendance_status, rule_set_id
                 FROM analytics.fact_student_risk_summary WHERE course_id = %s AND snapshot_date = %s ORDER BY user_id"""


def test_rescore_in_analytics_equals_etl_rerun_from_moodle(client, teacher_headers, course, db, snapshot):
    """
    Chấm lại trên CSDL phân tích khi lưu luật == ETL student_risk chạy lại từ Moodle cùng ngày, từng dòng (mức, điểm,
    lý do). Nếu khác, job sẽ ghi đè và rows_loaded > 0.
    """
    from common.settings import resolve_as_of
    from etl.jobs import job_course_progress, job_student_risk

    as_of = resolve_as_of()
    url = teacher_base(course) + "/risk-rules"
    params = PRESETS["PROJECT"]["params"]
    params = {**params, "extra_rules": [{"type": "consecutive_missing", "count": 2, "level": "RED"},
                                        {"type": "absent_sessions", "count": 2, "level": "RED"}]}
    try:
        saved = client.put(url, json={"preset": "CUSTOM", "params": params, "note": "[pytest] đối chiếu ETL"},
                           headers=teacher_headers)
        assert saved.status_code == 200, saved.text
        rescored = db.execute(RESCORE_SQL, (course["course_id"], snapshot)).fetchall()
        assert {r[8] for r in rescored} == {saved.json()["rule_set_id"]}

        stats = job_student_risk.run(as_of)
        assert stats is not None and stats.rows_loaded == 0, "ETL chấm khác kết quả chấm lại trên CSDL phân tích"
        assert db.execute(RESCORE_SQL, (course["course_id"], snapshot)).fetchall() == rescored
        progress = job_course_progress.run(as_of)
        assert progress is not None and progress.rows_loaded == 0, "Số Đỏ/Vàng/Xanh của bảng tiến độ môn lệch"
    finally:
        assert client.delete(url, headers=teacher_headers).status_code == 200
        db.execute("DELETE FROM analytics.risk_rule_set WHERE note LIKE '[pytest]%%'")
    # Khôi phục mặc định cũng phải trùng ETL
    stats = job_student_risk.run(as_of)
    assert stats is not None and stats.rows_loaded == 0


def test_global_rule_version_is_published_when_etl_config_changes(db, monkeypatch):
    """G2-5: đổi ngưỡng trong etl/config.py -> lần chạy ETL kế tiếp phát hành phiên bản GLOBAL mới (trong giao dịch, rollback)."""
    from backend.app.core.db import get_engine
    from etl import rules as rule_mod

    base = rule_mod.default_params()
    changed = {**base, "thresholds": {**base["thresholds"], "absence_red": 0.35}}
    with get_engine().connect() as conn:
        tx = conn.begin()
        try:
            current = rule_mod.ensure_global_rule(conn)
            assert rule_mod.ensure_global_rule(conn).rule_set_id == current.rule_set_id     # cấu hình không đổi
            monkeypatch.setattr(rule_mod, "default_params", lambda: rule_mod.copy.deepcopy(changed))
            published = rule_mod.ensure_global_rule(conn)
            assert published.rule_set_id != current.rule_set_id
            assert published.params["thresholds"]["absence_red"] == 0.35
            active = conn.exec_driver_sql("SELECT rule_set_id FROM analytics.risk_rule_set "
                                          "WHERE scope = 'GLOBAL' AND is_active").all()
            assert active == [(published.rule_set_id,)]
        finally:
            tx.rollback()
    assert db.execute("SELECT COUNT(*) FROM analytics.risk_rule_set WHERE scope = 'GLOBAL' AND is_active").fetchone()[0] == 1


# ----------------------------------------------------------------------------- Mục 5.12: nhắc tự động, phân quyền, hiệu năng
def _rule(client, headers, course, trigger, params, template_code):
    tpl = next(t for t in client.get(f"{API}/teacher/message-templates", headers=headers).json()["items"]
               if t["code"] == template_code)
    res = client.post(teacher_base(course) + "/auto-prompts", headers=headers, json={
        "name": f"[pytest] {trigger}", "trigger_type": trigger, "params": params, "channels": ["MOODLE"],
        "template_id": tpl["template_id"], "send_mode": "REVIEW", "cooldown_days": 7})
    assert res.status_code == 201, res.text
    return res.json()["rule_id"]


def test_became_red_trigger_matches_level_change_between_snapshots(client, teacher_headers, course, channels, db, snapshot):
    rid = _rule(client, teacher_headers, course, "BECAME_RED", {}, "RISK_HIGH")
    dry = client.post(teacher_base(course) + f"/auto-prompts/{rid}/dry-run", headers=teacher_headers).json()
    expected = {r[0] for r in db.execute("""
        SELECT t.user_id FROM analytics.fact_student_risk_summary t
        LEFT JOIN analytics.fact_student_risk_summary p
               ON p.course_id = t.course_id AND p.user_id = t.user_id
              AND p.snapshot_date = (SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary
                                     WHERE course_id = t.course_id AND snapshot_date < t.snapshot_date)
        WHERE t.course_id = %s AND t.snapshot_date = %s AND t.risk_level = 'RED'
          AND p.risk_level IS DISTINCT FROM 'RED'""", (course["course_id"], snapshot))}
    assert {r["user_id"] for r in dry["recipients"]} == expected and dry["created"] == 0


def test_missed_deadline_trigger_matches_assignment_detail(client, teacher_headers, course, channels, db, snapshot):
    due = db.execute("""SELECT (MAX(snapshot_date) - DATE(MAX((a->>'duedate')::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh'))) AS d
                        FROM analytics.fact_student_risk_summary r, jsonb_array_elements(r.assignment_detail) a
                        WHERE r.course_id = %s AND r.snapshot_date = %s AND a->>'status' = 'missing'""",
                     (course["course_id"], snapshot)).fetchone()[0]
    if due is None or not 0 <= due <= 7:
        pytest.skip("Môn kiểm thử không có bài quá hạn trong 7 ngày gần nhất")
    rid = _rule(client, teacher_headers, course, "MISSED_DEADLINE", {"days_after": int(due)}, "MISSING_WORK")
    dry = client.post(teacher_base(course) + f"/auto-prompts/{rid}/dry-run", headers=teacher_headers).json()
    expected = {r[0] for r in db.execute("""
        SELECT DISTINCT r.user_id FROM analytics.fact_student_risk_summary r, jsonb_array_elements(r.assignment_detail) a
        WHERE r.course_id = %s AND r.snapshot_date = %s AND a->>'status' = 'missing'
          AND DATE((a->>'duedate')::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh') = %s::date - %s""",
        (course["course_id"], snapshot, snapshot, int(due)))}
    assert expected and {r["user_id"] for r in dry["recipients"]} == expected


def test_auto_prompt_parameters_are_validated(client, teacher_headers, course):
    tpl = client.get(f"{API}/teacher/message-templates", headers=teacher_headers).json()["items"][0]["template_id"]
    res = client.post(teacher_base(course) + "/auto-prompts", headers=teacher_headers, json={
        "name": "[pytest] sai tham số", "trigger_type": "INACTIVE_DAYS", "params": {"days": 90}, "channels": ["EMAIL"],
        "template_id": tpl})
    assert res.status_code == 422 and "3 đến 30" in res.json()["detail"]


def test_admin_and_other_teacher_cannot_send_or_approve(client, admin_headers, other_teacher_headers, course, channels):
    body = {"request_id": uuid.uuid4().hex, "items": [{"user_id": 1, "channel": "EMAIL", "subject": "x", "body": "y"}]}
    for headers in (admin_headers, other_teacher_headers):
        assert client.post(teacher_base(course) + "/messages", json=body, headers=headers).status_code == 403
        assert client.post(teacher_base(course) + "/messages/1/approve", headers=headers).status_code == 403
        assert client.post(teacher_base(course) + "/auto-prompts", json={}, headers=headers).status_code in (403, 422)
    assert client.get(f"{API}/teacher/message-templates", headers=admin_headers).status_code == 403
    assert client.get(teacher_base(course) + "/messages").status_code == 401


def test_bulk_200_messages_in_file_and_stub_mode_under_30_seconds(client, teacher_headers, course, channels, db,
                                                                   snapshot):
    """Mục 5.12: gửi hàng loạt 200 tin (100 SV × 2 kênh) ở chế độ file/Moodle mô phỏng trong dưới 30 giây."""
    ids = [r[0] for r in db.execute("""SELECT user_id FROM analytics.fact_student_risk_summary
                                       WHERE course_id = %s AND snapshot_date = %s AND email IS NOT NULL
                                       ORDER BY user_id LIMIT 100""", (course["course_id"], snapshot))]
    if len(ids) < 100:
        pytest.skip("Môn kiểm thử có ít hơn 100 sinh viên có email")
    items = [{"user_id": uid, "channel": ch, "subject": "[pytest] gửi hàng loạt", "body": "Tin kiểm thử."}
             for uid in ids for ch in ("EMAIL", "MOODLE")]
    started = time.perf_counter()
    res = client.post(teacher_base(course) + "/messages", json={"request_id": uuid.uuid4().hex, "items": items},
                      headers=teacher_headers)
    elapsed = time.perf_counter() - started
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["created"], body["sent"], body["failed"], body["retry"]) == (200, 200, 0, 0), body["results"][:3]
    assert len(list(channels.glob("*.eml"))) == 100
    assert elapsed < 30, f"Gửi 200 tin mất {elapsed:.1f}s"
