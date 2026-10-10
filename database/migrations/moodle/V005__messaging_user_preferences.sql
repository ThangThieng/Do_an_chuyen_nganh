-- =============================================================================
-- MOODLE_SRC V005 – Hệ thống nhắn tin của Moodle (core_message) và tùy chọn người dùng
-- Nguồn cấu trúc: Moodle 3.9 lib/db/install.xml – https://moodleschema.zoola.io/
--
-- Dùng cho chức năng "Trung tâm can thiệp": máy chủ Moodle mô phỏng (tools/moodle_ws_stub) nhận lời gọi
-- core_message_send_instant_messages và ghi tin vào ĐÚNG các bảng mà Moodle thật ghi, để trình diễn
-- "sinh viên nhận được gì" và để kiểm thử đọc lại. ETL KHÔNG đọc các bảng này.
-- Giữ quy ước của các migration trước: tên bảng/cột/kiểu/mặc định như Moodle 3.9 trên PostgreSQL,
-- không có khóa ngoại vật lý (Moodle quản lý quan hệ ở tầng ứng dụng).
-- =============================================================================

-- ---------------------------------------------------------------- mdl_user_preferences
-- Tùy chọn của người dùng. Nhắn tin dùng 'message_blocknoncontacts':
--   0 = chỉ nhận từ liên hệ, 1 = thành viên chung khóa học (mặc định), 2 = mọi người trên site.
CREATE TABLE mdl_user_preferences (
    id      BIGSERIAL     PRIMARY KEY,
    userid  BIGINT        NOT NULL DEFAULT 0,
    name    VARCHAR(255)  NOT NULL DEFAULT '',
    value   VARCHAR(1333) NOT NULL DEFAULT '',
    CONSTRAINT mdl_userpref_usenam_uix UNIQUE (userid, name)
);
COMMENT ON TABLE mdl_user_preferences IS 'Tùy chọn người dùng (Moodle core) – dùng message_blocknoncontacts khi gửi tin';

-- ---------------------------------------------------------------- mdl_message_conversations
CREATE TABLE mdl_message_conversations (
    id            BIGSERIAL    PRIMARY KEY,
    type          BIGINT       NOT NULL DEFAULT 1,
    name          VARCHAR(255),
    convhash      VARCHAR(40),
    component     VARCHAR(100),
    itemtype      VARCHAR(100),
    itemid        BIGINT,
    contextid     BIGINT,
    enabled       SMALLINT     NOT NULL DEFAULT 0,
    timecreated   BIGINT       NOT NULL,
    timemodified  BIGINT
);
CREATE INDEX mdl_messconv_typ_ix ON mdl_message_conversations (type);
CREATE INDEX mdl_messconv_con_ix ON mdl_message_conversations (convhash);
CREATE INDEX mdl_messconv_comiteitecon_ix ON mdl_message_conversations (component, itemtype, itemid, contextid);
CREATE INDEX mdl_messconv_con2_ix ON mdl_message_conversations (contextid);
COMMENT ON TABLE mdl_message_conversations IS 'Cuộc hội thoại: type 1 = cá nhân (convhash = sha1 của hai user id đã sắp xếp nối bằng "-"), 2 = nhóm, 3 = tự nhắn';

-- ---------------------------------------------------------------- mdl_message_conversation_members
CREATE TABLE mdl_message_conversation_members (
    id              BIGSERIAL  PRIMARY KEY,
    conversationid  BIGINT     NOT NULL,
    userid          BIGINT     NOT NULL,
    timecreated     BIGINT     NOT NULL
);
CREATE INDEX mdl_messconvmemb_con_ix ON mdl_message_conversation_members (conversationid);
CREATE INDEX mdl_messconvmemb_use_ix ON mdl_message_conversation_members (userid);

-- ---------------------------------------------------------------- mdl_messages
CREATE TABLE mdl_messages (
    id                 BIGSERIAL  PRIMARY KEY,
    useridfrom         BIGINT     NOT NULL,
    conversationid     BIGINT     NOT NULL,
    subject            TEXT,
    fullmessage        TEXT,
    fullmessageformat  SMALLINT   NOT NULL DEFAULT 0,
    fullmessagehtml    TEXT,
    smallmessage       TEXT,
    timecreated        BIGINT     NOT NULL,
    fullmessagetrust   SMALLINT   NOT NULL DEFAULT 0,
    customdata         TEXT
);
CREATE INDEX mdl_mess_contim_ix ON mdl_messages (conversationid, timecreated);
CREATE INDEX mdl_mess_use_ix ON mdl_messages (useridfrom);
CREATE INDEX mdl_mess_con_ix ON mdl_messages (conversationid);
COMMENT ON TABLE mdl_messages IS 'Tin nhắn cá nhân/nhóm (Moodle 3.6+). Mã tin = id, trả về ở trường msgid của core_message_send_instant_messages';

-- ---------------------------------------------------------------- mdl_notifications
CREATE TABLE mdl_notifications (
    id                 BIGSERIAL     PRIMARY KEY,
    useridfrom         BIGINT        NOT NULL,
    useridto           BIGINT        NOT NULL,
    subject            TEXT,
    fullmessage        TEXT,
    fullmessageformat  SMALLINT      NOT NULL DEFAULT 0,
    fullmessagehtml    TEXT,
    smallmessage       TEXT,
    component          VARCHAR(100),
    eventtype          VARCHAR(100),
    contexturl         TEXT,
    contexturlname     TEXT,
    timeread           BIGINT,
    timecreated        BIGINT        NOT NULL,
    customdata         TEXT
);
CREATE INDEX mdl_noti_use_ix ON mdl_notifications (useridto);
CREATE INDEX mdl_noti_use2_ix ON mdl_notifications (useridfrom);
COMMENT ON TABLE mdl_notifications IS 'Thông báo hệ thống (useridfrom có thể âm: noreply/support user – nên không phải khóa ngoại)';
