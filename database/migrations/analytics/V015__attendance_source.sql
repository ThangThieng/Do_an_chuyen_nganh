-- =============================================================================
-- V015 – Nguồn số liệu chuyên cần của tiêu chí C1
-- SESSIONS  : đếm từng buổi từ plugin mod_attendance (mặc định, như trước nay).
-- GRADEBOOK : trường không cung cấp bảng của plugin -> lấy điểm điểm danh trong sổ điểm (grade_items +
--             grade_grades). Khi đó total_sessions = 100 và attended/absent_sessions là PHẦN TRĂM quy đổi,
--             không phải số buổi; giao diện hiển thị theo tỷ lệ.
-- Thay đổi chỉ cộng thêm: dòng cũ nhận 'SESSIONS', các API hiện có không đổi.
-- =============================================================================
ALTER TABLE analytics.fact_student_risk_summary
    ADD COLUMN attendance_source VARCHAR(10) NOT NULL DEFAULT 'SESSIONS',
    ADD CONSTRAINT ck_risk_attendance_source CHECK (attendance_source IN ('SESSIONS', 'GRADEBOOK')),
    ADD CONSTRAINT ck_risk_attendance_gradebook CHECK (attendance_source = 'SESSIONS' OR total_sessions IN (0, 100));

COMMENT ON COLUMN analytics.fact_student_risk_summary.attendance_source IS
    'SESSIONS = đếm buổi từ mod_attendance; GRADEBOOK = quy đổi từ điểm điểm danh trong sổ điểm (thang 100)';
