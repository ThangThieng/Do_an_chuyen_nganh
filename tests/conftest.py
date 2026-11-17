"""
Mọi kiểm thử chạy trên bản sao CSDL, không bao giờ trên dữ liệu thật đang dùng.

Đặt tên CSDL kiểm thử vào biến môi trường TRƯỚC khi mô-đun nào nạp .env (load_dotenv không ghi đè biến đã đặt):
    ANALYTICS_DB_NAME   = LMS_TEST_ANALYTICS_DB    (mặc định lms_analytics_test)
    MOODLE_DB_NAME      = LMS_TEST_MOODLE_DB       (mặc định moodle_src_test)
    MOODLE_STUB_DB_NAME = LMS_TEST_MOODLE_STUB_DB  (mặc định moodle_stub_test)
Tạo / làm mới bản sao: python -m scripts.make_test_db (tạm dừng API / ETL / Moodle mô phỏng trong lúc sao).
Kiểm thử không cần CSDL (tests/etl, tests/messaging…) không bị ảnh hưởng.
"""
from __future__ import annotations

import os

TEST_DATABASES = {"ANALYTICS_DB_NAME": os.getenv("LMS_TEST_ANALYTICS_DB") or "lms_analytics_test",
                  "MOODLE_DB_NAME": os.getenv("LMS_TEST_MOODLE_DB") or "moodle_src_test",
                  "MOODLE_STUB_DB_NAME": os.getenv("LMS_TEST_MOODLE_STUB_DB") or "moodle_stub_test"}
os.environ.update(TEST_DATABASES)
