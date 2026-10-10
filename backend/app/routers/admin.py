"""Admin 1.1 (tổng quan, Khoa → Môn → SV) và 1.2 (lưu lượng truy cập). Chỉ vai trò ADMIN."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Connection

from backend.app.core.config import today
from backend.app.core.db import get_conn
from backend.app.repositories import admin as admin_repo
from backend.app.repositories import rules as rules_repo
from backend.app.repositories import teacher as teacher_repo
from backend.app.repositories import trends as trends_repo
from backend.app.repositories import traffic as traffic_repo
from backend.app.routers.deps import admin_user, not_found, now_local, now_minute, stamp, term, unprocessable
from backend.app.schemas.admin import (CourseEnrollmentOut, CourseStudentsOut, FacultyCompareOut, FacultyEnrollmentOut,
                                       HeatmapOut, KpisOut, RealtimeOut, RiskTrendOut, TrafficHourlyOut)
from backend.app.schemas.common import RiskLevel
from backend.app.schemas.teacher import CompareOut, RiskStudentsOut, RiskSummaryOut, StudentDetailOut

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(admin_user)])

TRAFFIC_MAX_DAYS = 92


@router.get("/overview/kpis", response_model=KpisOut, summary="Thẻ KPI trang tổng quan")
def overview_kpis(selected: tuple[str, int] = Depends(term), faculty_id: int | None = Query(None, ge=1),
                  conn: Connection = Depends(get_conn)) -> dict:
    data = admin_repo.overview_kpis(conn, selected[0], selected[1], faculty_id, now_minute())
    return {**data, "data_updated_at": stamp(conn)}


@router.get("/enrollment/by-faculty", response_model=FacultyEnrollmentOut,
            summary="SV đăng ký và SV tương tác theo khoa (stacked bar)")
def enrollment_by_faculty(selected: tuple[str, int] = Depends(term), conn: Connection = Depends(get_conn)) -> dict:
    items = admin_repo.enrollment_by_faculty(conn, selected[0], selected[1], today())
    return {"academic_year": selected[0], "semester": selected[1], "items": items, "data_updated_at": stamp(conn)}


@router.get("/enrollment/faculties/{faculty_id}/courses", response_model=CourseEnrollmentOut,
            summary="Drill-down: các môn của một khoa")
def faculty_courses(faculty_id: int = Path(ge=1), selected: tuple[str, int] = Depends(term),
                    sort: Literal["active_rate", "enrolled", "active", "red_count", "red_rate", "shortname",
                                  "fullname"] = "active_rate",
                    order: Literal["asc", "desc"] = "desc", conn: Connection = Depends(get_conn)) -> dict:
    items = admin_repo.faculty_courses(conn, faculty_id, selected[0], selected[1], today(), sort, order)
    if not items:
        raise not_found("Khoa không có môn học nào trong học kỳ đã chọn")
    summary = admin_repo.faculty_summary(conn, faculty_id, selected[0], selected[1], today())
    return {"faculty_id": faculty_id, "academic_year": selected[0], "semester": selected[1], "items": items,
            "summary": summary, "data_updated_at": stamp(conn)}


@router.get("/enrollment/courses/{course_id}/students", response_model=CourseStudentsOut,
            summary="Drill-down cấp cuối: sinh viên của một môn")
def course_students(course_id: int = Path(ge=1),
                    status: Literal["active", "inactive"] | None = Query(None, description="active = có tương tác trong học kỳ"),
                    search: str | None = Query(None, max_length=100, description="MSSV, họ tên hoặc email"),
                    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                    conn: Connection = Depends(get_conn)) -> dict:
    header = admin_repo.course_header(conn, course_id, today())
    snapshot = admin_repo.latest_risk_snapshot_date(conn, course_id, today()) if header else None
    if header is None or snapshot is None:
        raise not_found("Không tìm thấy dữ liệu của môn học")
    items, total = admin_repo.course_students(conn, course_id, snapshot, status=status, search=search,
                                              page=page, page_size=page_size)
    return {"course": header, "snapshot_date": snapshot, "items": items, "total": total, "page": page,
            "page_size": page_size, "data_updated_at": stamp(conn)}


@router.get("/traffic/hourly", response_model=TrafficHourlyOut, summary="Lưu lượng theo giờ (dual-axis line)")
def traffic_hourly(from_date: date | None = Query(None, alias="from", description="YYYY-MM-DD, mặc định 6 ngày trước `to`"),
                   to_date: date | None = Query(None, alias="to", description="YYYY-MM-DD, mặc định hôm nay"),
                   conn: Connection = Depends(get_conn)) -> dict:
    end = to_date or today()
    start = from_date or end - timedelta(days=6)
    if start > end:
        raise unprocessable("`from` phải không muộn hơn `to`")
    if (end - start).days + 1 > TRAFFIC_MAX_DAYS:
        raise unprocessable(f"Khoảng thời gian tối đa {TRAFFIC_MAX_DAYS} ngày")
    return {"from_date": start, "to_date": end, "items": traffic_repo.hourly(conn, start, end),
            "data_updated_at": stamp(conn)}


@router.get("/traffic/realtime", response_model=RealtimeOut,
            summary="Online hiện tại + 24 giờ gần nhất (frontend gọi lại mỗi 60 giây)")
def traffic_realtime(conn: Connection = Depends(get_conn)) -> dict:
    return {**traffic_repo.realtime(conn, now_local()), "data_updated_at": stamp(conn)}


@router.get("/traffic/heatmap", response_model=HeatmapOut, summary="Heatmap giờ × thứ (trung bình N tuần)")
def traffic_heatmap(weeks: int = Query(4, ge=1, le=12), conn: Connection = Depends(get_conn)) -> dict:
    return {**traffic_repo.heatmap(conn, weeks, today()), "data_updated_at": stamp(conn)}


# ============================================================================ phiên bản 1.2 – so sánh, xu hướng, cấp Môn học
@router.get("/compare/faculties", response_model=FacultyCompareOut,
            summary="So sánh giữa các Khoa: quy mô, tỷ lệ tương tác, phân bố rủi ro, so với tuần trước")
def compare_faculties(selected: tuple[str, int] = Depends(term), conn: Connection = Depends(get_conn)) -> dict:
    data = admin_repo.compare_faculties(conn, selected[0], selected[1], today())
    return {**data, "academic_year": selected[0], "semester": selected[1], "data_updated_at": stamp(conn)}


@router.get("/risk-trend", response_model=RiskTrendOut,
            summary="Xu hướng tỷ lệ Đỏ/Vàng/Xanh theo tuần/ngày cho toàn trường, một khoa hoặc một môn")
def risk_trend(selected: tuple[str, int] = Depends(term), faculty_id: int | None = Query(None, ge=1),
               course_id: int | None = Query(None, ge=1), granularity: Literal["week", "day"] = "week",
               conn: Connection = Depends(get_conn)) -> dict:
    data = trends_repo.risk_trend(conn, selected[0], selected[1], today(), granularity, faculty_id=faculty_id,
                                  course_id=course_id)
    scope = "course" if course_id else "faculty" if faculty_id else "school"
    return {**data, "academic_year": selected[0], "semester": selected[1], "scope": scope,
            "data_updated_at": stamp(conn)}


def _admin_snapshot(conn: Connection, course_id: int):
    snapshot = teacher_repo.risk_snapshot_date(conn, course_id, None, today())
    if snapshot is None:
        raise not_found("Môn học chưa có dữ liệu cảnh báo")
    return snapshot


@router.get("/courses/{course_id}/risk-summary", response_model=RiskSummaryOut,
            summary="Trang Môn học (chỉ đọc): số SV theo đèn giao thông, theo tiêu chí, so với tuần trước")
def course_risk_summary(course_id: int = Path(ge=1), conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _admin_snapshot(conn, course_id)
    row = teacher_repo.risk_summary(conn, course_id, None, snapshot)
    return {
        "course_id": course_id, "snapshot_date": snapshot,
        "total": row["total"], "red": row["red"], "yellow": row["yellow"], "green": row["green"],
        "by_criterion": {k: row[k] for k in ("attendance", "inactivity", "assignment")},
        "by_criterion_red": {k: row[f"{k}_red"] for k in ("attendance", "inactivity", "assignment")},
        "attendance_no_data": row["attendance_no_data"], "data_updated_at": stamp(conn),
        "prev_week": teacher_repo.counts_at(conn, course_id, None, snapshot - timedelta(days=7)),
        "rule": rules_repo.rule_info(conn, course_id),
    }


@router.get("/courses/{course_id}/risk-students", response_model=RiskStudentsOut,
            summary="Trang Môn học (chỉ đọc): bảng cảnh báo sinh viên")
def course_risk_students(course_id: int = Path(ge=1),
                         risk_level: list[RiskLevel] = Query(default=[]),
                         criterion: Literal["attendance", "inactivity", "assignment"] | None = Query(None),
                         search: str | None = Query(None, max_length=100),
                         sort: Literal["risk", "risk_score", "student_code", "student_name", "absence_rate",
                                       "missing_assignments", "days_since_last_access", "last_access_time"] = "risk",
                         order: Literal["asc", "desc"] = "desc",
                         page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                         conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _admin_snapshot(conn, course_id)
    items, total = teacher_repo.students(conn, course_id, None, snapshot, risk_levels=sorted(set(risk_level)),
                                         criterion=criterion, search=search, sort=sort, order=order, page=page,
                                         page_size=page_size)
    for r in items:
        r["missing_assignments"] = f"{r['missing_assignments_count']}/{r['total_assignments']}"
    return {"course_id": course_id, "snapshot_date": snapshot, "items": items, "total": total, "page": page,
            "page_size": page_size, "data_updated_at": stamp(conn)}


@router.get("/courses/{course_id}/students/{user_id}", response_model=StudentDetailOut,
            summary="Trang Môn học (chỉ đọc): chi tiết sinh viên")
def course_student_detail(course_id: int = Path(ge=1), user_id: int = Path(ge=1),
                          conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _admin_snapshot(conn, course_id)
    row = teacher_repo.student_detail(conn, course_id, user_id, None, snapshot)
    if row is None:
        raise not_found("Sinh viên không có trong danh sách lớp hiện tại")
    row["missing_assignments"] = f"{row['missing_assignments_count']}/{row['total_assignments']}"
    row["risk_history"] = teacher_repo.risk_history(conn, course_id, user_id, None, today())
    row["interventions"] = teacher_repo.interventions(conn, course_id, user_id)
    row["data_updated_at"] = stamp(conn)
    return row


@router.get("/courses/{course_id}/students/{user_id}/compare", response_model=CompareOut,
            summary="Trang Môn học (chỉ đọc): so sánh sinh viên với trung bình lớp")
def course_student_compare(course_id: int = Path(ge=1), user_id: int = Path(ge=1),
                           conn: Connection = Depends(get_conn)) -> dict:
    snapshot = _admin_snapshot(conn, course_id)
    row = teacher_repo.compare(conn, course_id, user_id, None, snapshot)
    if row is None:
        raise not_found("Sinh viên không có trong danh sách lớp hiện tại")
    return {"course_id": course_id, "user_id": user_id, "snapshot_date": snapshot,
            "metrics": teacher_repo.compare_metrics(row), "data_updated_at": stamp(conn)}
