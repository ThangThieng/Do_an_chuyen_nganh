-- =============================================================================
-- MOODLE_SRC V007 – Quiz, điểm chấm bài tập, grouping
-- Nguồn cấu trúc: Moodle 3.11 (mod/quiz, mod/assign, lib/db/install.xml), đủ cột như bản gốc.
-- Cột password của mdl_quiz KHÔNG được tạo (dữ liệu nhạy cảm, hệ thống không dùng).\n-- =============================================================================

-- ---------------------------------------------------------------- mdl_quiz
CREATE TABLE mdl_quiz (
    id                          BIGSERIAL PRIMARY KEY,
    course                      BIGINT NOT NULL DEFAULT 0,
    name                        VARCHAR(255) NOT NULL,
    intro                       TEXT NOT NULL,
    introformat                 SMALLINT NOT NULL DEFAULT 0,
    timeopen                    BIGINT NOT NULL DEFAULT 0,
    timeclose                   BIGINT NOT NULL DEFAULT 0,
    timelimit                   BIGINT NOT NULL DEFAULT 0,
    overduehandling             VARCHAR(16) NOT NULL DEFAULT 'autoabandon',
    graceperiod                 BIGINT NOT NULL DEFAULT 0,
    preferredbehaviour          VARCHAR(32) NOT NULL,
    canredoquestions            SMALLINT NOT NULL DEFAULT 0,
    attempts                    INTEGER NOT NULL DEFAULT 0,
    attemptonlast               SMALLINT NOT NULL DEFAULT 0,
    grademethod                 SMALLINT NOT NULL DEFAULT 1,
    decimalpoints               SMALLINT NOT NULL DEFAULT 2,
    questiondecimalpoints       SMALLINT NOT NULL DEFAULT -1,
    reviewattempt               INTEGER NOT NULL DEFAULT 0,
    reviewcorrectness           INTEGER NOT NULL DEFAULT 0,
    reviewmarks                 INTEGER NOT NULL DEFAULT 0,
    reviewspecificfeedback      INTEGER NOT NULL DEFAULT 0,
    reviewgeneralfeedback       INTEGER NOT NULL DEFAULT 0,
    reviewrightanswer           INTEGER NOT NULL DEFAULT 0,
    reviewoverallfeedback       INTEGER NOT NULL DEFAULT 0,
    questionsperpage            BIGINT NOT NULL DEFAULT 0,
    navmethod                   VARCHAR(16) NOT NULL DEFAULT 'free',
    shuffleanswers              SMALLINT NOT NULL DEFAULT 0,
    sumgrades                   NUMERIC(10,5) NOT NULL DEFAULT 0,
    grade                       NUMERIC(10,5) NOT NULL DEFAULT 0,
    timecreated                 BIGINT NOT NULL DEFAULT 0,
    timemodified                BIGINT NOT NULL DEFAULT 0,
    subnet                      VARCHAR(255) NOT NULL,
    browsersecurity             VARCHAR(32) NOT NULL,
    delay1                      BIGINT NOT NULL DEFAULT 0,
    delay2                      BIGINT NOT NULL DEFAULT 0,
    showuserpicture             SMALLINT NOT NULL DEFAULT 0,
    showblocks                  SMALLINT NOT NULL DEFAULT 0,
    completionattemptsexhausted SMALLINT DEFAULT 0,
    completionpass              SMALLINT DEFAULT 0,
    completionminattempts       BIGINT NOT NULL DEFAULT 0,
    allowofflineattempts        SMALLINT DEFAULT 0
);
CREATE INDEX mdl_quiz_course_ix ON mdl_quiz (course);
COMMENT ON TABLE mdl_quiz IS 'The settings for each quiz.';

-- ---------------------------------------------------------------- mdl_quiz_attempts
CREATE TABLE mdl_quiz_attempts (
    id                  BIGSERIAL PRIMARY KEY,
    quiz                BIGINT NOT NULL DEFAULT 0,
    userid              BIGINT NOT NULL DEFAULT 0,
    attempt             INTEGER NOT NULL DEFAULT 0,
    uniqueid            BIGINT NOT NULL DEFAULT 0,
    layout              TEXT NOT NULL,
    currentpage         BIGINT NOT NULL DEFAULT 0,
    preview             SMALLINT NOT NULL DEFAULT 0,
    state               VARCHAR(16) NOT NULL DEFAULT 'inprogress',
    timestart           BIGINT NOT NULL DEFAULT 0,
    timefinish          BIGINT NOT NULL DEFAULT 0,
    timemodified        BIGINT NOT NULL DEFAULT 0,
    timemodifiedoffline BIGINT NOT NULL DEFAULT 0,
    timecheckstate      BIGINT DEFAULT 0,
    sumgrades           NUMERIC(10,5)
);
CREATE INDEX mdl_quiz_attempts_quiz_ix ON mdl_quiz_attempts (quiz);
CREATE INDEX mdl_quiz_attempts_userid_ix ON mdl_quiz_attempts (userid);
CREATE UNIQUE INDEX mdl_quiz_attempts_uniqueid_uix ON mdl_quiz_attempts (uniqueid);
CREATE UNIQUE INDEX mdl_quiz_attempts_quiz_userid_attempt_uix ON mdl_quiz_attempts (quiz, userid, attempt);
CREATE INDEX mdl_quiz_attempts_state_timecheckstate_ix ON mdl_quiz_attempts (state, timecheckstate);
COMMENT ON TABLE mdl_quiz_attempts IS 'Stores users attempts at quizzes.';

-- ---------------------------------------------------------------- mdl_quiz_grades
CREATE TABLE mdl_quiz_grades (
    id           BIGSERIAL PRIMARY KEY,
    quiz         BIGINT NOT NULL DEFAULT 0,
    userid       BIGINT NOT NULL DEFAULT 0,
    grade        NUMERIC(10,5) NOT NULL DEFAULT 0,
    timemodified BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_quiz_grades_quiz_ix ON mdl_quiz_grades (quiz);
CREATE INDEX mdl_quiz_grades_userid_ix ON mdl_quiz_grades (userid);
COMMENT ON TABLE mdl_quiz_grades IS 'Stores the overall grade for each user on the quiz, based on their various attempts and the quiz.grademethod setting.';

-- ---------------------------------------------------------------- mdl_assign_grades
CREATE TABLE mdl_assign_grades (
    id            BIGSERIAL PRIMARY KEY,
    assignment    BIGINT NOT NULL DEFAULT 0,
    userid        BIGINT NOT NULL DEFAULT 0,
    timecreated   BIGINT NOT NULL DEFAULT 0,
    timemodified  BIGINT NOT NULL DEFAULT 0,
    grader        BIGINT NOT NULL DEFAULT 0,
    grade         NUMERIC(10,5) DEFAULT 0,
    attemptnumber BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_assign_grades_assignment_ix ON mdl_assign_grades (assignment);
CREATE INDEX mdl_assign_grades_userid_ix ON mdl_assign_grades (userid);
CREATE INDEX mdl_assign_grades_attemptnumber_ix ON mdl_assign_grades (attemptnumber);
CREATE UNIQUE INDEX mdl_assign_grades_assignment_userid_attemptnumber_uix ON mdl_assign_grades (assignment, userid, attemptnumber);
COMMENT ON TABLE mdl_assign_grades IS 'Grading information about a single assignment submission.';

-- ---------------------------------------------------------------- mdl_groupings
CREATE TABLE mdl_groupings (
    id                BIGSERIAL PRIMARY KEY,
    courseid          BIGINT NOT NULL DEFAULT 0,
    name              VARCHAR(255) NOT NULL,
    idnumber          VARCHAR(100) NOT NULL,
    description       TEXT,
    descriptionformat SMALLINT NOT NULL DEFAULT 0,
    configdata        TEXT,
    timecreated       BIGINT NOT NULL DEFAULT 0,
    timemodified      BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_groupings_courseid_ix ON mdl_groupings (courseid);
CREATE INDEX mdl_groupings_idnumber_ix ON mdl_groupings (idnumber);
COMMENT ON TABLE mdl_groupings IS 'A grouping is a collection of groups. WAS: groups_groupings';
