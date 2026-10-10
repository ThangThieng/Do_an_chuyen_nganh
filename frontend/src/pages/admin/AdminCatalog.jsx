/**
 * Danh mục môn học: khoa, bộ môn, mã/tên môn, giảng viên phụ trách (chính / trợ giảng), sĩ số, luật cảnh báo đang áp dụng.
 * Chỉ tra cứu – danh mục được quản lý trong Moodle và nạp sang qua ETL.
 */
import { Alert, Card, Input, Table, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { errorText } from "../../api/client.js";
import { useCatalog, useFilters } from "../../api/hooks.js";
import TermFilterBar from "../../components/TermFilterBar.jsx";
import { fmtDate, fmtInt } from "../../utils/format.js";

export default function AdminCatalog() {
  const { data: filters } = useFilters();
  const [term, setTerm] = useState(null);
  const [facultyId, setFacultyId] = useState();
  const [search, setSearch] = useState("");
  useEffect(() => {
    if (filters && !term) setTerm(filters.current);
  }, [filters, term]);
  const catalog = useCatalog(term, facultyId);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (catalog.data?.items ?? []).filter((c) => !q || [c.shortname, c.fullname, ...c.teachers.map((t) => t.full_name)]
      .some((v) => v?.toLowerCase().includes(q)));
  }, [catalog.data, search]);

  const columns = [
    { title: "Khoa", dataIndex: "faculty_name" },
    { title: "Bộ môn", dataIndex: "category_name" },
    { title: "Mã môn", dataIndex: "shortname", sorter: (a, b) => a.shortname.localeCompare(b.shortname) },
    { title: "Tên môn học", dataIndex: "fullname" },
    {
      title: "Giảng viên phụ trách", dataIndex: "teachers",
      render: (list) => (list.length ? list.map((t) => (
        <Tag key={t.user_id} title={t.is_editing ? "Giảng viên chính (được đổi luật cảnh báo của môn)" : "Trợ giảng"}>
          {t.full_name ?? `#${t.user_id}`}{t.is_editing ? "" : " (trợ giảng)"}
        </Tag>
      )) : <span className="no-data">Chưa phân công</span>),
    },
    {
      title: "Luật cảnh báo", dataIndex: "rule_scope",
      filters: [{ text: "Mặc định của trường", value: "GLOBAL" }, { text: "Riêng của môn", value: "COURSE" }],
      onFilter: (value, r) => r.rule_scope === value,
      render: (v, r) => (v === "COURSE"
        ? <Tag color="orange" title={r.rule_updated_at ? `Cập nhật ${fmtDate(r.rule_updated_at)}` : undefined}>Riêng ({r.rule_label})</Tag>
        : <span className="muted">Mặc định ({r.rule_label})</span>),
    },
    { title: "Sĩ số", dataIndex: "enrolled", align: "right", render: fmtInt, sorter: (a, b) => a.enrolled - b.enrolled },
    { title: "Số liệu ngày", dataIndex: "stat_date", render: fmtDate },
  ];

  return (
    <>
      <div className="filter-bar">
        <b>Danh mục môn học</b>
        <TermFilterBar filters={filters} term={term} onTermChange={setTerm} facultyId={facultyId} onFacultyChange={setFacultyId} />
        <Input.Search allowClear placeholder="Tìm mã môn, tên môn, giảng viên" style={{ width: 300 }}
          value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm môn học" />
      </div>
      <Card title="Môn học và giảng viên phụ trách"
        extra={catalog.data && <span className="muted">{fmtInt(rows.length)} môn</span>}>
        {catalog.error && <Alert type="error" showIcon message={errorText(catalog.error)} style={{ marginBottom: 12 }} />}
        <Table rowKey="course_id" size="small" loading={catalog.isLoading} columns={columns} dataSource={rows}
          scroll={{ x: "max-content" }} pagination={{ pageSize: 20, hideOnSinglePage: true }} />
        <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          Danh mục khoa, môn học và phân công giảng dạy được quản lý trong Moodle; màn hình này chỉ tra cứu dữ liệu đã được ETL nạp sang.
        </div>
      </Card>
    </>
  );
}
