/**
 * Góp ý 4 – Phân tích điểm rủi ro của một sinh viên: số liệu thực tế → so với ngưỡng của luật đang áp dụng → điểm 0/1/2
 * → trọng số → đóng góp; dòng tổng; giải thích luật nào làm sinh viên bị xếp mức đó; bảng Moodle nguồn.
 * Ngưỡng/trọng số lấy từ API (/meta/risk-rule) – cùng luật mà ETL đã dùng để chấm.
 */
import { Table, Tag } from "antd";
import { fmtDecimal } from "../utils/format.js";
import { RiskBadge } from "./common.jsx";

const pct = (v) => `${Math.round(Number(v) * 1000) / 10}%`;

function band(score, low, high) {
  if (score === 2) return `từ ${high} → mức 2`;
  if (score === 1) return `từ ${low}, dưới ${high} → mức 1`;
  return `dưới ${low} → mức 0`;
}

export default function ScoreBreakdown({ s, rule }) {
  if (!rule) return null;
  const t = rule.thresholds;
  const w = rule.weights;
  const absence = s.total_sessions ? s.absent_sessions / s.total_sessions : null;
  const missing = s.total_assignments ? s.missing_assignments_count / s.total_assignments : null;
  const rows = [
    {
      key: "c1", name: "C1 – Vắng học", score: s.score_attendance, weight: w.attendance,
      actual: absence == null ? "chưa có buổi điểm danh" : `vắng ${s.absent_sessions}/${s.total_sessions} buổi = ${pct(absence)}`,
      band: absence == null ? "chưa áp dụng → 0" : band(s.score_attendance, pct(t.absence_yellow), pct(t.absence_red)),
      source: "mdl_attendance_sessions, mdl_attendance_log, mdl_attendance_statuses",
    },
    {
      key: "c2", name: "C2 – Không tương tác", score: s.score_inactivity, weight: w.inactivity,
      actual: s.days_since_last_access == null ? "chưa từng truy cập môn"
        : `${s.days_since_last_access} ngày chưa vào; ${s.access_count_14d} lượt truy cập 14 ngày`,
      band: s.score_inactivity === 2 ? `chưa từng vào hoặc quá ${t.inactive_red_days} ngày → mức 2`
        : s.score_inactivity === 1 ? `quá ${t.inactive_yellow_days} ngày, hoặc dưới ${pct(t.low_access_ratio)} trung vị lớp → mức 1`
          : `vào trong ${t.inactive_yellow_days} ngày và đủ lượt truy cập → mức 0`,
      source: "mdl_logstore_standard_log",
    },
    {
      key: "c3", name: "C3 – Thiếu bài tập", score: s.score_assignment, weight: w.assignment,
      actual: missing == null ? "chưa có bài tới hạn" : `thiếu ${s.missing_assignments_count}/${s.total_assignments} bài = ${pct(missing)}`,
      band: missing == null ? "chưa áp dụng → 0" : band(s.score_assignment, pct(t.missing_yellow), pct(t.missing_red)),
      source: "mdl_assign, mdl_assign_submission",
    },
  ].map((r) => ({ ...r, contribution: (100 * r.weight * r.score) / 2 }));
  const total = rows.reduce((a, r) => a + r.score, 0);
  const contribution = rows.reduce((a, r) => a + r.contribution, 0);

  const lr = rule.level_rules;
  const why = [];
  if (s.risk_level === "RED") {
    if (lr.red_if_inactivity_red && s.score_inactivity === 2) why.push("C2 = 2 (luật 1)");
    const twos = rows.filter((r) => r.score === 2).length;
    if (twos >= lr.red_min_red_criteria) why.push(`${twos} tiêu chí đạt 2 điểm (luật 2)`);
    if (total >= lr.red_min_total) why.push(`tổng ${total} ≥ ${lr.red_min_total} (luật 3)`);
  } else if (s.risk_level === "YELLOW" && total >= 1) why.push(`tổng ${total} ≥ 1`);
  (s.risk_reasons ?? []).filter((x) => x.endsWith("(luật của môn)")).forEach((x) => why.push(x));

  return (
    <div className="score-breakdown">
      <Table size="small" pagination={false} rowKey="key" dataSource={rows}
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={3}><b>Tổng</b> = 100 × (
              {rows.map((r, i) => `${i ? " + " : ""}${fmtDecimal(r.weight, 2)}·${r.score}`).join("")}) ÷ 2</Table.Summary.Cell>
            <Table.Summary.Cell index={3} align="center"><b>{total}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={4} />
            <Table.Summary.Cell index={5} align="right"><b>{Math.round(contribution)}</b></Table.Summary.Cell>
          </Table.Summary.Row>
        )}
        columns={[
          { title: "Tiêu chí", dataIndex: "name", width: 150 },
          { title: "Số liệu của sinh viên", dataIndex: "actual" },
          { title: "So với ngưỡng", dataIndex: "band" },
          { title: "Điểm", dataIndex: "score", align: "center", render: (v) => <b>{v}/2</b> },
          { title: "Trọng số", dataIndex: "weight", align: "right", render: (v) => pct(v) },
          { title: "Đóng góp", dataIndex: "contribution", align: "right", render: (v) => fmtDecimal(v, 1) },
        ]} />
      <div style={{ marginTop: 8 }}>
        Xếp <RiskBadge level={s.risk_level} /> {why.length ? <>vì: {why.join(" · ")}</> : "vì tổng điểm bằng 0"}.
        {Math.round(contribution) !== s.risk_score && (
          <Tag color="warning" style={{ marginLeft: 8 }}>Điểm đã lưu {s.risk_score} – chấm theo luật khác thời điểm này</Tag>
        )}
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
        Nguồn Moodle: {rows.map((r) => r.source).join(" · ")}. Luật: {rule.scope === "COURSE" ? `riêng của môn (${rule.label})` : `mặc định của trường (${rule.label})`}.
      </div>
    </div>
  );
}
