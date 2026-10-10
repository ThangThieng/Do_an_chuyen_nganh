/** Hệ thống › Nhật ký ETL: lần chạy gần nhất của từng job + bảng các lần chạy (lọc theo job, trạng thái). */
import { Alert, Card, Col, Row, Select, Table, Tag, Tooltip } from "antd";
import { useState } from "react";
import { errorText } from "../../api/client.js";
import { useEtlRuns, useEtlStatus } from "../../api/hooks.js";
import { fmtDateTime, fmtDecimal, fmtInt } from "../../utils/format.js";

const JOBS = {
  traffic: { label: "Lưu lượng", schedule: "5 phút/lần" },
  course_progress: { label: "Tiến độ môn", schedule: "phút 05 mỗi giờ" },
  student_risk: { label: "Cảnh báo rủi ro", schedule: "7h15–21h15, 2 giờ/lần" },
  nightly: { label: "Chốt số liệu đêm", schedule: "01:00 hằng ngày" },
  maintenance: { label: "Bảo trì", schedule: "03:00 Chủ nhật" },
  backfill: { label: "Nạp lịch sử", schedule: "chạy tay" },
};
const STATUS_TAG = {
  SUCCESS: <Tag color="green">Thành công</Tag>,
  FAILED: <Tag color="red">Lỗi</Tag>,
  RUNNING: <Tag color="blue">Đang chạy</Tag>,
};
const jobLabel = (name) => JOBS[name]?.label ?? name;

export default function AdminEtlLog() {
  const [jobName, setJobName] = useState();
  const [status, setStatus] = useState();
  const { data: latest } = useEtlStatus();
  const runs = useEtlRuns({ job_name: jobName, status, limit: 500 });

  const columns = [
    { title: "Mã lần chạy", dataIndex: "run_id", align: "right" },
    { title: "Job", dataIndex: "job_name", render: jobLabel },
    { title: "Bắt đầu", dataIndex: "started_at", render: fmtDateTime },
    { title: "Kết thúc", dataIndex: "finished_at", render: (v) => (v ? fmtDateTime(v) : "–") },
    { title: "Thời gian (giây)", dataIndex: "duration_seconds", align: "right", render: (v) => (v == null ? "–" : fmtDecimal(v, 2)) },
    { title: "Trạng thái", dataIndex: "status", render: (v) => STATUS_TAG[v] },
    { title: "Dòng đọc", dataIndex: "rows_extracted", align: "right", render: (v) => (v == null ? "–" : fmtInt(v)) },
    { title: "Dòng ghi", dataIndex: "rows_loaded", align: "right", render: (v) => (v == null ? "–" : fmtInt(v)) },
    {
      title: "Lỗi", dataIndex: "error_message", width: 280, ellipsis: { showTitle: false },
      render: (v) => (v ? <Tooltip title={v}><span style={{ color: "var(--red)" }}>{v}</span></Tooltip> : ""),
    },
  ];

  return (
    <>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {(latest ?? []).map((j) => (
          <Col key={j.job_name} xs={12} md={8} xl={4}>
            <Card size="small">
              <div className="kpi-label">{jobLabel(j.job_name)} <span className="muted">· {JOBS[j.job_name]?.schedule}</span></div>
              <div style={{ margin: "6px 0 2px" }}>{j.status ? STATUS_TAG[j.status] : <Tag>Chưa chạy</Tag>}</div>
              <div className="kpi-hint">Thành công gần nhất: {j.last_success_at ? fmtDateTime(j.last_success_at) : "–"}</div>
            </Card>
          </Col>
        ))}
      </Row>
      <div className="filter-bar">
        <b>Nhật ký ETL</b>
        <Select aria-label="Job" allowClear placeholder="Mọi job" style={{ width: 220 }} value={jobName} onChange={setJobName}
          options={(runs.data?.job_names ?? []).map((j) => ({ value: j, label: jobLabel(j) }))} />
        <Select aria-label="Trạng thái" allowClear placeholder="Mọi trạng thái" style={{ width: 180 }} value={status} onChange={setStatus}
          options={[{ value: "SUCCESS", label: "Thành công" }, { value: "FAILED", label: "Lỗi" }, { value: "RUNNING", label: "Đang chạy" }]} />
      </div>
      <Card title="Các lần chạy" extra={runs.data && <span className="muted">{fmtInt(runs.data.items.length)} / {fmtInt(runs.data.total)} lần chạy (mới nhất trước)</span>}>
        {runs.error && <Alert type="error" showIcon message={errorText(runs.error)} style={{ marginBottom: 12 }} />}
        <Table rowKey="run_id" size="small" loading={runs.isLoading} columns={columns} dataSource={runs.data?.items ?? []}
          scroll={{ x: "max-content" }} pagination={{ pageSize: 20, showSizeChanger: false }} />
      </Card>
    </>
  );
}
