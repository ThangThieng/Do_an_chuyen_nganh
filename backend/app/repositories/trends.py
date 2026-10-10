"""
Xu hướng mức rủi ro theo thời gian (góp ý 2 – đồ thị xu hướng đi kèm biểu đồ tròn) cho toàn trường, khoa, môn.

Nguồn: fact_course_progress_daily – mỗi môn mỗi ngày một dòng, đã có số Đỏ/Vàng/Xanh khớp bảng cảnh báo
(lấy từ snapshot rủi ro của ngày đó). Chi phí truy vấn tăng theo số môn × số ngày, không theo số sinh viên.

Theo tuần: cấp trường/khoa đánh số tuần từ academic_term.week1_start (không có lịch thì lấy ngày dữ liệu sớm nhất của
học kỳ); cấp môn đánh số từ ngày bắt đầu của chính môn đó (course_start_date, V013) – kế hoạch Mục 3.4, 7.4;
mỗi môn lấy dòng MỚI NHẤT trong tuần (ngày cuối tuần, tuần hiện tại tới hôm nay) rồi cộng theo phạm vi.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import Connection

from backend.app.core.cache import cached
from backend.app.core.db import fetch_all, fetch_value
from backend.app.repositories._sql import where


def _rate(part: int, total: int) -> float | None:
    return round(100 * part / total, 2) if total else None


def week1_start(conn: Connection, academic_year: str, semester: int) -> date | None:
    value = fetch_value(conn, """SELECT week1_start FROM analytics.academic_term
                                 WHERE academic_year = :ay AND semester = :sem""",
                        {"ay": academic_year, "sem": semester})
    if value is None:
        value = fetch_value(conn, """SELECT MIN(stat_date) FROM analytics.fact_course_progress_daily
                                     WHERE academic_year = :ay AND semester = :sem""",
                            {"ay": academic_year, "sem": semester})
        if value is not None:
            value = value - timedelta(days=value.weekday())     # về Thứ 2 của tuần đầu
    return value


def course_start(conn: Connection, course_id: int, today: date) -> date | None:
    """Ngày bắt đầu môn theo dòng tiến độ mới nhất (dòng nạp trước V013 có thể chưa có giá trị)."""
    return fetch_value(conn, """SELECT course_start_date FROM analytics.fact_course_progress_daily
                                WHERE course_id = :c AND stat_date <= :today AND course_start_date IS NOT NULL
                                ORDER BY stat_date DESC LIMIT 1""", {"c": course_id, "today": today})


@cached
def risk_trend(conn: Connection, academic_year: str, semester: int, today: date, granularity: str = "week",
               faculty_id: int | None = None, course_id: int | None = None,
               teacher_id: int | None = None) -> dict:
    conditions = ["academic_year = :ay", "semester = :sem", "stat_date <= :today"]
    params: dict = {"ay": academic_year, "sem": semester, "today": today}
    if faculty_id is not None:
        conditions.append("faculty_id = :faculty_id")
        params["faculty_id"] = faculty_id
    if course_id is not None:
        conditions.append("course_id = :course_id")
        params["course_id"] = course_id
    if teacher_id is not None:
        conditions.append("teacher_ids @> ARRAY[CAST(:teacher_id AS integer)]")
        params["teacher_id"] = teacher_id
    week1 = ((course_start(conn, course_id, today) if course_id is not None else None)
             or week1_start(conn, academic_year, semester) or today)
    params["week1"] = week1
    period = "stat_date" if granularity == "day" else "(stat_date - CAST(:week1 AS date)) / 7 + 1"

    rows = fetch_all(conn, f"""
        WITH days AS (
            SELECT course_id, stat_date, red_count, yellow_count, green_count, rule_set_id, {period} AS period
            FROM analytics.fact_course_progress_daily
            WHERE {where(conditions)}
        ), last_of_period AS (
            SELECT DISTINCT ON (course_id, period) *
            FROM days
            ORDER BY course_id, period, stat_date DESC
        )
        SELECT period, MIN(stat_date) AS first_date, MAX(stat_date) AS stat_date,
               SUM(red_count) AS red, SUM(yellow_count) AS yellow, SUM(green_count) AS green,
               COUNT(*) AS courses
        FROM last_of_period
        GROUP BY period
        ORDER BY period""", params)

    series = []
    for r in rows:
        red, yellow, green = int(r["red"]), int(r["yellow"]), int(r["green"])
        total = red + yellow + green
        if granularity == "day":
            start = end = r["period"]
            label = r["period"].strftime("%d/%m")
        else:
            start = week1 + timedelta(weeks=int(r["period"]) - 1)
            end = start + timedelta(days=6)
            label = f"T{int(r['period'])}"
        series.append(dict(period=label, period_start=start, period_end=end, stat_date=r["stat_date"],
                           red=red, yellow=yellow, green=green, total=total, courses=int(r["courses"]),
                           red_rate=_rate(red, total), yellow_rate=_rate(yellow, total),
                           green_rate=_rate(green, total)))

    # Ngày một môn trong phạm vi đổi bộ luật (vạch đánh dấu trên đồ thị)
    changes = fetch_all(conn, f"""
        WITH d AS (
            SELECT course_id, course_shortname, stat_date, rule_set_id,
                   LAG(rule_set_id) OVER (PARTITION BY course_id ORDER BY stat_date) AS prev_rule
            FROM analytics.fact_course_progress_daily
            WHERE {where(conditions)}
        )
        SELECT d.stat_date AS date, d.course_id, d.course_shortname, rs.label, rs.scope
        FROM d JOIN analytics.risk_rule_set rs ON rs.rule_set_id = d.rule_set_id
        WHERE d.prev_rule IS NOT NULL AND d.rule_set_id IS DISTINCT FROM d.prev_rule
        ORDER BY d.stat_date, d.course_shortname""", params)
    rule_changes = [dict(date=c["date"], course_id=c["course_id"],
                         label=(f"{c['course_shortname']}: " if course_id is None else "")
                         + ("luật riêng " + c["label"] if c["scope"] == "COURSE" else "luật mặc định " + c["label"]))
                    for c in changes]
    return dict(granularity=granularity, week1_start=week1, series=series, rule_changes=rule_changes)
