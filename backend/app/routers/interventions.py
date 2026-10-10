"""
Chức năng 2 – Trung tâm can thiệp: danh sách cần liên hệ, mẫu tin cá nhân hóa, gửi tin nhắn Moodle/email thật,
lịch sử gửi (kèm mã xác nhận), duyệt tin chờ duyệt, quy tắc nhắc tự động. Chỉ giảng viên của môn.

Người nhận luôn lấy từ snapshot rủi ro (email = mdl_user.email, Moodle = mdl_user.id) – không nhận từ trình duyệt.
Chế độ gửi (offline / chuyển hướng / thật) do common.messaging.config quyết định, có chốt chặn gửi thật.
"""
from __future__ import annotations

import re
from datetime import timedelta
from http import HTTPStatus
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Connection

from backend.app.core.config import today
from backend.app.core.db import get_conn, get_engine
from backend.app.core.security import CurrentUser
from backend.app.repositories import interventions as repo
from backend.app.routers.deps import not_found, teacher_user
from backend.app.routers.teacher import CourseAccess, _snapshot, course_access
from common.messaging import auto_prompt, compose
from common.messaging.config import (CHANNEL_EMAIL, CHANNEL_MOODLE, MessagingConfigError, MessagingSettings,
                                     load_settings)
from common.messaging.outbox import effective_modes, enqueue, now, send_now
from common.messaging.templates import VARIABLES, TemplateError, validate_template

router = APIRouter(prefix="/teacher", tags=["Trung tâm can thiệp"])

Channel = Literal["MOODLE", "EMAIL"]
Purpose = Literal["RISK_HIGH", "INACTIVE", "MISSING_WORK", "CHECK_IN", "GENERAL"]
LEFTOVER = re.compile(r"\{[a-z_]+\}")


def settings_or_503() -> MessagingSettings:
    try:
        return load_settings()
    except MessagingConfigError as exc:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, f"Cấu hình kênh gửi tin chưa đúng: {exc}") from exc


def _course(rows: list[dict]) -> dict:
    return dict(shortname=rows[0]["course_shortname"], fullname=rows[0]["course_fullname"]) if rows else {}


# ----------------------------------------------------------------------------- cần liên hệ
@router.get("/courses/{course_id}/contact-list", summary="Sinh viên cần liên hệ (Đỏ/Vàng) và lần liên hệ gần nhất")
def contact_list(access: CourseAccess = Depends(course_access),
                 levels: list[Literal["RED", "YELLOW"]] = Query(default=["RED", "YELLOW"]),
                 not_contacted_days: int = Query(7, ge=0, le=60),
                 conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _snapshot(conn, access)
    items = repo.contact_list(conn, access.course_id, snapshot, sorted(set(levels)),
                              now() - timedelta(days=not_contacted_days), include_contacted=not_contacted_days == 0)
    return {"course_id": access.course_id, "snapshot_date": snapshot, "items": items}


# ----------------------------------------------------------------------------- mẫu tin
class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    purpose: Purpose = "GENERAL"
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


def _check_template(body: TemplateIn) -> None:
    try:
        validate_template(body.subject, body.body)
    except TemplateError as exc:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/message-templates", summary="Mẫu tin: mẫu hệ thống và mẫu riêng của giảng viên, danh sách biến")
def list_templates(user: CurrentUser = Depends(teacher_user), conn: Connection = Depends(get_conn)) -> dict:
    return {"items": repo.templates(conn, user.user_id),
            "variables": [dict(name=k, label=v) for k, v in VARIABLES.items()]}


@router.post("/message-templates", status_code=HTTPStatus.CREATED, summary="Tạo mẫu tin riêng")
def create_template(body: TemplateIn, user: CurrentUser = Depends(teacher_user),
                    conn: Connection = Depends(get_conn)) -> dict:
    _check_template(body)
    tid = repo.create_template(conn, user.user_id, body.name, body.purpose, body.subject, body.body)
    conn.commit()
    return {"template_id": tid}


def _own_template(conn: Connection, template_id: int, user: CurrentUser) -> dict:
    tpl = repo.template_of(conn, template_id)
    if tpl is None or not tpl["is_active"]:
        raise not_found("Không tìm thấy mẫu tin")
    if tpl["owner_id"] != user.user_id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "Mẫu hệ thống chỉ đọc – hãy tạo bản sao để chỉnh")
    return tpl


@router.put("/message-templates/{template_id}", summary="Sửa mẫu tin riêng")
def update_template(body: TemplateIn, template_id: int = Path(ge=1), user: CurrentUser = Depends(teacher_user),
                    conn: Connection = Depends(get_conn)) -> dict:
    _own_template(conn, template_id, user)
    _check_template(body)
    repo.update_template(conn, template_id, body.name, body.purpose, body.subject, body.body)
    conn.commit()
    return {"template_id": template_id}


@router.delete("/message-templates/{template_id}", summary="Xóa (ẩn) mẫu tin riêng")
def delete_template(template_id: int = Path(ge=1), user: CurrentUser = Depends(teacher_user),
                    conn: Connection = Depends(get_conn)) -> dict:
    _own_template(conn, template_id, user)
    repo.deactivate_template(conn, template_id)
    conn.commit()
    return {"template_id": template_id, "deleted": True}


# ----------------------------------------------------------------------------- soạn & gửi
class PreviewIn(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=200)
    channels: list[Channel] = Field(min_length=1)
    template_id: int | None = None
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=5000)
    contact_days: int = Field(7, ge=1, le=30)


@router.post("/courses/{course_id}/messages/preview",
             summary="Bản xem trước từng sinh viên × kênh (điền biến từ snapshot rủi ro mới nhất)")
def preview(body: PreviewIn, access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    settings = settings_or_503()
    if body.template_id is not None:
        tpl = repo.template_of(conn, body.template_id)
        if tpl is None:
            raise not_found("Không tìm thấy mẫu tin")
        subject, text = body.subject or tpl["subject"], body.body or tpl["body"]
    elif body.subject and body.body:
        subject, text = body.subject, body.body
    else:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Cần chọn mẫu tin hoặc nhập tiêu đề và nội dung")
    snapshot = _snapshot(conn, access)
    rows = compose.students(conn, access.course_id, snapshot, body.user_ids)
    if len(rows) != len(set(body.user_ids)):
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Có sinh viên không thuộc danh sách lớp hiện tại")
    drafts = compose.drafts_for(rows, body.channels, subject, text, course=_course(rows),
                                sender=compose.teacher(conn, access.teacher_id), today=today(),
                                contact_days=body.contact_days)
    modes = effective_modes(conn, settings)
    return {"snapshot_date": snapshot, "channels": {ch: {"mode": m, "warnings": w} for ch, (m, w) in modes.items()},
            "drafts": [d.__dict__ for d in drafts]}


class SendItem(BaseModel):
    user_id: int = Field(ge=1)
    channel: Channel
    subject: str | None = Field(default=None, max_length=255)
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def _no_placeholder(cls, value: str) -> str:
        if LEFTOVER.search(value):
            raise ValueError("Nội dung còn biến chưa điền dạng {…}")
        return value


class SendIn(BaseModel):
    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    template_id: int | None = None
    items: list[SendItem] = Field(min_length=1, max_length=400)


@router.post("/courses/{course_id}/messages", summary="Gửi tin (tạo trong hàng đợi và gửi ngay, trả kết quả từng tin)")
def send(body: SendIn, access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    settings = settings_or_503()
    modes = effective_modes(conn, settings)
    unavailable = {ch for ch, (m, _) in modes.items() if m is None}
    bad = [i.channel for i in body.items if i.channel in unavailable]
    if bad:
        warnings = "; ".join(w for ch in set(bad) for w in modes[ch][1])
        raise HTTPException(HTTPStatus.CONFLICT, f"Kênh không dùng được: {warnings}")
    snapshot = _snapshot(conn, access)
    rows = {r["user_id"]: r for r in compose.students(conn, access.course_id, snapshot, {i.user_id for i in body.items})}
    missing = sorted({i.user_id for i in body.items} - set(rows))
    if missing:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Có sinh viên không thuộc danh sách lớp hiện tại")
    ids, skipped = [], []
    for item in body.items:
        student = rows[item.user_id]
        recipient = compose.recipient_of(student, item.channel)
        if recipient is None:
            skipped.append(dict(user_id=item.user_id, channel=item.channel, error="Sinh viên chưa có email trong Moodle"))
            continue
        if item.channel == CHANNEL_EMAIL and not (item.subject or "").strip():
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Email cần có tiêu đề")
        text = item.body if item.channel == CHANNEL_EMAIL else compose.moodle_text(item.subject, item.body)
        mid = enqueue(conn, course_id=access.course_id, user_id=item.user_id, sender_id=access.teacher_id,
                      origin="MANUAL", channel=item.channel, recipient=recipient,
                      recipient_name=student["student_name"], subject=item.subject, body=text, status="QUEUED",
                      template_id=body.template_id, risk_level=student["risk_level"], snapshot_date=snapshot,
                      idempotency_key=f"manual:{body.request_id}:{item.user_id}:{item.channel}")
        if mid is not None:
            ids.append(int(mid))
    conn.commit()
    result = send_now(get_engine(), settings, ids)
    return {**result, "created": len(ids), "skipped": skipped}


@router.get("/courses/{course_id}/messages", summary="Lịch sử gửi tin của môn (kèm mã xác nhận)")
def list_messages(access: CourseAccess = Depends(course_access),
                  status: Literal["PENDING_REVIEW", "QUEUED", "SENDING", "SENT", "FAILED", "CANCELLED"] | None = None,
                  origin: Literal["MANUAL", "AUTO"] | None = None, channel: Channel | None = None,
                  user_id: int | None = Query(None, ge=1),
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  conn: Connection = Depends(get_conn)) -> dict:
    items, total = repo.messages(conn, access.course_id, status=status, origin=origin, channel=channel,
                                 user_id=user_id, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "counts": repo.message_counts(conn, access.course_id)}


def _message(conn: Connection, access: CourseAccess, message_id: int) -> dict:
    msg = repo.message_of(conn, access.course_id, message_id)
    if msg is None:
        raise not_found("Không tìm thấy tin")
    return msg


@router.post("/courses/{course_id}/messages/{message_id}/{action}",
             summary="Duyệt (approve) tin chờ duyệt, hủy (cancel), gửi lại (retry) tin lỗi")
def message_action(action: Literal["approve", "cancel", "retry"], message_id: int = Path(ge=1),
                   access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    _message(conn, access, message_id)
    if action == "cancel":
        ok = repo.set_status(conn, message_id, ("PENDING_REVIEW", "QUEUED"), "CANCELLED")
    elif action == "approve":
        ok = repo.set_status(conn, message_id, ("PENDING_REVIEW",), "QUEUED")
    else:
        ok = repo.set_status(conn, message_id, ("FAILED",), "QUEUED", reset_attempts=True)
    if not ok:
        raise HTTPException(HTTPStatus.CONFLICT, "Trạng thái hiện tại của tin không cho phép thao tác này")
    conn.commit()
    result = send_now(get_engine(), settings_or_503(), [message_id]) if action != "cancel" else {}
    return {"message_id": message_id, "action": action, **result}


# ----------------------------------------------------------------------------- nhắc tự động
class PromptRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    trigger_type: Literal["INACTIVE_DAYS", "BECAME_RED", "MISSED_DEADLINE"]
    params: dict = Field(default_factory=dict)
    channels: list[Channel] = Field(min_length=1)
    template_id: int = Field(ge=1)
    send_mode: Literal["AUTO", "REVIEW"] = "REVIEW"
    cooldown_days: int = Field(7, ge=1, le=60)
    is_active: bool = True


def _check_rule(conn: Connection, body: PromptRuleIn, user: int) -> dict:
    spec = auto_prompt.TRIGGERS[body.trigger_type]
    params = {}
    if spec["param"]:
        try:
            value = int(body.params.get(spec["param"], spec["default"]))
        except (TypeError, ValueError) as exc:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, f"{spec['name']}: tham số phải là số nguyên") from exc
        if not spec["lo"] <= value <= spec["hi"]:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY,
                                f"{spec['name']}: tham số phải từ {spec['lo']} đến {spec['hi']}")
        params[spec["param"]] = value
    tpl = repo.template_of(conn, body.template_id)
    if tpl is None or not tpl["is_active"] or tpl["owner_id"] not in (None, user):
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Mẫu tin không hợp lệ")
    return {**body.model_dump(), "params": params, "channels": sorted(set(body.channels))}


@router.get("/courses/{course_id}/auto-prompts", summary="Quy tắc nhắc tự động của môn")
def list_prompts(access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    return {"items": repo.prompt_rules(conn, access.course_id),
            "triggers": [dict(code=k, **{x: v for x, v in t.items()}) for k, t in auto_prompt.TRIGGERS.items()]}


@router.post("/courses/{course_id}/auto-prompts", status_code=HTTPStatus.CREATED, summary="Thêm quy tắc nhắc tự động")
def create_prompt(body: PromptRuleIn, access: CourseAccess = Depends(course_access),
                  conn: Connection = Depends(get_conn)) -> dict:
    rid = repo.save_prompt_rule(conn, access.course_id, access.teacher_id, _check_rule(conn, body, access.teacher_id))
    conn.commit()
    return {"rule_id": rid}


def _prompt(conn: Connection, access: CourseAccess, rule_id: int) -> dict:
    rule = repo.prompt_rule(conn, access.course_id, rule_id)
    if rule is None:
        raise not_found("Không tìm thấy quy tắc")
    return rule


@router.put("/courses/{course_id}/auto-prompts/{rule_id}", summary="Sửa / bật / tắt quy tắc nhắc tự động")
def update_prompt(body: PromptRuleIn, rule_id: int = Path(ge=1), access: CourseAccess = Depends(course_access),
                  conn: Connection = Depends(get_conn)) -> dict:
    _prompt(conn, access, rule_id)
    repo.save_prompt_rule(conn, access.course_id, access.teacher_id, _check_rule(conn, body, access.teacher_id), rule_id)
    conn.commit()
    return {"rule_id": rule_id}


@router.delete("/courses/{course_id}/auto-prompts/{rule_id}", summary="Tắt quy tắc nhắc tự động")
def delete_prompt(rule_id: int = Path(ge=1), access: CourseAccess = Depends(course_access),
                  conn: Connection = Depends(get_conn)) -> dict:
    rule = _prompt(conn, access, rule_id)
    rule.update(is_active=False)
    repo.save_prompt_rule(conn, access.course_id, access.teacher_id, rule, rule_id)
    conn.commit()
    return {"rule_id": rule_id, "is_active": False}


@router.post("/courses/{course_id}/auto-prompts/{rule_id}/{action}",
             summary="Chạy thử (dry-run: không tạo tin) hoặc chạy ngay (run) một quy tắc")
def run_prompt(action: Literal["dry-run", "run"], rule_id: int = Path(ge=1),
               access: CourseAccess = Depends(course_access), conn: Connection = Depends(get_conn)) -> dict:
    rule = _prompt(conn, access, rule_id)
    settings = settings_or_503()
    result = auto_prompt.evaluate(conn, rule, today(), settings, dry_run=action == "dry-run")
    if action == "run":
        conn.commit()
    return result
