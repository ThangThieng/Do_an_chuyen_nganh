-- Người dùng online tại :as_of: phiên có hoạt động trong :window giây gần nhất (SPEC 1.4)
-- covered = bảng phiên có dữ liệu không muộn hơn :as_of. Bản xuất CSV chỉ chụp mdl_sessions SAU mốc tính thì covered = 0:
-- khi đó ETL giữ số ước tính từ nhật ký (LOGSTORE) thay vì ghi 0.
SELECT COUNT(DISTINCT userid) FILTER (WHERE timemodified >= CAST(:as_of AS bigint) - CAST(:window AS bigint)
                                        AND timemodified <= :as_of) AS online_users,
       COUNT(*) FILTER (WHERE timemodified <= :as_of)                AS covered
FROM mdl_sessions
WHERE userid > 0
