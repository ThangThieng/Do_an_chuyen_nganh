-- =============================================================================
-- V017 – Số ngày đã điểm danh của môn (đếm từ nhật ký mod_attendance) cho tiêu chí C1
-- Dữ liệu thật: 5 môn cả học kỳ chỉ điểm danh 1 ngày nhưng điểm chuyên cần trong sổ điểm vẫn có (0% / 100%) ->
-- SV vắng đúng buổi đó bị chấm "vắng 100%". Môn lấy chuyên cần từ sổ điểm có dưới MIN_ATTENDANCE_DAYS (etl/config.py,
-- mặc định 3) ngày điểm danh thì C1 không áp dụng: total/attended/absent_sessions = 0, attendance_source vẫn GRADEBOOK.
-- NULL = không xác định (dòng nạp trước V017 hoặc môn lấy chuyên cần theo buổi của plugin).
-- =============================================================================
ALTER TABLE analytics.fact_student_risk_summary ADD COLUMN attendance_days SMALLINT;
ALTER TABLE analytics.fact_course_progress_daily ADD COLUMN attendance_days SMALLINT;

COMMENT ON COLUMN analytics.fact_student_risk_summary.attendance_days IS
    'Số ngày môn có điểm danh (giảng viên điểm danh hoặc SV tự điểm danh) tới snapshot, đếm từ nhật ký mod_attendance';
COMMENT ON COLUMN analytics.fact_course_progress_daily.attendance_days IS
    'Số ngày môn có điểm danh tới ngày thống kê, đếm từ nhật ký mod_attendance';
