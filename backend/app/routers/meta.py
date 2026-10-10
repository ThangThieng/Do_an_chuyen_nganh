"""
Minh bạch nguồn dữ liệu và cách tính (góp ý 4): danh mục chỉ số, luật cảnh báo đang áp dụng, độ mới của số liệu,
chế độ gửi tin hiện hành. Nội dung lấy từ cùng nguồn mà ETL dùng – giao diện không tự viết công thức/ngưỡng.
"""
from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection

from backend.app.core.config import as_of, today
from backend.app.core.db import fetch_value, get_conn
from backend.app.core.security import ROLE_TEACHER, CurrentUser, get_current_user
from backend.app.repositories import admin as admin_repo
from backend.app.repositories import common as common_repo
from backend.app.repositories import rules as rules_repo
from backend.app.repositories import teacher as teacher_repo
from common.messaging.config import CHANNEL_EMAIL, CHANNEL_MOODLE, MessagingConfigError, load_settings
from common.messaging.outbox import effective_modes
from common.metrics_catalog import PIPELINE, catalog
from common.settings import is_clock_frozen

router = APIRouter(prefix="/meta", tags=["Minh bạch"])

MODE_LABELS = {"FILE": "Kiểm thử offline – email ghi thành file .eml",
               "REDIRECT": "Kiểm thử chuyển hướng – email gửi qua SMTP thật tới hộp thư kiểm thử",
               "LIVE": "Vận hành thật – gửi tới người nhận thật",
               "STUB": "Moodle mô phỏng (Moodle 3.9 Web Service)"}


@router.get("/metrics", summary="Danh mục chỉ số: ý nghĩa, công thức, bảng Moodle nguồn, bảng phân tích, job ETL")
def metrics(keys: list[str] | None = Query(None), _: CurrentUser = Depends(get_current_user)) -> dict:
    return {"items": catalog(keys), "pipeline": list(PIPELINE)}


@router.get("/risk-rule", summary="Luật cảnh báo đang áp dụng (mặc định của trường hoặc luật riêng của môn)")
def risk_rule(course_id: int | None = Query(None, ge=1), user: CurrentUser = Depends(get_current_user),
              conn: Connection = Depends(get_conn)) -> dict:
    if course_id is not None and user.role == ROLE_TEACHER:
        teachers = teacher_repo.course_teacher_ids(conn, course_id, today())
        if teachers is None:
            raise HTTPException(HTTPStatus.NOT_FOUND, "Không tìm thấy môn học")
        if user.user_id not in teachers:
            raise HTTPException(HTTPStatus.FORBIDDEN, "Bạn không phụ trách môn học này")
    info = rules_repo.rule_info(conn, course_id) if course_id is not None else rules_repo.rule_info(conn, 0)
    info["score_formula"] = "round(100 × (wC1·C1 + wC2·C2 + wC3·C3) ÷ 2)"
    return info


@router.get("/freshness", summary="Độ mới của số liệu: thời điểm tham chiếu, lần chạy gần nhất của từng job ETL")
def freshness(_: CurrentUser = Depends(get_current_user), conn: Connection = Depends(get_conn)) -> dict:
    # Snapshot mới nhất = MAX theo từng môn (tra chỉ mục), không quét cả bảng cảnh báo
    latest = fetch_value(conn, f"WITH {admin_repo.latest_risk_snapshots_cte(term=False)} SELECT MAX(d) FROM snap",
                         {"today": today()})
    return {"as_of": as_of(), "clock_frozen": is_clock_frozen(), "latest_snapshot_date": latest,
            "jobs": common_repo.etl_status(conn), "data_updated_at": common_repo.data_updated_at(conn)}


@router.get("/channels", summary="Chế độ gửi tin hiện hành (để hiện dải thông báo trên trình soạn tin)")
def channels(_: CurrentUser = Depends(get_current_user), conn: Connection = Depends(get_conn)) -> dict:
    try:
        settings = load_settings()
    except MessagingConfigError as exc:
        return {"configured": False, "error": str(exc), "channels": {}}
    modes = effective_modes(conn, settings)
    return {"configured": True, "channels": {
        ch: {"mode": mode, "mode_label": MODE_LABELS.get(mode) if mode else "Không dùng được",
             "available": mode is not None, "warnings": warnings,
             "redirect_to": settings.mail_redirect_to if ch == CHANNEL_EMAIL and mode == "REDIRECT" else None}
        for ch, (mode, warnings) in modes.items()}, "order": [CHANNEL_MOODLE, CHANNEL_EMAIL]}
