-- Sinh viên ghi danh hợp lệ + thông tin hiển thị (MSSV, họ tên, email)
WITH student_enrol AS ({{student_enrol}})
SELECT se.course_id,
       se.user_id,
       -- MSSV: idnumber; nếu trường không dùng idnumber thì lấy cụm 7 chữ số trong username
       COALESCE(NULLIF(u.idnumber, ''), substring(u.username from '(?<![0-9])[0-9]{7}(?![0-9])')) AS student_code,
       u.lastname,
       u.firstname,
       NULLIF(u.email, '')    AS email
FROM student_enrol se
JOIN mdl_user u ON u.id = se.user_id
ORDER BY se.course_id, se.user_id
