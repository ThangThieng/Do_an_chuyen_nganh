-- =============================================================================
-- V014 – Chỉ mục phủ cho "sinh viên của snapshot mới nhất từng môn"
--
-- Các số liệu v1.2 "sinh viên duy nhất" (thẻ KPI, so sánh khoa, trang Khoa) lấy user_id của snapshot mới nhất của
-- từng môn. Khóa chính (course_id, user_id, snapshot_date) đặt snapshot_date cuối nên phải duyệt toàn bộ lịch sử của
-- môn (số ngày × số SV) rồi mới lọc một ngày; dữ liệu 5 khoa: 82–90 ms, tăng theo độ dài học kỳ và số SV.
-- Chỉ mục (course_id, snapshot_date) INCLUDE (user_id, faculty_id): đọc đúng các dòng của một ngày, không cần đọc bảng
-- (index-only scan). Đo lại bằng: python -m perf.explain_queries --dataset x1
-- =============================================================================
CREATE INDEX ix_risk_course_snapshot_users ON analytics.fact_student_risk_summary
    (course_id, snapshot_date) INCLUDE (user_id, faculty_id);
