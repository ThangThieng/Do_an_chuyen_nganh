-- Bộ luật đã dùng cho snapshot rủi ro mới nhất (không muộn hơn :stat_date) của mỗi môn – để bảng tiến độ môn
-- ghi rule_set_id theo ngày (vạch "đổi luật" trên đồ thị xu hướng).
SELECT DISTINCT ON (r.course_id) r.course_id, r.rule_set_id
FROM analytics.fact_student_risk_summary r
WHERE r.course_id = ANY(CAST(:course_ids AS integer[]))
  AND r.snapshot_date <= :stat_date
ORDER BY r.course_id, r.snapshot_date DESC
