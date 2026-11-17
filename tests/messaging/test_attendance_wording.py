"""Câu chữ chuyên cần theo nguồn dữ liệu (theo buổi / sổ điểm) trong lý do cảnh báo và tin nhắn – không cần CSDL."""
from __future__ import annotations

from datetime import date

from common import attendance_text
from common.messaging.templates import build_context, session_variable_notice, situation_lines

BASE = dict(student_name="Bùi Mai Oanh", student_code="2212032", days_since_last_access=2, risk_level="YELLOW",
            risk_reasons=[], score_attendance=1, score_inactivity=0, score_assignment=0, assignment_detail=[])
SESSIONS = dict(BASE, total_sessions=15, absent_sessions=3, attendance_source="SESSIONS")
GRADEBOOK = dict(BASE, total_sessions=100, absent_sessions=25, attendance_source="GRADEBOOK")
NO_DATA = dict(BASE, total_sessions=0, absent_sessions=0, score_attendance=0, attendance_source="SESSIONS")
COURSE = dict(shortname="IT004", fullname="Cơ sở dữ liệu")
TEACHER = dict(full_name="Lê Quốc Bảo", email="lequocbao@dlu.edu.vn", salutation="Thầy")


def ctx(student):
    return build_context(student, COURSE, TEACHER, today=date(2026, 11, 12))


def test_risk_reason_keeps_previous_wording():
    assert attendance_text.risk_reason(SESSIONS) == "Vắng 3/15 buổi (20%)"
    assert attendance_text.risk_reason(GRADEBOOK) == "Chuyên cần 75% theo sổ điểm (vắng 25%)"


def test_message_never_invents_sessions_for_gradebook():
    lines = " ".join(situation_lines(GRADEBOOK))
    assert "chuyên cần của em đạt 75% (theo sổ điểm)" in lines
    assert "buổi" not in lines
    assert "em đã vắng 3/15 buổi (20%)" in " ".join(situation_lines(SESSIONS))


def test_chuyen_can_variable_works_for_every_source():
    assert ctx(SESSIONS)["chuyen_can"] == "có mặt 12/15 buổi"
    assert ctx(GRADEBOOK)["chuyen_can"] == "75% (theo sổ điểm)"
    assert ctx(NO_DATA)["chuyen_can"] == "chưa có dữ liệu điểm danh"


def test_session_variables_are_not_faked_for_gradebook():
    c = ctx(GRADEBOOK)
    assert c["so_buoi_vang"] == "không rõ" and c["tong_buoi"] == "không rõ"
    assert c["ty_le_vang"] == "25% (theo sổ điểm)"
    s = ctx(SESSIONS)
    assert (s["so_buoi_vang"], s["tong_buoi"], s["ty_le_vang"]) == ("3", "15", "20%")


def test_composer_notice_only_when_session_variables_meet_gradebook():
    body = "Em đã vắng {so_buoi_vang}/{tong_buoi} buổi."
    assert session_variable_notice("Nhắc", body, [GRADEBOOK, SESSIONS]) is not None
    assert session_variable_notice("Nhắc", body, [SESSIONS]) is None
    assert session_variable_notice("Nhắc", "Chuyên cần: {chuyen_can}", [GRADEBOOK]) is None


def test_too_few_attendance_days_wording():
    from common import attendance_text
    r = {"attendance_source": "GRADEBOOK", "total_sessions": 0, "absent_sessions": 0, "attendance_days": 1}
    assert attendance_text.summary(r) == "môn mới điểm danh 1 buổi, chưa tính chuyên cần"
    assert attendance_text.message_phrase(r) == "môn mới điểm danh 1 buổi, chưa tính chuyên cần"
    assert attendance_text.summary({**r, "attendance_days": None}) == "chưa có dữ liệu điểm danh"
