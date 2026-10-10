/**
 * Bảng môn học của một khoa và bảng sinh viên của một môn (tách từ bảng phân cấp v1.1 – giữ nguyên các cột).
 * v1.2: bảng môn thêm cột "% Nguy cơ cao" và "Luật cảnh báo"; drill-down sang trang riêng có URL thay vì mở rộng tại chỗ.
 */
import { Button, Input, Progress, Segmented, Table, Tag } from "antd";
import { useState } from "react";
import { useCourseStudents, useFacultyCourses } from "../api/hooks.js";
import { RISK, SERIES } from "../theme/tokens.js";
import { fmtDaysSince, fmtInt, fmtPercent } from "../utils/format.js";
import { Rate, RiskBadge } from "./common.jsx";

const rateBar = (value) => (
  <div style={{ minWidth: 150 }}>
    <Progress percent={Number(value)} size="small" strokeColor={SERIES.blue} format={(p) => fmtPercent(p)}
      aria-label={`Tỷ lệ tương tác ${fmtPercent(value)}`} />
  </div>
);
const COURSE_SORT = { shortname: "shortname", fullname: "fullname", enrolled: "enrolled", active: "active",
  active_rate: "active_rate", red_count: "red_count", red_rate: "red_rate" };

/**
 * department: lọc theo bộ môn (cùng ô lọc với biểu đồ ở đầu trang Khoa); highlight(row) -> tô nổi dòng (mức rủi ro đang
 * chọn trên biểu đồ tròn của khoa).
 */
export function CourseTable({ facultyId, term, onPick, department, highlight }) {
  const [sort, setSort] = useState({ field: "active_rate", order: "desc" });
  const { data, isLoading, isFetching } = useFacultyCourses(facultyId, term, sort.field, sort.order);
  const rows = (data?.items ?? []).filter((c) => !department || c.category_name === department);
  const sortOrder = (key) => (sort.field === key ? (sort.order === "asc" ? "ascend" : "descend") : null);
  return (
    <Table
      rowKey="course_id" size="middle" loading={isLoading || isFetching} pagination={false}
      dataSource={rows} scroll={{ x: "max-content" }}
      onRow={(row) => ({ onClick: () => onPick(row), style: { cursor: "pointer" } })}
      rowClassName={(row) => (highlight?.(row) ? "row-focus" : "")}
      onChange={(_, __, sorter) => setSort(sorter.order
        ? { field: COURSE_SORT[sorter.columnKey], order: sorter.order === "ascend" ? "asc" : "desc" }
        : { field: "active_rate", order: "desc" })}
      columns={[
        { title: "Mã môn", key: "shortname", dataIndex: "shortname", sorter: true, sortOrder: sortOrder("shortname") },
        { title: "Tên môn", key: "fullname", dataIndex: "fullname", sorter: true, sortOrder: sortOrder("fullname") },
        { title: "Bộ môn", dataIndex: "category_name", responsive: ["lg"] },
        { title: "Đăng ký", key: "enrolled", dataIndex: "enrolled", align: "right", render: fmtInt, sorter: true, sortOrder: sortOrder("enrolled") },
        { title: "Tương tác", key: "active", dataIndex: "active", align: "right", render: fmtInt, sorter: true, sortOrder: sortOrder("active") },
        { title: "Tỷ lệ tương tác", key: "active_rate", dataIndex: "active_rate", render: rateBar, sorter: true, sortOrder: sortOrder("active_rate") },
        { title: "Nộp bài", dataIndex: "assignment_submission_rate", align: "right", render: (v) => <Rate value={v} /> },
        { title: "Chuyên cần", dataIndex: "attendance_rate", align: "right", render: (v) => <Rate value={v} /> },
        { title: "Nguy cơ đỏ", key: "red_count", dataIndex: "red_count", align: "right", render: fmtInt, sorter: true, sortOrder: sortOrder("red_count") },
        { title: "% Nguy cơ cao", key: "red_rate", dataIndex: "red_rate", align: "right", sorter: true, sortOrder: sortOrder("red_rate"),
          render: (v) => <span className="tabular" style={{ color: RISK.RED.ink }}>{fmtPercent(v, 1, "–")}</span> },
        { title: "Luật cảnh báo", dataIndex: "rule_scope",
          render: (v, r) => (v === "COURSE" ? <Tag color="orange">Riêng ({r.rule_label})</Tag> : <span className="muted">Mặc định</span>) },
        { title: "", key: "open", width: 90,
          render: (_, r) => <Button size="small" onClick={(e) => { e.stopPropagation(); onPick(r); }}>Xem SV</Button> },
      ]}
    />
  );
}

export function CourseStudentsTable({ courseId, onPick }) {
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState({ current: 1, pageSize: 20 });
  const params = { status: status === "all" ? undefined : status, search: search || undefined, page: page.current, page_size: page.pageSize };
  const { data, isLoading, isFetching } = useCourseStudents(courseId, params);
  return (
    <>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12, alignItems: "center" }}>
        <Segmented value={status} onChange={(v) => { setStatus(v); setPage((p) => ({ ...p, current: 1 })); }}
          options={[{ label: "Tất cả", value: "all" }, { label: "Có tương tác", value: "active" }, { label: "Không tương tác", value: "inactive" }]} />
        <Input.Search allowClear placeholder="Tìm MSSV, họ tên, email" style={{ width: 280 }}
          onSearch={(v) => { setSearch(v.trim()); setPage((p) => ({ ...p, current: 1 })); }} />
      </div>
      <Table
        rowKey="user_id" size="small" loading={isLoading || isFetching} dataSource={data?.items ?? []} scroll={{ x: "max-content" }}
        onRow={(r) => ({ onClick: () => onPick?.(r.user_id), style: { cursor: onPick ? "pointer" : "default" } })}
        pagination={{ ...page, total: data?.total ?? 0, showSizeChanger: true, pageSizeOptions: [20, 50, 100, 200], showTotal: (t) => `${fmtInt(t)} sinh viên` }}
        onChange={(pagination) => setPage({ current: pagination.current, pageSize: pagination.pageSize })}
        columns={[
          { title: "MSSV", dataIndex: "student_code" },
          { title: "Họ tên", dataIndex: "student_name" },
          { title: "Email", dataIndex: "email", responsive: ["md"] },
          { title: "Tương tác", dataIndex: "is_active", render: (v) => (v ? <Tag color="blue">Có</Tag> : <Tag>Chưa</Tag>) },
          { title: "Lượt truy cập", dataIndex: "total_access_count", align: "right", render: fmtInt },
          { title: "7 ngày", dataIndex: "access_count_7d", align: "right", render: fmtInt },
          { title: "Truy cập cuối", dataIndex: "days_since_last_access", render: fmtDaysSince },
          { title: "Mức rủi ro", dataIndex: "risk_level", render: (v) => <RiskBadge level={v} /> },
          { title: "Điểm", dataIndex: "risk_score", align: "right" },
        ]}
      />
    </>
  );
}
