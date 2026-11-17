-- =============================================================================
-- MOODLE_SRC V009 – Vùng đệm (staging) cho việc nạp dữ liệu Moodle thật từ CSV
-- stg.<bảng>          : do công cụ ingest tạo lại mỗi lần đọc file (mọi cột kiểu text, giữ nguyên dữ liệu file)
-- stg.scope_course    : các môn trong phạm vi nạp và tính toán
-- stg.ingest_batch    : nhật ký từng file đã đọc (mã băm, số dòng đọc / nạp / loại)
-- stg.reject          : dòng bị loại – chỉ lưu số dòng và lý do, KHÔNG lưu nội dung
-- =============================================================================
CREATE SCHEMA stg;
COMMENT ON SCHEMA stg IS 'Vùng đệm nạp CSV Moodle thật (python -m ingest.run)';

CREATE TABLE stg.scope_course (
    id BIGINT PRIMARY KEY
);
COMMENT ON TABLE stg.scope_course IS 'id các môn học trong phạm vi nạp (vd 173 môn khoa CNTT)';

CREATE TABLE stg.ingest_batch (
    batch_id      BIGSERIAL   PRIMARY KEY,
    batch         TEXT        NOT NULL,
    table_name    TEXT        NOT NULL,
    file_name     TEXT        NOT NULL,
    file_sha256   CHAR(64)    NOT NULL,
    file_bytes    BIGINT      NOT NULL,
    rows_read     BIGINT      NOT NULL DEFAULT 0,
    rows_staged   BIGINT      NOT NULL DEFAULT 0,
    rows_rejected BIGINT      NOT NULL DEFAULT 0,
    status        TEXT        NOT NULL DEFAULT 'READING',
    started_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at   TIMESTAMPTZ,
    CONSTRAINT ck_ingest_batch_status CHECK (status IN ('READING', 'STAGED', 'LOADED'))
);
CREATE INDEX ix_ingest_batch_table_sha ON stg.ingest_batch (table_name, file_sha256);

CREATE TABLE stg.reject (
    reject_id   BIGSERIAL PRIMARY KEY,
    batch_id    BIGINT    NOT NULL REFERENCES stg.ingest_batch (batch_id) ON DELETE CASCADE,
    line_no     BIGINT    NOT NULL,
    field_count INTEGER   NOT NULL,
    reason      TEXT      NOT NULL
);
