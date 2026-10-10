/**
 * Trang Môn học – cấp Micro của quản trị viên (chỉ đọc): biểu đồ tròn + xu hướng rủi ro của môn, bảng cảnh báo có
 * điểm từng tiêu chí, danh sách sinh viên có/không tương tác (giữ nguyên từ v1.1), cửa sổ chi tiết sinh viên.
 * Gửi tin và đổi luật cảnh báo là việc của giảng viên phụ trách nên không có ở đây.
 */
import { Alert, Card, Col, Row, Tabs } from "antd";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { errorText } from "../../api/client.js";
import { useAdminRiskStudents, useAdminRiskSummary, useCourseStudents } from "../../api/hooks.js";
import { CourseStudentsTable } from "../../components/CourseTables.jsx";
import { Delta, KpiCard } from "../../components/common.jsx";
import LevelBreadcrumb from "../../components/LevelBreadcrumb.jsx";
import RiskOverviewPanel from "../../components/RiskOverviewPanel.jsx";
import RiskStudentTable, { INITIAL_TABLE_STATE, studentParams } from "../../components/RiskStudentTable.jsx";
import StudentDetailModal from "../../components/StudentDetailModal.jsx";
import { RISK, RISK_LEVELS } from "../../theme/tokens.js";
import { fmtDate, fmtInt, fmtPercent, share } from "../../utils/format.js";
import useStudentParam from "../../utils/useStudentParam.js";
import useTerm from "../../utils/useTerm.js";

export default function AdminCourse() {
  const { courseId } = useParams();
  const { term, search } = useTerm();
  const [table, setTable] = useState(INITIAL_TABLE_STATE);
  const [openUser, setOpenUser, closeUser] = useStudentParam();
  const update = (patch) => setTable((s) => ({ ...s, ...patch }));
  const summary = useAdminRiskSummary(courseId);
  const students = useAdminRiskStudents(courseId, studentParams(table));
  const header = useCourseStudents(courseId, { page: 1, page_size: 1 }).data?.course;
  const sum = summary.data;

  if (summary.error) {
    return <Alert type="error" showIcon message="Không mở được môn học" description={errorText(summary.error)} />;
  }
  const courseName = header ? `${header.shortname} – ${header.fullname}` : "Môn học";
  return (
    <>
      <LevelBreadcrumb level={openUser ? "student" : "course"} search={search}
        faculty={header ? { id: header.faculty_id, name: header.faculty_name } : undefined}
        course={{ id: courseId, name: courseName }} />
      <Row gutter={[16, 16]}>
        {RISK_LEVELS.map((level) => {
          const key = level.toLowerCase();
          const prev = sum?.prev_week?.[key];
          return (
            <Col xs={24} sm={8} key={level}>
              <KpiCard label={RISK[level].label} loading={!sum} accent={RISK[level].color}
                value={<>{fmtInt(sum?.[key])} SV <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({fmtPercent(share(sum?.[key], sum?.total), 0)})</span></>}
                hint={prev != null ? <Delta value={sum[key] - prev} unit="sv" betterWhen={level === "GREEN" ? "up" : "down"} /> : undefined} />
            </Col>
          );
        })}
        <Col span={24}>
          <RiskOverviewPanel title={header?.shortname} loading={!sum} courseId={courseId} centerLabel="sinh viên"
            summary={sum ? { red: sum.red, yellow: sum.yellow, green: sum.green, total: sum.total } : null}
            trend={{ term, courseId: Number(courseId) }}
            footnote={sum ? `Snapshot ${fmtDate(sum.snapshot_date)} · luật cảnh báo: ${sum.rule?.scope === "COURSE" ? `riêng của môn (${sum.rule.label})` : "mặc định của trường"}` : undefined} />
        </Col>
        <Col span={24}>
          <Card>
            <Tabs items={[
              { key: "risk", label: "Bảng cảnh báo", children: (
                <RiskStudentTable state={table} setState={update} data={students.data} loading={students.isFetching}
                  onOpen={setOpenUser} rule={sum?.rule} />) },
              { key: "all", label: "Tất cả sinh viên", children: <CourseStudentsTable courseId={courseId} onPick={setOpenUser} /> },
            ]} />
          </Card>
        </Col>
      </Row>
      {openUser && <StudentDetailModal readOnly courseId={courseId} userId={openUser} onClose={closeUser} />}
    </>
  );
}
