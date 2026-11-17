"""
Manifest của đợt dữ liệu thật Moodle 3.11 (khoa CNTT, xuất 12/11/2026).

Mỗi bảng khai báo: file CSV, thứ tự cột trong file (None = đúng thứ tự Moodle 3.11), điều kiện phạm vi khi chuyển
từ vùng đệm stg sang bảng mdl_*, và biểu thức ghi đè cho từng cột đích. Đợt dữ liệu sau (hoặc mở rộng ra toàn
trường) chỉ cần sửa file này, không sửa ingest/loader.py.

Quy ước trong biểu thức SQL: `s` là bí danh của bảng đệm stg.<bảng> (mọi cột kiểu text),
`stg.scope_course` chứa id các môn trong phạm vi.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Thư mục con trong REAL_DATA_DIR
BATCH1 = "Data_11-2026"
BATCH2 = "NEW/NEW"

IN_SCOPE = "(SELECT id FROM stg.scope_course)"


@dataclass(frozen=True)
class Source:
    table: str                                   # tên bảng Moodle, không tiền tố
    file: str                                    # đường dẫn tương đối trong REAL_DATA_DIR
    columns: tuple[str, ...] | None = None       # None = thứ tự cột Moodle 3.11
    scope: str | None = None                     # điều kiện WHERE khi chuyển stg -> mdl_ (None = lấy hết)
    overrides: dict[str, str] = field(default_factory=dict)   # cột đích -> biểu thức SQL
    skip: tuple[str, ...] = ()                   # cột nguồn KHÔNG nạp (nhạy cảm)
    optional: bool = False                       # file chưa có thì bỏ qua (bảng đích để rỗng)
    stage: str | None = None                     # tên bảng đệm stg khi một bảng đích nạp từ nhiều file

    @property
    def stage_name(self) -> str:
        return self.stage or self.table


# File xác định phạm vi: danh sách môn được nạp và tính toán (cột đầu tiên là id môn).
SCOPE_FILE = f"{BATCH1}/dlu_course_cntt.csv"

# Danh mục cha không có trong file danh mục (file chỉ chứa cấp 3–4 của khoa CNTT).
# Tên lấy từ đường dẫn danh mục của các môn; cần để ETL xác định Khoa = phần tử đầu của path.
# (id, name, parent, depth, path)
DERIVED_CATEGORIES: tuple[tuple[int, str, int, int, str], ...] = (
    (2, "Khoa Công nghệ Thông tin", 0, 1, "/2"),
    (4, "Chuyên ngành Mạng và Truyền thông", 2, 2, "/2/4"),
    (5, "Chuyên ngành Kỹ thuật phần mềm", 2, 2, "/2/5"),
    (6, "Cơ sở ngành", 2, 2, "/2/6"),
)

# Thứ tự khai báo = thứ tự chuyển sang mdl_* (bảng sau lọc theo bảng trước đã nạp).
SOURCES: tuple[Source, ...] = (
    # ------------------------------------------------------------------ danh mục, môn học, cấu trúc
    Source("course_categories", f"{BATCH1}/dlu_course_categories_cntt.csv"),
    Source("course", f"{BATCH1}/dlu_course.csv", scope=f"s.id::bigint IN {IN_SCOPE}"),
    Source("modules", f"{BATCH1}/dlu_modules.csv"),
    Source("course_sections", f"{BATCH1}/dlu_course_sections.csv", scope=f"s.course::bigint IN {IN_SCOPE}"),
    Source("course_modules", f"{BATCH1}/dlu_course_modules_cntt.csv", scope=f"s.course::bigint IN {IN_SCOPE}"),
    # ------------------------------------------------------------------ vai trò, ghi danh
    Source("role", f"{BATCH1}/dlu_role.csv"),
    Source("context", f"{BATCH1}/dlu_context.csv",
           scope=f"s.contextlevel = '10' OR (s.contextlevel = '50' AND s.instanceid::bigint IN {IN_SCOPE})"),
    Source("role_assignments", f"{BATCH1}/dlu_role_assignments.csv",
           scope="s.contextid::bigint IN (SELECT id FROM mdl_context)"),
    Source("enrol", f"{BATCH1}/dlu_enrol.csv", scope=f"s.courseid::bigint IN {IN_SCOPE}",
           skip=("password",)),                                   # khóa ghi danh
    Source("user_enrolments", f"{BATCH1}/dlu_user_enrolments.csv",
           scope="s.enrolid::bigint IN (SELECT id FROM mdl_enrol)"),
    # ------------------------------------------------------------------ nhóm
    Source("groups", f"{BATCH2}/dlu_groups.csv",
           columns=("id", "courseid", "idnumber", "name", "description", "descriptionformat",
                    "timecreated", "timemodified"),               # file đã bỏ enrolmentkey, picture
           scope=f"s.courseid::bigint IN {IN_SCOPE}"),
    Source("groups_members", f"{BATCH2}/dlu_groups_members.csv",
           scope="s.groupid::bigint IN (SELECT id FROM mdl_groups)"),
    Source("groupings", f"{BATCH2}/dlu_groupings.csv", scope=f"s.courseid::bigint IN {IN_SCOPE}"),
    # ------------------------------------------------------------------ người dùng (sau ghi danh/vai trò/nhóm)
    Source("user", f"{BATCH2}/dlu_user.csv",
           # File 15 cột theo thứ tự tự chọn của người xuất (đã dò bằng mẫu dữ liệu, đối chiếu file đợt 1).
           # Cột họ đệm (dài, có dấu cách) -> lastname, cột tên (ngắn) -> firstname: hệ thống hiển thị
           # "lastname firstname" nên ra đúng "Họ đệm Tên".
           columns=("id", "auth", "deleted", "suspended", "mnethostid", "username", "idnumber", "email",
                    "lastname", "firstname", "x_time1", "x_time2", "x_time3", "x_unknown", "timecreated"),
           scope=("s.deleted = '0' AND s.id::bigint IN ("
                  "SELECT userid FROM mdl_user_enrolments UNION SELECT userid FROM mdl_role_assignments "
                  "UNION SELECT userid FROM mdl_groups_members)"),
           overrides={"password": "''", "confirmed": "1"}),
    # Bổ sung tài khoản có vai trò / ghi danh nhưng vắng trong file đợt 2 (dữ liệu thật: id 3 – giảng viên của
    # 23 môn). File đợt 1 chỉ có 5 cột, không có họ tên: họ tên lấy từ tệp sửa tên (common/person_name.py).
    Source("user", f"{BATCH1}/dlu_user.csv", stage="user_batch1",
           columns=("id", "auth", "deleted", "username", "email"),
           scope=("s.deleted = '0' AND s.id::bigint NOT IN (SELECT id FROM mdl_user) AND s.id::bigint IN ("
                  "SELECT userid FROM mdl_user_enrolments UNION SELECT userid FROM mdl_role_assignments)"),
           overrides={"password": "''", "confirmed": "1", "mnethostid": "1"}),
    # ------------------------------------------------------------------ bài tập
    Source("assign", f"{BATCH1}/dlu_assign.csv", scope=f"s.course::bigint IN {IN_SCOPE}"),
    Source("assign_submission", f"{BATCH1}/dlu_assign_submission.csv",
           scope="s.assignment::bigint IN (SELECT id FROM mdl_assign)"),
    Source("assign_grades", f"{BATCH1}/dlu_assign_grades.csv",
           scope="s.assignment::bigint IN (SELECT id FROM mdl_assign)"),
    Source("assign_overrides", f"{BATCH2}/dlu_assign_overrides.csv", optional=True,
           scope="s.assignid::bigint IN (SELECT id FROM mdl_assign)"),
    Source("assign_user_flags", f"{BATCH2}/dlu_assign_user_flags.csv", optional=True,
           scope="s.assignment::bigint IN (SELECT id FROM mdl_assign)"),
    # ------------------------------------------------------------------ sổ điểm
    Source("scale", f"{BATCH2}/dlu_scale.csv"),
    Source("grade_categories", f"{BATCH2}/dlu_grade_categories.csv", scope=f"s.courseid::bigint IN {IN_SCOPE}"),
    Source("grade_items", f"{BATCH1}/dlu_grade_items.csv", scope=f"s.courseid::bigint IN {IN_SCOPE}"),
    Source("grade_grades", f"{BATCH1}/dlu_grade_grades.csv",
           scope="s.itemid::bigint IN (SELECT id FROM mdl_grade_items)"),
    # ------------------------------------------------------------------ quiz
    Source("quiz", f"{BATCH2}/dlu_quiz_cntt.csv", scope=f"s.course::bigint IN {IN_SCOPE}",
           skip=("password",)),
    Source("quiz_attempts", f"{BATCH1}/dlu_quiz_attempts_cntt.csv",
           scope="s.quiz::bigint IN (SELECT id FROM mdl_quiz)"),
    Source("quiz_grades", f"{BATCH1}/dlu_quiz_grades_cntt.csv",
           scope="s.quiz::bigint IN (SELECT id FROM mdl_quiz)"),
    Source("quiz_overrides", f"{BATCH2}/dlu_quiz_overrides.csv", optional=True,
           scope="s.quiz::bigint IN (SELECT id FROM mdl_quiz)", skip=("password",)),
    # ------------------------------------------------------------------ hoàn thành hoạt động (chưa có file)
    Source("course_modules_completion", f"{BATCH2}/dlu_course_modules_completion.csv", optional=True,
           scope="s.coursemoduleid::bigint IN (SELECT id FROM mdl_course_modules)"),
    # ------------------------------------------------------------------ nhật ký, phiên, thông báo
    Source("logstore_standard_log", f"{BATCH2}/dlu_logstore_standard_log.csv",
           scope=f"s.courseid::bigint IN {IN_SCOPE} OR s.courseid IN ('0', '1')",
           skip=("ip", "other")),                                 # địa chỉ IP và dữ liệu kèm sự kiện
    Source("sessions", f"{BATCH2}/dlu_sessions.csv",
           columns=("id", "state", "userid", "timecreated", "timemodified"),   # file đã bỏ sid, sessdata, ip
           scope="s.userid::bigint IN (SELECT id FROM mdl_user)",
           overrides={"sid": "'csv-' || s.id"}),
    Source("notifications", f"{BATCH2}/dlu_notifications.csv",
           scope="s.useridto::bigint IN (SELECT id FROM mdl_user)"),
)

# Kiểm tra bản ghi mồ côi sau khi nạp: (bảng con, cột, bảng cha, điều kiện bỏ qua)
ORPHAN_CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("course", "category", "course_categories", "TRUE"),
    ("course_modules", "course", "course", "TRUE"),
    ("course_modules", "module", "modules", "TRUE"),
    ("course_sections", "course", "course", "TRUE"),
    ("enrol", "courseid", "course", "TRUE"),
    ("user_enrolments", "userid", "user", "TRUE"),
    ("role_assignments", "userid", "user", "TRUE"),
    ("role_assignments", "roleid", "role", "TRUE"),
    ("groups_members", "userid", "user", "TRUE"),
    ("assign_submission", "userid", "user", "c.userid <> 0"),
    ("assign_submission", "groupid", "groups", "c.groupid <> 0"),
    ("grade_items", "categoryid", "grade_categories", "c.categoryid IS NOT NULL"),
    ("grade_grades", "userid", "user", "TRUE"),
    ("quiz_attempts", "userid", "user", "TRUE"),
    ("logstore_standard_log", "userid", "user", "c.userid > 0"),
)
