"""
Lập lịch ETL bằng APScheduler (SPEC 4.2). Chạy như một tiến trình nền:

    python -m etl.scheduler

| Job              | Lịch                  | Ghi chú                                                         |
| traffic          | */5 phút              | không thử lại: lượt 5 phút kế tiếp tự bù nhờ watermark          |
| course_progress  | phút 05 mỗi giờ       | thử lại 1–5–15 phút                                             |
| student_risk     | 07:15–21:15, 2 giờ/lần | thử lại 1–5–15 phút                                             |
| nightly          | 01:00                 | thử lại 1–5–15 phút                                             |
| maintenance      | Chủ nhật 03:00        | thử lại 1–5–15 phút                                             |
| auto_prompt      | ngay sau student_risk | nhắc tự động (chức năng 2) – tạo tin trong hàng đợi             |
| message_dispatch | mỗi phút              | gửi tin đến hạn; hàng đợi tự thử lại 1–5–15 phút cho từng tin   |
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from etl.config import APP_TIMEZONE
from etl.jobs import job_course_progress, job_messaging, job_student_risk, job_traffic, maintenance, nightly
from etl.jobs.runner import configure_logging, run_with_retries

log = logging.getLogger("etl.scheduler")


def _with_retries(name: str, job):
    return lambda: run_with_retries(job, name)


def build_scheduler() -> BlockingScheduler:
    sched = BlockingScheduler(timezone=APP_TIMEZONE)
    common = dict(max_instances=1, coalesce=True, misfire_grace_time=300)
    sched.add_job(job_traffic.run, CronTrigger(minute="*/5", timezone=APP_TIMEZONE), id="traffic", **common)
    sched.add_job(_with_retries("course_progress", job_course_progress.run),
                  CronTrigger(minute=5, timezone=APP_TIMEZONE), id="course_progress", **common)
    sched.add_job(_with_retries("student_risk", _risk_then_prompts),
                  CronTrigger(hour="7-21/2", minute=15, timezone=APP_TIMEZONE), id="student_risk", **common)
    sched.add_job(_with_retries("nightly", nightly.run),
                  CronTrigger(hour=1, minute=0, timezone=APP_TIMEZONE), id="nightly", **common)
    sched.add_job(_with_retries("maintenance", maintenance.run),
                  CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=APP_TIMEZONE), id="maintenance", **common)
    sched.add_job(job_messaging.run_dispatch, CronTrigger(minute="*", timezone=APP_TIMEZONE), id="message_dispatch",
                  **common)
    return sched


def _risk_then_prompts():
    """Nhắc tự động dựa trên snapshot rủi ro vừa tính: chạy ngay sau student_risk thành công."""
    stats = job_student_risk.run()
    if stats is not None:
        job_messaging.run_auto_prompt()
    return stats


def main() -> None:
    configure_logging()
    sched = build_scheduler()
    for job in sched.get_jobs():
        log.info("Đăng ký job %-16s %s", job.id, job.trigger)
    log.info("Scheduler ETL đang chạy (Ctrl+C để dừng)")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Đã dừng scheduler")


if __name__ == "__main__":
    main()
