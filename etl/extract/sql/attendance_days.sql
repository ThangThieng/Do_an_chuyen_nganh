-- Tiêu chí 1 – số NGÀY môn có điểm danh tới :as_of, đếm từ nhật ký của plugin mod_attendance (giảng viên điểm danh
-- hoặc SV tự điểm danh). Dùng để không chấm C1 khi môn mới điểm danh quá ít buổi (etl/config.py MIN_ATTENDANCE_DAYS).
SELECT l.courseid AS course_id,
       COUNT(DISTINCT (to_timestamp(l.timecreated) AT TIME ZONE :tz)::date) AS attendance_days
FROM mdl_logstore_standard_log l
WHERE l.courseid = ANY(CAST(:course_ids AS bigint[]))
  AND l.component = 'mod_attendance'
  AND l.eventname IN ('\mod_attendance\event\attendance_taken', '\mod_attendance\event\attendance_taken_by_student')
  AND l.timecreated <= :as_of
GROUP BY l.courseid
