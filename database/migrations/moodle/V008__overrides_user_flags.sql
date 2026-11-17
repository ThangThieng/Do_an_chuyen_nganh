-- =============================================================================
-- MOODLE_SRC V008 – Hạn riêng và gia hạn (override)
-- Nguồn cấu trúc: Moodle 3.11 (mod/assign, mod/quiz), đủ cột như bản gốc.
-- Tạo sẵn để ETL áp dụng hạn hiệu lực theo quy tắc Moodle; bảng rỗng thì kết quả như không có hạn riêng.\n-- Cột password của mdl_quiz_overrides KHÔNG được tạo.\n-- =============================================================================

-- ---------------------------------------------------------------- mdl_assign_overrides
CREATE TABLE mdl_assign_overrides (
    id                       BIGSERIAL PRIMARY KEY,
    assignid                 BIGINT NOT NULL DEFAULT 0,
    groupid                  BIGINT,
    userid                   BIGINT,
    sortorder                BIGINT,
    allowsubmissionsfromdate BIGINT,
    duedate                  BIGINT,
    cutoffdate               BIGINT
);
CREATE INDEX mdl_assign_overrides_assignid_ix ON mdl_assign_overrides (assignid);
CREATE INDEX mdl_assign_overrides_groupid_ix ON mdl_assign_overrides (groupid);
CREATE INDEX mdl_assign_overrides_userid_ix ON mdl_assign_overrides (userid);
COMMENT ON TABLE mdl_assign_overrides IS 'The overrides to assign settings.';

-- ---------------------------------------------------------------- mdl_assign_user_flags
CREATE TABLE mdl_assign_user_flags (
    id               BIGSERIAL PRIMARY KEY,
    userid           BIGINT NOT NULL DEFAULT 0,
    assignment       BIGINT NOT NULL DEFAULT 0,
    locked           BIGINT NOT NULL DEFAULT 0,
    mailed           SMALLINT NOT NULL DEFAULT 0,
    extensionduedate BIGINT NOT NULL DEFAULT 0,
    workflowstate    VARCHAR(20),
    allocatedmarker  BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_assign_user_flags_userid_ix ON mdl_assign_user_flags (userid);
CREATE INDEX mdl_assign_user_flags_assignment_ix ON mdl_assign_user_flags (assignment);
CREATE INDEX mdl_assign_user_flags_mailed_ix ON mdl_assign_user_flags (mailed);
COMMENT ON TABLE mdl_assign_user_flags IS 'List of flags that can be set for a single user in a single assignment.';

-- ---------------------------------------------------------------- mdl_quiz_overrides
CREATE TABLE mdl_quiz_overrides (
    id        BIGSERIAL PRIMARY KEY,
    quiz      BIGINT NOT NULL DEFAULT 0,
    groupid   BIGINT,
    userid    BIGINT,
    timeopen  BIGINT,
    timeclose BIGINT,
    timelimit BIGINT,
    attempts  INTEGER
);
CREATE INDEX mdl_quiz_overrides_quiz_ix ON mdl_quiz_overrides (quiz);
CREATE INDEX mdl_quiz_overrides_groupid_ix ON mdl_quiz_overrides (groupid);
CREATE INDEX mdl_quiz_overrides_userid_ix ON mdl_quiz_overrides (userid);
COMMENT ON TABLE mdl_quiz_overrides IS 'The overrides to quiz settings on a per-user and per-group basis.';
