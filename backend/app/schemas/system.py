"""Schema nhánh Hệ thống / Danh mục của Admin: người dùng, nhật ký ETL, danh mục môn, sao lưu."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.common import ItemList, Stamped


class AppUserRow(BaseModel):
    user_id: int
    username: str
    full_name: str | None
    email: str | None
    role: Literal["ADMIN", "TEACHER"]
    is_active: bool
    last_login_at: datetime | None
    password_changed_at: datetime | None
    created_at: datetime
    course_count: int


class UserActiveIn(BaseModel):
    is_active: bool


class UserActiveOut(BaseModel):
    user_id: int
    username: str
    is_active: bool


class PasswordResetOut(BaseModel):
    user_id: int
    username: str
    temporary_password: str


class EtlRun(BaseModel):
    run_id: int
    job_name: str
    started_at: datetime
    finished_at: datetime | None
    status: Literal["RUNNING", "SUCCESS", "FAILED"]
    rows_extracted: int | None
    rows_loaded: int | None
    error_message: str | None
    duration_seconds: float | None


class EtlRunsOut(ItemList[EtlRun]):
    total: int
    job_names: list[str]


class CatalogTeacher(BaseModel):
    user_id: int
    full_name: str | None
    username: str | None
    is_editing: bool = True                    # giảng viên chính (editingteacher); False = trợ giảng (teacher)


class CatalogCourse(BaseModel):
    course_id: int
    faculty_id: int
    faculty_name: str
    category_name: str
    shortname: str
    fullname: str
    academic_year: str
    semester: int
    enrolled: int
    stat_date: date
    teachers: list[CatalogTeacher]
    rule_scope: str = "GLOBAL"                 # GLOBAL = luật mặc định của trường, COURSE = luật riêng của môn
    rule_label: str | None = None
    rule_preset: str | None = None
    rule_updated_at: datetime | None = None


class CatalogOut(ItemList[CatalogCourse]):
    academic_year: str
    semester: int


class BackupItem(BaseModel):
    name: str
    size_bytes: int
    created_at: str
    created_by: str | None
    as_of: str | None
    migration_version: int | None
    total_rows: int
    tables: dict[str, int]


class BackupListOut(Stamped):
    items: list[BackupItem]
    directory: str


class RestoreIn(BaseModel):
    confirm_name: str = Field(min_length=1, max_length=100, description="Nhập lại đúng tên file để xác nhận")


class RestoreOut(BaseModel):
    name: str
    tables: dict[str, int]
    total_rows: int
