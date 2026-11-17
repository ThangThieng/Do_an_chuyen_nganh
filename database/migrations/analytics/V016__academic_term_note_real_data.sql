-- V016 – Ghi chú lịch học kỳ khi chạy trên dữ liệu thật của Khoa CNTT (xuất 12/11/2026).
-- Lịch HK1 2026-2027 (07/09 – 20/12/2026) được đặt từ thời dữ liệu mô phỏng; chưa có lịch chính thức của trường để
-- đối chiếu nên GIỮ ngày, chỉ sửa ghi chú cho đúng sự thật. Có lịch thật thì cập nhật start_date, end_date,
-- week1_start (đánh số tuần T1, T2… trên đồ thị xu hướng cấp trường/khoa).
UPDATE analytics.academic_term
SET note = 'HK1 2026-2027 – lịch tạm, chưa đối chiếu lịch chính thức của trường'
WHERE academic_year = '2026-2027' AND semester = 1 AND note LIKE '%mô phỏng%';
