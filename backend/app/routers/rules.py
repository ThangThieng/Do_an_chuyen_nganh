"""
Chức năng 1 – Thiết lập ngưỡng, trọng số và luật cảnh báo riêng theo môn (giảng viên).

GET     /teacher/courses/{id}/risk-rules           luật đang áp dụng, mẫu, giới hạn, hoạt động điểm danh, lịch sử
POST    /teacher/courses/{id}/risk-rules/preview   xem trước tác động (không ghi CSDL)
PUT     /teacher/courses/{id}/risk-rules           lưu phiên bản mới + áp dụng cho snapshot hôm nay (GV chính)
DELETE  /teacher/courses/{id}/risk-rules           khôi phục luật mặc định của trường (GV chính)
"""
from __future__ import annotations

from http import HTTPStatus
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Connection

from backend.app.core.cache import clear_cache
from backend.app.core.config import today
from backend.app.core.db import get_conn
from backend.app.repositories import rules as rules_repo
from backend.app.routers.teacher import CourseAccess, _snapshot, course_access
from etl.rules import PRESETS, RuleValidationError, validate_params

router = APIRouter(prefix="/teacher/courses/{course_id}/risk-rules", tags=["Luật cảnh báo theo môn"])

Preset = Literal["DEFAULT", "THEORY", "PRACTICE", "PROJECT", "CUSTOM"]


class RuleIn(BaseModel):
    preset: Preset = "CUSTOM"
    params: dict
    note: str | None = Field(default=None, max_length=500)


def _validated(conn: Connection, body: RuleIn) -> dict:
    _, global_rule, _ = rules_repo.course_rule(conn, 0)
    try:
        return validate_params(body.params, level_rules=global_rule.params["level_rules"])
    except RuleValidationError as exc:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY,
                            {"message": "Luật vượt giới hạn cho phép", "errors": [
                                {"field": f, "message": m} for f, m in exc.errors]}) from exc


def _require_editing(conn: Connection, access: CourseAccess) -> None:
    if not rules_repo.is_editing_teacher(conn, access.course_id, access.teacher_id, today()):
        raise HTTPException(HTTPStatus.FORBIDDEN, "Chỉ giảng viên chính của môn được thay đổi luật cảnh báo")


@router.get("", summary="Luật cảnh báo của môn, các mẫu, giới hạn an toàn, lịch sử phiên bản")
def get_rules(access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _snapshot(conn, access)
    return {
        "course_id": access.course_id, "snapshot_date": snapshot,
        "active": rules_repo.rule_info(conn, access.course_id),
        "presets": rules_repo.presets_payload(), "bounds": rules_repo.bounds_payload(),
        "attendance_activities": rules_repo.attendance_activities(conn, access.course_id, snapshot),
        "history": rules_repo.history(conn, access.course_id),
        "can_edit": rules_repo.is_editing_teacher(conn, access.course_id, access.teacher_id, today()),
    }


@router.post("/preview", summary="Xem trước: phân bố Đỏ/Vàng/Xanh trước – sau và sinh viên đổi mức (không ghi CSDL)")
def preview(body: RuleIn, access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    params = _validated(conn, body)
    snapshot = _snapshot(conn, access)
    return {"snapshot_date": snapshot, **rules_repo.preview(rules_repo.snapshot_rows(conn, access.course_id, snapshot),
                                                            params)}


@router.put("", summary="Lưu phiên bản luật mới của môn và áp dụng cho số liệu hôm nay")
def save(body: RuleIn, access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    _require_editing(conn, access)
    params = _validated(conn, body)
    snapshot = _snapshot(conn, access)
    # Mẫu chỉ được ghi nhận khi giá trị đúng như mẫu; chỉnh tay -> "Tùy chỉnh". Lưu đúng mặc định -> cũng là luật riêng.
    preset = body.preset if body.preset in PRESETS and PRESETS[body.preset]["params"] == params else "CUSTOM"
    preset = "CUSTOM" if preset == "DEFAULT" else preset
    rule_set_id = rules_repo.save_course_rule(conn, access.course_id, preset, params, body.note, access.teacher_id)
    applied = rules_repo.apply_to_snapshot(conn, access.course_id, snapshot, rule_set_id, params)
    conn.commit()
    clear_cache()
    return {"rule_set_id": rule_set_id, "applied": applied, "active": rules_repo.rule_info(conn, access.course_id)}


@router.delete("", summary="Khôi phục luật mặc định của trường cho môn")
def reset(access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    _require_editing(conn, access)
    snapshot = _snapshot(conn, access)
    changed = rules_repo.deactivate_course_rule(conn, access.course_id)
    rule, global_rule, params = rules_repo.course_rule(conn, access.course_id)
    applied = rules_repo.apply_to_snapshot(conn, access.course_id, snapshot, global_rule.rule_set_id, params)
    conn.commit()
    clear_cache()
    return {"changed": changed, "applied": applied, "active": rules_repo.rule_info(conn, access.course_id)}
