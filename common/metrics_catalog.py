"""
Danh mục chỉ số hiển thị trên Dashboard – NGUỒN DUY NHẤT cho ngăn "Nguồn & cách tính", trang Trợ giúp và tài liệu.

Mỗi chỉ số ghi: ý nghĩa, công thức, đơn vị, bảng Moodle nguồn (lược đồ Moodle 3.9), bảng phân tích và job ETL.
Ngưỡng/trọng số KHÔNG viết ở đây: API ghép vào từ bộ luật đang áp dụng (etl/rules.py, bảng risk_rule_set),
để giao diện không bao giờ lệch với cách ETL thực sự tính.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

ENROL_TABLES = ("mdl_user_enrolments", "mdl_enrol", "mdl_role_assignments", "mdl_role", "mdl_context", "mdl_user")
ATTENDANCE_TABLES = ("mdl_attendance", "mdl_attendance_sessions", "mdl_attendance_log", "mdl_attendance_statuses")
ASSIGN_TABLES = ("mdl_assign", "mdl_assign_submission", "mdl_groups_members", "mdl_course_modules")

ETL_JOBS = {
    "student_risk": "07:15–21:15, 2 giờ/lần; chốt ngày lúc 01:00",
    "course_progress": "phút 05 mỗi giờ",
    "traffic": "mỗi 5 phút",
}


@dataclass(frozen=True)
class Metric:
    key: str
    name: str
    description: str
    formula: str
    unit: str
    moodle_tables: tuple[str, ...]
    analytics_table: str
    etl_job: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["moodle_tables"] = list(self.moodle_tables)
        d["schedule"] = ETL_JOBS.get(self.etl_job, "")
        return d


METRICS: tuple[Metric, ...] = (
    Metric("enrolled", "Lượt ghi danh",
           "Số cặp (sinh viên, môn) có ghi danh còn hiệu lực",
           "Ghi danh status = 0, phương thức đang bật, vai trò student, tài khoản không bị xóa/khóa, trong thời hạn",
           "lượt", ENROL_TABLES, "fact_course_progress_daily", "course_progress"),
    Metric("unique_students", "Sinh viên duy nhất",
           "Số sinh viên khác nhau (một sinh viên học nhiều môn chỉ tính một lần)",
           "COUNT(DISTINCT user_id) trên snapshot rủi ro mới nhất của phạm vi",
           "sinh viên", ENROL_TABLES, "fact_student_risk_summary", "student_risk"),
    Metric("active_rate", "Tỷ lệ tương tác",
           "Phần trăm lượt ghi danh có ít nhất một hoạt động trong môn từ đầu học kỳ",
           "Số sinh viên có sự kiện trong môn ÷ lượt ghi danh × 100",
           "%", ("mdl_logstore_standard_log",), "fact_course_progress_daily", "course_progress"),
    Metric("submission_rate", "Tỷ lệ nộp bài",
           "Phần trăm bài đã nộp trên số bài đã tới hạn",
           "Bài nộp hợp lệ (status = submitted, bản mới nhất) ÷ bài đã tới hạn × 100; bài nộp nhóm tính cho cả nhóm",
           "%", ASSIGN_TABLES, "fact_course_progress_daily", "course_progress"),
    Metric("attendance_rate", "Chuyên cần",
           "Phần trăm lượt có mặt trên số lượt điểm danh đã diễn ra",
           "Lượt có mặt (P, L, E) ÷ lượt điểm danh đã diễn ra × 100; môn chưa có buổi điểm danh = Chưa có dữ liệu",
           "%", ATTENDANCE_TABLES, "fact_course_progress_daily", "course_progress"),
    Metric("c1_attendance", "C1 – Vắng học",
           "Mức vắng học của sinh viên trong môn",
           "Tỷ lệ vắng = buổi vắng ÷ buổi đã điểm danh; so với hai ngưỡng của luật đang áp dụng → 0, 1 hoặc 2 điểm",
           "điểm 0–2", ATTENDANCE_TABLES, "fact_student_risk_summary", "student_risk"),
    Metric("c2_inactivity", "C2 – Không tương tác",
           "Mức không tương tác với môn học trên Moodle",
           "2 điểm: chưa từng vào hoặc quá ngưỡng ngày (mức cao); 1 điểm: quá ngưỡng ngày (mức thấp) hoặc lượt truy cập "
           "14 ngày dưới tỷ lệ so với trung vị lớp; còn lại 0 điểm",
           "điểm 0–2", ("mdl_logstore_standard_log",), "fact_student_risk_summary", "student_risk"),
    Metric("c3_assignment", "C3 – Thiếu bài tập",
           "Mức thiếu bài tập đã tới hạn",
           "Tỷ lệ thiếu = bài thiếu ÷ bài đã tới hạn; so với hai ngưỡng của luật đang áp dụng → 0, 1 hoặc 2 điểm",
           "điểm 0–2", ASSIGN_TABLES, "fact_student_risk_summary", "student_risk"),
    Metric("risk_score", "Điểm rủi ro",
           "Điểm tổng hợp 0–100 từ 3 tiêu chí theo trọng số của luật đang áp dụng",
           "round(100 × (wC1·C1 + wC2·C2 + wC3·C3) ÷ 2)",
           "điểm 0–100", ATTENDANCE_TABLES + ("mdl_logstore_standard_log",) + ASSIGN_TABLES,
           "fact_student_risk_summary", "student_risk"),
    Metric("risk_level", "Mức rủi ro",
           "Đèn giao thông: Nguy cơ cao / Cần lưu ý / An toàn",
           "Nguy cơ cao khi C2 = 2, hoặc ≥ 2 tiêu chí đạt 2 điểm, hoặc tổng điểm ≥ 4, hoặc khớp luật bổ sung mức đỏ "
           "của môn; Cần lưu ý khi tổng ≥ 1 hoặc khớp luật bổ sung mức vàng; còn lại An toàn",
           "mức", ATTENDANCE_TABLES + ("mdl_logstore_standard_log",) + ASSIGN_TABLES,
           "fact_student_risk_summary", "student_risk"),
    Metric("risk_trend", "Xu hướng mức rủi ro",
           "Tỷ lệ Đỏ/Vàng/Xanh của phạm vi theo thời gian",
           "Tại ngày cuối mỗi tuần (tuần hiện tại: hôm nay): số lượt ghi danh mỗi mức ÷ tổng lượt ghi danh × 100",
           "%", (), "fact_course_progress_daily", "course_progress"),
    Metric("max_consecutive_missing", "Bỏ nộp liên tiếp",
           "Số bài đã tới hạn bị bỏ nộp liên tiếp dài nhất (dùng cho luật bổ sung của môn)",
           "Xếp các bài đã tới hạn theo hạn nộp, đếm chuỗi “thiếu” dài nhất",
           "bài", ASSIGN_TABLES, "fact_student_risk_summary", "student_risk"),
    Metric("traffic", "Lưu lượng truy cập",
           "Số sự kiện (requests) theo giờ và người dùng online",
           "Đếm sự kiện logstore theo giờ địa phương; online = phiên có hoạt động trong 5 phút; giờ cao điểm vượt P90 28 ngày",
           "sự kiện/giờ", ("mdl_logstore_standard_log", "mdl_sessions"), "fact_server_traffic_hourly", "traffic"),
)
BY_KEY = {m.key: m for m in METRICS}

PIPELINE = (
    "Moodle (các bảng nguồn – chỉ đọc)",
    "Job ETL trích xuất – biến đổi – nạp",
    "CSDL phân tích lms_analytics",
    "API LMS Analytics",
    "Biểu đồ / bảng trên Dashboard",
)


def catalog(keys: list[str] | None = None) -> list[dict]:
    items = METRICS if not keys else tuple(BY_KEY[k] for k in keys if k in BY_KEY)
    return [m.to_dict() for m in items]
