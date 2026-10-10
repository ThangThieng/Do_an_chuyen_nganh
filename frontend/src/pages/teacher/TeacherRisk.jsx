/**
 * GV – Cảnh báo (SPEC 5.3, v1.2): 3 thẻ đèn giao thông + biểu đồ tròn (giữ nguyên) · đồ thị xu hướng đi kèm (góp ý 2)
 * · bảng cảnh báo có điểm từng tiêu chí và chú giải công thức (góp ý 4) · cửa sổ chi tiết có phân tích điểm và gửi tin.
 */
import { Alert, App, Button, Card, Col, Dropdown, Row, Segmented } from "antd";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { downloadFile, errorMessage, errorText } from "../../api/client.js";
import { useRiskStudents, useRiskSummary, useRiskTrend } from "../../api/hooks.js";
import RiskDoughnut from "../../charts/RiskDoughnut.jsx";
import RiskTrendChart, { trendTableColumns } from "../../charts/RiskTrendChart.jsx";
import { ChartCard, Delta, KpiCard } from "../../components/common.jsx";
import MetricInfo from "../../components/MetricInfo.jsx";
import RiskStudentTable, { INITIAL_TABLE_STATE, studentParams } from "../../components/RiskStudentTable.jsx";
import StudentDetailModal from "../../components/StudentDetailModal.jsx";
import { RISK, RISK_LEVELS } from "../../theme/tokens.js";
import { fmtDate, fmtInt, fmtPercent, share } from "../../utils/format.js";
import useStudentParam from "../../utils/useStudentParam.js";

export default function TeacherRisk() {
  const { courseId } = useParams();
  const { message } = App.useApp();
  const [table, setTable] = useState(INITIAL_TABLE_STATE);
  const [granularity, setGranularity] = useState("week");
  const [openUser, setOpenUser, closeUser] = useStudentParam();
  const [exporting, setExporting] = useState(false);
  const update = (patch) => setTable((s) => ({ ...s, ...patch }));

  const summary = useRiskSummary(courseId);
  const students = useRiskStudents(courseId, studentParams(table));
  const trend = useRiskTrend({ teacherCourseId: courseId, granularity });
  const sum = summary.data;
  const rule = sum?.rule;
  const toggleLevel = (level) => update({
    levels: table.levels.includes(level) ? table.levels.filter((l) => l !== level) : [...table.levels, level],
    page: { ...table.page, current: 1 },
  });

  async function onExport({ key }) {
    setExporting(true);
    try {
      const riskLevel = table.levels.length === 1 ? table.levels[0] : undefined;
      const name = await downloadFile(`/teacher/courses/${courseId}/export`, { format: key, risk_level: riskLevel }, `canh_bao.${key}`);
      message.success(`Đã tải ${name}`);
    } catch (err) {
      message.error(await errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  if (summary.error) {
    return <Alert type="error" showIcon message="Không mở được môn học" description={errorText(summary.error)} />;
  }
  const info = { keys: ["risk_level", "risk_score"], courseId };

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Row gutter={[12, 12]}>
            {RISK_LEVELS.map((level) => {
              const key = level.toLowerCase();
              const count = sum?.[key];
              const prev = sum?.prev_week?.[key];
              const selected = table.levels.includes(level);
              return (
                <Col xs={24} sm={8} key={level}>
                  <div role="button" tabIndex={0} aria-pressed={selected} className={`risk-card${selected ? " selected" : ""}`}
                    title={selected ? "Đang lọc bảng – nhấn để bỏ lọc" : "Nhấn để lọc bảng theo mức này"}
                    style={{ height: "100%", borderRadius: 8, borderTopColor: RISK[level].color }}
                    onClick={() => toggleLevel(level)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && toggleLevel(level)}>
                    <KpiCard
                      label={RISK[level].label} loading={!sum} accent={RISK[level].color}
                      value={<>{fmtInt(count)} SV <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({fmtPercent(share(count, sum?.total), 0)})</span></>}
                      hint={prev != null ? <Delta value={count - prev} unit="sv" betterWhen={level === "GREEN" ? "up" : "down"} /> : undefined}
                    />
                  </div>
                </Col>
              );
            })}
            <Col span={24}>
              <ChartCard title="Diễn biến mức rủi ro theo tuần" info={{ keys: ["risk_trend", "risk_level"], courseId }}
                extra={<Segmented size="small" value={granularity} onChange={setGranularity}
                  options={[{ label: "Theo tuần", value: "week" }, { label: "Theo ngày", value: "day" }]} />}
                loading={trend.isLoading} error={trend.error} fetching={trend.isFetching} height={240}
                table={{ rowKey: "period", dataSource: trend.data?.series ?? [], columns: trendTableColumns }}>
                {trend.data && <RiskTrendChart series={trend.data.series} ruleChanges={trend.data.rule_changes}
                  granularity={granularity} />}
              </ChartCard>
            </Col>
          </Row>
        </Col>
        <Col xs={24} xl={10}>
          <Card title="Tỷ lệ rủi ro" size="small" style={{ height: "100%" }} loading={!sum} extra={<MetricInfo metric={info} />}>
            {sum && (
              <>
                <RiskDoughnut summary={sum} selectedLevels={table.levels} onToggleLevel={toggleLevel}
                  criterion={table.criterion} onCriterion={(c) => update({ criterion: c, page: { ...table.page, current: 1 } })}
                  rule={rule} />
                <div className="muted" style={{ fontSize: 12, marginTop: 12, borderTop: "1px solid #f0f0f0", paddingTop: 8 }}>
                  Snapshot {fmtDate(sum.snapshot_date)} · {fmtInt(sum.total)} sinh viên · luật cảnh báo:{" "}
                  {rule?.scope === "COURSE" ? `riêng của môn (${rule.label})` : "mặc định của trường"}
                  {sum.attendance_no_data === sum.total && sum.total > 0 && " · môn chưa có buổi điểm danh (tiêu chí vắng học chưa áp dụng)"}
                </div>
              </>
            )}
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Bảng cảnh báo sinh viên">
            <RiskStudentTable state={table} setState={update} data={students.data} loading={students.isFetching}
              onOpen={setOpenUser} rule={rule}
              toolbarExtra={(
                <Dropdown menu={{ items: [{ key: "xlsx", label: "Excel (.xlsx)" }, { key: "pdf", label: "PDF" }], onClick: onExport }}>
                  <Button loading={exporting}>Xuất danh sách</Button>
                </Dropdown>
              )} />
          </Card>
        </Col>
      </Row>
      {openUser && <StudentDetailModal courseId={courseId} userId={openUser} onClose={closeUser} />}
    </>
  );
}
