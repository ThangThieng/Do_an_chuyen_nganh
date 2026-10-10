/**
 * Bảng cảnh báo sinh viên – dùng chung cho trang Cảnh báo (giảng viên) và trang Môn học (quản trị, chỉ đọc).
 * Giữ nguyên lọc/sắp xếp/phân trang v1.1; v1.2 thêm cột điểm từng tiêu chí C1/C2/C3 và chú giải công thức ở tiêu đề
 * cột "Điểm" (góp ý 4), bỏ icon trang trí.
 */
import { Input, Select, Space, Table, Tag, Tooltip } from "antd";
import { CRITERIA, RISK, RISK_LEVELS } from "../theme/tokens.js";
import { fmtDaysSince, fmtInt, fmtPercent } from "../utils/format.js";
import { Rate, RiskBadge } from "./common.jsx";

const SORT_FIELDS = {
  risk_score: "risk_score", student_code: "student_code", student_name: "student_name", absence_rate: "absence_rate",
  days_since_last_access: "days_since_last_access", assignments: "missing_assignments",
};

function ScoreChips({ r }) {
  const items = [["C1", r.score_attendance, "Vắng học"], ["C2", r.score_inactivity, "Không tương tác"],
    ["C3", r.score_assignment, "Thiếu bài tập"]];
  return (
    <span className="score-chips">
      {items.map(([k, v, name]) => (
        <Tooltip key={k} title={`${name}: ${v}/2 điểm`}>
          <span className={`score-chip s${v}`}>{k} {v}</span>
        </Tooltip>
      ))}
    </span>
  );
}

export function formulaText(rule) {
  if (!rule) return "Điểm = 100 × (wC1·C1 + wC2·C2 + wC3·C3) ÷ 2; mỗi tiêu chí 0/1/2 điểm";
  const w = rule.weights;
  const p = (x) => String(Math.round(x * 100) / 100).replace(".", ",");
  return `Điểm = 100 × (${p(w.attendance)}·C1 + ${p(w.inactivity)}·C2 + ${p(w.assignment)}·C3) ÷ 2; mỗi tiêu chí 0/1/2 điểm`;
}

export default function RiskStudentTable({ state, setState, data, loading, onOpen, rule, toolbarExtra }) {
  const { levels, criterion, sort, page } = state;
  const resetPage = { page: { ...page, current: 1 } };
  const sortOrder = (key) => (sort.key === key ? (sort.order === "asc" ? "ascend" : "descend") : null);
  const columns = [
    { title: "Mức", dataIndex: "risk_level", render: (v) => <RiskBadge level={v} />, width: 120 },
    { title: "MSSV", key: "student_code", dataIndex: "student_code", sorter: true, sortOrder: sortOrder("student_code") },
    { title: "Họ tên", key: "student_name", dataIndex: "student_name", sorter: true, sortOrder: sortOrder("student_name") },
    {
      title: "Vắng", key: "absence_rate", sorter: true, sortOrder: sortOrder("absence_rate"), align: "right",
      render: (_, r) => (r.total_sessions ? <span className="tabular">{fmtPercent(r.absence_rate, 0)} <span className="muted">({r.absent_sessions}/{r.total_sessions})</span></span> : <Rate value={null} />),
    },
    {
      title: "Truy cập cuối", key: "days_since_last_access", dataIndex: "days_since_last_access", sorter: true,
      sortOrder: sortOrder("days_since_last_access"), render: fmtDaysSince,
    },
    {
      title: "Bài tập (đã nộp)", key: "assignments", sorter: true, sortOrder: sortOrder("assignments"), align: "right",
      render: (_, r) => (r.total_assignments ? <span className="tabular">{r.submitted_assignments}/{r.total_assignments}</span> : <span className="muted">chưa tới hạn</span>),
    },
    {
      title: <Tooltip title={formulaText(rule)}><span className="has-tip">Điểm</span></Tooltip>,
      key: "risk_score", dataIndex: "risk_score", sorter: true, sortOrder: sortOrder("risk_score"), align: "right",
    },
    { title: "Điểm tiêu chí", key: "scores", render: (_, r) => <ScoreChips r={r} /> },
    {
      title: "Lý do", dataIndex: "risk_reasons", width: 300,
      render: (reasons) => (reasons.length
        ? <Space size={[4, 4]} wrap>{reasons.map((x) => <Tag key={x} style={{ marginInlineEnd: 0 }}>{x}</Tag>)}</Space>
        : <span className="muted">–</span>),
    },
  ];
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder="Tìm MSSV / tên" style={{ width: 220 }}
          onSearch={(v) => setState({ search: v.trim(), ...resetPage })} />
        <Select mode="multiple" allowClear placeholder="Mức" style={{ minWidth: 150 }} value={levels} aria-label="Lọc mức rủi ro"
          onChange={(v) => setState({ levels: v, ...resetPage })} maxTagCount="responsive"
          options={RISK_LEVELS.map((l) => ({ value: l, label: RISK[l].label }))} />
        <Select allowClear placeholder="Tiêu chí" style={{ width: 160 }} value={criterion} aria-label="Lọc tiêu chí"
          onChange={(v) => setState({ criterion: v, ...resetPage })}
          options={Object.entries(CRITERIA).map(([value, label]) => ({ value, label }))} />
        {toolbarExtra}
      </Space>
      <Table
        rowKey="user_id" size="middle" columns={columns} dataSource={data?.items ?? []}
        loading={loading} scroll={{ x: "max-content" }} rowClassName={() => "clickable-row"}
        onRow={(r) => ({ onClick: () => onOpen(r.user_id), style: { cursor: "pointer" } })}
        pagination={{ ...page, total: data?.total ?? 0, showSizeChanger: true, pageSizeOptions: [20, 50, 100, 200], showTotal: (t) => `${fmtInt(t)} sinh viên` }}
        onChange={(pagination, _, sorter) => setState({
          page: { current: pagination.current, pageSize: pagination.pageSize },
          sort: sorter.order ? { key: sorter.columnKey, order: sorter.order === "ascend" ? "asc" : "desc" } : { key: null, order: "desc" },
        })}
      />
    </>
  );
}

export function studentParams(state) {
  return {
    risk_level: state.levels, criterion: state.criterion, search: state.search || undefined,
    sort: state.sort.key ? SORT_FIELDS[state.sort.key] : "risk", order: state.sort.order,
    page: state.page.current, page_size: state.page.pageSize,
  };
}

export const INITIAL_TABLE_STATE = { levels: [], criterion: undefined, search: "", sort: { key: null, order: "desc" },
  page: { current: 1, pageSize: 50 } };

