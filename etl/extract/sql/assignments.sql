-- Tiêu chí 3 – bài tập (SPEC 1.6c), trả về MỖI (SV, bài tập) để tính tổng và chi tiết cho Modal.
-- Bài nộp hợp lệ: status = 'submitted', latest = 1, nộp trước :as_of.
-- Bài nộp nhóm (teamsubmission = 1): bản ghi userid = 0, groupid = nhóm của SV trong môn.
-- Việc "đã tới hạn" (duedate < :as_of) được xét ở bước Transform.
-- duedate trả về là HẠN HIỆU LỰC của từng sinh viên theo quy tắc Moodle:
--   gia hạn (assign_user_flags.extensionduedate) > hạn riêng của SV > hạn riêng của nhóm có sortorder nhỏ nhất
--   > hạn chung. Hai bảng override rỗng thì hạn hiệu lực = hạn chung.
-- Bài không đặt hạn nộp (duedate = 0): dùng hạn khóa nộp (cutoffdate), không có thì hạn chấm bài (gradingduedate) –
--   hạn chấm luôn sau hạn nộp dự kiến nên chỉ tính thiếu muộn hơn, không tính oan sớm. Không có cả ba: không tính.
-- Bài kiểm tra trắc nghiệm (quiz) có ngày đóng (timeclose) cũng là một bài cần làm: "đã nộp" = có lượt làm
--   hoàn thành (state = 'finished', không phải lượt xem trước) trước :as_of. assign_id của quiz là số ÂM (-quiz.id)
--   để không trùng mã bài tập; cột kind = 'assign' | 'quiz'.
-- Bài / bài kiểm tra có Hạn chế truy cập theo nhóm (course_modules.availability) chỉ tính cho SV trong nhóm đó
--   (dữ liệu thật: môn gộp nhiều lớp giao bài riêng từng lớp, vd "Bài tập nhóm buổi 4 - CTK48B").
WITH student_enrol AS ({{student_enrol}}),
member_groups AS (
    SELECT g.courseid, gm.userid, gm.groupid
    FROM mdl_groups g
    JOIN mdl_groups_members gm ON gm.groupid = g.id
    WHERE g.courseid = ANY(CAST(:course_ids AS bigint[]))
)
SELECT a.course        AS course_id,
       se.user_id,
       a.id            AS assign_id,
       a.name          AS assign_name,
       due.duedate,
       sub.submitted_ts,
       'assign'        AS kind
FROM mdl_assign a
JOIN mdl_course_modules cm ON cm.instance = a.id AND cm.course = a.course
                          AND cm.visible = 1 AND cm.deletioninprogress = 0 AND cm.added <= :as_of
JOIN mdl_modules m         ON m.id = cm.module AND m.name = 'assign'
JOIN student_enrol se      ON se.course_id = a.course
CROSS JOIN LATERAL (
    -- Bài chỉ giao cho một số nhóm (Hạn chế truy cập: "Nhóm") không tính cho SV ngoài nhóm. Xét điều kiện "group"
    -- cấp ngoài cùng: op "&" -> phải thuộc mọi nhóm nêu tên, op "|" -> thuộc ít nhất một nhóm (hoặc có điều kiện khác
    -- không phải nhóm thì coi là có thể thỏa). Điều kiện không có id = thuộc nhóm bất kỳ. Phủ định / lồng nhau: vẫn tính.
    SELECT CASE
        WHEN cm.availability IS NULL OR cm.availability !~ '"type"\s*:\s*"group"' OR cm.availability !~ '^\s*\{' THEN TRUE
        ELSE (
            SELECT CASE j.v->>'op'
                       WHEN '&' THEN COALESCE(bool_and(x.member) FILTER (WHERE x.is_group), TRUE)
                       WHEN '|' THEN COALESCE(bool_or(x.member) FILTER (WHERE x.is_group), TRUE)
                                     OR bool_or(NOT x.is_group)
                       ELSE TRUE END
            FROM (SELECT cm.availability::jsonb AS v) j
            CROSS JOIN LATERAL (
                SELECT c->>'type' = 'group' AS is_group,
                       EXISTS (SELECT 1 FROM member_groups mg
                               WHERE mg.courseid = cm.course AND mg.userid = se.user_id
                                 AND (NOT (c ? 'id') OR mg.groupid = (c->>'id')::bigint)) AS member
                FROM jsonb_array_elements(COALESCE(j.v->'c', '[]'::jsonb)) c
            ) x
            GROUP BY j.v
        )
    END AS applies
) av
LEFT JOIN mdl_assign_user_flags uf ON uf.assignment = a.id AND uf.userid = se.user_id
LEFT JOIN mdl_assign_overrides uo  ON uo.assignid = a.id AND uo.userid = se.user_id
LEFT JOIN LATERAL (
    SELECT o.duedate
    FROM mdl_assign_overrides o
    WHERE o.assignid = a.id
      AND o.duedate IS NOT NULL
      AND o.groupid IN (SELECT mg.groupid FROM member_groups mg
                        WHERE mg.courseid = a.course AND mg.userid = se.user_id)
    ORDER BY o.sortorder, o.id
    LIMIT 1
) go ON TRUE
CROSS JOIN LATERAL (
    SELECT COALESCE(NULLIF(uf.extensionduedate, 0), uo.duedate, go.duedate, NULLIF(a.duedate, 0),
                    NULLIF(a.cutoffdate, 0), NULLIF(a.gradingduedate, 0), 0) AS duedate
) due
LEFT JOIN LATERAL (
    SELECT MIN(s.timemodified) AS submitted_ts
    FROM mdl_assign_submission s
    WHERE s.assignment = a.id
      AND s.latest = 1
      AND s.status = 'submitted'
      AND s.timemodified <= :as_of
      AND (
            (a.teamsubmission = 0 AND s.userid = se.user_id)
         OR (a.teamsubmission = 1 AND s.userid = 0 AND s.groupid IN (
                SELECT mg.groupid FROM member_groups mg WHERE mg.courseid = a.course AND mg.userid = se.user_id))
      )
) sub ON TRUE
WHERE a.course = ANY(CAST(:course_ids AS bigint[]))
  AND due.duedate > 0
  AND av.applies

UNION ALL

SELECT q.course        AS course_id,
       se.user_id,
       -q.id           AS assign_id,
       q.name          AS assign_name,
       q.timeclose     AS duedate,
       fin.submitted_ts,
       'quiz'          AS kind
FROM mdl_quiz q
JOIN mdl_course_modules cm ON cm.instance = q.id AND cm.course = q.course
                          AND cm.visible = 1 AND cm.deletioninprogress = 0 AND cm.added <= :as_of
JOIN mdl_modules m         ON m.id = cm.module AND m.name = 'quiz'
JOIN student_enrol se      ON se.course_id = q.course
CROSS JOIN LATERAL (
    -- Bài chỉ giao cho một số nhóm (Hạn chế truy cập: "Nhóm") không tính cho SV ngoài nhóm. Xét điều kiện "group"
    -- cấp ngoài cùng: op "&" -> phải thuộc mọi nhóm nêu tên, op "|" -> thuộc ít nhất một nhóm (hoặc có điều kiện khác
    -- không phải nhóm thì coi là có thể thỏa). Điều kiện không có id = thuộc nhóm bất kỳ. Phủ định / lồng nhau: vẫn tính.
    SELECT CASE
        WHEN cm.availability IS NULL OR cm.availability !~ '"type"\s*:\s*"group"' OR cm.availability !~ '^\s*\{' THEN TRUE
        ELSE (
            SELECT CASE j.v->>'op'
                       WHEN '&' THEN COALESCE(bool_and(x.member) FILTER (WHERE x.is_group), TRUE)
                       WHEN '|' THEN COALESCE(bool_or(x.member) FILTER (WHERE x.is_group), TRUE)
                                     OR bool_or(NOT x.is_group)
                       ELSE TRUE END
            FROM (SELECT cm.availability::jsonb AS v) j
            CROSS JOIN LATERAL (
                SELECT c->>'type' = 'group' AS is_group,
                       EXISTS (SELECT 1 FROM member_groups mg
                               WHERE mg.courseid = cm.course AND mg.userid = se.user_id
                                 AND (NOT (c ? 'id') OR mg.groupid = (c->>'id')::bigint)) AS member
                FROM jsonb_array_elements(COALESCE(j.v->'c', '[]'::jsonb)) c
            ) x
            GROUP BY j.v
        )
    END AS applies
) av
LEFT JOIN LATERAL (
    SELECT MIN(qa.timefinish) AS submitted_ts
    FROM mdl_quiz_attempts qa
    WHERE qa.quiz = q.id AND qa.userid = se.user_id AND qa.preview = 0
      AND qa.state = 'finished' AND qa.timefinish > 0 AND qa.timefinish <= :as_of
) fin ON TRUE
WHERE q.course = ANY(CAST(:course_ids AS bigint[]))
  AND q.timeclose > 0
  AND av.applies
ORDER BY 1, 2, 5, 3
