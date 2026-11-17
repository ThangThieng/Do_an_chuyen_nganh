"""
Trích xuất bộ dữ liệu của các môn đang diễn ra tại một thời điểm AS_OF.

Dùng chung cho job rủi ro sinh viên và job tiến độ môn học. Mọi truy vấn chạy trong MỘT transaction
REPEATABLE READ chỉ đọc, nên các bảng được đọc trên cùng một ảnh chụp dữ liệu, không lệch nhau.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy import Engine, text

from etl.db import read_frame
from etl.extract import load_sql
from etl.transform.semester import academic_term, category_term, term_start

log = logging.getLogger(__name__)

DATASET_QUERIES = ("enrolments", "interaction", "weekly_activity", "attendance", "assignments", "completion",
                   "submissions_day", "attendance_grades", "section_access")
ATTENDANCE_GRADE_COLUMNS = ["course_id", "user_id", "attendance_id", "attendance_name", "points", "max_points"]
SECTION_ACCESS_COLUMNS = ["course_id", "section_no", "section_name", "modules", "students_opened"]

# Cột epoch có thể NULL. Nếu MỌI dòng đều NULL (vd đầu học kỳ chưa có bài nộp), pandas suy ra kiểu object/None
# thay vì số -> ép về kiểu số nguyên nullable Int64 để Transform luôn nhận cùng một kiểu dữ liệu.
NULLABLE_EPOCH_COLUMNS: dict[str, tuple[str, ...]] = {
    "interaction": ("last_access_ts", "log_last_access_ts"),
    "assignments": ("submitted_ts",),
}


@dataclass
class CourseDataset:
    as_of: datetime            # thời điểm tham chiếu (có múi giờ địa phương)
    day_start: datetime        # 00:00 cùng ngày với as_of
    courses: pd.DataFrame
    enrolments: pd.DataFrame
    interaction: pd.DataFrame
    weekly_activity: pd.DataFrame
    attendance: pd.DataFrame
    assignments: pd.DataFrame
    completion: pd.DataFrame
    submissions_day: pd.DataFrame
    # Chuyên cần lấy từ sổ điểm cho môn không có dữ liệu buổi của mod_attendance (attendance_grades.sql)
    attendance_grades: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=ATTENDANCE_GRADE_COLUMNS))
    # Số SV đã mở nội dung theo chương – thay "hoàn thành theo chương" khi môn không có dữ liệu hoàn thành
    section_access: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=SECTION_ACCESS_COLUMNS))
    # Thời điểm của dòng log đầu tiên (dữ liệu thật: 13/09/2026) – để lý do cảnh báo nói rõ "từ ngày nào"
    log_start_ts: int | None = None

    def __post_init__(self) -> None:
        for frame_name, columns in NULLABLE_EPOCH_COLUMNS.items():
            df = getattr(self, frame_name)
            present = {c: df[c].astype("Int64") for c in columns if c in df.columns}
            if present:
                setattr(self, frame_name, df.assign(**present))

    @property
    def as_of_ts(self) -> int:
        return int(self.as_of.timestamp())

    @property
    def course_ids(self) -> list[int]:
        return [int(x) for x in self.courses["course_id"]]

    @property
    def source_rows(self) -> int:
        return sum(len(getattr(self, name)) for name in ("courses",) + DATASET_QUERIES)


def warn_term_mismatch(courses: pd.DataFrame) -> list[int]:
    """Ghi cảnh báo các môn có học kỳ trong tên danh mục khác học kỳ suy từ ngày bắt đầu (vẫn tính như bình thường)."""
    if "term_category_name" not in courses:
        return []
    odd = []
    for c in courses.itertuples(index=False):
        named = category_term(c.year_category_name, c.term_category_name)
        if named is not None and named != academic_term(int(c.startdate)):
            odd.append(int(c.course_id))
    if odd:
        log.warning("%d môn có học kỳ theo danh mục khác học kỳ theo ngày bắt đầu (vẫn tính theo ngày bắt đầu): %s",
                    len(odd), ", ".join(map(str, odd)))
    return odd


def start_of_day(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def extract_course_dataset(moodle: Engine, as_of: datetime) -> CourseDataset:
    day_start = start_of_day(as_of)
    params = {"as_of": int(as_of.timestamp()), "day_start": int(day_start.timestamp()),
              "term_start": int(term_start(as_of).timestamp())}
    with moodle.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        courses = read_frame(conn, load_sql("courses"), params)
        warn_term_mismatch(courses)
        params["course_ids"] = [int(x) for x in courses["course_id"]]
        frames = {name: read_frame(conn, load_sql(name), params) for name in DATASET_QUERIES}
        log_start = conn.execute(text("SELECT MIN(timecreated) FROM mdl_logstore_standard_log")).scalar()
    return CourseDataset(as_of=as_of, day_start=day_start, courses=courses, **frames,
                         log_start_ts=int(log_start) if log_start else None)
