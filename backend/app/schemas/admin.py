"""Schema các endpoint Admin 1.1, 1.2."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from backend.app.schemas.common import Page, Stamped


class PeakRequests(BaseModel):
    hour: str
    stat_hour: datetime
    value: int


class KpisOut(Stamped):
    academic_year: str
    semester: int
    faculty_id: int | None
    stat_date: date | None
    total_courses: int
    total_enrolled: int
    total_active: int
    active_rate: float
    red_students: int
    yellow_students: int
    green_students: int
    red_rate: float
    peak_requests_today: PeakRequests | None
    avg_online_users_today: float
    current_online: int
    current_online_at: datetime | None
    unique_students: int = 0                   # sinh viên khác nhau (một SV học nhiều môn tính một lần)
    red_rate_prev_week: float | None = None    # tỷ lệ đỏ 7 ngày trước – cho dòng "so với tuần trước"


class FacultyEnrollment(BaseModel):
    faculty_id: int
    faculty_name: str
    course_count: int
    enrolled: int
    active: int
    inactive: int
    active_rate: float
    red_count: int
    yellow_count: int
    green_count: int


class FacultyEnrollmentOut(Stamped):
    academic_year: str
    semester: int
    items: list[FacultyEnrollment]


class CourseEnrollment(BaseModel):
    course_id: int
    shortname: str
    fullname: str
    category_id: int
    category_name: str
    stat_date: date
    enrolled: int
    active: int
    inactive: int
    active_rate: float
    red_count: int
    yellow_count: int
    green_count: int
    avg_completion_rate: float | None          # None = chưa có dữ liệu (migration V007)
    assignment_submission_rate: float | None
    attendance_rate: float | None
    red_rate: float | None = None
    yellow_rate: float | None = None
    green_rate: float | None = None
    rule_scope: str | None = None              # GLOBAL = luật mặc định, COURSE = luật riêng của môn
    rule_label: str | None = None


class FacultySummary(BaseModel):
    faculty_id: int
    faculty_name: str
    course_count: int
    enrolled: int
    unique_students: int
    active: int
    avg_active_rate: float | None
    avg_submission_rate: float | None
    avg_attendance_rate: float | None
    red: int
    yellow: int
    green: int
    red_rate: float | None
    red_rate_delta_week: float | None
    custom_rule_courses: int
    school_enrolled: int | None = None
    school_active_rate: float | None
    school_red_rate: float | None
    school_submission_rate: float | None = None     # so sánh KPI khoa với toàn trường (kế hoạch Mục 3.3)
    school_attendance_rate: float | None = None


class CourseEnrollmentOut(Stamped):
    faculty_id: int
    academic_year: str
    semester: int
    items: list[CourseEnrollment]
    summary: FacultySummary | None = None


class CourseHeader(BaseModel):
    course_id: int
    shortname: str
    fullname: str
    faculty_id: int
    faculty_name: str
    category_name: str
    academic_year: str
    semester: int
    enrolled: int
    active: int


class CourseStudent(BaseModel):
    user_id: int
    student_code: str | None
    student_name: str
    email: str | None
    is_active: bool
    total_access_count: int
    access_count_7d: int
    last_access_time: datetime | None
    days_since_last_access: int | None
    risk_level: str
    risk_score: int


class CourseStudentsOut(Page[CourseStudent]):
    course: CourseHeader
    snapshot_date: date


class TrafficHour(BaseModel):
    stat_hour: datetime
    stat_date: date
    hour_of_day: int
    day_of_week: int
    total_requests: int
    unique_users: int
    login_count: int
    failed_login_count: int
    ws_requests: int
    peak_online_users: int
    avg_online_users: float
    online_sample_count: int
    is_peak_hour: bool


class TrafficHourlyOut(Stamped):
    from_date: date
    to_date: date
    items: list[TrafficHour]


class RealtimeOut(Stamped):
    current_hour: datetime
    current_online: int
    current_online_at: datetime | None
    current_online_source: str | None
    requests_current_hour: int
    requests_so_far: int
    series_24h: list[TrafficHour]


class HeatCell(BaseModel):
    day_of_week: int
    hour_of_day: int
    avg_requests: float
    avg_online_users: float
    peak_share: float
    days: int


class HeatmapOut(Stamped):
    weeks: int
    from_date: date
    to_date: date
    matrix: list[HeatCell]


class FacultyCompareItem(BaseModel):
    faculty_id: int
    faculty_name: str
    course_count: int
    enrolled: int
    unique_students: int
    active: int
    inactive: int
    active_rate: float | None
    avg_submission_rate: float | None
    avg_attendance_rate: float | None
    red: int
    yellow: int
    green: int
    red_rate: float | None
    yellow_rate: float | None
    green_rate: float | None
    red_rate_delta_week: float | None
    custom_rule_courses: int


class SchoolSummary(BaseModel):
    enrolled: int
    unique_students: int
    active: int
    course_count: int
    red: int
    yellow: int
    green: int
    active_rate: float | None
    red_rate: float | None
    yellow_rate: float | None
    green_rate: float | None
    avg_submission_rate: float | None = None
    avg_attendance_rate: float | None = None


class FacultyCompareOut(Stamped):
    academic_year: str
    semester: int
    school: SchoolSummary
    items: list[FacultyCompareItem]


class TrendPoint(BaseModel):
    period: str
    period_start: date
    period_end: date
    stat_date: date
    red: int
    yellow: int
    green: int
    total: int
    courses: int
    red_rate: float | None
    yellow_rate: float | None
    green_rate: float | None


class RuleChange(BaseModel):
    date: date
    course_id: int
    label: str


class RiskTrendOut(Stamped):
    academic_year: str
    semester: int
    scope: str                                 # school | faculty | course
    granularity: str
    week1_start: date
    series: list[TrendPoint]
    rule_changes: list[RuleChange]
