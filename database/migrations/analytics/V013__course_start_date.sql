-- =============================================================================
-- V013 – Ngày bắt đầu môn học (mdl_course.startdate, theo giờ địa phương) trên bảng tiến độ môn
--
-- Kế hoạch v1.2 Mục 3.4 / 7.4: đồ thị xu hướng ở cấp môn đánh số "tuần 1" từ ngày bắt đầu của chính môn đó
-- (Moodle cho phép mỗi môn bắt đầu một ngày khác nhau); cấp khoa/trường vẫn theo academic_term.week1_start.
-- Cột cho phép NULL: dòng lịch sử nạp trước V013 chưa có giá trị, API khi đó dùng lịch học kỳ.
-- =============================================================================
ALTER TABLE analytics.fact_course_progress_daily
    ADD COLUMN course_start_date DATE;

COMMENT ON COLUMN analytics.fact_course_progress_daily.course_start_date IS
    'Ngày bắt đầu môn (mdl_course.startdate, giờ địa phương) – mốc tuần 1 của đồ thị xu hướng cấp môn';
