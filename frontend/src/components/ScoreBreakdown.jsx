/**
 * Góp ý 4 – Phân tích điểm rủi ro của một sinh viên: số liệu thực tế → so với ngưỡng của luật đang áp dụng → điểm 0/1/2
 * → trọng số → đóng góp; dòng tổng; giải thích luật nào làm sinh viên bị xếp mức đó; bảng Moodle nguồn.
 * Ngưỡng/trọng số lấy từ API (/meta/risk-rule) – cùng luật mà ETL đã dùng để chấm.
 */
import { Table, Tag } from "antd";
import { fmtDecimal, isGradebookAttendance } from "../utils/format.js";
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
      actual: absence == null ? "chưa có buổi điểm danh"
        : isGradebookAttendance(s) ? `vắng ${pct(absence)} (chuyên cần ${s.attended_sessions}% theo sổ điểm)`
          : `vắng ${s.absent_sessions}/${s.total_sessions} buổi = ${pct(absence)}`,
      applies: absence != null,
      band: absence == null ? "không áp dụng (không tính vào điểm)" : band(s.score_attendance, pct(t.absence_yellow), pct(t.absence_red)),
      source: isGradebookAttendance(s) ? "mdl_grade_items, mdl_grade_grades (mục điểm danh trong sổ điểm)"
        : "mdl_attendance_sessions, mdl_attendance_log, mdl_attendance_statuses",
    },
    {
      key: "c2", name: "C2 – Không tương tác", score: s.score_inactivity, weight: w.inactivity, applies: true,
      actual: s.days_since_last_access == null ? "không có hoạt động nào được ghi nhận (log, bài nộp, bài kiểm tra)"
        : `${s.days_since_last_access} ngày chưa vào; ${s.access_count_14d} lượt truy cập 14 ngày`,
      band: s.score_inactivity === 2 ? `không có hoạt động nào hoặc quá ${t.inactive_red_days} ngày → mức 2`
        : s.score_inactivity === 1 ? `quá ${t.inactive_yellow_days} ngày, hoặc dưới ${pct(t.low_access_ratio)} trung vị lớp → mức 1`
          : `vào trong ${t.inactive_yellow_days} ngày và đủ lượt truy cập → mức 0`,
      source: "mdl_logstore_standard_log",
    },
    {
      key: "c3", name: "C3 – Thiếu bài tập, kiểm tra", score: s.score_assignment, weight: w.assignment,
      actual: missing == null ? "chưa có bài tới hạn" : `thiếu ${s.missing_assignments_count}/${s.total_assignments} bài = ${pct(missing)}`,
      applies: missing != null,
      band: missing == null ? "không áp dụng (không tính vào điểm)" : band(s.score_assignment, pct(t.missing_yellow), pct(t.missing_red)),
      source: "mdl_assign, mdl_assign_submission, mdl_quiz, mdl_quiz_attempts",
    },
  ];
  // Tiêu chí không có dữ liệu không tính vào điểm; trọng số chia lại cho các tiêu chí còn lại (cùng cách ETL chấm).
  const weightSum = rows.filter((r) => r.applies).reduce((a, r) => a + r.weight, 0);
  rows.forEach((r) => {
    r.used = r.applies ? r.weight / weightSum : 0;
    r.contribution = (100 * r.used * r.score) / 2;
  });
  const reweighted = rows.some((r) => !r.applies);
  const total = rows.reduce((a, r) => a + r.score, 0);
  const contribution = rows.reduce((a, r) => a + r.contribution, 0);

  const lr = rule.level_rules;
  const why = [];
  if (s.risk_level === "RED") {
    if (lr.red_if_inactivity_red && s.score_inactivity === 2) why.push("C2 = 2 (luật 1)");
    const twos = rows.filter((r) => r.score === 2).length;
    if (twos >= lr.red_min_red_criteria) why.push(`${twos} tiêu chí đạt 2 điểm (luật 2)`);
    // Ngưỡng tổng co theo số tiêu chí có dữ liệu (cùng cách ETL chấm): 3 tiêu chí -> 4, 2 tiêu chí -> 3
    const applicable = rows.filter((r) => r.applies).length;
    const redTotal = Math.ceil((lr.red_min_total * applicable) / 3);
    if (total >= redTotal) why.push(`tổng ${total} ≥ ${redTotal}${applicable < 3 ? ` (ngưỡng cho ${applicable} tiêu chí có dữ liệu)` : ""} (luật 3)`);
  } else if (s.risk_level === "YELLOW" && total >= 1) why.push(`tổng ${total} ≥ 1`);
  (s.risk_reasons ?? []).filter((x) => x.endsWith("(luật của môn)")).forEach((x) => why.push(x));

  return (
    <div className="score-breakdown">
      <Table size="small" pagination={false} rowKey="key" dataSource={rows}
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={3}><b>Tổng</b> = 100 × (
              {rows.filter((r) => r.applies).map((r, i) => `${i ? " + " : ""}${fmtDecimal(r.used, 2)}·${r.score}`).join("")}) ÷ 2</Table.Summary.Cell>
            <Table.Summary.Cell index={3} align="center"><b>{total}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={4} />
            <Table.Summary.Cell index={5} align="right"><b>{Math.round(contribution)}</b></Table.Summary.Cell>
          </Table.Summary.Row>
        )}
        columns={[
          { title: "Tiêu chí", dataIndex: "name", width: 150 },
          { title: "Số liệu của sinh viên", dataIndex: "actual" },
          { title: "So với ngưỡng", dataIndex: "band" },
          { title: "Điểm", dataIndex: "score", align: "center", render: (v, r) => (r.applies ? <b>{v}/2</b> : "–") },
          { title: "Trọng số", dataIndex: "used", align: "right",
            render: (v, r) => (!r.applies ? "–" : reweighted ? <span title={`Trọng số gốc ${pct(r.weight)}`}>{pct(v)}</span> : pct(v)) },
          { title: "Đóng góp", dataIndex: "contribution", align: "right", render: (v) => fmtDecimal(v, 1) },
        ]} />
      <div style={{ marginTop: 8 }}>
        Xếp <RiskBadge level={s.risk_level} /> {why.length ? <>vì: {why.join(" · ")}</> : "vì tổng điểm bằng 0"}.
        {Math.round(contribution) !== s.risk_score && (
          <Tag color="warning" style={{ marginLeft: 8 }}>Điểm đã lưu {s.risk_score} – chấm theo luật khác thời điểm này</Tag>
        )}
      </div>
      {reweighted && (
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          Tiêu chí không có dữ liệu không tính vào điểm; trọng số của các tiêu chí còn lại được chia lại cho đủ 100%,
          và ngưỡng “tổng điểm” của mức Nguy cơ cao hạ tương ứng (2 tiêu chí: tổng từ 3).
        </div>
      )}
      <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
        Nguồn Moodle: {rows.map((r) => r.source).join(" · ")}. Luật: {rule.scope === "COURSE" ? `riêng của môn (${rule.label})` : `mặc định của trường (${rule.label})`}.
      </div>
    </div>
  );
}
