"""
Tạo (lại) bản sao CSDL dành riêng cho bộ kiểm thử Backend – kiểm thử không bao giờ chạy trên dữ liệu thật.

    python -m scripts.make_test_db            # sao lms_analytics_real -> lms_analytics_test, moodle_src_real -> moodle_src_test

Dùng CREATE DATABASE ... TEMPLATE (nhanh, sao nguyên dữ liệu + lược đồ). PostgreSQL yêu cầu CSDL nguồn không có kết
nối nào khác trong lúc sao: hãy tạm dừng API (uvicorn), ETL scheduler và máy chủ Moodle mô phỏng.
Tên CSDL kiểm thử: LMS_TEST_ANALYTICS_DB (mặc định lms_analytics_test), LMS_TEST_MOODLE_DB (mặc định moodle_src_test).
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg import sql

from database.config import load_db_config

PAIRS = (("ANALYTICS_DB", "LMS_TEST_ANALYTICS_DB", "lms_analytics_test"),
         ("MOODLE_DB", "LMS_TEST_MOODLE_DB", "moodle_src_test"))


def clone(prefix: str, env: str, default: str) -> str:
    cfg = load_db_config(prefix)
    target = os.getenv(env) or default
    if target == cfg.dbname:
        raise SystemExit(f"{env} trùng CSDL thật {cfg.dbname!r} – từ chối")
    with psycopg.connect(**cfg.conninfo(dbname=cfg.maintenance_db, application_name="lms-make-test-db"),
                         autocommit=True) as admin:
        others = admin.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                               (cfg.dbname,)).fetchone()[0]
        if others:
            raise SystemExit(f"CSDL {cfg.dbname!r} đang có {others} kết nối khác – dừng API / ETL / Moodle mô phỏng rồi chạy lại")
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(target)))
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(target), sql.Identifier(cfg.dbname)))
    return f"{cfg.dbname} -> {target}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for pair in PAIRS:
        print("Đã sao", clone(*pair))
    return 0


if __name__ == "__main__":
    sys.exit(main())
