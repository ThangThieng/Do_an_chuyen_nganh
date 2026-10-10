-- =============================================================================
-- V008: Theo dõi mật khẩu và lần đăng nhập của tài khoản Dashboard
--   - password_changed_at: token JWT phát hành TRƯỚC thời điểm này bị từ chối
--     (đổi mật khẩu / quản trị viên đặt lại mật khẩu -> các phiên cũ mất hiệu lực).
--   - last_login_at: lần đăng nhập thành công gần nhất (hiển thị ở màn hình Quản lý người dùng).
-- =============================================================================

ALTER TABLE analytics.app_user
    ADD COLUMN password_changed_at TIMESTAMPTZ,
    ADD COLUMN last_login_at       TIMESTAMPTZ;

COMMENT ON COLUMN analytics.app_user.password_changed_at IS
    'Lần đổi/đặt lại mật khẩu gần nhất; JWT có iat nhỏ hơn giá trị này (làm tròn xuống giây) bị từ chối';
COMMENT ON COLUMN analytics.app_user.last_login_at IS 'Lần đăng nhập Dashboard thành công gần nhất';
