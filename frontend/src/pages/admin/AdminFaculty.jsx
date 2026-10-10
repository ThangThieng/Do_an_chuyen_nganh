/**
 * Trang Khoa – cấp Meso (góp ý 1, 2, 3): KPI của khoa so với toàn trường, biểu đồ tròn + xu hướng rủi ro của khoa,
 * so sánh các môn trong khoa (thanh ngang theo chỉ số chọn được, đường trung bình khoa; phân bố rủi ro 100%),
 * bảng môn học (giữ nguyên cột, thêm % Nguy cơ cao và luật cảnh báo). Nhấn môn -> trang Môn học.
 */
import { Alert, Card, Col, Input, Row, Segmented, Select } from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { errorText } from "../../api/client.js";
import { useFacultyCourses } from "../../api/hooks.js";
import { ComparisonColumns, RiskShareBars, chartHeight } from "../../charts/ComparisonCharts.jsx";
import { CourseTable } from "../../components/CourseTables.jsx";
import { Delta, KpiCard } from "../../components/common.jsx";
import LevelBreadcrumb from "../../components/LevelBreadcrumb.jsx";
import MetricInfo from "../../components/MetricInfo.jsx";
import RiskOverviewPanel from "../../components/RiskOverviewPanel.jsx";
import TermFilterBar from "../../components/TermFilterBar.jsx";
import { RISK } from "../../theme/tokens.js";
import { fmtInt, fmtPercent, share } from "../../utils/format.js";
import useTerm from "../../utils/useTerm.js";

const METRICS = {
  active_rate: { label: "Tỷ lệ tương tác", ref: "avg_active_rate", info: "active_rate" },
  assignment_submission_rate: { label: "Nộp bài", ref: "avg_submission_rate", info: "submission_rate" },
  attendance_rate: { label: "Chuyên cần", ref: "avg_attendance_rate", info: "attendance_rate" },
};
// Khoa có hơn 25 môn: biểu đồ mặc định hiện 15 môn thấp nhất theo chỉ số đang chọn, kèm "Xem tất cả" (Mục 3.3)
const MANY_COURSES = 25;
const TOP_N = 15;

export default function AdminFaculty() {
  const { facultyId } = useParams();
  const navigate = useNavigate();
  const { term, setTerm, search, filters } = useTerm();
  const [metric, setMetric] = useState("active_rate");
  const [dept, setDept] = useState();
  const [query, setQuery] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [focusLevel, setFocusLevel] = useState(null);
  const courses = useFacultyCourses(Number(facultyId), term);
  const summary = courses.data?.summary;
  const all = courses.data?.items ?? [];
  const openCourse = (c) => navigate(`/admin/courses/${c.course_id}${search}`);

  const filtered = useMemo(() => all
    .filter((c) => !dept || c.category_name === dept)
    .filter((c) => !query || `${c.shortname} ${c.fullname}`.toLowerCase().includes(query.toLowerCase()))
    .map((c) => ({ ...c, label: `${c.shortname} ${c.fullname}` })), [all, dept, query]);
  const limited = !showAll && filtered.length > MANY_COURSES;
  const byMetric = useMemo(() => {
    const withData = filtered.filter((c) => c[metric] != null).sort((a, b) => Number(a[metric]) - Number(b[metric]));
    return limited ? withData.slice(0, TOP_N) : withData;
  }, [filtered, metric, limited]);
  const byRisk = useMemo(() => {
    const sorted = [...filtered].sort((a, b) => Number(b.red_rate ?? 0) - Number(a.red_rate ?? 0));
    return limited ? sorted.slice(0, TOP_N) : sorted;
  }, [filtered, limited]);
  const noData = filtered.filter((c) => c[metric] == null).length;
  const departments = [...new Set(all.map((c) => c.category_name))];

  if (courses.error) {
    return <Alert type="error" showIcon message="Không mở được khoa" description={errorText(courses.error)} />;
  }
  const facultyName = summary?.faculty_name ?? "Khoa";
  const m = METRICS[metric];
  // Nhấn lát cắt biểu đồ tròn của khoa -> tô nổi các môn có tỷ lệ mức đó cao hơn trung bình khoa (Mục 3.2–3.3)
  const rateKey = focusLevel ? `${focusLevel.toLowerCase()}_rate` : null;
  const facultyRate = focusLevel && summary?.enrolled
    ? (100 * summary[focusLevel.toLowerCase()]) / summary.enrolled : null;
  const highlight = facultyRate != null ? (c) => c[rateKey] != null && Number(c[rateKey]) > facultyRate : undefined;
  const highlightNote = facultyRate != null
    ? `Tỷ lệ ${RISK[focusLevel].label.toLowerCase()} cao hơn trung bình khoa (${fmtPercent(facultyRate)})` : undefined;

  return (
    <>
      <LevelBreadcrumb level="faculty" faculty={{ id: facultyId, name: facultyName }} search={search} />
      <div className="filter-bar">
        <TermFilterBar filters={filters} term={term} onTermChange={setTerm} facultyId={Number(facultyId)}
          onFacultyChange={(id) => navigate(id ? `/admin/faculties/${id}${search}` : `/admin${search}`)} />
        <Select allowClear placeholder="Bộ môn: tất cả" style={{ width: 260 }} value={dept} onChange={setDept}
          aria-label="Lọc bộ môn" options={departments.map((d) => ({ value: d, label: d }))} />
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={5}>
          <KpiCard label="Số môn" loading={!summary} value={fmtInt(summary?.course_count)}
            hint={`${departments.length} bộ môn`} />
        </Col>
        <Col xs={24} sm={12} xl={5}>
          <KpiCard label="Lượt ghi danh" loading={!summary} value={fmtInt(summary?.enrolled)}
            hint={`${fmtPercent(share(summary?.enrolled, summary?.school_enrolled), 0)} toàn trường`}
            detail={`${fmtInt(summary?.unique_students)} sinh viên khác nhau; toàn trường ${fmtInt(summary?.school_enrolled)} lượt ghi danh`}
            info="enrolled" />
        </Col>
        <Col xs={24} sm={12} xl={5}>
          <KpiCard label="Tỷ lệ tương tác" loading={!summary} value={fmtPercent(summary?.avg_active_rate)}
            hint={`toàn trường ${fmtPercent(summary?.school_active_rate)}`} info="active_rate" />
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <KpiCard label="Nộp bài" loading={!summary} value={fmtPercent(summary?.avg_submission_rate)}
            hint={`toàn trường ${fmtPercent(summary?.school_submission_rate)}`}
            detail={`Chuyên cần của khoa ${fmtPercent(summary?.avg_attendance_rate)}, toàn trường ${fmtPercent(summary?.school_attendance_rate)}`}
            info="submission_rate" />
        </Col>
        <Col xs={24} sm={12} xl={5}>
          <KpiCard label="SV nguy cơ cao" loading={!summary} accent={RISK.RED.color} value={fmtInt(summary?.red)}
            hint={<>{fmtPercent(summary?.red_rate)} · <Delta value={summary?.red_rate_delta_week} /></>}
            detail={`Toàn trường ${fmtPercent(summary?.school_red_rate)}. ${summary?.custom_rule_courses ? `${summary.custom_rule_courses} môn dùng luật cảnh báo riêng.` : ""}`}
            info="risk_level" />
        </Col>

        <Col span={24}>
          <RiskOverviewPanel title={facultyName} loading={!summary}
            summary={summary ? { red: summary.red, yellow: summary.yellow, green: summary.green, total: summary.enrolled } : null}
            trend={{ term, facultyId: Number(facultyId) }} focusLevel={focusLevel} onFocusLevel={setFocusLevel}
            ruleNote={summary ? `${summary.custom_rule_courses}/${summary.course_count} môn của khoa dùng luật cảnh báo riêng do giảng viên đặt; số Đỏ/Vàng/Xanh của các môn đó được chấm theo luật riêng.` : undefined}
            footnote={summary?.custom_rule_courses
              ? `${summary.custom_rule_courses}/${summary.course_count} môn của khoa đang dùng luật cảnh báo riêng do giảng viên đặt.` : undefined} />
        </Col>

        <Col span={24}>
          <Card title="So sánh các môn trong khoa" loading={courses.isLoading}
            extra={(
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <Input.Search allowClear placeholder="Tìm môn" style={{ width: 200 }} onSearch={(v) => setQuery(v.trim())} />
                <MetricInfo metric={{ keys: [m.info, "risk_level"], note: summary ? `${summary.custom_rule_courses}/${summary.course_count} môn của khoa dùng luật cảnh báo riêng.` : undefined }} />
              </div>
            )}>
            {highlightNote && (
              <div className="focus-note" style={{ marginBottom: 8 }}>
                Đang tô nổi các môn có tỷ lệ <b>{RISK[focusLevel].label.toLowerCase()}</b> cao hơn trung bình khoa
                ({fmtPercent(facultyRate)}). <a role="button" onClick={() => setFocusLevel(null)}>Bỏ chọn</a>
              </div>
            )}
            <Row gutter={[24, 16]}>
              <Col xs={24} xl={12}>
                <div className="chart-title" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                  <span>Chỉ số theo môn</span>
                  <Segmented size="small" value={metric} onChange={setMetric}
                    options={Object.entries(METRICS).map(([value, x]) => ({ value, label: x.label }))} />
                </div>
                <div style={{ height: chartHeight(byMetric.length, "horizontal") }}>
                  <ComparisonColumns items={byMetric} labelKey="label" valueKey={metric} label={m.label}
                    orientation="horizontal" onSelect={openCourse} highlight={highlight} highlightNote={highlightNote}
                    reference={summary?.[m.ref] != null ? { value: Number(summary[m.ref]), label: `TB khoa ${fmtPercent(summary[m.ref])}` } : undefined} />
                </div>
                {noData > 0 && <div className="muted" style={{ fontSize: 12 }}>{noData} môn chưa có dữ liệu {m.label.toLowerCase()} – không vẽ.</div>}
              </Col>
              <Col xs={24} xl={12}>
                <div className="chart-title">Phân bố mức rủi ro theo môn</div>
                <div style={{ height: chartHeight(byRisk.length, "horizontal") }}>
                  <RiskShareBars items={byRisk} labelKey="label" orientation="horizontal" onSelect={openCourse}
                    countKeys={{ RED: "red_count", YELLOW: "yellow_count", GREEN: "green_count" }}
                    highlight={highlight} highlightNote={highlightNote} />
                </div>
              </Col>
            </Row>
            {filtered.length > MANY_COURSES && (
              <a role="button" onClick={() => setShowAll((v) => !v)}>
                {showAll ? `Chỉ hiện ${TOP_N} môn thấp nhất` : `Xem tất cả ${filtered.length} môn`}
              </a>
            )}
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Bảng môn học của khoa">
            <CourseTable facultyId={Number(facultyId)} term={term} onPick={openCourse} department={dept} highlight={highlight} />
          </Card>
        </Col>
      </Row>
    </>
  );
}
