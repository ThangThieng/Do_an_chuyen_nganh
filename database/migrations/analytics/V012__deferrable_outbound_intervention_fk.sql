-- =============================================================================
-- V012 – Hai khóa ngoại tham chiếu chéo giữa nhật ký can thiệp và tin gửi đi được hoãn kiểm tra tới cuối giao dịch
--
-- intervention_log.outbound_id -> outbound_message và outbound_message.intervention_id -> intervention_log
-- tham chiếu lẫn nhau nên không có thứ tự nạp nào thỏa cả hai chiều khi phục hồi bản sao lưu (COPY từng bảng).
-- DEFERRABLE INITIALLY IMMEDIATE: mọi giao dịch thường vẫn kiểm tra ngay như cũ; chỉ giao dịch phục hồi chủ động
-- SET CONSTRAINTS … DEFERRED để kiểm tra khi COMMIT.
-- =============================================================================
ALTER TABLE analytics.intervention_log
    ALTER CONSTRAINT fk_intervention_outbound DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE analytics.outbound_message
    ALTER CONSTRAINT fk_outbound_intervention DEFERRABLE INITIALLY IMMEDIATE;
