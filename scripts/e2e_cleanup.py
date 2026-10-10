"""
Xóa dữ liệu do bộ E2E tạo trong CSDL đang cấu hình:
  - can thiệp có nội dung bắt đầu bằng "[e2e]";
  - tin gửi đi có tiêu đề bắt đầu bằng "[e2e]" (và nhật ký can thiệp gắn với tin);
  - tin nhắn Moodle tương ứng do máy chủ Moodle mô phỏng ghi vào mdl_messages.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import psycopg  # noqa: E402

from database.config import load_db_config  # noqa: E402

MARK = "[e2e]%"

def restore_default_rules() -> int:
    """
    Luật "[e2e]" còn hoạt động (E2E dừng giữa chừng trước bước Khôi phục mặc định): khôi phục luật của trường bằng đúng
    hàm của backend – ngừng luật riêng, chấm lại snapshot gần nhất của môn theo luật trường, cập nhật bảng tiến độ môn.
    """
    from backend.app.core.db import get_engine
    from backend.app.repositories import rules as rules_repo
    from sqlalchemy import text

    with get_engine().begin() as conn:
        courses = [r[0] for r in conn.execute(text("""SELECT DISTINCT course_id FROM analytics.risk_rule_set
                                                      WHERE scope = 'COURSE' AND is_active AND note LIKE :m"""),
                                              {"m": MARK})]
        for course_id in courses:
            snapshot = conn.execute(text("""SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary
                                            WHERE course_id = :c"""), {"c": course_id}).scalar()
            rules_repo.deactivate_course_rule(conn, course_id)
            _, global_rule, params = rules_repo.course_rule(conn, course_id)
            if snapshot is not None:
                rules_repo.apply_to_snapshot(conn, course_id, snapshot, global_rule.rule_set_id, params)
    return len(courses)


restored = restore_default_rules()

with psycopg.connect(**load_db_config("ANALYTICS_DB").conninfo(application_name="lms-e2e-cleanup")) as conn:
    linked = conn.execute("""DELETE FROM analytics.intervention_log WHERE outbound_id IN
                             (SELECT message_id FROM analytics.outbound_message WHERE subject LIKE %s)""", (MARK,)).rowcount
    messages = conn.execute("DELETE FROM analytics.outbound_message WHERE subject LIKE %s", (MARK,)).rowcount
    notes = conn.execute("DELETE FROM analytics.intervention_log WHERE content LIKE %s", (MARK,)).rowcount
    prompts = conn.execute("""DELETE FROM analytics.auto_prompt_rule p WHERE name LIKE %s AND NOT EXISTS
                              (SELECT 1 FROM analytics.outbound_message o WHERE o.rule_id = p.rule_id)""", (MARK,)).rowcount
    # Bộ luật thử của E2E đã được khôi phục mặc định (không còn hoạt động, không còn dòng số liệu nào tham chiếu)
    rules = conn.execute("""DELETE FROM analytics.risk_rule_set r WHERE r.note LIKE %s AND NOT r.is_active
                              AND NOT EXISTS (SELECT 1 FROM analytics.fact_student_risk_summary f WHERE f.rule_set_id = r.rule_set_id)
                              AND NOT EXISTS (SELECT 1 FROM analytics.fact_course_progress_daily f WHERE f.rule_set_id = r.rule_set_id)""",
                         (MARK,)).rowcount

with psycopg.connect(**load_db_config("MOODLE_DB").conninfo(application_name="lms-e2e-cleanup")) as conn:
    moodle = conn.execute("DELETE FROM mdl_messages WHERE fullmessage LIKE %s OR subject LIKE %s", (MARK, MARK)).rowcount

print(f"[e2e] Đã xóa {notes + linked} can thiệp, {messages} tin gửi đi, {moodle} tin nhắn Moodle, "
      f"{prompts} quy tắc nhắc, {rules} bộ luật thử do E2E tạo; khôi phục luật mặc định cho {restored} môn.")
