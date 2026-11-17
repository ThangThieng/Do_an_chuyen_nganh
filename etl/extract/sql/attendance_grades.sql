-- Tiêu chí 1 – chuyên cần lấy từ SỔ ĐIỂM, dùng khi môn không có dữ liệu buổi của plugin mod_attendance
-- (trường không cung cấp các bảng mdl_attendance*). Plugin tự ghi điểm chuyên cần vào mục điểm
-- itemmodule = 'attendance'; tỷ lệ có mặt = (finalgrade - grademin) / (grademax - grademin).
-- Môn đã có buổi điểm danh trong bảng plugin thì KHÔNG trả dòng ở đây (ưu tiên số liệu theo buổi).
-- Chỉ lấy điểm được sửa lần cuối không muộn hơn :as_of (không dùng số liệu tương lai khi nạp lại lịch sử).
WITH student_enrol AS ({{student_enrol}})
SELECT gi.courseid                                     AS course_id,
       se.user_id,
       gi.iteminstance                                 AS attendance_id,
       COALESCE(NULLIF(gi.itemname, ''), 'Điểm danh')  AS attendance_name,
       (gg.finalgrade - gi.grademin)::float8           AS points,
       (gi.grademax - gi.grademin)::float8             AS max_points
FROM mdl_grade_items gi
JOIN student_enrol se     ON se.course_id = gi.courseid
JOIN mdl_grade_grades gg  ON gg.itemid = gi.id AND gg.userid = se.user_id
WHERE gi.courseid = ANY(CAST(:course_ids AS bigint[]))
  AND gi.itemtype = 'mod'
  AND gi.itemmodule = 'attendance'
  AND gi.gradetype = 1
  AND gi.grademax > gi.grademin
  AND gg.finalgrade IS NOT NULL
  AND COALESCE(gg.timemodified, gg.timecreated, 0) <= :as_of
  AND NOT EXISTS (SELECT 1
                  FROM mdl_attendance a
                  JOIN mdl_attendance_sessions s ON s.attendanceid = a.id AND s.lasttaken > 0
                  WHERE a.course = gi.courseid)
ORDER BY gi.courseid, se.user_id, gi.iteminstance
