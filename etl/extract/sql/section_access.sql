-- Mức tiếp cận nội dung theo chương: số SV (ghi danh hợp lệ) đã mở ít nhất một nội dung của chương tới :as_of.
-- Dùng thay "hoàn thành theo chương" khi môn không có dữ liệu hoàn thành hoạt động (trường không cung cấp
-- mdl_course_modules_completion). Chỉ tính nội dung đang hiển thị, đã thêm trước :as_of; bỏ nhãn (label) vì nhãn
-- không có trang để mở. "Đã mở" = có ít nhất một dòng nhật ký gắn với chính hoạt động đó (contextlevel 70).
WITH student_enrol AS ({{student_enrol}}),
mods AS (
    SELECT cm.id, cm.course, cs.section,
           COALESCE(NULLIF(cs.name, ''), CASE WHEN cs.section = 0 THEN 'Chung' ELSE 'Tuần ' || cs.section END) AS name
    FROM mdl_course_modules cm
    JOIN mdl_course_sections cs ON cs.id = cm.section
    JOIN mdl_modules m          ON m.id = cm.module AND m.name <> 'label'
    WHERE cm.course = ANY(CAST(:course_ids AS bigint[]))
      AND cm.visible = 1
      AND cm.deletioninprogress = 0
      AND cm.added <= :as_of
),
seen AS (
    SELECT DISTINCT l.contextinstanceid AS cmid, l.userid
    FROM mdl_logstore_standard_log l
    WHERE l.courseid = ANY(CAST(:course_ids AS bigint[]))
      AND l.contextlevel = 70
      AND l.userid > 0
      AND l.timecreated <= :as_of
)
SELECT m.course                                                           AS course_id,
       m.section                                                          AS section_no,
       m.name                                                             AS section_name,
       COUNT(DISTINCT m.id)                                               AS modules,
       COUNT(DISTINCT se.user_id) FILTER (WHERE s.userid IS NOT NULL)     AS students_opened
FROM mods m
JOIN student_enrol se ON se.course_id = m.course
LEFT JOIN seen s      ON s.cmid = m.id AND s.userid = se.user_id
GROUP BY m.course, m.section, m.name
ORDER BY 1, 2
