"""
Kiểm thử tích hợp dữ liệu giả lập trong moodle_src.
Tiền điều kiện: đã chạy seed_structure + generate_activity với cùng LMS_AS_OF trong .env.
"""
from __future__ import annotations

import pandas as pd
import psycopg
import pytest

from common.settings import resolve_as_of
from database.config import load_db_config
from mockdata import config as cfg
from mockdata.generate_activity import OUTPUT_DIR


@pytest.fixture(scope="module")
def conn():
    c = load_db_config("MOODLE_DB")
    with psycopg.connect(**c.conninfo(application_name="lms-mock-tests"), autocommit=True) as connection:
        yield connection


def scalar(conn, query: str, params=None):
    return conn.execute(query, params).fetchone()[0]


AS_OF_TS = int(resolve_as_of().timestamp())


# ----------------------------------------------------------------------------- quy mô đã thống nhất (10/10/2026: 5 khoa)
def test_scale_matches_agreed_scope(conn):
    faculties = conn.execute("SELECT idnumber, name FROM mdl_course_categories WHERE depth = 1 ORDER BY sortorder").fetchall()
    assert faculties == [(f["code"], f["name"]) for f in cfg.FACULTIES]
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_course WHERE id <> 1") == len(cfg.ALL_COURSES)
    students = scalar(conn, """SELECT COUNT(DISTINCT ra.userid) FROM mdl_role_assignments ra
                               JOIN mdl_role r ON r.id = ra.roleid AND r.shortname = 'student'""")
    assert students == cfg.N_STUDENTS
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE username LIKE 'gv.%'") == len(cfg.TEACHERS)


def test_students_belong_to_their_faculty(conn):
    """mdl_user.department = khoa quản lý; MSSV đúng dải của khoa; số SV mỗi khoa đúng cấu hình."""
    rows = dict(conn.execute("""SELECT department, COUNT(*) FROM mdl_user
                                WHERE username ~ '^22[0-9]{5}$' GROUP BY department""").fetchall())
    assert rows == {f["name"]: f["students"] for f in cfg.FACULTIES}
    for f in cfg.FACULTIES:
        bad = scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE department = %(d)s AND username ~ '^22[0-9]{5}$' "
                           "AND substr(username, 3, 1) <> %(digit)s", {"d": f["name"], "digit": str(f["digit"])})
        assert bad == 0, f["code"]
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE username ~ '^22' AND institution <> %(i)s",
                  {"i": cfg.INSTITUTION}) == 0


def test_course_structure_follows_course_type(conn):
    """Lý thuyết 3 bài lớn + 1 điểm danh; thực hành báo cáo hằng tuần + 2 điểm danh; đồ án báo cáo tiến độ + gặp GVHD."""
    counts = {r[0]: (r[1], r[2]) for r in conn.execute("""
        SELECT c.shortname,
               (SELECT COUNT(*) FROM mdl_assign a WHERE a.course = c.id),
               (SELECT COUNT(*) FROM mdl_attendance a WHERE a.course = c.id)
        FROM mdl_course c WHERE c.id <> 1""").fetchall()}
    for shortname, (_, _, kind) in cfg.ALL_COURSES.items():
        assert counts[shortname] == (len(cfg.ASSIGNMENT_PLAN[kind]), len(cfg.ATTENDANCE_PLAN[kind])), shortname


def test_shared_course_has_students_from_other_faculties(conn):
    other = scalar(conn, """SELECT COUNT(DISTINCT u.department) FROM mdl_user_enrolments ue
        JOIN mdl_enrol e ON e.id = ue.enrolid JOIN mdl_course c ON c.id = e.courseid
        JOIN mdl_user u ON u.id = ue.userid
        WHERE c.shortname = ANY(%(codes)s) AND u.username ~ '^22'""", {"codes": list(cfg.SHARED_COURSES)})
    assert other == len(cfg.FACULTIES) - 1      # mọi khoa trừ Ngoại ngữ


def test_messaging_tables_match_moodle_39(conn):
    """Các bảng nhắn tin tạo đúng cột của Moodle 3.9 (lib/db/install.xml)."""
    expected = {
        "mdl_messages": ["id", "useridfrom", "conversationid", "subject", "fullmessage", "fullmessageformat",
                         "fullmessagehtml", "smallmessage", "timecreated", "fullmessagetrust", "customdata"],
        "mdl_message_conversations": ["id", "type", "name", "convhash", "component", "itemtype", "itemid",
                                      "contextid", "enabled", "timecreated", "timemodified"],
        "mdl_message_conversation_members": ["id", "conversationid", "userid", "timecreated"],
        "mdl_user_preferences": ["id", "userid", "name", "value"],
    }
    for table, columns in expected.items():
        actual = [r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %(t)s ORDER BY ordinal_position",
            {"t": table}).fetchall()]
        assert actual == columns, table
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE username = %(u)s",
                  {"u": cfg.SERVICE_ACCOUNT["username"]}) == 1
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user_preferences WHERE name = 'message_blocknoncontacts' AND value = '0'") > 0


# ----------------------------------------------------------------------------- toàn vẹn tham chiếu (Moodle không có FK)
ORPHAN_QUERIES = {
    "role_assignments.contextid": "SELECT COUNT(*) FROM mdl_role_assignments ra LEFT JOIN mdl_context c ON c.id = ra.contextid WHERE c.id IS NULL",
    "role_assignments.userid": "SELECT COUNT(*) FROM mdl_role_assignments ra LEFT JOIN mdl_user u ON u.id = ra.userid WHERE u.id IS NULL",
    "user_enrolments.enrolid": "SELECT COUNT(*) FROM mdl_user_enrolments ue LEFT JOIN mdl_enrol e ON e.id = ue.enrolid WHERE e.id IS NULL",
    "course.category": "SELECT COUNT(*) FROM mdl_course c LEFT JOIN mdl_course_categories cc ON cc.id = c.category WHERE c.id <> 1 AND cc.id IS NULL",
    "course_modules.section": "SELECT COUNT(*) FROM mdl_course_modules cm LEFT JOIN mdl_course_sections s ON s.id = cm.section AND s.course = cm.course WHERE s.id IS NULL",
    "course_modules.context": "SELECT COUNT(*) FROM mdl_course_modules cm LEFT JOIN mdl_context c ON c.instanceid = cm.id AND c.contextlevel = 70 WHERE c.id IS NULL",
    "course_modules.instance": """SELECT COUNT(*) FROM mdl_course_modules cm JOIN mdl_modules m ON m.id = cm.module
        WHERE NOT CASE m.name
            WHEN 'assign' THEN EXISTS (SELECT 1 FROM mdl_assign x WHERE x.id = cm.instance AND x.course = cm.course)
            WHEN 'page' THEN EXISTS (SELECT 1 FROM mdl_page x WHERE x.id = cm.instance AND x.course = cm.course)
            WHEN 'forum' THEN EXISTS (SELECT 1 FROM mdl_forum x WHERE x.id = cm.instance AND x.course = cm.course)
            WHEN 'attendance' THEN EXISTS (SELECT 1 FROM mdl_attendance x WHERE x.id = cm.instance AND x.course = cm.course)
            ELSE FALSE END""",
    "assign_submission.assignment": "SELECT COUNT(*) FROM mdl_assign_submission s LEFT JOIN mdl_assign a ON a.id = s.assignment WHERE a.id IS NULL",
    "attendance_log.sessionid": "SELECT COUNT(*) FROM mdl_attendance_log l LEFT JOIN mdl_attendance_sessions s ON s.id = l.sessionid WHERE s.id IS NULL",
    "attendance_log.statusid": """SELECT COUNT(*) FROM mdl_attendance_log l JOIN mdl_attendance_sessions s ON s.id = l.sessionid
        LEFT JOIN mdl_attendance_statuses st ON st.id = l.statusid AND st.attendanceid = s.attendanceid WHERE st.id IS NULL""",
    "completion.coursemoduleid": "SELECT COUNT(*) FROM mdl_course_modules_completion x LEFT JOIN mdl_course_modules cm ON cm.id = x.coursemoduleid WHERE cm.id IS NULL",
    "groups_members.groupid": "SELECT COUNT(*) FROM mdl_groups_members gm LEFT JOIN mdl_groups g ON g.id = gm.groupid WHERE g.id IS NULL",
    "logstore.contextid": "SELECT COUNT(*) FROM mdl_logstore_standard_log l LEFT JOIN mdl_context c ON c.id = l.contextid WHERE c.id IS NULL",
    "logstore.context_matches": """SELECT COUNT(*) FROM mdl_logstore_standard_log l JOIN mdl_context c ON c.id = l.contextid
        WHERE c.contextlevel <> l.contextlevel OR c.instanceid <> l.contextinstanceid""",
}


@pytest.mark.parametrize("name", list(ORPHAN_QUERIES))
def test_no_orphan_references(conn, name):
    assert scalar(conn, ORPHAN_QUERIES[name]) == 0


# ----------------------------------------------------------------------------- không có dữ liệu "tương lai"
@pytest.mark.parametrize(
    "query",
    [
        "SELECT COUNT(*) FROM mdl_logstore_standard_log WHERE timecreated > %(as_of)s",
        "SELECT COUNT(*) FROM mdl_assign_submission WHERE timemodified > %(as_of)s",
        "SELECT COUNT(*) FROM mdl_attendance_log WHERE timetaken > %(as_of)s",
        "SELECT COUNT(*) FROM mdl_course_modules_completion WHERE timemodified > %(as_of)s",
        "SELECT COUNT(*) FROM mdl_attendance_sessions WHERE lasttaken > %(as_of)s",
        "SELECT COUNT(*) FROM mdl_attendance_sessions WHERE lasttaken > 0 AND sessdate >= %(as_of)s",
    ],
)
def test_nothing_after_as_of(conn, query):
    assert scalar(conn, query, {"as_of": AS_OF_TS}) == 0


def test_log_ids_follow_time_order(conn):
    assert scalar(conn, """SELECT COUNT(*) FROM (
        SELECT timecreated < LAG(timecreated) OVER (ORDER BY id) AS out_of_order FROM mdl_logstore_standard_log) t
        WHERE out_of_order""") == 0


# ----------------------------------------------------------------------------- ca biên theo SPEC 3.1
def test_inactive_users_and_enrolments_have_no_course_activity(conn):
    assert scalar(conn, """SELECT COUNT(*) FROM mdl_logstore_standard_log l JOIN mdl_user u ON u.id = l.userid
                           WHERE u.deleted = 1 OR u.suspended = 1""") == 0
    assert scalar(conn, """SELECT COUNT(*) FROM mdl_logstore_standard_log l
        JOIN mdl_enrol e ON e.courseid = l.courseid
        JOIN mdl_user_enrolments ue ON ue.enrolid = e.id AND ue.userid = l.userid
        WHERE ue.status = 1 OR l.timecreated >= ue.timeend""") == 0


def test_edge_cases_are_present(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user_enrolments WHERE status = 1") > 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user_enrolments WHERE timeend < %(as_of)s", {"as_of": AS_OF_TS}) > 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE suspended = 1") == cfg.SUSPENDED_STUDENTS
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_user WHERE deleted = 1") == cfg.DELETED_STUDENTS
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_assign_submission WHERE userid = 0 AND groupid > 0") > 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_assign_submission WHERE status = 'new'") > 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_attendance_sessions WHERE groupid <> 0") > 0
    assert scalar(conn, """SELECT COUNT(*) FROM mdl_attendance_sessions s JOIN mdl_attendance a ON a.id = s.attendanceid
                           JOIN mdl_course c ON c.id = a.course WHERE c.shortname = ANY(%(codes)s)""",
                  {"codes": list(cfg.NO_ATTENDANCE_SESSION_COURSES)}) == 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_logstore_standard_log WHERE eventname = '\\core\\event\\user_login_failed'") > 0
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_logstore_standard_log WHERE ip NOT LIKE %(p)s",
                  {"p": cfg.MOCK_IP_PREFIX + "%"}) == 0


def test_online_sessions_exist_at_as_of(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM mdl_sessions WHERE timemodified > %(t)s",
                  {"t": AS_OF_TS - cfg.ONLINE_SESSION_TIMEOUT}) > 0


# ----------------------------------------------------------------------------- hồ sơ hành vi
def test_ground_truth_distribution_matches_spec():
    """Tỷ lệ hồ sơ hành vi của từng khoa khớp cấu hình (sai số ngẫu nhiên ±3 điểm %)."""
    truth = pd.read_csv(OUTPUT_DIR / "ground_truth_profiles.csv")
    for f in cfg.FACULTIES:
        share = truth.loc[truth["department"] == f["name"], "profile"].value_counts(normalize=True)
        for profile, expected in f["profiles"].items():
            assert abs(share[profile] - expected) < 0.03, f"{f['code']} {profile}: {share[profile]:.3f} vs {expected}"
    red = truth[truth["profile"] == "RED"]
    assert abs(red["never"].mean() - cfg.BEHAVIOR["RED"]["never"]) < 0.08


def test_peak_hours_have_more_traffic_than_night(conn):
    rows = dict(conn.execute("""
        SELECT EXTRACT(HOUR FROM to_timestamp(timecreated) AT TIME ZONE 'Asia/Ho_Chi_Minh')::int AS h, COUNT(*)
        FROM mdl_logstore_standard_log GROUP BY 1""").fetchall())
    peak = (rows[9] + rows[15]) / 2
    night = (rows[2] + rows[3]) / 2
    assert peak > 10 * night
