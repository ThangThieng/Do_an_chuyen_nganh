"""Xác thực: POST /auth/login, GET /auth/me, POST /auth/change-password."""
from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Connection

from backend.app.core.db import get_conn
from backend.app.core.security import (CurrentUser, create_access_token, get_current_user, hash_password,
                                       login_limiter, validate_new_password, verify_dummy, verify_password)
from backend.app.repositories import users as users_repo
from backend.app.schemas.auth import ChangePasswordIn, LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Xác thực"])

INVALID_LOGIN = "Sai tên đăng nhập hoặc mật khẩu"


@router.post("/login", response_model=TokenOut, summary="Đăng nhập, nhận JWT")
def login(body: LoginIn, request: Request, conn: Connection = Depends(get_conn)) -> TokenOut:
    ip = request.client.host if request.client else "unknown"
    limiter = login_limiter()
    wait = limiter.retry_after(ip, body.username)
    if wait:
        raise HTTPException(HTTPStatus.TOO_MANY_REQUESTS,
                            f"Đăng nhập sai quá nhiều lần, vui lòng thử lại sau {wait} giây",
                            headers={"Retry-After": str(wait)})

    user = users_repo.find_by_username(conn, body.username)
    if user is None:
        verify_dummy()          # giữ thời gian phản hồi tương đương, không lộ username có tồn tại hay không
        valid = False
    else:
        valid = verify_password(body.password, user["password_hash"]) and bool(user["is_active"])
    if not valid:
        limiter.record_failure(ip, body.username)
        raise HTTPException(HTTPStatus.UNAUTHORIZED, INVALID_LOGIN, headers={"WWW-Authenticate": "Bearer"})

    limiter.reset(ip, body.username)
    users_repo.record_login(conn, user["user_id"])
    token, expires_in = create_access_token(user["user_id"], user["role"])
    return TokenOut(access_token=token, expires_in=expires_in,
                    user=UserOut(id=user["user_id"], username=user["username"], full_name=user["full_name"],
                                 email=user["email"], role=user["role"]))


@router.get("/me", response_model=UserOut, summary="Thông tin tài khoản đang đăng nhập")
def me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.user_id, username=user.username, full_name=user.full_name, email=user.email, role=user.role)


@router.post("/change-password", response_model=TokenOut, summary="Đổi mật khẩu của tài khoản đang đăng nhập")
def change_password(body: ChangePasswordIn, user: CurrentUser = Depends(get_current_user),
                    conn: Connection = Depends(get_conn)) -> TokenOut:
    """Các phiên đăng nhập khác của tài khoản mất hiệu lực; phiên hiện tại nhận token mới trong response."""
    account = users_repo.find_by_id(conn, user.user_id)
    if account is None or not verify_password(body.current_password, account["password_hash"]):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Mật khẩu hiện tại không đúng")
    if body.new_password == body.current_password:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Mật khẩu mới phải khác mật khẩu hiện tại")
    problem = validate_new_password(body.new_password)
    if problem:
        raise HTTPException(HTTPStatus.BAD_REQUEST, problem)
    users_repo.set_password_hash(conn, user.user_id, hash_password(body.new_password))
    token, expires_in = create_access_token(user.user_id, user.role)
    return TokenOut(access_token=token, expires_in=expires_in,
                    user=UserOut(id=user.user_id, username=user.username, full_name=user.full_name,
                                 email=user.email, role=user.role))
