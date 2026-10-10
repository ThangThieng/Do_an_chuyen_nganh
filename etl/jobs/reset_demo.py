"""
Làm sạch dữ liệu phân tích của bộ demo trước khi backfill lại từ moodle_src vừa sinh mới.

Xóa: 3 bảng fact, mẫu online, watermark, nhật ký ETL, nhật ký can thiệp, tin đã gửi, quy tắc nhắc tự động,
mẫu tin của giảng viên, luật riêng của môn. GIỮ: tài khoản Dashboard (app_user), bộ luật mặc định của trường,
mẫu tin hệ thống, lịch học kỳ.

Chỉ chạy được ở chế độ demo (LMS_AS_OF đang đặt) – không bao giờ chạy trên dữ liệu thật.

    python -m etl.jobs.reset_demo --yes
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from common.settings import is_clock_frozen
from etl.db import analytics_engine

STATEMENTS = (
    "DELETE FROM analytics.outbound_message",
    "DELETE FROM analytics.intervention_log",
    "DELETE FROM analytics.auto_prompt_rule",
    "DELETE FROM analytics.message_template WHERE owner_id IS NOT NULL",
    "TRUNCATE analytics.fact_student_risk_summary, analytics.fact_course_progress_daily, "
    "analytics.fact_server_traffic_hourly, analytics.etl_online_snapshot, analytics.etl_watermark",
    "DELETE FROM analytics.risk_rule_set WHERE scope = 'COURSE'",
    "DELETE FROM analytics.etl_run_log",
)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Làm sạch dữ liệu phân tích của bộ demo")
    parser.add_argument("--yes", action="store_true", help="xác nhận xóa")
    args = parser.parse_args(argv)
    if not is_clock_frozen():
        print("Từ chối: LMS_AS_OF đang trống (chế độ vận hành thật). Lệnh này chỉ dành cho dữ liệu demo.",
              file=sys.stderr)
        return 2
    if not args.yes:
        print("Thêm --yes để xác nhận xóa dữ liệu phân tích của bộ demo.", file=sys.stderr)
        return 1
    with analytics_engine().begin() as conn:
        for statement in STATEMENTS:
            conn.execute(text(statement))
    print("Đã làm sạch dữ liệu phân tích. Bước tiếp: python -m etl.jobs.backfill --from 2026-09-07")
    return 0


if __name__ == "__main__":
    sys.exit(main())
