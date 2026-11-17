"""Suy ra năm học / học kỳ từ ngày bắt đầu môn học (Moodle không có sẵn khái niệm này) – SPEC Phần 1.1."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from etl.config import SEMESTER_BY_MONTH, TZ


def academic_term(course_start: datetime | int) -> tuple[str, int]:
    """
    Trả về (academic_year, semester), ví dụ 07/09/2026 -> ('2026-2027', 1); 15/02/2027 -> ('2026-2027', 2).
    course_start: datetime có múi giờ hoặc epoch giây (mdl_course.startdate).
    """
    if isinstance(course_start, (int, float)):
        if course_start <= 0:
            raise ValueError("mdl_course.startdate = 0: môn học chưa đặt ngày bắt đầu, không suy ra được học kỳ")
        course_start = datetime.fromtimestamp(course_start, TZ)
    elif course_start.tzinfo is None:
        raise ValueError("course_start phải có múi giờ")

    local = course_start.astimezone(TZ)
    semester = SEMESTER_BY_MONTH[local.month]
    first_year = local.year if semester == 1 else local.year - 1
    return f"{first_year}-{first_year + 1}", semester


def term_start(moment: datetime) -> datetime:
    """
    00:00 ngày đầu tiên của học kỳ chứa `moment` theo SEMESTER_BY_MONTH (vd 12/11/2026 -> 01/08/2026).
    Dùng để xác định môn KHÔNG đặt ngày kết thúc (enddate = 0) có còn thuộc học kỳ hiện tại hay không.
    """
    if moment.tzinfo is None:
        raise ValueError("moment phải có múi giờ")
    local = moment.astimezone(TZ)
    semester = SEMESTER_BY_MONTH[local.month]
    year, month = local.year, local.month
    while True:
        prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
        if SEMESTER_BY_MONTH[prev_month] != semester:
            break
        year, month = prev_year, prev_month
    return datetime(year, month, 1, tzinfo=TZ)


_YEAR_NAME = re.compile(r"(\d{4})\s*-\s*(\d{4})")
_TERM_NAME = re.compile(r"^\s*hoc\s*k[yi]\s*(\d)\s*$")       # so sau khi bỏ dấu: "Học kỳ 1", "Học kì 2"


def _plain(text: str) -> str:
    """Bỏ dấu tiếng Việt và viết thường (tên danh mục có thể lưu dấu dạng tổ hợp hoặc dựng sẵn)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d").replace("Đ", "D").lower()


def category_term(year_name: str | None, term_name: str | None) -> tuple[str, int] | None:
    """
    Học kỳ ghi trong tên danh mục của Moodle trường ("Năm học 2026 - 2027" › "Học kỳ 1") -> ('2026-2027', 1).
    Không đọc được (dữ liệu giả, danh mục đặt tên khác) -> None. Chỉ dùng để đối chiếu, không thay academic_term().
    """
    year = _YEAR_NAME.search(year_name or "")
    term = _TERM_NAME.match(_plain(term_name or ""))
    if not year or not term or int(year.group(2)) != int(year.group(1)) + 1:
        return None
    return f"{year.group(1)}-{year.group(2)}", int(term.group(1))
