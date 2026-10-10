"""Luật cảnh báo theo môn: luật bổ sung, mẫu luật, giới hạn an toàn (etl/rules.py, etl/transform/risk_rules.py)."""
from __future__ import annotations

import pytest

from etl.rules import PRESETS, RuleValidationError, default_params, describe_extra, diff_from, validate_params
from etl.transform.risk_rules import score_student
from etl.transform.student_risk import max_consecutive_missing

GOOD = dict(total_sessions=10, absent_sessions=0, days_since_last_access=1, access_count_14d=20,
            total_assignments=5, missing_assignments_count=0, max_consecutive_missing=0,
            attendance_detail=[dict(attendance_id=1, name="Điểm danh lý thuyết", sessions=5, absent=0),
                               dict(attendance_id=2, name="Điểm danh thực hành", sessions=5, absent=0)])


def score(extra_rules, **changes):
    p = default_params()
    return score_student({**GOOD, **changes}, 20, p["thresholds"], p["weights"], p["level_rules"], extra_rules)


# ----------------------------------------------------------------------------- luật bổ sung
def test_consecutive_missing_rule_raises_level_only_at_threshold():
    rule = [dict(type="consecutive_missing", count=2, level="RED")]
    assert score(rule, missing_assignments_count=1, max_consecutive_missing=1)["risk_level"] == "YELLOW"  # 1/5 = 20%
    r = score(rule, missing_assignments_count=2, max_consecutive_missing=2)
    assert r["risk_level"] == "RED"
    assert "Bỏ nộp 2 bài liên tiếp (luật của môn)" in r["risk_reasons"]
    assert r["matched_rules"] == [dict(index=0, type="consecutive_missing", level="RED", reason="Bỏ nộp 2 bài liên tiếp")]


def test_absent_sessions_rule_targets_one_attendance_activity():
    detail = [dict(attendance_id=1, name="Điểm danh lý thuyết", sessions=5, absent=2),
              dict(attendance_id=2, name="Điểm danh thực hành", sessions=5, absent=1)]
    by_id = [dict(type="absent_sessions", count=2, attendance_id=2, level="RED")]
    by_name = [dict(type="absent_sessions", count=2, attendance_name="thực hành", level="RED")]
    any_activity = [dict(type="absent_sessions", count=3, level="RED")]
    kw = dict(absent_sessions=3, attendance_detail=detail)
    assert score(by_id, **kw)["risk_level"] != "RED"            # chỉ vắng 1 buổi thực hành
    assert score(by_name, **kw)["risk_level"] != "RED"
    assert score(any_activity, **kw)["risk_level"] == "RED"     # tổng 3 buổi
    detail[1]["absent"] = 2
    r = score(by_id, **kw)
    assert r["risk_level"] == "RED"
    assert "Vắng 2 buổi (Điểm danh thực hành) (luật của môn)" in r["risk_reasons"]


@pytest.mark.parametrize("absent, expected", [(2, False), (3, True)])
def test_absence_rate_rule_uses_exact_fraction(absent, expected):
    r = score([dict(type="absence_rate", percent=25, level="RED")], total_sessions=12, absent_sessions=absent)
    assert (r["risk_level"] == "RED") is expected        # 3/12 = 25% đúng ngưỡng


def test_extra_rule_never_lowers_level_and_never_changes_score():
    base = score([], days_since_last_access=None)
    assert base["risk_level"] == "RED"
    lowered = score([dict(type="missing_count", count=1, level="YELLOW")], days_since_last_access=None,
                    missing_assignments_count=1)
    assert lowered["risk_level"] == "RED"
    yellow_rule = score([dict(type="inactive_days", days=5, level="YELLOW")], days_since_last_access=6)
    assert yellow_rule["risk_level"] == "YELLOW"
    assert yellow_rule["risk_score"] == score([], days_since_last_access=6)["risk_score"]


def test_course_weights_change_score():
    p = PRESETS["PROJECT"]["params"]
    r = score_student({**GOOD, "missing_assignments_count": 5}, 20, p["thresholds"], p["weights"], p["level_rules"])
    assert r["score_assignment"] == 2
    assert r["risk_score"] == 50          # 100 × 0,5 × 2 ÷ 2


def test_max_consecutive_missing_follows_due_dates():
    details = [dict(assign_id=i, duedate=f"2026-09-{d:02d}T23:59:00+07:00", status=s)
               for i, (d, s) in enumerate([(13, "missing"), (20, "submitted"), (27, "missing"), (6, "missing")])]
    # theo hạn nộp: 06 thiếu, 13 thiếu, 20 nộp, 27 thiếu -> chuỗi dài nhất = 2
    assert max_consecutive_missing(details) == 2
    assert max_consecutive_missing([dict(assign_id=1, duedate=None, status="not_due")]) == 0


# ----------------------------------------------------------------------------- mẫu luật & giới hạn
@pytest.mark.parametrize("preset", list(PRESETS))
def test_every_preset_is_valid(preset):
    validate_params(PRESETS[preset]["params"])


def test_validation_reports_every_error_in_vietnamese():
    p = default_params()
    p["thresholds"].update(absence_yellow=0.70, missing_red=0.10, inactive_red_days=5)
    p["weights"] = dict(attendance=0.05, inactivity=0.30, assignment=0.30)
    p["extra_rules"] = [dict(type="consecutive_missing", count=50), dict(type="unknown")]
    with pytest.raises(RuleValidationError) as exc:
        validate_params(p)
    fields = {f for f, _ in exc.value.errors}
    assert {"absence_yellow", "missing_red", "inactive_red_days", "attendance", "weights",
            "extra_rules[0]", "extra_rules[1]"} <= fields
    assert any("Tổng trọng số phải bằng 100%" in m for _, m in exc.value.errors)


def test_level_rules_cannot_be_changed_by_teacher():
    p = default_params()
    p["level_rules"] = dict(red_if_inactivity_red=False, red_min_red_criteria=3, red_min_total=6)
    assert validate_params(p)["level_rules"] == default_params()["level_rules"]


def test_diff_and_description_are_readable():
    p = PRESETS["PRACTICE"]["params"]
    lines = diff_from(p, default_params())
    assert "Ngưỡng vắng (nguy cơ cao): 20% (mặc định 30%)" in lines
    assert describe_extra(p["extra_rules"][0]) == "vắng từ 2 buổi của hoạt động “thực hành” → nguy cơ cao"
