"""
Nhánh Hệ thống và Danh mục của Admin: quản lý người dùng, nhật ký ETL, danh mục môn học, sao lưu/phục hồi.
Chỉ vai trò ADMIN.
"""
from __future__ import annotations

import secrets
import string
from http import HTTPStatus
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import Connection

from backend.app.core.cache import clear_cache
from backend.app.core.config import today
from backend.app.core.db import get_conn
from backend.app.core.security import CurrentUser, hash_password
from backend.app.repositories import system as system_repo
from backend.app.repositories import users as users_repo
from backend.app.routers.deps import admin_user, not_found, stamp, term
from backend.app.schemas.system import (AppUserRow, BackupItem, BackupListOut, CatalogOut, EtlRunsOut,
                                        PasswordResetOut, RestoreIn, RestoreOut, UserActiveIn, UserActiveOut)
from backend.app.services import backup as backup_service

router = APIRouter(prefix="/admin", tags=["Hệ thống"], dependencies=[Depends(admin_user)])

TEMP_PASSWORD_LENGTH = 12
_TEMP_ALPHABET = string.ascii_letters + string.digits


def _temporary_password() -> str:
    """Mật khẩu tạm ngẫu nhiên, luôn có cả chữ và số (đạt chính sách mật khẩu)."""
    while True:
        value = "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(TEMP_PASSWORD_LENGTH))
        if any(c.isalpha() for c in value) and any(c.isdigit() for c in value):
            return value


def _conflict(detail: str) -> HTTPException:
    return HTTPException(HTTPStatus.CONFLICT, detail)


# ----------------------------------------------------------------------------- người dùng
@router.get("/users", response_model=list[AppUserRow], summary="Danh sách tài khoản Dashboard")
def list_users(conn: Connection = Depends(get_conn)) -> list[dict]:
    return users_repo.list_users(conn, today())


@router.post("/users/{user_id}/active", response_model=UserActiveOut, summary="Khóa / mở khóa tài khoản")
def set_user_active(body: UserActiveIn, user_id: int = Path(ge=1), admin: CurrentUser = Depends(admin_user),
                    conn: Connection = Depends(get_conn)) -> dict:
    if user_id == admin.user_id and not body.is_active:
        raise _conflict("Không thể tự khóa tài khoản đang đăng nhập")
    row = users_repo.set_active(conn, user_id, body.is_active)
    if row is None:
        raise not_found("Không tìm thấy tài khoản")
    return row


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetOut,
             summary="Đặt lại mật khẩu, trả về mật khẩu tạm (chỉ hiển thị một lần)")
def reset_password(user_id: int = Path(ge=1), admin: CurrentUser = Depends(admin_user),
                   conn: Connection = Depends(get_conn)) -> dict:
    if user_id == admin.user_id:
        raise _conflict("Hãy dùng chức năng Đổi mật khẩu cho tài khoản của chính mình")
    account = users_repo.find_by_id(conn, user_id)
    if account is None:
        raise not_found("Không tìm thấy tài khoản")
    password = _temporary_password()
    users_repo.set_password_hash(conn, user_id, hash_password(password))
    return {"user_id": user_id, "username": account["username"], "temporary_password": password}


# ----------------------------------------------------------------------------- nhật ký ETL
@router.get("/etl/runs", response_model=EtlRunsOut, summary="Nhật ký các lần chạy job ETL")
def etl_runs(job_name: str | None = Query(None, max_length=50),
             status: Literal["RUNNING", "SUCCESS", "FAILED"] | None = None,
             limit: int = Query(200, ge=1, le=1000), conn: Connection = Depends(get_conn)) -> dict:
    items, total = system_repo.etl_runs(conn, job_name, status, limit)
    return {"items": items, "total": total, "job_names": system_repo.etl_job_names(conn),
            "data_updated_at": stamp(conn)}


# ----------------------------------------------------------------------------- danh mục
@router.get("/catalog/courses", response_model=CatalogOut, summary="Danh mục môn học và giảng viên phụ trách")
def catalog_courses(selected: tuple[str, int] = Depends(term), faculty_id: int | None = Query(None, ge=1),
                    conn: Connection = Depends(get_conn)) -> dict:
    items = system_repo.course_catalog(conn, selected[0], selected[1], faculty_id, today())
    return {"academic_year": selected[0], "semester": selected[1], "items": items, "data_updated_at": stamp(conn)}


# ----------------------------------------------------------------------------- sao lưu & phục hồi
@router.get("/backups", response_model=BackupListOut, summary="Danh sách bản sao lưu")
def list_backups() -> dict:
    return {"items": [i.to_dict() for i in backup_service.list_backups()],
            "directory": str(backup_service.backup_dir())}


@router.post("/backups", response_model=BackupItem, status_code=HTTPStatus.CREATED, summary="Tạo bản sao lưu mới")
def create_backup(admin: CurrentUser = Depends(admin_user)) -> dict:
    try:
        return backup_service.create_backup(admin.username).to_dict()
    except backup_service.BackupBusy as exc:
        raise _conflict(str(exc)) from exc


@router.get("/backups/{name}/download", summary="Tải file sao lưu",
            responses={200: {"content": {"application/zip": {}}}})
def download_backup(name: str) -> FileResponse:
    try:
        path = backup_service.backup_path(name)
    except backup_service.BackupNotFound as exc:
        raise not_found(str(exc)) from exc
    return FileResponse(path, media_type="application/zip", filename=name)


@router.post("/backups/{name}/restore", response_model=RestoreOut,
             summary="Phục hồi dữ liệu từ bản sao lưu (thay toàn bộ dữ liệu hiện tại)")
def restore_backup(name: str, body: RestoreIn) -> dict:
    if body.confirm_name != name:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Tên xác nhận không khớp với tên bản sao lưu")
    try:
        result = backup_service.restore_backup(name)
    except backup_service.BackupNotFound as exc:
        raise not_found(str(exc)) from exc
    except backup_service.BackupError as exc:
        raise _conflict(str(exc)) from exc
    clear_cache()
    return result


@router.delete("/backups/{name}", status_code=HTTPStatus.NO_CONTENT, response_class=Response,
               summary="Xóa bản sao lưu")
def delete_backup(name: str) -> Response:
    try:
        backup_service.delete_backup(name)
    except backup_service.BackupNotFound as exc:
        raise not_found(str(exc)) from exc
    return Response(status_code=HTTPStatus.NO_CONTENT)
