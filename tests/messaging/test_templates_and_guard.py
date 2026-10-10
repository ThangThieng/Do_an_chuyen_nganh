"""Mẫu tin cá nhân hóa và chốt chặn chế độ gửi thật (không cần CSDL)."""
from __future__ import annotations

from datetime import date

import pytest

from common.messaging.config import (MODE_FILE, MODE_LIVE, MODE_REDIRECT, MODE_STUB, MessagingSettings, email_mode,
                                     live_blockers, moodle_mode)
from common.messaging.templates import TemplateError, build_context, render, situation_lines, text_to_html

STUDENT = dict(student_name="Bùi Mai Oanh", student_code="2212032", total_sessions=18, absent_sessions=4,
               absence_rate=22.2, days_since_last_access=9, risk_level="RED",
               risk_reasons=["Vắng 4/18 buổi (22%)", "Bỏ nộp 2 bài liên tiếp (luật của môn)"],
               score_attendance=1, score_inactivity=1, score_assignment=1,
               assignment_detail=[dict(name="Bài tập 2", duedate="2026-09-27T23:59:00+07:00", status="missing"),
                                  dict(name="Bài tập 3", duedate="2026-10-04T23:59:00+07:00", status="submitted")])
COURSE = dict(shortname="IT004", fullname="Cơ sở dữ liệu")
TEACHER = dict(full_name="Lê Quốc Bảo", email="lequocbao@dlu.edu.vn", salutation="Thầy")


def ctx():
    return build_context(STUDENT, COURSE, TEACHER, today=date(2026, 11, 6), contact_days=7)


def test_context_fills_every_variable_from_snapshot():
    c = ctx()
    assert c["ten_sv"] == "Oanh" and c["mssv"] == "2212032" and c["xung_ho"] == "Thầy"
    assert c["bai_chua_nop"] == "Bài tập 2 (hạn 27/09/2026)"
    assert c["han_lien_he"] == "13/11/2026"
    assert c["so_ngay_khong_vao"] == "9"


def test_situation_lines_describe_each_problem_including_course_rule():
    lines = situation_lines(STUDENT)
    assert lines[0] == "– em đã vắng 4/18 buổi (22%);"
    assert "– em đã 9 ngày chưa vào môn học trên Moodle;" in lines
    assert "– em chưa nộp Bài tập 2 (hạn 27/09/2026);" in lines
    assert lines[-1] == "– bỏ nộp 2 bài liên tiếp."


def test_render_system_template():
    r = render("[{ma_mon}] {xung_ho} cần trao đổi với em về môn {ten_mon}",
               "Chào em {ten_sv},\n\n{tinh_hinh}\n\nEm liên hệ {xung_ho} trước ngày {han_lien_he}.", ctx())
    assert r.subject == "[IT004] Thầy cần trao đổi với em về môn Cơ sở dữ liệu"
    assert r.body.startswith("Chào em Oanh,") and "13/11/2026" in r.body and "{" not in r.body


def test_unknown_or_empty_variable_is_rejected():
    with pytest.raises(TemplateError, match="Biến không hợp lệ"):
        render("x", "{ten_lop}", ctx())
    c = ctx()
    c["email_gv"] = ""
    with pytest.raises(TemplateError, match="email_gv"):
        render("x", "Liên hệ {email_gv}", c)


def test_html_body_is_escaped():
    assert text_to_html("A <b>&\nB") == "<p>A &lt;b&gt;&amp;<br>B</p>"


# ----------------------------------------------------------------------------- chốt chặn gửi thật
LIVE = MessagingSettings(mail_transport="smtp", smtp_host="smtp.example", mail_delivery="live",
                         mail_redirect_to="lms.test@example.com", moodle_ws_url="https://lms.example",
                         moodle_ws_token="t", moodle_ws_env="live", allow_live=True)


def test_demo_data_can_never_reach_real_recipients(monkeypatch):
    monkeypatch.setenv("LMS_AS_OF", "2026-11-06T10:30:00+07:00")
    assert any("demo" in r for r in live_blockers(LIVE, "EMAIL", check_ok=True))
    assert email_mode(LIVE, check_ok=True)[0] == MODE_REDIRECT          # tự hạ về chuyển hướng
    assert moodle_mode(LIVE, check_ok=True)[0] is None                  # Moodle thật bị từ chối


def test_live_requires_flag_and_successful_check(monkeypatch):
    monkeypatch.setenv("LMS_AS_OF", "")
    assert email_mode(LIVE, check_ok=False)[0] == MODE_REDIRECT
    off = MessagingSettings(**{**LIVE.__dict__, "allow_live": False})
    assert email_mode(off, check_ok=True)[0] == MODE_REDIRECT
    assert email_mode(LIVE, check_ok=True)[0] == MODE_LIVE
    assert moodle_mode(LIVE, check_ok=True)[0] == MODE_LIVE


def test_redirect_without_test_mailbox_is_unavailable(monkeypatch):
    monkeypatch.setenv("LMS_AS_OF", "2026-11-06T10:30:00+07:00")
    s = MessagingSettings(**{**LIVE.__dict__, "mail_redirect_to": ""})
    mode, warnings = email_mode(s, check_ok=True)
    assert mode is None and any("MAIL_REDIRECT_TO" in w for w in warnings)


def test_file_and_stub_modes_are_always_safe(monkeypatch):
    monkeypatch.setenv("LMS_AS_OF", "2026-11-06T10:30:00+07:00")
    s = MessagingSettings(mail_transport="file", moodle_ws_url="http://127.0.0.1:8091", moodle_ws_token="t",
                          moodle_ws_env="stub")
    assert email_mode(s, check_ok=False)[0] == MODE_FILE
    assert moodle_mode(s, check_ok=False)[0] == MODE_STUB


def test_fingerprint_changes_with_server_but_never_contains_secret():
    a = MessagingSettings(smtp_host="a", smtp_password="secret-1")
    b = MessagingSettings(smtp_host="b", smtp_password="secret-1")
    assert a.fingerprint("EMAIL") != b.fingerprint("EMAIL")
    assert "secret" not in str(a.describe()) and "secret" not in repr(a)


def test_auto_messages_created_in_quiet_hours_are_scheduled_at_seven():
    """Kế hoạch v1.2 Mục 5.7: không gửi tự động 22:00–06:00; tin tạo trong khung này hẹn gửi 07:00."""
    from datetime import datetime

    from common.messaging.config import MessagingSettings
    from common.messaging.outbox import next_allowed_time

    s = MessagingSettings(quiet_hours=(22, 6))
    assert next_allowed_time(datetime(2026, 11, 6, 23, 30), s) == datetime(2026, 11, 7, 7, 0)
    assert next_allowed_time(datetime(2026, 11, 7, 2, 15), s) == datetime(2026, 11, 7, 7, 0)
    assert next_allowed_time(datetime(2026, 11, 7, 5, 59), s) == datetime(2026, 11, 7, 7, 0)
    assert next_allowed_time(datetime(2026, 11, 7, 6, 0), s) == datetime(2026, 11, 7, 6, 0)      # hết khung yên lặng
    assert next_allowed_time(datetime(2026, 11, 7, 21, 59), s) == datetime(2026, 11, 7, 21, 59)
    assert next_allowed_time(datetime(2026, 11, 7, 22, 0), s) == datetime(2026, 11, 8, 7, 0)
