-- =============================================================================
-- MOODLE_SRC V006 – Sổ điểm (gradebook)
-- Nguồn cấu trúc: Moodle 3.11 (lib/db/install.xml), đủ cột như bản gốc.
-- Dùng cho: điểm danh lấy từ sổ điểm (tiêu chí C1 khi không có bảng plugin mod_attendance) và các chức năng điểm.\n-- =============================================================================

-- ---------------------------------------------------------------- mdl_scale
CREATE TABLE mdl_scale (
    id                BIGSERIAL PRIMARY KEY,
    courseid          BIGINT NOT NULL DEFAULT 0,
    userid            BIGINT NOT NULL DEFAULT 0,
    name              VARCHAR(255) NOT NULL,
    scale             TEXT NOT NULL,
    description       TEXT NOT NULL,
    descriptionformat SMALLINT NOT NULL DEFAULT 0,
    timemodified      BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_scale_courseid_ix ON mdl_scale (courseid);
COMMENT ON TABLE mdl_scale IS 'Defines grading scales';

-- ---------------------------------------------------------------- mdl_grade_categories
CREATE TABLE mdl_grade_categories (
    id                  BIGSERIAL PRIMARY KEY,
    courseid            BIGINT NOT NULL,
    parent              BIGINT,
    depth               BIGINT NOT NULL DEFAULT 0,
    path                VARCHAR(255),
    fullname            VARCHAR(255) NOT NULL,
    aggregation         BIGINT NOT NULL DEFAULT 0,
    keephigh            BIGINT NOT NULL DEFAULT 0,
    droplow             BIGINT NOT NULL DEFAULT 0,
    aggregateonlygraded SMALLINT NOT NULL DEFAULT 0,
    aggregateoutcomes   SMALLINT NOT NULL DEFAULT 0,
    timecreated         BIGINT NOT NULL,
    timemodified        BIGINT NOT NULL,
    hidden              BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX mdl_grade_categories_courseid_ix ON mdl_grade_categories (courseid);
CREATE INDEX mdl_grade_categories_parent_ix ON mdl_grade_categories (parent);
COMMENT ON TABLE mdl_grade_categories IS 'This table keeps information about categories, used for grouping items.';

-- ---------------------------------------------------------------- mdl_grade_items
CREATE TABLE mdl_grade_items (
    id               BIGSERIAL PRIMARY KEY,
    courseid         BIGINT,
    categoryid       BIGINT,
    itemname         VARCHAR(255),
    itemtype         VARCHAR(30) NOT NULL,
    itemmodule       VARCHAR(30),
    iteminstance     BIGINT,
    itemnumber       BIGINT,
    iteminfo         TEXT,
    idnumber         VARCHAR(255),
    calculation      TEXT,
    gradetype        SMALLINT NOT NULL DEFAULT 1,
    grademax         NUMERIC(10,5) NOT NULL DEFAULT 100,
    grademin         NUMERIC(10,5) NOT NULL DEFAULT 0,
    scaleid          BIGINT,
    outcomeid        BIGINT,
    gradepass        NUMERIC(10,5) NOT NULL DEFAULT 0,
    multfactor       NUMERIC(10,5) NOT NULL DEFAULT 1.0,
    plusfactor       NUMERIC(10,5) NOT NULL DEFAULT 0,
    aggregationcoef  NUMERIC(10,5) NOT NULL DEFAULT 0,
    aggregationcoef2 NUMERIC(10,5) NOT NULL DEFAULT 0,
    sortorder        BIGINT NOT NULL DEFAULT 0,
    display          BIGINT NOT NULL DEFAULT 0,
    decimals         SMALLINT,
    hidden           BIGINT NOT NULL DEFAULT 0,
    locked           BIGINT NOT NULL DEFAULT 0,
    locktime         BIGINT NOT NULL DEFAULT 0,
    needsupdate      BIGINT NOT NULL DEFAULT 0,
    weightoverride   SMALLINT NOT NULL DEFAULT 0,
    timecreated      BIGINT,
    timemodified     BIGINT
);
CREATE INDEX mdl_grade_items_courseid_ix ON mdl_grade_items (courseid);
CREATE INDEX mdl_grade_items_categoryid_ix ON mdl_grade_items (categoryid);
CREATE INDEX mdl_grade_items_scaleid_ix ON mdl_grade_items (scaleid);
CREATE INDEX mdl_grade_items_outcomeid_ix ON mdl_grade_items (outcomeid);
CREATE INDEX mdl_grade_items_locked_locktime_ix ON mdl_grade_items (locked, locktime);
CREATE INDEX mdl_grade_items_itemtype_needsupdate_ix ON mdl_grade_items (itemtype, needsupdate);
CREATE INDEX mdl_grade_items_gradetype_ix ON mdl_grade_items (gradetype);
CREATE INDEX mdl_grade_items_idnumber_courseid_ix ON mdl_grade_items (idnumber, courseid);
COMMENT ON TABLE mdl_grade_items IS 'This table keeps information about gradeable items (ie columns). If an activity (eg an assignment or quiz) has multiple grade_items associated with it (eg several outcomes or numerical grades), then there will be a corresponding multiple number of rows in this table.';

-- ---------------------------------------------------------------- mdl_grade_grades
CREATE TABLE mdl_grade_grades (
    id                BIGSERIAL PRIMARY KEY,
    itemid            BIGINT NOT NULL,
    userid            BIGINT NOT NULL,
    rawgrade          NUMERIC(10,5),
    rawgrademax       NUMERIC(10,5) NOT NULL DEFAULT 100,
    rawgrademin       NUMERIC(10,5) NOT NULL DEFAULT 0,
    rawscaleid        BIGINT,
    usermodified      BIGINT,
    finalgrade        NUMERIC(10,5),
    hidden            BIGINT NOT NULL DEFAULT 0,
    locked            BIGINT NOT NULL DEFAULT 0,
    locktime          BIGINT NOT NULL DEFAULT 0,
    exported          BIGINT NOT NULL DEFAULT 0,
    overridden        BIGINT NOT NULL DEFAULT 0,
    excluded          BIGINT NOT NULL DEFAULT 0,
    feedback          TEXT,
    feedbackformat    BIGINT NOT NULL DEFAULT 0,
    information       TEXT,
    informationformat BIGINT NOT NULL DEFAULT 0,
    timecreated       BIGINT,
    timemodified      BIGINT,
    aggregationstatus VARCHAR(10) NOT NULL DEFAULT 'unknown',
    aggregationweight NUMERIC(10,5)
);
CREATE INDEX mdl_grade_grades_itemid_ix ON mdl_grade_grades (itemid);
CREATE INDEX mdl_grade_grades_userid_ix ON mdl_grade_grades (userid);
CREATE INDEX mdl_grade_grades_rawscaleid_ix ON mdl_grade_grades (rawscaleid);
CREATE INDEX mdl_grade_grades_usermodified_ix ON mdl_grade_grades (usermodified);
CREATE UNIQUE INDEX mdl_grade_grades_userid_itemid_uix ON mdl_grade_grades (userid, itemid);
CREATE INDEX mdl_grade_grades_locked_locktime_ix ON mdl_grade_grades (locked, locktime);
COMMENT ON TABLE mdl_grade_grades IS 'grade_grades  This table keeps individual grades for each user and each item, exactly as imported or submitted by modules. The rawgrademax/min and rawscaleid are stored here to record the values at the time the grade was stored, because teachers might change this for an activity! All the results are normalised/resampled for the final grade value.';
