"""
Soạn tin nhắn can thiệp từ mẫu: biến trong ngoặc nhọn ({ten_sv}, {tinh_hinh}, ...) được điền từ snapshot rủi ro
mới nhất của sinh viên. Biến lạ hoặc thiếu dữ liệu -> lỗi rõ ràng (không bao giờ gửi tin còn sót "{...}").
"""
from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
LEVEL_LABELS = {"RED": "Nguy cơ cao", "YELLOW": "Cần lưu ý", "GREEN": "An toàn"}

# Biến hợp lệ và mô tả (hiện trong trình soạn tin)
VARIABLES: dict[str, str] = {
    "ten_sv": "Tên sinh viên", "ho_ten_sv": "Họ tên sinh viên", "mssv": "Mã số sinh viên",
    "ma_mon": "Mã môn", "ten_mon": "Tên môn", "ten_gv": "Tên giảng viên", "email_gv": "Email giảng viên",
    "xung_ho": "Thầy/Cô", "so_buoi_vang": "Số buổi vắng", "tong_buoi": "Số buổi đã điểm danh",
    "ty_le_vang": "Tỷ lệ vắng", "so_ngay_khong_vao": "Số ngày chưa vào môn", "bai_chua_nop": "Bài chưa nộp (tên, hạn)",
    "so_bai_thieu": "Số bài thiếu", "muc_rui_ro": "Mức rủi ro", "ly_do": "Lý do cảnh báo",
    "tinh_hinh": "Các câu mô tả tình hình theo từng tiêu chí", "han_lien_he": "Hạn liên hệ",
}


class TemplateError(ValueError):
    """Mẫu tin không điền được (biến lạ, thiếu dữ liệu)."""


@dataclass(frozen=True)
class Rendered:
    subject: str
    body: str

    @property
    def html(self) -> str:
        return text_to_html(self.body)


def text_to_html(text: str) -> str:
    escaped = html.escape(text)
    paragraphs = [p.replace("\n", "<br>") for p in escaped.split("\n\n")]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def _fmt_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d/%m/%Y")


def _missing_assignments(student: Mapping) -> list[str]:
    out = []
    for a in student.get("assignment_detail") or []:
        if a.get("status") == "missing":
            due = f" (hạn {_fmt_date(a.get('duedate'))})" if a.get("duedate") else ""
            out.append(f"{a['name']}{due}")
    return out


def situation_lines(student: Mapping) -> list[str]:
    """Các câu mô tả tình hình theo tiêu chí đang có vấn đề – nội dung của biến {tinh_hinh}."""
    lines = []
    total, absent = int(student.get("total_sessions") or 0), int(student.get("absent_sessions") or 0)
    if student.get("score_attendance") and total:
        lines.append(f"em đã vắng {absent}/{total} buổi ({round(100 * absent / total)}%)")
    days = student.get("days_since_last_access")
    if student.get("score_inactivity"):
        lines.append("em chưa truy cập môn học trên Moodle" if days is None
                     else f"em đã {days} ngày chưa vào môn học trên Moodle" if days > 7
                     else "mức độ truy cập môn học của em thấp hơn nhiều so với lớp")
    missing = _missing_assignments(student)
    if student.get("score_assignment") and missing:
        lines.append(f"em chưa nộp {', '.join(missing)}")
    for reason in student.get("risk_reasons") or []:
        if reason.endswith("(luật của môn)"):
            text = reason.removesuffix(" (luật của môn)")
            lines.append(text[0].lower() + text[1:])
    if not lines:
        lines.append("việc học của em gần đây có dấu hiệu cần chú ý")
    return [f"– {line};" if i < len(lines) - 1 else f"– {line}." for i, line in enumerate(lines)]


def build_context(student: Mapping, course: Mapping, teacher: Mapping, *, today: date,
                  contact_days: int = 7) -> dict[str, str]:
    """
    student: dòng snapshot rủi ro (student_name, student_code, total_sessions, absent_sessions, absence_rate,
             days_since_last_access, assignment_detail, risk_level, risk_reasons, score_*...).
    course:  {shortname, fullname}. teacher: {full_name, email, salutation}.
    """
    full = str(student.get("student_name") or "").strip()
    first = full.split()[-1] if full else ""
    missing = _missing_assignments(student)
    salutation = teacher.get("salutation") or "Thầy/Cô"
    total = int(student.get("total_sessions") or 0)
    days = student.get("days_since_last_access")
    return {
        "ten_sv": first, "ho_ten_sv": full, "mssv": str(student.get("student_code") or ""),
        "ma_mon": str(course.get("shortname") or ""), "ten_mon": str(course.get("fullname") or ""),
        "ten_gv": str(teacher.get("full_name") or ""), "email_gv": str(teacher.get("email") or ""),
        "xung_ho": salutation,
        "so_buoi_vang": str(int(student.get("absent_sessions") or 0)), "tong_buoi": str(total),
        "ty_le_vang": f"{round(100 * int(student.get('absent_sessions') or 0) / total)}%" if total else "chưa có buổi điểm danh",
        "so_ngay_khong_vao": "chưa từng" if days is None else str(days),
        "bai_chua_nop": ", ".join(missing) if missing else "bài tập",
        "so_bai_thieu": str(len(missing)),
        "muc_rui_ro": LEVEL_LABELS.get(student.get("risk_level"), ""),
        "ly_do": "; ".join(student.get("risk_reasons") or []) or "không có",
        "tinh_hinh": "\n".join(situation_lines(student)),
        "han_lien_he": (today + timedelta(days=contact_days)).strftime("%d/%m/%Y"),
    }


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def validate_template(subject: str, body: str) -> None:
    unknown = (placeholders(subject) | placeholders(body)) - set(VARIABLES)
    if unknown:
        raise TemplateError("Biến không hợp lệ trong mẫu: " + ", ".join(f"{{{u}}}" for u in sorted(unknown)))
    if not subject.strip() or not body.strip():
        raise TemplateError("Tiêu đề và nội dung không được để trống")


def render(subject: str, body: str, context: Mapping[str, str]) -> Rendered:
    validate_template(subject, body)

    def fill(text: str) -> str:
        def repl(m: re.Match) -> str:
            value = context.get(m.group(1))
            if value is None or value == "":
                raise TemplateError(f"Không có dữ liệu cho biến {{{m.group(1)}}}")
            return value
        return PLACEHOLDER.sub(repl, text)

    out_subject = " ".join(fill(subject).split())       # tiêu đề email một dòng
    return Rendered(subject=out_subject[:255], body=fill(body).strip())
