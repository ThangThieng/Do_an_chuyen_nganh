"""
Câu chữ mô tả chuyên cần dùng chung cho lý do cảnh báo (ETL) và tin nhắn gửi sinh viên.

Hai nguồn dữ liệu:
  - SESSIONS: số buổi thật từ plugin điểm danh (total/attended/absent_sessions là số buổi);
  - GRADEBOOK: mục điểm danh trong sổ điểm, chỉ có tỷ lệ cả kỳ (các cột trên là phần trăm, total = 100).
Gom về một chỗ để lý do cảnh báo, tin nhắn và giao diện không diễn đạt lệch nhau.
"""
from __future__ import annotations

from collections.abc import Mapping

GRADEBOOK = "GRADEBOOK"


def is_gradebook(r: Mapping) -> bool:
    return r.get("attendance_source") == GRADEBOOK


def _counts(r: Mapping) -> tuple[int, int]:
    return int(r.get("total_sessions") or 0), int(r.get("absent_sessions") or 0)


def has_attendance(r: Mapping) -> bool:
    return _counts(r)[0] > 0


def too_few_days(r: Mapping) -> bool:
    """Chuyên cần theo sổ điểm nhưng môn mới điểm danh quá ít ngày nên C1 không chấm (số buổi đặt 0)."""
    return is_gradebook(r) and not has_attendance(r) and r.get("attendance_days") is not None


def few_days_text(r: Mapping) -> str:
    return f"môn mới điểm danh {int(r.get('attendance_days') or 0)} buổi, chưa tính chuyên cần"


def risk_reason(r: Mapping) -> str:
    """Lý do C1 trong bảng cảnh báo, ví dụ 'Vắng 3/15 buổi (20%)' hoặc 'Chuyên cần 75% theo sổ điểm (vắng 25%)'."""
    total, absent = _counts(r)
    if is_gradebook(r):
        return f"Chuyên cần {total - absent}% theo sổ điểm (vắng {absent}%)"
    return f"Vắng {absent}/{total} buổi ({absent / total:.0%})"


def message_phrase(r: Mapping) -> str:
    """Câu cho tin nhắn gửi sinh viên (ngôi thứ hai), ví dụ 'em đã vắng 3/15 buổi (20%)'."""
    total, absent = _counts(r)
    if too_few_days(r):
        return few_days_text(r)
    if not total:
        return "môn chưa có dữ liệu điểm danh"
    if is_gradebook(r):
        return f"chuyên cần của em đạt {total - absent}% (theo sổ điểm)"
    return f"em đã vắng {absent}/{total} buổi ({round(100 * absent / total)}%)"


def summary(r: Mapping) -> str:
    """Giá trị biến {chuyen_can}: dùng được cho cả hai nguồn."""
    total, absent = _counts(r)
    if too_few_days(r):
        return few_days_text(r)
    if not total:
        return "chưa có dữ liệu điểm danh"
    if is_gradebook(r):
        return f"{total - absent}% (theo sổ điểm)"
    return f"có mặt {total - absent}/{total} buổi"
