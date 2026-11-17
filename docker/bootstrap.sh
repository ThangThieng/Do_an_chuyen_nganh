#!/bin/sh
# Khởi tạo một lần cho docker compose (dịch vụ "init"):
#   migrate 2 CSDL -> (nếu CSDL phân tích còn trống) nạp CSV Moodle thật + ETL backfill -> đồng bộ tài khoản Dashboard.
# Chạy lại an toàn: dữ liệu đã có thì bỏ qua bước nạp/backfill. Không còn sinh dữ liệu giả.
set -eu

echo "[init] Áp dụng migration..."
python -m database.migrate up --target analytics
python -m database.migrate up --target moodle

HAS_DATA=$(python - <<'EOF'
import psycopg
from database.config import load_db_config
with psycopg.connect(**load_db_config("ANALYTICS_DB").conninfo()) as conn:
    print(conn.execute("SELECT COUNT(*) FROM analytics.fact_course_progress_daily").fetchone()[0])
EOF
)

if [ "$HAS_DATA" -gt 0 ]; then
    echo "[init] CSDL phân tích đã có $HAS_DATA dòng tiến độ – bỏ qua nạp dữ liệu và backfill."
elif [ -f "${REAL_DATA_DIR}/Data_11-2026/dlu_course_cntt.csv" ]; then
    echo "[init] Nạp CSV Moodle thật từ ${REAL_DATA_DIR}..."
    python -m ingest.run --data-dir "${REAL_DATA_DIR}" --batch "${REAL_DATA_BATCH}"
    echo "[init] ETL backfill từ ${BACKFILL_FROM}..."
    python -m etl.jobs.backfill --from "${BACKFILL_FROM}"
else
    echo "[init] CHƯA CÓ DỮ LIỆU: đặt REAL_DATA_DIR trong docker/.env trỏ tới thư mục CSV Moodle thật"
    echo "       (chứa Data_11-2026/ và NEW/NEW/) rồi chạy lại: docker compose --env-file docker/.env up init"
fi

echo "[init] Đồng bộ tài khoản Dashboard (admin + giảng viên)..."
python -m backend.app.cli sync-users
echo "[init] Hoàn tất."
