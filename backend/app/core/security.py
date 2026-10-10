"""
Xác thực & phân quyền (SPEC 5.1, 6.3):
  - Mật khẩu băm bcrypt.
  - JWT HS256 (PyJWT) mang sub = app_user.user_id (= mdl_user.id) và role; hết hạn -> 401.
  - Mỗi request nạp lại app_user để tài khoản bị khóa/đổi vai trò mất quyền ngay, không chờ token hết hạn.
  - Token phát hành trước lần đổi/đặt lại mật khẩu gần nhất (password_changed_at) bị từ chối.
  - require_role(...) -> 403 khi sai vai trò.
  - Giới hạn đăng nhập sai: quá N lần trong cửa sổ thời gian theo (IP, username) -> 429.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Connection

from backend.app.core.config import get_settings
from backend.app.core.db import fetch_one, get_conn

ROLE_ADMIN = "ADMIN"
ROLE_TEACHER = "TEACHER"
BCRYPT_MAX_BYTES = 72
MIN_PASSWORD_LENGTH = 8

_bearer = HTTPBearer(auto_error=False)
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    username: str
    full_name: str | None
    email: str | None
    role: str


# ----------------------------------------------------------------------------- mật khẩu
def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Mật khẩu dài quá {BCRYPT_MAX_BYTES} byte (giới hạn của bcrypt)")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("ascii"))
    except ValueError:          # hash hỏng / không phải bcrypt
        return False


# Băm sẵn một mật khẩu giả để thời gian phản hồi khi username không tồn tại ~ khi sai mật khẩu
_DUMMY_HASH = bcrypt.hashpw(b"lms-dummy-password", bcrypt.gensalt()).decode("ascii")


def verify_dummy() -> None:
    verify_password("lms-invalid", _DUMMY_HASH)


# ----------------------------------------------------------------------------- JWT
def create_access_token(user_id: int, role: str, *, expires_minutes: int | None = None,
                        now: datetime | None = None) -> tuple[str, int]:
    """Trả về (token, số giây hiệu lực). Thời điểm dùng giờ thực (không phải AS_OF) vì liên quan bảo mật."""
    settings = get_settings()
    minutes = settings.jwt_expire_minutes if expires_minutes is None else expires_minutes
    issued = now or datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": issued, "exp": issued + timedelta(minutes=minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), minutes * 60


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                          options={"require": ["sub", "exp", "iat"]})
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn",
                            headers=_UNAUTHORIZED_HEADERS) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ",
                            headers=_UNAUTHORIZED_HEADERS) from exc


def token_revoked(payload: dict, password_changed_at: datetime | None) -> bool:
    """iat của JWT tính bằng giây nguyên -> so với password_changed_at đã làm tròn xuống giây,
    để token cấp ngay sau khi đổi mật khẩu (cùng giây) vẫn hợp lệ."""
    if password_changed_at is None:
        return False
    return int(payload["iat"]) < int(password_changed_at.timestamp())


def validate_new_password(password: str) -> str | None:
    """Trả về thông báo lỗi nếu mật khẩu mới không đạt yêu cầu, None nếu hợp lệ."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự"
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return f"Mật khẩu dài quá {BCRYPT_MAX_BYTES} byte"
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return "Mật khẩu phải có cả chữ và số"
    return None


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     conn: Connection = Depends(get_conn)) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập", headers=_UNAUTHORIZED_HEADERS)
    payload = decode_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ", headers=_UNAUTHORIZED_HEADERS) from exc
    row = fetch_one(conn, """SELECT user_id, username, full_name, email, role, is_active, password_changed_at
                             FROM analytics.app_user WHERE user_id = :uid""", {"uid": user_id})
    # Kết thúc giao dịch đọc ngay: không giữ khóa ACCESS SHARE trên app_user suốt request
    # (phục hồi dữ liệu cần TRUNCATE app_user, sẽ phải chờ khóa này nếu giao dịch còn mở)
    conn.rollback()
    if row is None or not row["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khóa",
                            headers=_UNAUTHORIZED_HEADERS)
    if token_revoked(payload, row["password_changed_at"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mật khẩu đã thay đổi, vui lòng đăng nhập lại",
                            headers=_UNAUTHORIZED_HEADERS)
    return CurrentUser(user_id=row["user_id"], username=row["username"], full_name=row["full_name"],
                       email=row["email"], role=row["role"])


def require_role(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Không có quyền truy cập chức năng này")
        return user
    return dependency


# ----------------------------------------------------------------------------- giới hạn đăng nhập sai
class LoginRateLimiter:
    """Đếm lần đăng nhập SAI trong cửa sổ trượt theo khóa (IP, username). Chạy trong bộ nhớ của 1 tiến trình."""

    def __init__(self, max_failures: int, window_seconds: int, clock=time.monotonic) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self.clock = clock
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: tuple[str, str], now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] >= self.window:
            q.popleft()
        return q

    def retry_after(self, ip: str, username: str) -> int:
        """0 nếu được phép thử; ngược lại số giây phải chờ."""
        key, now = (ip, username.lower()), self.clock()
        with self._lock:
            q = self._prune(key, now)
            if len(q) < self.max_failures:
                return 0
            return max(1, int(self.window - (now - q[0])) + 1)

    def record_failure(self, ip: str, username: str) -> None:
        key = (ip, username.lower())
        with self._lock:
            self._prune(key, self.clock()).append(self.clock())

    def reset(self, ip: str, username: str) -> None:
        with self._lock:
            self._failures.pop((ip, username.lower()), None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


_limiter: LoginRateLimiter | None = None


def login_limiter() -> LoginRateLimiter:
    global _limiter
    if _limiter is None:
        s = get_settings()
        _limiter = LoginRateLimiter(s.login_max_failures, s.login_window_seconds)
    return _limiter
