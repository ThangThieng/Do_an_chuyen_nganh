"""Truy vấn cho nhánh Hệ thống / Danh mục của Admin: nhật ký ETL, danh mục môn học."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Connection

from backend.app.core.db import fetch_all, fetch_value
from backend.app.repositories._sql import where


def etl_runs(conn: Connection, job_name: str | None, status: str | None, limit: int) -> tuple[list[dict], int]:
    conditions, params = [], {"limit": limit}
    if job_name:
        conditions.append("job_name = :job_name")
        params["job_name"] = job_name
    if status:
        conditions.append("status = :status")
        params["status"] = status
    clause = f"WHERE {where(conditions)}" if conditions else ""
    rows = fetch_all(conn, f"""
        SELECT run_id, job_name, started_at, finished_at, status, rows_extracted, rows_loaded, error_message,
               ROUND(EXTRACT(EPOCH FROM (finished_at - started_at))::numeric, 2) AS duration_seconds
        FROM analytics.etl_run_log {clause}
        ORDER BY started_at DESC, run_id DESC
        LIMIT :limit""", params)
    total = fetch_value(conn, f"SELECT COUNT(*) FROM analytics.etl_run_log {clause}", params)
    return rows, int(total)


def etl_job_names(conn: Connection) -> list[str]:
    return [r["job_name"] for r in fetch_all(conn, "SELECT DISTINCT job_name FROM analytics.etl_run_log ORDER BY 1")]


def course_catalog(conn: Connection, academic_year: str, semester: int, faculty_id: int | None,
                   today: date) -> list[dict]:
    """
    Danh mục môn của một học kỳ: khoa, mã, tên, giảng viên phụ trách (giảng viên chính / trợ giảng theo vai trò Moodle),
    sĩ số (dòng tiến độ mới nhất của từng môn) và luật cảnh báo đang áp dụng (mặc định của trường hoặc riêng của môn).
    """
    conditions = ["stat_date <= :today", "academic_year = :ay", "semester = :sem"]
    if faculty_id is not None:
        conditions.append("faculty_id = :faculty_id")
    return fetch_all(conn, f"""
        WITH latest AS (
            SELECT DISTINCT ON (course_id) course_id, faculty_id, faculty_name, category_name, course_shortname,
                   course_fullname, academic_year, semester, teacher_ids, editing_teacher_ids,
                   total_enrolled_students, stat_date
            FROM analytics.fact_course_progress_daily
            WHERE {where(conditions)}
            ORDER BY course_id, stat_date DESC)
        SELECT l.course_id, l.faculty_id, l.faculty_name, l.category_name, l.course_shortname AS shortname,
               l.course_fullname AS fullname, l.academic_year, l.semester,
               l.total_enrolled_students AS enrolled, l.stat_date,
               COALESCE((SELECT json_agg(json_build_object('user_id', t.id, 'full_name', u.full_name,
                                                           'username', u.username,
                                                           'is_editing', t.id = ANY(l.editing_teacher_ids)) ORDER BY t.ord)
                         FROM unnest(l.teacher_ids) WITH ORDINALITY AS t(id, ord)
                         LEFT JOIN analytics.app_user u ON u.user_id = t.id), '[]'::json) AS teachers,
               COALESCE(cr.scope, 'GLOBAL') AS rule_scope, COALESCE(cr.label, gr.label) AS rule_label,
               cr.preset AS rule_preset, cr.created_at AS rule_updated_at
        FROM latest l
        CROSS JOIN (SELECT label FROM analytics.risk_rule_set WHERE scope = 'GLOBAL' AND is_active) gr
        LEFT JOIN analytics.risk_rule_set cr ON cr.scope = 'COURSE' AND cr.is_active AND cr.course_id = l.course_id
        ORDER BY l.faculty_name, l.course_shortname""",
        {"ay": academic_year, "sem": semester, "faculty_id": faculty_id, "today": today})
