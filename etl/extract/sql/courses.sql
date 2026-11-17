-- Môn học đang diễn ra trong ngày của :as_of, kèm chiều phi chuẩn hóa (SPEC 1.3, 1.6 "danh sách môn của GV")
-- Khoa = danh mục cấp 1, Bộ môn / Chuyên ngành = danh mục cấp 2, đều lấy từ path (/<khoa>/<bo_mon>/...).
-- Moodle của trường đặt môn ở cấp 4 (Khoa › Chuyên ngành › Năm học › Học kỳ) nên KHÔNG lấy danh mục trực tiếp
-- của môn làm bộ môn. Môn đặt thẳng trong Khoa thì khoa = bộ môn = chính danh mục đó.
-- term_category_name, year_category_name: tên danh mục trực tiếp và danh mục cha (dữ liệu thật: "Học kỳ 1",
-- "Năm học 2026 - 2027"), chỉ dùng để đối chiếu với học kỳ suy từ ngày bắt đầu, không ghi vào bảng fact.
SELECT c.id                AS course_id,
       c.shortname         AS course_shortname,
       c.fullname          AS course_fullname,
       c.startdate,
       c.enddate,
       dep.id              AS category_id,
       dep.name            AS category_name,
       cc.name             AS term_category_name,
       par.name            AS year_category_name,
       fac.id              AS faculty_id,
       fac.name            AS faculty_name,
       COALESCE(t.teacher_ids, ARRAY[]::bigint[]) AS teacher_ids,
       COALESCE(t.editing_teacher_ids, ARRAY[]::bigint[]) AS editing_teacher_ids
FROM mdl_course c
JOIN mdl_course_categories cc  ON cc.id = c.category
JOIN mdl_course_categories fac ON fac.id = split_part(cc.path, '/', 2)::bigint
JOIN mdl_course_categories dep ON dep.id = COALESCE(NULLIF(split_part(cc.path, '/', 3), '')::bigint, cc.id)
LEFT JOIN mdl_course_categories par ON par.id = cc.parent
LEFT JOIN LATERAL (
    SELECT array_agg(DISTINCT ra.userid ORDER BY ra.userid) AS teacher_ids,
           array_agg(DISTINCT ra.userid ORDER BY ra.userid) FILTER (WHERE r.shortname = 'editingteacher')
               AS editing_teacher_ids
    FROM mdl_context ctx
    JOIN mdl_role_assignments ra ON ra.contextid = ctx.id
    JOIN mdl_role r              ON r.id = ra.roleid AND r.shortname IN ('editingteacher', 'teacher')
    -- Tài khoản giảng viên có thể vắng mặt trong tệp mdl_user xuất ra (dữ liệu thật: userid 3 dạy 23 môn nhưng
    -- không có dòng trong dlu_user.csv) – vẫn tính là môn có giảng viên; chỉ loại tài khoản đã bị xóa.
    LEFT JOIN mdl_user u         ON u.id = ra.userid
    WHERE ctx.contextlevel = 50 AND ctx.instanceid = c.id
      AND COALESCE(u.deleted, 0) = 0
) t ON TRUE
WHERE c.id <> 1
  AND c.visible = 1
  AND c.startdate > 0
  AND c.startdate <= :as_of
  -- Môn có ngày kết thúc: còn hạn. Môn KHÔNG đặt ngày kết thúc (phổ biến ở Moodle thật): chỉ tính khi bắt đầu
  -- trong học kỳ chứa :as_of, để môn của các học kỳ trước không bị coi là đang diễn ra mãi.
  AND (c.enddate >= :day_start OR (c.enddate = 0 AND c.startdate >= :term_start))
  -- Môn không có ai được gán vai trò giảng viên / trợ giảng: không đưa vào thống kê (không ai phụ trách,
  -- không ai nhận cảnh báo). Dữ liệu thật 12/11/2026: loại UDCNTT-AVK49AE.
  AND t.teacher_ids IS NOT NULL
ORDER BY c.id
