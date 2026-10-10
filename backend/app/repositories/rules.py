"""
Luật cảnh báo theo môn (chức năng 1 – màn hình "Thiết lập cảnh báo").

Xem trước và áp dụng CHẤM LẠI snapshot mới nhất của môn bằng ĐÚNG hàm chấm điểm của ETL
(etl.transform.risk_rules.score_student) trên dữ liệu đã lưu trong fact_student_risk_summary – mọi đầu vào của luật
(số buổi, số ngày chưa vào, số bài, chi tiết điểm danh theo hoạt động, bỏ nộp liên tiếp) đều có sẵn trong dòng snapshot,
trung vị lớp tính lại từ cùng snapshot. Không cần kết nối Moodle.
Snapshot các ngày trước giữ nguyên kết quả theo luật cũ (rule_set_id trên từng dòng).
"""
from __future__ import annotations

import json
import statistics
from datetime import date

from sqlalchemy import Connection, text

from backend.app.core.db import fetch_all, fetch_one, fetch_value
from etl.rules import (BOUNDS, EXTRA_RULE_TYPES, PRESETS, RuleSet, active_rule_sets, default_params, describe_extra,
                       diff_from, effective_params, validate_params)
from etl.transform.risk_rules import score_student

LEVELS = ("RED", "YELLOW", "GREEN")
SCORE_INPUTS = """user_id, student_code, student_name, total_sessions, absent_sessions, days_since_last_access,
       access_count_14d, total_assignments, missing_assignments_count, max_consecutive_missing, attendance_detail,
       risk_level, risk_score, risk_reasons, rule_set_id"""


def _json(value):
    return value if not isinstance(value, str) else json.loads(value)


def course_rule(conn: Connection, course_id: int) -> tuple[RuleSet, RuleSet, dict]:
    """(bộ luật đang áp dụng cho môn, bộ GLOBAL, params hiệu lực)."""
    global_rule, course_rules = active_rule_sets(conn)
    rule = course_rules.get(course_id, global_rule)
    return rule, global_rule, effective_params(rule, global_rule)


def rule_info(conn: Connection, course_id: int) -> dict:
    """Thông tin luật hiển thị ở trang Cảnh báo, ngăn "Nguồn & cách tính", Trợ giúp."""
    rule, global_rule, params = course_rule(conn, course_id)
    return dict(rule_set_id=rule.rule_set_id, scope=rule.scope, label=rule.label, preset=rule.preset,
                preset_name=PRESETS.get(rule.preset, {}).get("name", "Tùy chỉnh"),
                thresholds=params["thresholds"], weights=params["weights"], level_rules=params["level_rules"],
                extra_rules=[{**r, "text": describe_extra(r)} for r in params["extra_rules"]],
                differs_from_default=diff_from(params, global_rule.params) if rule.scope == "COURSE" else [],
                default_label=global_rule.label)


def history(conn: Connection, course_id: int) -> list[dict]:
    return fetch_all(conn, """
        SELECT rs.rule_set_id, rs.scope, rs.label, rs.preset, rs.note, rs.created_at, rs.is_active,
               rs.superseded_at, u.full_name AS created_by_name
        FROM analytics.risk_rule_set rs
        LEFT JOIN analytics.app_user u ON u.user_id = rs.created_by
        WHERE rs.course_id = :course_id OR rs.scope = 'GLOBAL'
        ORDER BY rs.created_at DESC, rs.rule_set_id DESC""", {"course_id": course_id})


def attendance_activities(conn: Connection, course_id: int, snapshot_date: date) -> list[dict]:
    """Các hoạt động điểm danh của môn (từ attendance_detail của snapshot) – để chọn trong luật “vắng n buổi …”."""
    return fetch_all(conn, """
        SELECT (d->>'attendance_id')::int AS attendance_id, d->>'name' AS name, MAX((d->>'sessions')::int) AS sessions
        FROM analytics.fact_student_risk_summary r, jsonb_array_elements(r.attendance_detail) d
        WHERE r.course_id = :course_id AND r.snapshot_date = :snapshot_date
        GROUP BY 1, 2 ORDER BY 1""", {"course_id": course_id, "snapshot_date": snapshot_date})


def snapshot_rows(conn: Connection, course_id: int, snapshot_date: date) -> list[dict]:
    rows = fetch_all(conn, f"""SELECT {SCORE_INPUTS} FROM analytics.fact_student_risk_summary
                               WHERE course_id = :course_id AND snapshot_date = :snapshot_date
                               ORDER BY user_id""", {"course_id": course_id, "snapshot_date": snapshot_date})
    for r in rows:
        r["attendance_detail"] = _json(r["attendance_detail"])
        r["risk_reasons"] = _json(r["risk_reasons"])
    return rows


def rescore(rows: list[dict], params: dict) -> list[dict]:
    """Chấm lại cả lớp theo params bằng hàm của ETL. Trung vị lớp tính trên chính snapshot này."""
    if not rows:
        return []
    median = float(statistics.median(int(r["access_count_14d"]) for r in rows))
    return [score_student(r, median, thresholds=params["thresholds"], weights=params["weights"],
                          level_rules=params["level_rules"], extra_rules=params.get("extra_rules", ())) for r in rows]


def preview(rows: list[dict], params: dict) -> dict:
    results = rescore(rows, params)
    before = {lv: sum(r["risk_level"] == lv for r in rows) for lv in LEVELS}
    after = {lv: sum(x["risk_level"] == lv for x in results) for lv in LEVELS}
    changes = []
    for r, x in zip(rows, results):
        if r["risk_level"] != x["risk_level"]:
            caused = [m["reason"] + " (luật của môn)" for m in x["matched_rules"]]
            changes.append(dict(user_id=r["user_id"], student_code=r["student_code"], student_name=r["student_name"],
                                from_level=r["risk_level"], to_level=x["risk_level"],
                                from_score=r["risk_score"], to_score=x["risk_score"],
                                reasons=caused or x["risk_reasons"]))
    order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
    changes.sort(key=lambda c: (order[c["to_level"]], c["student_code"] or ""))
    return dict(total=len(rows), before=before, after=after, changed=len(changes), changes=changes)


def save_course_rule(conn: Connection, course_id: int, preset: str, params: dict, note: str | None,
                     user_id: int) -> int:
    """Tạo phiên bản mới (không sửa phiên bản cũ) và vô hiệu hóa bộ riêng đang hoạt động của môn."""
    conn.execute(text("""UPDATE analytics.risk_rule_set SET is_active = FALSE, superseded_at = now()
                         WHERE scope = 'COURSE' AND course_id = :c AND is_active"""), {"c": course_id})
    version = int(fetch_value(conn, """SELECT COALESCE(MAX(version_no), 0) + 1 FROM analytics.risk_rule_set
                                       WHERE scope = 'COURSE' AND course_id = :c""", {"c": course_id}))
    return int(fetch_value(conn, """
        INSERT INTO analytics.risk_rule_set (scope, course_id, version_no, label, preset, params, note, created_by)
        VALUES ('COURSE', :c, :v, :label, :preset, CAST(:params AS jsonb), :note, :by)
        RETURNING rule_set_id""",
        {"c": course_id, "v": version, "label": f"riêng v{version}", "preset": preset,
         "params": json.dumps(params, ensure_ascii=False), "note": note, "by": user_id}))


def deactivate_course_rule(conn: Connection, course_id: int) -> bool:
    return conn.execute(text("""UPDATE analytics.risk_rule_set SET is_active = FALSE, superseded_at = now()
                                WHERE scope = 'COURSE' AND course_id = :c AND is_active"""),
                        {"c": course_id}).rowcount > 0


def apply_to_snapshot(conn: Connection, course_id: int, snapshot_date: date, rule_set_id: int, params: dict) -> dict:
    """Ghi kết quả chấm lại vào snapshot hôm nay của môn + cập nhật số Đỏ/Vàng/Xanh của bảng tiến độ môn."""
    rows = snapshot_rows(conn, course_id, snapshot_date)
    results = rescore(rows, params)
    payload = [dict(course_id=course_id, user_id=r["user_id"], snapshot_date=snapshot_date, rule_set_id=rule_set_id,
                    s1=x["score_attendance"], s2=x["score_inactivity"], s3=x["score_assignment"],
                    score=x["risk_score"], level=x["risk_level"], reasons=json.dumps(x["risk_reasons"], ensure_ascii=False),
                    status=x["attendance_status"])
               for r, x in zip(rows, results)]
    if payload:
        conn.execute(text("""
            UPDATE analytics.fact_student_risk_summary
            SET score_attendance = :s1, score_inactivity = :s2, score_assignment = :s3, risk_score = :score,
                risk_level = :level, risk_reasons = CAST(:reasons AS jsonb), attendance_status = :status,
                rule_set_id = :rule_set_id
            WHERE course_id = :course_id AND user_id = :user_id AND snapshot_date = :snapshot_date"""), payload)
    counts = {lv: sum(x["risk_level"] == lv for x in results) for lv in LEVELS}
    conn.execute(text("""
        UPDATE analytics.fact_course_progress_daily
        SET red_count = :red, yellow_count = :yellow, green_count = :green, rule_set_id = :rule_set_id
        WHERE course_id = :course_id AND stat_date = :d"""),
        {"red": counts["RED"], "yellow": counts["YELLOW"], "green": counts["GREEN"], "rule_set_id": rule_set_id,
         "course_id": course_id, "d": snapshot_date})
    return dict(snapshot_date=snapshot_date, total=len(rows), red=counts["RED"], yellow=counts["YELLOW"],
                green=counts["GREEN"])


def presets_payload() -> list[dict]:
    return [dict(code=k, name=v["name"], description=v["description"], params=v["params"]) for k, v in PRESETS.items()]


def bounds_payload() -> dict:
    return dict(thresholds={k: list(v) for k, v in BOUNDS.items() if k != "weight"}, weight=list(BOUNDS["weight"]),
                extra_rule_types={k: dict(field=v["field"], min=v["lo"], max=v["hi"], label=v["label"])
                                  for k, v in EXTRA_RULE_TYPES.items()},
                max_extra_rules=5)


def is_editing_teacher(conn: Connection, course_id: int, user_id: int, today: date) -> bool:
    row = fetch_one(conn, """SELECT editing_teacher_ids FROM analytics.fact_course_progress_daily
                             WHERE course_id = :c AND stat_date <= :today ORDER BY stat_date DESC LIMIT 1""",
                    {"c": course_id, "today": today})
    return bool(row and user_id in [int(x) for x in row["editing_teacher_ids"]])


__all__ = ["validate_params", "default_params"]
