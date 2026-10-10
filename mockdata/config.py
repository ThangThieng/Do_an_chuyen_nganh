"""
Tham số sinh dữ liệu giả lập – SPEC Phần 3.2.

Quy mô (chốt lại ngày 10/10/2026, thay cho bộ 1 khoa ngày 14/09/2026): 5 khoa, 58 môn, khoảng 3.000 sinh viên.
Cấu trúc theo đúng lược đồ Moodle 3.9 (lib/db/install.xml – https://moodleschema.zoola.io/) và plugin mod_attendance.
Hồ sơ hành vi, trọng số giờ/thứ, hệ số cao điểm giữ nguyên theo spec; thêm tỷ lệ hồ sơ và hệ số truy cập theo khoa.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import numpy as np

from common.settings import TZ

RANDOM_SEED = 2026

# ----------------------------------------------------------------------------- học kỳ
SEMESTER_START = datetime(2026, 9, 7, tzinfo=TZ)          # Thứ 2, HK1 2026-2027
SEMESTER_WEEKS = 15
SEMESTER_END = SEMESTER_START + timedelta(weeks=SEMESTER_WEEKS)
STRUCTURE_CREATED_AT = SEMESTER_START - timedelta(days=21)  # thời điểm tạo khóa học/tài khoản
ENROL_START = SEMESTER_START - timedelta(days=7)

DAY = 86_400
WEEK = 7 * DAY

# ----------------------------------------------------------------------------- tổ chức
MOCK_IP_PREFIX = "10.99."                                  # dấu hiệu nhận biết dữ liệu giả lập
STUDENT_EMAIL_DOMAIN = "student.dlu.edu.vn"
STAFF_EMAIL_DOMAIN = "dlu.edu.vn"
INSTITUTION = "Trường Đại học Đà Lạt"                      # mdl_user.institution
ACADEMIC_TERM_TAG = "HK1_2026-2027"

# Loại môn (Moodle không có trường này – chỉ dùng khi sinh dữ liệu, quyết định cấu trúc bài tập và điểm danh):
#   LT lý thuyết · TH thực hành · DA đồ án
COURSE_TYPES = ("LT", "TH", "DA")


def _course(shortname: str, fullname: str, kind: str) -> tuple[str, str, str]:
    assert kind in COURSE_TYPES, kind
    return shortname, fullname, kind


# Mỗi khoa: mã (idnumber danh mục cấp 1), tên, chữ số trong MSSV, số sinh viên, tỷ lệ hồ sơ hành vi, hệ số tần suất
# truy cập, các bộ môn (mã, tên, [môn]), giảng viên (username, họ + đệm, tên) và phân công {mã môn: (GV chính, (trợ giảng))}.
# Khoa CNTT giữ nguyên 15 môn, 8 giảng viên và phân công của bộ dữ liệu 1 khoa (tài khoản demo không đổi).
FACULTIES: list[dict] = [
    dict(
        code="CNTT", name="Khoa Công nghệ Thông tin", digit=1, students=600,
        profiles={"GREEN": 0.65, "YELLOW": 0.20, "RED": 0.15}, activity=1.00,
        departments=[
            ("KHMT", "Bộ môn Khoa học Máy tính", [
                _course("IT001", "Nhập môn lập trình", "TH"), _course("IT002", "Toán rời rạc", "LT"),
                _course("IT003", "Cấu trúc dữ liệu và giải thuật", "TH"), _course("IT010", "Trí tuệ nhân tạo", "LT")]),
            ("HTTT", "Bộ môn Hệ thống Thông tin", [
                _course("IT004", "Cơ sở dữ liệu", "LT"), _course("IT005", "Hệ quản trị cơ sở dữ liệu", "TH"),
                _course("IT006", "Phân tích thiết kế hệ thống thông tin", "DA"),
                _course("IT011", "Kho dữ liệu và khai phá dữ liệu", "LT")]),
            ("KTPM", "Bộ môn Kỹ thuật Phần mềm", [
                _course("IT007", "Lập trình hướng đối tượng", "TH"), _course("IT008", "Công nghệ phần mềm", "DA"),
                _course("IT009", "Lập trình Web", "TH"), _course("IT012", "Kiểm thử phần mềm", "TH")]),
            ("MMT", "Bộ môn Mạng máy tính và Truyền thông", [
                _course("IT013", "Mạng máy tính", "TH"), _course("IT014", "Hệ điều hành", "LT"),
                _course("IT015", "An toàn thông tin", "LT")]),
        ],
        teachers=[
            ("gv.tranminhhung", "Trần Minh", "Hùng"), ("gv.nguyenthilan", "Nguyễn Thị", "Lan"),
            ("gv.lequocbao", "Lê Quốc", "Bảo"), ("gv.phamthuha", "Phạm Thu", "Hà"),
            ("gv.vothanhtam", "Võ Thanh", "Tâm"), ("gv.dangngocanh", "Đặng Ngọc", "Ánh"),
            ("gv.buiducthang", "Bùi Đức", "Thắng"), ("gv.hohaiyen", "Hồ Hải", "Yến"),
        ],
        assignments={
            "IT001": (0, (7,)), "IT002": (0, ()), "IT003": (1, ()), "IT010": (1, ()),
            "IT004": (2, (6,)), "IT005": (2, ()), "IT006": (3, ()), "IT011": (3, ()),
            "IT007": (4, ()), "IT008": (4, ()), "IT009": (5, (7,)), "IT012": (5, ()),
            "IT013": (6, ()), "IT014": (6, ()), "IT015": (7, ()),
        },
    ),
    dict(
        code="KT", name="Khoa Kinh tế – Quản trị kinh doanh", digit=2, students=850,
        profiles={"GREEN": 0.70, "YELLOW": 0.19, "RED": 0.11}, activity=0.90,
        departments=[
            ("QTKD", "Bộ môn Quản trị kinh doanh", [
                _course("KT106", "Quản trị học", "LT"), _course("KT107", "Marketing căn bản", "LT"),
                _course("KT108", "Quản trị nhân lực", "LT"), _course("KT110", "Đồ án quản trị doanh nghiệp", "DA"),
                _course("KT111", "Thương mại điện tử", "TH")]),
            ("KTTC", "Bộ môn Kế toán – Tài chính", [
                _course("KT103", "Nguyên lý kế toán", "LT"), _course("KT104", "Kế toán tài chính", "TH"),
                _course("KT105", "Tài chính doanh nghiệp", "LT")]),
            ("KTH", "Bộ môn Kinh tế học", [
                _course("KT101", "Kinh tế vi mô", "LT"), _course("KT102", "Kinh tế vĩ mô", "LT"),
                _course("KT109", "Thống kê kinh doanh", "TH"), _course("KT112", "Kinh tế lượng", "TH")]),
        ],
        teachers=[
            ("gv.nguyenvankhanh", "Nguyễn Văn", "Khánh"), ("gv.tranthimy", "Trần Thị", "Mỹ"),
            ("gv.lehoangnam", "Lê Hoàng", "Nam"), ("gv.phamngocquynh", "Phạm Ngọc", "Quỳnh"),
            ("gv.doanminhtri", "Đoàn Minh", "Trí"),
        ],
        assignments={
            "KT106": (0, ()), "KT107": (0, ()), "KT108": (1, ()), "KT110": (1, (4,)), "KT111": (2, ()),
            "KT103": (3, ()), "KT104": (3, ()), "KT105": (4, ()),
            "KT101": (2, ()), "KT102": (4, ()), "KT109": (1, ()), "KT112": (0, ()),
        },
    ),
    dict(
        code="NN", name="Khoa Ngoại ngữ", digit=3, students=500,
        profiles={"GREEN": 0.75, "YELLOW": 0.17, "RED": 0.08}, activity=1.15,
        departments=[
            ("TACB", "Bộ môn Tiếng Anh cơ bản", [
                _course("NN101_N01", "Tiếng Anh 1 – Nhóm 01", "TH"), _course("NN101_N02", "Tiếng Anh 1 – Nhóm 02", "TH"),
                _course("NN101_N03", "Tiếng Anh 1 – Nhóm 03", "TH"), _course("NN101_N04", "Tiếng Anh 1 – Nhóm 04", "TH")]),
            ("NNA", "Bộ môn Ngôn ngữ Anh", [
                _course("NN201", "Ngữ âm học tiếng Anh", "LT"), _course("NN202", "Ngữ pháp tiếng Anh nâng cao", "LT"),
                _course("NN203", "Kỹ năng Nghe – Nói", "TH"), _course("NN204", "Kỹ năng Đọc – Viết", "TH"),
                _course("NN205", "Lý thuyết biên dịch", "LT"), _course("NN206", "Thực hành phiên dịch", "TH"),
                _course("NN207", "Văn hóa Anh – Mỹ", "LT"), _course("NN208", "Dự án biên dịch", "DA")]),
        ],
        teachers=[
            ("gv.nguyenthuytrang", "Nguyễn Thùy", "Trang"), ("gv.lethanhthao", "Lê Thanh", "Thảo"),
            ("gv.hoangdieulinh", "Hoàng Diệu", "Linh"), ("gv.tranquocviet", "Trần Quốc", "Việt"),
            ("gv.vothuhuong", "Võ Thu", "Hương"),
        ],
        assignments={
            "NN101_N01": (0, ()), "NN101_N02": (1, ()), "NN101_N03": (2, ()), "NN101_N04": (3, ()),
            "NN201": (4, ()), "NN202": (0, ()), "NN203": (1, (4,)), "NN204": (2, ()),
            "NN205": (3, ()), "NN206": (4, ()), "NN207": (0, ()), "NN208": (1, ()),
        },
    ),
    dict(
        code="LUAT", name="Khoa Luật", digit=4, students=550,
        profiles={"GREEN": 0.66, "YELLOW": 0.20, "RED": 0.14}, activity=0.85,
        departments=[
            ("LDS", "Bộ môn Luật Dân sự – Kinh tế", [
                _course("LU103", "Luật Dân sự", "LT"), _course("LU106", "Luật Thương mại", "LT"),
                _course("LU107", "Luật Lao động", "LT"), _course("LU109", "Luật Tố tụng dân sự", "LT"),
                _course("LU108", "Kỹ năng tư vấn pháp luật", "TH")]),
            ("LHC", "Bộ môn Luật Hành chính – Hình sự", [
                _course("LU101", "Lý luận nhà nước và pháp luật", "LT"), _course("LU102", "Luật Hiến pháp", "LT"),
                _course("LU104", "Luật Hình sự", "LT"), _course("LU105", "Luật Hành chính", "LT"),
                _course("LU110", "Phiên tòa giả định", "DA")]),
        ],
        teachers=[
            ("gv.phamvanthang", "Phạm Văn", "Thắng"), ("gv.nguyenthihoa", "Nguyễn Thị", "Hoa"),
            ("gv.dangquanghuy", "Đặng Quang", "Huy"), ("gv.buingocmai", "Bùi Ngọc", "Mai"),
            ("gv.ledinhkhoi", "Lê Đình", "Khôi"),
        ],
        assignments={
            "LU103": (0, ()), "LU106": (0, ()), "LU107": (1, ()), "LU109": (1, ()), "LU108": (2, (4,)),
            "LU101": (3, ()), "LU102": (3, ()), "LU104": (4, ()), "LU105": (2, ()), "LU110": (4, ()),
        },
    ),
    dict(
        code="SH", name="Khoa Sinh học", digit=5, students=500,
        profiles={"GREEN": 0.58, "YELLOW": 0.22, "RED": 0.20}, activity=0.80,
        departments=[
            ("SHTN", "Bộ môn Sinh học thực nghiệm", [
                _course("SH101", "Sinh học đại cương", "LT"), _course("SH102", "Thực hành sinh học đại cương", "TH"),
                _course("SH104", "Vi sinh vật học", "TH"), _course("SH106", "Sinh lý thực vật", "TH"),
                _course("SH109", "Sinh thái học", "LT")]),
            ("CNSH", "Bộ môn Công nghệ sinh học", [
                _course("SH103", "Hóa sinh học", "LT"), _course("SH105", "Di truyền học", "LT"),
                _course("SH107", "Công nghệ gen", "TH"), _course("SH108", "Đồ án công nghệ sinh học", "DA")]),
        ],
        teachers=[
            ("gv.huynhthanhson", "Huỳnh Thanh", "Sơn"), ("gv.nguyenkimngan", "Nguyễn Kim", "Ngân"),
            ("gv.tranvanloc", "Trần Văn", "Lộc"), ("gv.phanthiyen", "Phan Thị", "Yến"),
            ("gv.ngoquangtruong", "Ngô Quang", "Trường"),
        ],
        assignments={
            "SH101": (0, ()), "SH102": (0, (4,)), "SH104": (1, ()), "SH106": (2, ()), "SH109": (2, ()),
            "SH103": (3, ()), "SH105": (3, ()), "SH107": (1, ()), "SH108": (4, ()),
        },
    ),
]

# Lớp học phần chung: sinh viên các khoa khác học thêm một lớp Tiếng Anh 1 (ca "SV học môn của khoa khác",
# "một học phần nhiều lớp"). Sinh viên Khoa Ngoại ngữ không học các lớp này.
SHARED_COURSES = ("NN101_N01", "NN101_N02", "NN101_N03", "NN101_N04")
SHARED_COURSE_RATE = 0.40

# Tài khoản dịch vụ gửi tin nhắn Moodle (trên Moodle thật quản trị tạo tài khoản tương tự + token web service)
SERVICE_ACCOUNT = dict(username="lmsanalytics", lastname="Hệ thống", firstname="Cảnh báo học tập",
                       email=f"canhbao.lms@{STAFF_EMAIL_DOMAIN}", idnumber="SVC-LMS",
                       department="Phòng Khảo thí và Đảm bảo chất lượng")
# Tùy chọn nhận tin (Moodle 3.6+: message_blocknoncontacts 0 = chỉ liên hệ, 1 = thành viên chung khóa học, 2 = cả site)
ONLY_CONTACTS_RATE = 0.01

# ----------------------------------------------------------------------------- sinh viên & ghi danh
# MOCK_N_STUDENTS (chỉ dùng cho bộ dữ liệu đo hiệu năng ETL – perf/etl_bench.py, CSDL riêng) co giãn số sinh viên
# các khoa theo cùng tỷ lệ.
_BASE_STUDENTS = sum(f["students"] for f in FACULTIES)
N_STUDENTS = int(os.getenv("MOCK_N_STUDENTS", str(_BASE_STUDENTS)))
if N_STUDENTS != _BASE_STUDENTS:
    for _f in FACULTIES:
        _f["students"] = max(10, round(_f["students"] * N_STUDENTS / _BASE_STUDENTS))
    N_STUDENTS = sum(f["students"] for f in FACULTIES)
STUDENT_CODE_PREFIX = "22"        # MSSV = 22 + chữ số khoa + 2 + số thứ tự 3 chữ số (CNTT: 2212001…)
COURSES_PER_STUDENT = (3, 5)      # số môn của khoa mình mỗi sinh viên học
SUSPENDED_STUDENTS = 12           # mdl_user.suspended = 1 (ETL phải loại)
DELETED_STUDENTS = 6              # mdl_user.deleted = 1 (ETL phải loại)
SUSPENDED_ENROLMENT_RATE = 0.02   # mdl_user_enrolments.status = 1 ("hủy/tạm dừng ghi danh")
EXPIRED_ENROLMENT_RATE = 0.01     # timeend rơi vào tuần 3 của học kỳ
EXPIRED_AFTER_WEEKS = 3

# ----------------------------------------------------------------------------- nội dung môn học theo loại
# Bài tập: (tuần hạn nộp, tên). Hạn nộp Chủ nhật 23:59 của tuần đó.
ASSIGNMENT_PLAN: dict[str, list[tuple[int, str]]] = {
    "LT": [(5, "Bài kiểm tra 1"), (9, "Tiểu luận giữa kỳ"), (13, "Bài kiểm tra 2")],
    "TH": [(w, f"Báo cáo thực hành tuần {w}") for w in range(2, 14)],
    "DA": [(w, f"Báo cáo tiến độ tuần {w}") for w in range(2, 14)] + [(15, "Báo cáo cuối kỳ")],
}
# Hoạt động điểm danh: (tên, số buổi mỗi tuần (min, max), là buổi thực hành – chia nhóm ở môn LAB_GROUP_COURSES)
ATTENDANCE_PLAN: dict[str, list[tuple[str, tuple[int, int], bool]]] = {
    "LT": [("Điểm danh", (1, 2), False)],
    "TH": [("Điểm danh lý thuyết", (1, 1), False), ("Điểm danh thực hành", (1, 1), True)],
    "DA": [("Gặp giảng viên hướng dẫn", (1, 1), False)],
}
ASSIGNMENT_OPEN_DAYS = 14               # mở nộp trước hạn 14 ngày
ATTENDANCE_SLOT_HOURS = (7, 13)         # buổi sáng 07:00 hoặc chiều 13:00
TEAM_SUBMISSION_COURSES = ("IT008", "IT009", "KT110")   # ca biên: một bài nộp theo nhóm
TEAM_SIZE = 4
LAB_GROUP_COURSES = ("IT013", "SH102")         # ca biên: buổi thực hành gắn nhóm (groupid <> 0)
LAB_GROUPS = 2
NO_ATTENDANCE_SESSION_COURSES = ("IT015",)     # ca biên: môn chưa có buổi điểm danh

# Tương thích ngược cho mã/kiểm thử cũ
FACULTY = (FACULTIES[0]["code"], FACULTIES[0]["name"])
TEACHERS = [t for f in FACULTIES for t in f["teachers"]]
ALL_COURSES = {c[0]: (f["code"], c[1], c[2]) for f in FACULTIES for _, _, cs in f["departments"] for c in cs}

# ----------------------------------------------------------------------------- hồ sơ hành vi (SPEC 3.2)
PROFILES: dict[str, float] = {"GREEN": 0.65, "YELLOW": 0.20, "RED": 0.15}   # mặc định; từng khoa có "profiles" riêng
PROFILE_CONSISTENCY = 0.80   # 80% cặp SV–môn giữ hồ sơ chung của SV

BEHAVIOR: dict[str, dict] = {
    "GREEN":  dict(sessions_per_week=(4, 9), attend=0.95, submit=0.95, late=0.05, never=0.00, dropout=0.00, post_rate=0.05),
    "YELLOW": dict(sessions_per_week=(1, 4), attend=0.80, submit=0.70, late=0.25, never=0.00, dropout=0.10, post_rate=0.03),
    "RED":    dict(sessions_per_week=(0, 1), attend=0.50, submit=0.30, late=0.40, never=0.35, dropout=0.30, post_rate=0.02),
}
RED_MAX_SUBMIT_RATIO = 0.40      # RED: nộp tối đa 40% số bài đã tới hạn (đảm bảo thiếu ≥ 60%)
RED_FUTURE_SUBMIT_PROB = 0.30
DROPOUT_FROM_WEEK_INDEX = 6      # "bỏ dần": hoạt động giảm từ tuần thứ 7 (chỉ số 0-based = 6)
DROPOUT_ACTIVITY_DIVISOR = 3
DROPOUT_ATTEND_FACTOR = 0.60
DROPOUT_SUBMIT_FACTOR = 0.30

# ----------------------------------------------------------------------------- phân bổ thời gian (SPEC 3.2)
HOUR_WEIGHTS = np.array([.3, .2, .1, .1, .1, .2, .6, 1.5, 3.0, 3.2, 3.0, 2.0,
                         1.0, 1.5, 3.0, 3.2, 2.8, 1.8, 1.2, 1.4, 1.8, 1.6, 1.0, .6])
HOUR_P = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()
DOW_WEIGHTS = np.array([1, 1, 1, 1, 1, .5, .4])   # Thứ 2 ... Chủ nhật
DOW_P = DOW_WEIGHTS / DOW_WEIGHTS.sum()
MIDTERM_WEEK = 8                  # tuần 8 (1-based) – thi giữa kỳ
MIDTERM_FACTOR = 1.5
DEADLINE_WINDOW_DAYS = 2          # 48 giờ trước hạn nộp
DEADLINE_FACTOR = 2.5

# ----------------------------------------------------------------------------- chi tiết phiên truy cập
ACTIONS_PER_SESSION = (3, 15)     # thao tác trong môn mỗi phiên (không tính sự kiện đăng nhập)
ACTION_GAP_SECONDS = (20, 180)
MOBILE_SESSION_RATE = 0.10        # origin = 'ws' (ứng dụng Moodle Mobile)
FAILED_LOGIN_RATE = 0.005
ACTION_MIX = dict(page=0.55, assign=0.25)   # phần còn lại: xem diễn đàn / đăng bài (post_rate)
NEW_SUBMISSION_ROW_RATE = 0.30    # SV mở bài tập nhưng chưa nộp -> dòng status = 'new'
MISSING_ATTENDANCE_LOG_RATE = 0.01
ATTENDANCE_TAKEN_DELAY = 900      # GV điểm danh sau 15 phút đầu buổi
ONLINE_SESSION_TIMEOUT = 1800     # mdl_sessions: phiên còn hiệu lực trong 30 phút
