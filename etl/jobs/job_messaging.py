"""
Job của Trung tâm can thiệp (chức năng 2):

    auto_prompt       đánh giá mọi quy tắc nhắc tự động đang bật trên snapshot rủi ro mới nhất, tạo tin trong hàng đợi
                      (chạy ngay sau mỗi lần student_risk thành công và có thể chạy tay)
    message_dispatch  gửi các tin QUEUED đến hạn, thử lại lỗi tạm thời (mỗi phút)

    python -m etl.jobs.job_messaging auto_prompt [--as-of ...]
    python -m etl.jobs.job_messaging message_dispatch
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from sqlalchemy import text

from common.messaging import auto_prompt
from common.messaging.config import load_settings
from common.messaging.outbox import dispatch_due, now
from etl.db import analytics_engine
from etl.jobs.runner import JobContext, JobStats, as_of_argument, cli_exit_code, configure_logging, run_job

log = logging.getLogger("etl.messaging")


def compute_auto_prompt(ctx: JobContext) -> JobStats:
    settings = load_settings()
    with ctx.analytics.connect() as conn:
        rules = auto_prompt.active_rules(conn)
    created = matched = 0
    for rule in rules:
        with ctx.analytics.begin() as conn:
            result = auto_prompt.evaluate(conn, rule, ctx.as_of.date(), settings, dry_run=False)
        matched += result["matched"]
        created += result["created"]
        log.info("Quy tắc %s (môn %s): %d SV khớp, %d trong thời gian chờ, tạo %d tin", rule["rule_id"],
                 rule["course_id"], result["matched"], result["skipped_cooldown"], result["created"])
    return JobStats(rows_extracted=matched, rows_loaded=created)


def compute_dispatch(ctx: JobContext) -> JobStats:
    summary = dispatch_due(ctx.analytics, load_settings())
    if summary["sent"] or summary["retry"] or summary["failed"]:
        log.info("Gửi tin: %d thành công, %d chờ thử lại, %d lỗi", summary["sent"], summary["retry"], summary["failed"])
    return JobStats(rows_extracted=summary["sent"] + summary["retry"] + summary["failed"], rows_loaded=summary["sent"])


def run_auto_prompt(as_of: datetime | None = None) -> JobStats | None:
    return run_job("auto_prompt", compute_auto_prompt, locks=["auto_prompt"], as_of=as_of)


def run_dispatch() -> JobStats | None:
    """Chạy mỗi phút: hàng đợi trống thì thoát ngay, không ghi nhật ký ETL (tránh 1.440 dòng log/ngày)."""
    with analytics_engine().connect() as conn:
        due = conn.execute(text("""SELECT EXISTS (SELECT 1 FROM analytics.outbound_message
                                   WHERE status = 'QUEUED' AND (next_attempt_at IS NULL OR next_attempt_at <= :now))"""),
                           {"now": now()}).scalar()
    if not due:
        return JobStats()
    return run_job("message_dispatch", compute_dispatch, locks=["message_dispatch"])


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Job nhắc tự động / gửi hàng đợi tin nhắn")
    parser.add_argument("job", choices=["auto_prompt", "message_dispatch"])
    as_of_argument(parser)
    args = parser.parse_args(argv)
    return cli_exit_code(run_auto_prompt(args.as_of) if args.job == "auto_prompt" else run_dispatch())


if __name__ == "__main__":
    sys.exit(main())
