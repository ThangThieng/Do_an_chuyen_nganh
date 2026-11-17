"""
Thứ tự cột của các bảng Moodle 3.11 (sinh từ install.xml chính thức: lib, mod_assign, mod_quiz, logstore_standard).
Dùng để đọc các file CSV xuất nguyên bảng nhưng KHÔNG có dòng tiêu đề.
"""
from __future__ import annotations

COLUMNS: dict[str, tuple[str, ...]] = {
    "user": (
        "id", "auth", "confirmed", "policyagreed", "deleted", "suspended", "mnethostid", "username", "password",
        "idnumber", "firstname", "lastname", "email", "emailstop", "phone1", "phone2", "institution", "department",
        "address", "city", "country", "lang", "calendartype", "theme", "timezone", "firstaccess", "lastaccess",
        "lastlogin", "currentlogin", "lastip", "secret", "picture", "description", "descriptionformat",
        "mailformat", "maildigest", "maildisplay", "autosubscribe", "trackforums", "timecreated", "timemodified",
        "trustbitmask", "imagealt", "lastnamephonetic", "firstnamephonetic", "middlename", "alternatename",
        "moodlenetprofile",
    ),
    "course": (
        "id", "category", "sortorder", "fullname", "shortname", "idnumber", "summary", "summaryformat", "format",
        "showgrades", "newsitems", "startdate", "enddate", "relativedatesmode", "marker", "maxbytes",
        "legacyfiles", "showreports", "visible", "visibleold", "downloadcontent", "groupmode", "groupmodeforce",
        "defaultgroupingid", "lang", "calendartype", "theme", "timecreated", "timemodified", "requested",
        "enablecompletion", "completionnotify", "cacherev", "originalcourseid", "showactivitydates",
        "showcompletionconditions",
    ),
    "course_categories": (
        "id", "name", "idnumber", "description", "descriptionformat", "parent", "sortorder", "coursecount",
        "visible", "visibleold", "timemodified", "depth", "path", "theme",
    ),
    "role": (
        "id", "name", "shortname", "description", "sortorder", "archetype",
    ),
    "context": (
        "id", "contextlevel", "instanceid", "path", "depth", "locked",
    ),
    "modules": (
        "id", "name", "cron", "lastcron", "search", "visible",
    ),
    "assign": (
        "id", "course", "name", "intro", "introformat", "alwaysshowdescription", "nosubmissions",
        "submissiondrafts", "sendnotifications", "sendlatenotifications", "duedate", "allowsubmissionsfromdate",
        "grade", "timemodified", "requiresubmissionstatement", "completionsubmit", "cutoffdate", "gradingduedate",
        "teamsubmission", "requireallteammemberssubmit", "teamsubmissiongroupingid", "blindmarking", "hidegrader",
        "revealidentities", "attemptreopenmethod", "maxattempts", "markingworkflow", "markingallocation",
        "sendstudentnotifications", "preventsubmissionnotingroup",
    ),
    "quiz": (
        "id", "course", "name", "intro", "introformat", "timeopen", "timeclose", "timelimit", "overduehandling",
        "graceperiod", "preferredbehaviour", "canredoquestions", "attempts", "attemptonlast", "grademethod",
        "decimalpoints", "questiondecimalpoints", "reviewattempt", "reviewcorrectness", "reviewmarks",
        "reviewspecificfeedback", "reviewgeneralfeedback", "reviewrightanswer", "reviewoverallfeedback",
        "questionsperpage", "navmethod", "shuffleanswers", "sumgrades", "grade", "timecreated", "timemodified",
        "password", "subnet", "browsersecurity", "delay1", "delay2", "showuserpicture", "showblocks",
        "completionattemptsexhausted", "completionpass", "completionminattempts", "allowofflineattempts",
    ),
    "scale": (
        "id", "courseid", "userid", "name", "scale", "description", "descriptionformat", "timemodified",
    ),
    "enrol": (
        "id", "enrol", "status", "courseid", "sortorder", "name", "enrolperiod", "enrolstartdate", "enrolenddate",
        "expirynotify", "expirythreshold", "notifyall", "password", "cost", "currency", "roleid", "customint1",
        "customint2", "customint3", "customint4", "customint5", "customint6", "customint7", "customint8",
        "customchar1", "customchar2", "customchar3", "customdec1", "customdec2", "customtext1", "customtext2",
        "customtext3", "customtext4", "timecreated", "timemodified",
    ),
    "course_sections": (
        "id", "course", "section", "name", "summary", "summaryformat", "sequence", "visible", "availability",
        "timemodified",
    ),
    "course_modules": (
        "id", "course", "module", "instance", "section", "idnumber", "added", "score", "indent", "visible",
        "visibleoncoursepage", "visibleold", "groupmode", "groupingid", "completion", "completiongradeitemnumber",
        "completionview", "completionexpected", "showdescription", "availability", "deletioninprogress",
    ),
    "grade_categories": (
        "id", "courseid", "parent", "depth", "path", "fullname", "aggregation", "keephigh", "droplow",
        "aggregateonlygraded", "aggregateoutcomes", "timecreated", "timemodified", "hidden",
    ),
    "grade_items": (
        "id", "courseid", "categoryid", "itemname", "itemtype", "itemmodule", "iteminstance", "itemnumber",
        "iteminfo", "idnumber", "calculation", "gradetype", "grademax", "grademin", "scaleid", "outcomeid",
        "gradepass", "multfactor", "plusfactor", "aggregationcoef", "aggregationcoef2", "sortorder", "display",
        "decimals", "hidden", "locked", "locktime", "needsupdate", "weightoverride", "timecreated", "timemodified",
    ),
    "assign_submission": (
        "id", "assignment", "userid", "timecreated", "timemodified", "status", "groupid", "attemptnumber",
        "latest",
    ),
    "assign_grades": (
        "id", "assignment", "userid", "timecreated", "timemodified", "grader", "grade", "attemptnumber",
    ),
    "quiz_grades": (
        "id", "quiz", "userid", "grade", "timemodified",
    ),
    "groups": (
        "id", "courseid", "idnumber", "name", "description", "descriptionformat", "enrolmentkey", "picture",
        "timecreated", "timemodified",
    ),
    "groupings": (
        "id", "courseid", "name", "idnumber", "description", "descriptionformat", "configdata", "timecreated",
        "timemodified",
    ),
    "logstore_standard_log": (
        "id", "eventname", "component", "action", "target", "objecttable", "objectid", "crud", "edulevel",
        "contextid", "contextlevel", "contextinstanceid", "userid", "courseid", "relateduserid", "anonymous",
        "other", "timecreated", "origin", "ip", "realuserid",
    ),
    "notifications": (
        "id", "useridfrom", "useridto", "subject", "fullmessage", "fullmessageformat", "fullmessagehtml",
        "smallmessage", "component", "eventtype", "contexturl", "contexturlname", "timeread", "timecreated",
        "customdata",
    ),
    "sessions": (
        "id", "state", "sid", "userid", "sessdata", "timecreated", "timemodified", "firstip", "lastip",
    ),
    "role_assignments": (
        "id", "roleid", "contextid", "userid", "timemodified", "modifierid", "component", "itemid", "sortorder",
    ),
    "user_enrolments": (
        "id", "status", "enrolid", "userid", "timestart", "timeend", "modifierid", "timecreated", "timemodified",
    ),
    "groups_members": (
        "id", "groupid", "userid", "timeadded", "component", "itemid",
    ),
    "grade_grades": (
        "id", "itemid", "userid", "rawgrade", "rawgrademax", "rawgrademin", "rawscaleid", "usermodified",
        "finalgrade", "hidden", "locked", "locktime", "exported", "overridden", "excluded", "feedback",
        "feedbackformat", "information", "informationformat", "timecreated", "timemodified", "aggregationstatus",
        "aggregationweight",
    ),
    "quiz_attempts": (
        "id", "quiz", "userid", "attempt", "uniqueid", "layout", "currentpage", "preview", "state", "timestart",
        "timefinish", "timemodified", "timemodifiedoffline", "timecheckstate", "sumgrades",
    ),
    "course_modules_completion": (
        "id", "coursemoduleid", "userid", "completionstate", "viewed", "overrideby", "timemodified",
    ),
    "assign_overrides": (
        "id", "assignid", "groupid", "userid", "sortorder", "allowsubmissionsfromdate", "duedate", "cutoffdate",
    ),
    "assign_user_flags": (
        "id", "userid", "assignment", "locked", "mailed", "extensionduedate", "workflowstate", "allocatedmarker",
    ),
    "quiz_overrides": (
        "id", "quiz", "groupid", "userid", "timeopen", "timeclose", "timelimit", "attempts", "password",
    ),
    "groupings_groups": (
        "id", "groupingid", "groupid", "timeadded",
    ),
}
