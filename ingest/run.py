"""
Nạp đợt dữ liệu Moodle thật vào CSDL nguồn (MOODLE_DB_* trong .env hoặc biến môi trường).

    # CSDL đích phải là CSDL riêng cho dữ liệu thật (không phải moodle_src chứa dữ liệu mô phỏng)
    $env:MOODLE_DB_NAME = "moodle_src_real"
    python -m database.migrate up --target moodle
    python -m ingest.run --data-dir "D:\\Downloads\\Data_11-2026" --batch 2026-11

Tùy chọn:
    --stage-only   chỉ đọc CSV vào vùng đệm stg (không đụng bảng mdl_*)
    --force        đọc lại CSV kể cả khi file không đổi so với lần nạp trước
    --dry-run      in các câu INSERT sẽ chạy, không ghi bảng mdl_*
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg

from common.settings import TZ
from database.config import load_db_config
from ingest import loader
from ingest.manifest import SOURCES

log = logging.getLogger("ingest")
# CSDL chứa dữ liệu mô phỏng: không bao giờ ghi đè bằng công cụ này.
PROTECTED_DATABASES = {name.strip() for name in os.getenv("INGEST_PROTECTED_DBS", "moodle_src").split(",")}


def _local(epoch: int | None) -> str:
    return datetime.fromtimestamp(epoch, TZ).strftime("%d/%m/%Y %H:%M") if epoch else "–"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Nạp CSV Moodle thật vào CSDL nguồn qua vùng đệm stg")
    parser.add_argument("--data-dir", default=os.getenv("REAL_DATA_DIR"),
                        help="thư mục gốc chứa các file CSV (mặc định: biến REAL_DATA_DIR)")
    parser.add_argument("--batch", default=datetime.now(TZ).strftime("%Y-%m"), help="nhãn đợt dữ liệu")
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_dir:
        parser.error("cần --data-dir hoặc biến môi trường REAL_DATA_DIR")
    data_dir = Path(args.data_dir)

    cfg = load_db_config("MOODLE_DB")
    if cfg.dbname in PROTECTED_DATABASES:
        log.error("CSDL '%s' được bảo vệ (dữ liệu mô phỏng). Đặt MOODLE_DB_NAME sang CSDL dành cho dữ liệu thật.",
                  cfg.dbname)
        return 2

    started = time.perf_counter()
    with psycopg.connect(**cfg.conninfo(application_name="lms-ingest"), autocommit=True) as conn:
        if conn.execute("SELECT to_regclass('stg.ingest_batch')").fetchone()[0] is None:
            log.error("Chưa có schema stg – hãy chạy: python -m database.migrate up --target moodle")
            return 2

        scope = loader.stage_scope(conn, data_dir)
        log.info("Phạm vi: %d môn (CSDL đích %s)", scope, cfg.dbname)

        staged: dict[str, loader.StageResult] = {}
        for src in SOURCES:
            t0 = time.perf_counter()
            result = staged[src.stage_name] = loader.stage_file(conn, data_dir, src, args.batch, force=args.force)
            state = "chưa có file (bỏ qua)" if result.skipped else "dùng lại" if result.reused else "đã đọc"
            log.info("stg.%-26s %9d dòng, loại %d – %s (%.1fs)", src.stage_name, result.rows_staged,
                     result.rows_rejected, state, time.perf_counter() - t0)
        if args.stage_only:
            return 0

        if args.dry_run:
            for src in SOURCES:
                if not staged[src.stage_name].skipped:
                    print(loader.build_insert(conn, src), end=";\n\n")
            return 0

        log.info("Chuyển stg -> mdl_* (một transaction)")
        loaded = loader.transform(conn, staged)

        print("\n=== BÁO CÁO NẠP DỮ LIỆU ===")
        print(f"{'Bảng':<28}{'Đọc':>10}{'Loại':>7}{'Nạp':>10}  Ghi chú")
        for src in SOURCES:
            r = staged[src.stage_name]
            note = "chưa có file" if r.skipped else ""
            print(f"{src.stage_name:<28}{r.rows_read:>10}{r.rows_rejected:>7}{loaded[src.stage_name]:>10}  {note}")
        print("\nBản ghi mồ côi (bảng con.cột -> bảng cha):")
        for child, column, parent, count in loader.orphan_report(conn):
            print(f"  {child}.{column} -> {parent}: {count}")
        print("\nKhoảng thời gian dữ liệu:")
        for table, column, low, high in loader.epoch_ranges(conn):
            print(f"  {table}.{column}: {_local(low)} – {_local(high)}")
    log.info("Hoàn tất sau %.0fs", time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
