"""
Luật chấm điểm rủi ro "đèn giao thông" – SPEC Phần 2.3.

| Tiêu chí              | 0 (Xanh)                              | 1 (Vàng)                                  | 2 (Đỏ)                               |
| C1 Vắng học           | < 15%                                 | 15% – < 30%                               | >= 30%                               |
| C2 Không tương tác    | vào trong 7 ngày và 14d >= 50% trung vị| 7–14 ngày chưa vào HOẶC 14d < 50% trung vị | chưa từng vào HOẶC > 14 ngày         |
| C3 Thiếu bài tập      | < 20%                                 | 20% – < 60%                               | >= 60%                               |

Xếp mức (RISK_LEVEL_RULES, đã hiệu chỉnh): RED khi C2 = 2 hoặc >= 2 tiêu chí = 2 hoặc tổng >= 4 ·
YELLOW: tổng >= 1 · GREEN: tổng = 0.
risk_score = round(100 × (0.35·C1 + 0.30·C2 + 0.35·C3) / 2), làm tròn half-up. Tiêu chí không có dữ liệu
(môn không có điểm danh / chưa có bài tới hạn) không tính: chia cho tổng trọng số của các tiêu chí còn lại.
Chưa có dữ liệu (0 buổi điểm danh / 0 bài tới hạn) -> tiêu chí đó = 0; attendance_status = NO_DATA khi 0 buổi.

So sánh tỷ lệ với ngưỡng bằng phân số chính xác (Fraction) để các ca biên như "vắng đúng 3/10 buổi = 30%"
luôn cho kết quả đúng, không phụ thuộc sai số dấu phẩy động.

Luật riêng của môn (etl/rules.py): ngưỡng và trọng số của môn được truyền vào qua tham số; luật bổ sung
(extra_rules) chỉ NÂNG mức rủi ro, không hạ, và không đổi điểm 0–100 (để điểm còn so sánh được giữa các môn).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from common import attendance_text
from etl.config import RISK_LEVEL_RULES, RISK_THRESHOLDS, RISK_WEIGHTS

ATTENDANCE_STATUS_BY_SCORE = {0: "OK", 1: "WARN", 2: "CRITICAL"}
LEVEL_ORDER = {"GREEN": 0, "YELLOW": 1, "RED": 2}


def _exact(value: float) -> Fraction:
    return Fraction(str(value))


def _level(numerator: int, denominator: int, yellow: float, red: float) -> int:
    ratio = Fraction(numerator, denominator)
    if ratio >= _exact(red):
        return 2
    if ratio >= _exact(yellow):
        return 1
    return 0


def _validate(r: Mapping) -> None:
    if r["total_sessions"] < 0 or not 0 <= r["absent_sessions"] <= r["total_sessions"]:
        raise ValueError(f"Số buổi không hợp lệ: vắng {r['absent_sessions']}/{r['total_sessions']}")
    if r["total_assignments"] < 0 or not 0 <= r["missing_assignments_count"] <= r["total_assignments"]:
        raise ValueError(f"Số bài không hợp lệ: thiếu {r['missing_assignments_count']}/{r['total_assignments']}")
    days = r["days_since_last_access"]
    if days is not None and days < 0:
        raise ValueError(f"days_since_last_access âm: {days}")
    if r["access_count_14d"] < 0:
        raise ValueError(f"access_count_14d âm: {r['access_count_14d']}")


def _extra_rule_matches(rule: Mapping, r: Mapping) -> str | None:
    """Trả về câu lý do nếu sinh viên khớp luật bổ sung, ngược lại None."""
    t = rule["type"]
    if t == "consecutive_missing":
        n = int(r.get("max_consecutive_missing") or 0)
        return f"Bỏ nộp {n} bài liên tiếp" if n >= rule["count"] else None
    if t == "absent_sessions":
        if r.get("attendance_source") == "GRADEBOOK":      # sổ điểm chỉ có tỷ lệ, không có số buổi
            return None
        detail = r.get("attendance_detail") or []
        if rule.get("attendance_id"):
            chosen = [d for d in detail if int(d["attendance_id"]) == int(rule["attendance_id"])]
        elif rule.get("attendance_name"):
            key = str(rule["attendance_name"]).casefold()
            chosen = [d for d in detail if key in str(d["name"]).casefold()]
        else:
            chosen = detail
        absent = sum(int(d["absent"]) for d in chosen)
        if absent < rule["count"]:
            return None
        targeted = rule.get("attendance_id") or rule.get("attendance_name")
        scope = f" ({chosen[0]['name']})" if targeted and len(chosen) == 1 else ""
        return f"Vắng {absent} buổi{scope}"
    if t == "absence_rate":
        total = int(r["total_sessions"])
        if total and Fraction(int(r["absent_sessions"]), total) >= Fraction(int(rule["percent"]), 100):
            if r.get("attendance_source") == "GRADEBOOK":
                return f"Vắng {int(r['absent_sessions'])}% theo sổ điểm (từ {rule['percent']}%)"
            return f"Vắng {int(r['absent_sessions'])}/{total} buổi (từ {rule['percent']}%)"
        return None
    if t == "inactive_days":
        days = r["days_since_last_access"]
        if days is None:
            return no_activity_reason(r)
        return f"{days} ngày chưa truy cập" if days >= rule["days"] else None
    if t == "missing_count":
        n = int(r["missing_assignments_count"])
        return f"Thiếu {n} bài tập" if n >= rule["count"] else None
    raise ValueError(f"Loại luật bổ sung không hỗ trợ: {t}")


def no_activity_reason(r: Mapping) -> str:
    """
    Lý do khi không có hoạt động nào (không log, không bài nộp, không lượt làm bài kiểm tra). Nhật ký chỉ có từ một
    ngày nhất định (r["log_start"], vd "13/09/2026") nên không khẳng định "chưa từng truy cập".
    """
    start = r.get("log_start")
    return f"Không có hoạt động nào trong môn từ {start} (ngày đầu của nhật ký)" if start         else "Không có hoạt động nào được ghi nhận trong môn"


def applicable_criteria(r: Mapping) -> int:
    """Số tiêu chí có dữ liệu: C2 luôn có; C1 khi môn có điểm danh; C3 khi đã có bài tới hạn."""
    return 1 + (r["total_sessions"] > 0) + (r["total_assignments"] > 0)


def red_total_threshold(red_min_total: int, applicable: int) -> int:
    """
    Ngưỡng "tổng điểm" của mức Nguy cơ cao, co theo số tiêu chí có dữ liệu (quyết định của chủ dự án 17/11/2026):
    đủ 3 tiêu chí giữ nguyên (4), còn 2 tiêu chí -> làm tròn lên 4 × 2/3 = 3, còn 1 tiêu chí -> 2.
    """
    return -(-red_min_total * applicable // 3)


def score_student(r: Mapping, class_median_14d: float,
                  thresholds: Mapping[str, float] = RISK_THRESHOLDS,
                  weights: Mapping[str, float] = RISK_WEIGHTS,
                  level_rules: Mapping[str, int | bool] = RISK_LEVEL_RULES,
                  extra_rules: Sequence[Mapping] = ()) -> dict:
    """
    r cần các khóa: total_sessions, absent_sessions, days_since_last_access (None = chưa từng truy cập),
    access_count_14d, total_assignments, missing_assignments_count; khi có luật bổ sung cần thêm
    max_consecutive_missing và attendance_detail ([{attendance_id, name, sessions, absent}]).
    attendance_source = "GRADEBOOK" (tùy chọn): total/absent_sessions là phần trăm quy đổi từ sổ điểm (thang 100).
    class_median_14d: trung vị access_count_14d của lớp.
    """
    _validate(r)
    if class_median_14d < 0:
        raise ValueError(f"class_median_14d âm: {class_median_14d}")
    cfg = thresholds
    reasons: list[str] = []

    # ---- C1: vắng học
    c1 = 0
    total_sessions, absent = r["total_sessions"], r["absent_sessions"]
    if total_sessions > 0:
        c1 = _level(absent, total_sessions, cfg["absence_yellow"], cfg["absence_red"])
        if c1:
            reasons.append(attendance_text.risk_reason(r))

    # ---- C2: không tương tác
    days = r["days_since_last_access"]
    low_access = class_median_14d > 0 and \
        Fraction(r["access_count_14d"]) < _exact(cfg["low_access_ratio"]) * _exact(class_median_14d)
    if days is None or days > cfg["inactive_red_days"]:
        c2 = 2
    elif days > cfg["inactive_yellow_days"] or low_access:
        c2 = 1
    else:
        c2 = 0
    if days is None:
        reasons.append(no_activity_reason(r))
    elif c2:
        reasons.append(f"{days} ngày chưa truy cập" if days > cfg["inactive_yellow_days"]
                       else "Tương tác thấp hơn 50% trung vị lớp")

    # ---- C3: thiếu bài tập
    c3 = 0
    total_assign, missing = r["total_assignments"], r["missing_assignments_count"]
    if total_assign > 0:
        c3 = _level(missing, total_assign, cfg["missing_yellow"], cfg["missing_red"])
        if c3:
            reasons.append(f"Thiếu {missing}/{total_assign} bài tập")

    total = c1 + c2 + c3
    red_criteria = sum(score == 2 for score in (c1, c2, c3))
    is_red = ((level_rules["red_if_inactivity_red"] and c2 == 2)
              or red_criteria >= level_rules["red_min_red_criteria"]
              or total >= red_total_threshold(level_rules["red_min_total"], applicable_criteria(r)))
    level = "RED" if is_red else "YELLOW" if total >= 1 else "GREEN"

    # ---- luật bổ sung của môn: chỉ nâng mức
    matched: list[dict] = []
    for index, rule in enumerate(extra_rules):
        reason = _extra_rule_matches(rule, r)
        if reason is None:
            continue
        target = rule.get("level", "RED")
        matched.append(dict(index=index, type=rule["type"], level=target, reason=reason))
        if LEVEL_ORDER[target] > LEVEL_ORDER[level]:
            level = target
        text = f"{reason} (luật của môn)"
        if text not in reasons:
            reasons.append(text)

    # Tiêu chí không có dữ liệu (môn không có điểm danh / chưa có bài tới hạn) KHÔNG tính vào điểm: trọng số chia lại
    # cho các tiêu chí còn lại để điểm 0–100 vẫn so sánh được giữa các môn. Đủ 3 tiêu chí thì như công thức gốc.
    parts = [(weights["attendance"], c1, total_sessions > 0), (weights["inactivity"], c2, True),
             (weights["assignment"], c3, total_assign > 0)]
    applied = [(Decimal(str(w)), c) for w, c, ok in parts if ok]
    weight_sum = sum(w for w, _ in applied)
    weighted = sum(w * c for w, c in applied)
    score = int((Decimal(100) * weighted / (2 * weight_sum)).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    return dict(
        score_attendance=c1, score_inactivity=c2, score_assignment=c3,
        risk_score=score, risk_level=level, risk_reasons=reasons, matched_rules=matched,
        attendance_status="NO_DATA" if total_sessions == 0 else ATTENDANCE_STATUS_BY_SCORE[c1],
    )
