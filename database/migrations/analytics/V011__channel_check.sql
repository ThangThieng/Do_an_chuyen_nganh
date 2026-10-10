-- =============================================================================
-- V011 – Kết quả kiểm tra kết nối kênh gửi tin (điều kiện 3 của chốt chặn gửi thật)
-- Gửi tới người nhận thật chỉ được phép khi kênh đã kiểm tra thành công với ĐÚNG cấu hình hiện tại
-- (config_fingerprint = băm cấu hình không chứa bí mật – đổi máy chủ/tài khoản thì phải kiểm tra lại).
-- =============================================================================
CREATE TABLE analytics.channel_check (
    channel             VARCHAR(6)   PRIMARY KEY,
    ok                  BOOLEAN      NOT NULL,
    config_fingerprint  CHAR(64)     NOT NULL,
    detail              JSONB        NOT NULL DEFAULT '{}',
    checked_by          INTEGER,
    checked_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_channel_check_channel CHECK (channel IN ('EMAIL', 'MOODLE')),
    CONSTRAINT fk_channel_check_user FOREIGN KEY (checked_by) REFERENCES analytics.app_user (user_id) ON DELETE SET NULL
);
COMMENT ON TABLE analytics.channel_check IS 'Lần kiểm tra kết nối gần nhất của kênh EMAIL/MOODLE (Hệ thống › Kênh gửi tin)';
