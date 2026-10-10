"""
Bộ luật cảnh báo (risk rule set) – dùng chung cho ETL (chấm điểm hằng ngày) và backend (xem trước / áp dụng luật
riêng của môn trên màn hình "Thiết lập cảnh báo").

Một bộ luật = {"thresholds": {...}, "weights": {...}, "level_rules": {...}, "extra_rules": [...]}.
- Luật mặc định của trường (GLOBAL) lấy từ etl/config.py; mỗi khi cấu hình đổi, ETL phát hành phiên bản GLOBAL mới.
- Luật riêng của môn (COURSE): giảng viên chỉnh ngưỡng, trọng số và thêm luật bổ sung trong GIỚI HẠN AN TOÀN;
  luật xếp mức chung (level_rules) luôn lấy theo bộ GLOBAL để mức rủi ro so sánh được giữa các môn.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import Connection, text

from etl.config import (RISK_EXTRA_RULE_LIMITS, RISK_LEVEL_RULES, RISK_MAX_EXTRA_RULES, RISK_RULE_BOUNDS,
                        RISK_THRESHOLDS, RISK_WEIGHTS)

LEVELS = ("RED", "YELLOW")
THRESHOLD_KEYS = tuple(RISK_THRESHOLDS)
WEIGHT_KEYS = ("attendance", "inactivity", "assignment")
MAX_EXTRA_RULES = RISK_MAX_EXTRA_RULES

# Loại luật bổ sung: tham số chính (khoảng cho phép – etl/config.py) và mô tả dùng cho thông báo lỗi / lý do cảnh báo
_EXTRA_LABELS = {
    "consecutive_missing": "Bỏ nộp bài liên tiếp", "absent_sessions": "Vắng số buổi", "absence_rate": "Tỷ lệ vắng",
    "inactive_days": "Không truy cập", "missing_count": "Thiếu bài",
}
EXTRA_RULE_TYPES: dict[str, dict] = {
    key: dict(field=field, lo=lo, hi=hi, label=_EXTRA_LABELS[key])
    for key, (field, lo, hi) in RISK_EXTRA_RULE_LIMITS.items()
}

# Giới hạn an toàn (Mục 4.5 của kế hoạch) – khai báo trong etl/config.py
BOUNDS: dict[str, tuple[float, float]] = dict(RISK_RULE_BOUNDS)
FIELD_LABELS = {
    "absence_yellow": "Ngưỡng vắng (cần lưu ý)", "absence_red": "Ngưỡng vắng (nguy cơ cao)",
    "missing_yellow": "Ngưỡng thiếu bài (cần lưu ý)", "missing_red": "Ngưỡng thiếu bài (nguy cơ cao)",
    "inactive_yellow_days": "Số ngày chưa vào (cần lưu ý)", "inactive_red_days": "Số ngày chưa vào (nguy cơ cao)",
    "low_access_ratio": "Tỷ lệ so với trung vị lớp",
    "attendance": "Trọng số vắng học", "inactivity": "Trọng số không tương tác", "assignment": "Trọng số thiếu bài tập",
}


def default_params() -> dict:
    """Luật mặc định của trường theo etl/config.py."""
    return dict(thresholds=dict(RISK_THRESHOLDS), weights=dict(RISK_WEIGHTS), level_rules=dict(RISK_LEVEL_RULES),
                extra_rules=[])


def _preset(thresholds: dict, weights: tuple[float, float, float], extra_rules: list[dict]) -> dict:
    p = default_params()
    p["thresholds"].update(thresholds)
    p["weights"] = dict(zip(WEIGHT_KEYS, weights))
    p["extra_rules"] = extra_rules
    return p


# Mẫu luật theo loại môn (Mục 4.4) – giá trị đề xuất ban đầu, hiệu chỉnh lại trên dữ liệu 5 khoa
PRESETS: dict[str, dict] = {
    "DEFAULT": dict(name="Mặc định của trường", description="Luật chung v1.1 áp dụng cho mọi môn",
                    params=default_params()),
    "THEORY": dict(name="Lý thuyết", description="Ít bài lớn; vắng nhiều buổi lý thuyết là dấu hiệu quan trọng",
                   params=_preset(dict(absence_red=0.25, missing_yellow=0.34, missing_red=0.67), (0.40, 0.30, 0.30),
                                  [dict(type="absence_rate", percent=25, level="RED")])),
    "PRACTICE": dict(name="Thực hành", description="Buổi thực hành mỗi tuần; vắng 2 buổi thực hành là nguy cơ cao",
                     params=_preset(dict(absence_yellow=0.10, absence_red=0.20, missing_red=0.40), (0.40, 0.20, 0.40),
                                    [dict(type="absent_sessions", count=2, attendance_name="thực hành", level="RED")])),
    "PROJECT": dict(name="Đồ án", description="Nộp báo cáo tiến độ hằng tuần; bỏ 2 bài liên tiếp là nguy cơ cao",
                    params=_preset(dict(absence_red=0.25, missing_yellow=0.15, missing_red=0.40), (0.30, 0.20, 0.50),
                                   [dict(type="consecutive_missing", count=2, level="RED")])),
}


class RuleValidationError(ValueError):
    """Bộ luật vượt giới hạn an toàn. errors: [(trường, thông báo tiếng Việt)]."""

    def __init__(self, errors: list[tuple[str, str]]):
        super().__init__("; ".join(f"{field}: {msg}" for field, msg in errors))
        self.errors = errors


def _pct(v: float) -> str:
    return f"{v * 100:g}%"


def validate_params(params: Mapping, level_rules: Mapping | None = None) -> dict:
    """
    Kiểm tra và chuẩn hóa bộ luật của MÔN. Trả về bản sao đã chuẩn hóa (số thực/nguyên đúng kiểu,
    level_rules lấy theo luật chung). Ném RuleValidationError liệt kê mọi lỗi.
    """
    errors: list[tuple[str, str]] = []
    out = default_params()
    th_in = params.get("thresholds") or {}
    for key in THRESHOLD_KEYS:
        if key not in th_in:
            errors.append((key, "thiếu giá trị"))
            continue
        try:
            value = float(th_in[key])
        except (TypeError, ValueError):
            errors.append((key, "phải là số"))
            continue
        if key.endswith("_days"):
            if value != int(value):
                errors.append((key, "phải là số nguyên"))
            value = int(value)
        lo, hi = BOUNDS[key]
        if not lo <= value <= hi:
            unit = (lambda v: f"{v:g} ngày") if key.endswith("_days") else _pct
            errors.append((key, f"{FIELD_LABELS[key]} phải từ {unit(lo)} đến {unit(hi)}"))
        out["thresholds"][key] = value
    th = out["thresholds"]
    for low, high in (("absence_yellow", "absence_red"), ("missing_yellow", "missing_red"),
                      ("inactive_yellow_days", "inactive_red_days")):
        if th[high] <= th[low]:
            errors.append((high, f"{FIELD_LABELS[high]} phải lớn hơn {FIELD_LABELS[low].lower()}"))

    w_in = params.get("weights") or {}
    total = 0.0
    for key in WEIGHT_KEYS:
        try:
            value = round(float(w_in.get(key)), 4)
        except (TypeError, ValueError):
            errors.append((key, "phải là số"))
            continue
        lo, hi = BOUNDS["weight"]
        if not lo <= value <= hi:
            errors.append((key, f"{FIELD_LABELS[key]} phải từ {_pct(lo)} đến {_pct(hi)}"))
        out["weights"][key] = value
        total += value
    if abs(total - 1.0) > 0.001:
        errors.append(("weights", f"Tổng trọng số phải bằng 100% (hiện {total * 100:g}%)"))

    extras_in = params.get("extra_rules") or []
    if len(extras_in) > MAX_EXTRA_RULES:
        errors.append(("extra_rules", f"Tối đa {MAX_EXTRA_RULES} luật bổ sung"))
    out["extra_rules"] = []
    for i, rule in enumerate(extras_in[:MAX_EXTRA_RULES]):
        name = f"extra_rules[{i}]"
        spec = EXTRA_RULE_TYPES.get(rule.get("type"))
        if spec is None:
            errors.append((name, f"Loại luật không hợp lệ: {rule.get('type')!r}"))
            continue
        level = rule.get("level", "RED")
        if level not in LEVELS:
            errors.append((name, "Mức phải là RED (nguy cơ cao) hoặc YELLOW (cần lưu ý)"))
        try:
            value = int(rule.get(spec["field"]))
        except (TypeError, ValueError):
            errors.append((name, f"{spec['label']}: giá trị phải là số nguyên"))
            continue
        if not spec["lo"] <= value <= spec["hi"]:
            errors.append((name, f"{spec['label']}: giá trị phải từ {spec['lo']} đến {spec['hi']}"))
        clean = {"type": rule["type"], spec["field"]: value, "level": level}
        if rule["type"] == "absent_sessions":
            if rule.get("attendance_id") not in (None, ""):
                clean["attendance_id"] = int(rule["attendance_id"])
            elif rule.get("attendance_name"):
                clean["attendance_name"] = str(rule["attendance_name"])[:100]
        out["extra_rules"].append(clean)

    out["level_rules"] = dict(level_rules if level_rules is not None else RISK_LEVEL_RULES)
    if errors:
        raise RuleValidationError(errors)
    return out


def canonical(params: Mapping) -> str:
    """Chuỗi JSON chuẩn (khóa sắp xếp) để so sánh hai bộ luật."""
    return json.dumps(params, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def diff_from(params: Mapping, base: Mapping) -> list[str]:
    """Liệt kê ngắn gọn các điểm khác của params so với base (hiện trong ngăn "Nguồn & cách tính")."""
    out = []
    for key in THRESHOLD_KEYS:
        a, b = params["thresholds"][key], base["thresholds"][key]
        if a != b:
            fmt = (lambda v: f"{v:g} ngày") if key.endswith("_days") else _pct
            out.append(f"{FIELD_LABELS[key]}: {fmt(a)} (mặc định {fmt(b)})")
    for key in WEIGHT_KEYS:
        a, b = params["weights"][key], base["weights"][key]
        if abs(a - b) > 1e-9:
            out.append(f"{FIELD_LABELS[key]}: {_pct(a)} (mặc định {_pct(b)})")
    out += [f"Luật bổ sung: {describe_extra(r)}" for r in params.get("extra_rules", [])]
    return out


def describe_extra(rule: Mapping) -> str:
    level = "nguy cơ cao" if rule.get("level", "RED") == "RED" else "cần lưu ý"
    t = rule["type"]
    if t == "consecutive_missing":
        cond = f"bỏ nộp {rule['count']} bài liên tiếp"
    elif t == "absent_sessions":
        scope = (f" của hoạt động điểm danh #{rule['attendance_id']}" if rule.get("attendance_id")
                 else f" của hoạt động “{rule['attendance_name']}”" if rule.get("attendance_name") else "")
        cond = f"vắng từ {rule['count']} buổi{scope}"
    elif t == "absence_rate":
        cond = f"vắng từ {rule['percent']}% số buổi"
    elif t == "inactive_days":
        cond = f"không vào môn từ {rule['days']} ngày"
    else:
        cond = f"thiếu từ {rule['count']} bài"
    return f"{cond} → {level}"


# ----------------------------------------------------------------------------- đọc / ghi CSDL phân tích
@dataclass(frozen=True)
class RuleSet:
    rule_set_id: int
    scope: str
    course_id: int | None
    version_no: int
    label: str
    preset: str
    params: dict


def _row(r) -> RuleSet:
    params = r.params if isinstance(r.params, dict) else json.loads(r.params)
    return RuleSet(int(r.rule_set_id), r.scope, r.course_id, int(r.version_no), r.label, r.preset, params)


def ensure_global_rule(conn: Connection) -> RuleSet:
    """
    Bộ GLOBAL đang hoạt động; nếu khác etl/config.py thì phát hành phiên bản mới (đổi luật trường cũng có lịch sử).
    Giữ nguyên extra_rules của bộ cũ (luật trường hiện không dùng luật bổ sung).
    """
    current = conn.execute(text("""
        SELECT rule_set_id, scope, course_id, version_no, label, preset, params FROM analytics.risk_rule_set
        WHERE scope = 'GLOBAL' AND is_active FOR UPDATE""")).first()
    wanted = default_params()
    if current is not None:
        rs = _row(current)
        wanted["extra_rules"] = rs.params.get("extra_rules", [])
        if canonical(rs.params) == canonical(wanted):
            return rs
        conn.execute(text("UPDATE analytics.risk_rule_set SET is_active = FALSE, superseded_at = now() "
                          "WHERE rule_set_id = :id"), {"id": rs.rule_set_id})
        version = rs.version_no + 1
    else:
        version = 1
    new = conn.execute(text("""
        INSERT INTO analytics.risk_rule_set (scope, version_no, label, preset, params, note)
        VALUES ('GLOBAL', :v, :label, 'DEFAULT', CAST(:params AS jsonb), 'Phát hành tự động khi etl/config.py thay đổi')
        RETURNING rule_set_id, scope, course_id, version_no, label, preset, params"""),
        {"v": version, "label": f"v{version}", "params": canonical(wanted)}).one()
    return _row(new)


def active_rule_sets(conn: Connection) -> tuple[RuleSet, dict[int, RuleSet]]:
    """(bộ GLOBAL, {course_id: bộ riêng đang hoạt động})."""
    rows = conn.execute(text("""
        SELECT rule_set_id, scope, course_id, version_no, label, preset, params FROM analytics.risk_rule_set
        WHERE is_active""")).all()
    global_rule = next((_row(r) for r in rows if r.scope == "GLOBAL"), None)
    if global_rule is None:
        raise RuntimeError("Chưa có bộ luật GLOBAL đang hoạt động (migration V009)")
    return global_rule, {int(r.course_id): _row(r) for r in rows if r.scope == "COURSE"}


def effective_params(rule: RuleSet, global_rule: RuleSet) -> dict:
    """Luật riêng luôn dùng luật xếp mức chung của trường."""
    params = copy.deepcopy(rule.params)
    params["level_rules"] = dict(global_rule.params["level_rules"])
    return params
