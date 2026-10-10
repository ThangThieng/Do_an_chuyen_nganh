/**
 * Hệ thống › Sao lưu & phục hồi dữ liệu CSDL phân tích.
 * Phục hồi thay TOÀN BỘ dữ liệu hiện tại -> bắt buộc gõ lại tên file để xác nhận.
 */
import { Alert, App, Button, Card, Descriptions, Input, Modal, Popconfirm, Space, Table, Typography } from "antd";
import { useState } from "react";
import { downloadFile, errorMessage, errorText } from "../../api/client.js";
import { useBackups, useCreateBackup, useDeleteBackup, useRestoreBackup } from "../../api/hooks.js";
import { fmtDateTime, fmtDecimal, fmtInt } from "../../utils/format.js";

const TABLE_LABEL = {
  app_user: "Tài khoản",
  etl_run_log: "Nhật ký ETL",
  etl_watermark: "Mốc trích xuất",
  etl_online_snapshot: "Mẫu người online",
  fact_server_traffic_hourly: "Lưu lượng theo giờ",
  fact_course_progress_daily: "Tiến độ môn theo ngày",
  fact_student_risk_summary: "Cảnh báo sinh viên",
  intervention_log: "Nhật ký can thiệp",
};
const mb = (bytes) => `${fmtDecimal(bytes / 1_048_576, 1)} MB`;

export default function AdminBackups() {
  const { message, modal } = App.useApp();
  const backups = useBackups();
  const create = useCreateBackup();
  const remove = useDeleteBackup();
  const restore = useRestoreBackup();
  const [target, setTarget] = useState(null);
  const [confirmName, setConfirmName] = useState("");

  async function onCreate() {
    try {
      const info = await create.mutateAsync();
      message.success(`Đã tạo ${info.name} (${fmtInt(info.total_rows)} dòng, ${mb(info.size_bytes)})`);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  async function onRestore() {
    const name = target.name;
    try {
      const result = await restore.mutateAsync(name);
      setTarget(null);
      modal.success({ title: "Phục hồi hoàn tất", content: `Đã nạp lại ${fmtInt(result.total_rows)} dòng từ ${name}.` });
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  async function onDownload(name) {
    try {
      await downloadFile(`/admin/backups/${encodeURIComponent(name)}/download`, {}, name);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  async function onDelete(name) {
    try {
      await remove.mutateAsync(name);
      message.success(`Đã xóa ${name}`);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  const columns = [
    { title: "Tên file", dataIndex: "name", render: (v) => <code>{v}</code> },
    { title: "Thời điểm tạo", dataIndex: "created_at", render: fmtDateTime },
    { title: "Người tạo", dataIndex: "created_by", render: (v) => v ?? "–" },
    { title: "Dung lượng", dataIndex: "size_bytes", align: "right", render: mb },
    { title: "Số dòng", dataIndex: "total_rows", align: "right", render: fmtInt },
    { title: "Phiên bản CSDL", dataIndex: "migration_version", render: (v) => (v ? `V${String(v).padStart(3, "0")}` : "–") },
    {
      title: "Thao tác", key: "actions",
      render: (_, b) => (
        <Space>
          <Button size="small" onClick={() => onDownload(b.name)}>Tải về</Button>
          <Button size="small" type="primary" ghost onClick={() => { setTarget(b); setConfirmName(""); }}>Phục hồi</Button>
          <Popconfirm title={`Xóa bản sao lưu ${b.name}?`} okText="Xóa" cancelText="Hủy" okButtonProps={{ danger: true }}
            onConfirm={() => onDelete(b.name)}>
            <Button size="small" danger>Xóa</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="filter-bar">
        <b>Sao lưu &amp; phục hồi dữ liệu</b>
        <span className="spacer" />
        <Button type="primary" loading={create.isPending} onClick={onCreate}>Tạo bản sao lưu</Button>
      </div>
      <Alert type="info" showIcon style={{ marginBottom: 16 }}
        message="Bản sao lưu chứa toàn bộ dữ liệu của CSDL phân tích"
        description={(
          <>
            Gồm 3 bảng fact, nhật ký ETL, tài khoản Dashboard và nhật ký can thiệp; lưu dạng file zip (CSV từng bảng + manifest.json).
            Cấu trúc bảng do migration quản lý nên chỉ phục hồi được bản sao lưu có cùng phiên bản CSDL với hệ thống hiện tại.
            Dữ liệu Moodle không nằm trong bản sao lưu vì hệ thống chỉ đọc Moodle.
          </>
        )} />
      <Card title="Các bản sao lưu"
        extra={backups.data && <span className="muted">Thư mục trên máy chủ: <code>{backups.data.directory}</code></span>}>
        {backups.error && <Alert type="error" showIcon message={errorText(backups.error)} style={{ marginBottom: 12 }} />}
        <Table rowKey="name" size="small" loading={backups.isLoading} columns={columns} dataSource={backups.data?.items ?? []}
          scroll={{ x: "max-content" }} pagination={{ pageSize: 10, hideOnSinglePage: true }}
          locale={{ emptyText: "Chưa có bản sao lưu nào" }}
          expandable={{
            expandedRowRender: (b) => (
              <Descriptions size="small" column={{ xs: 1, md: 2, xl: 4 }} bordered>
                {Object.entries(b.tables).map(([table, rows]) => (
                  <Descriptions.Item key={table} label={TABLE_LABEL[table] ?? table}>{fmtInt(rows)} dòng</Descriptions.Item>
                ))}
              </Descriptions>
            ),
          }} />
      </Card>

      <Modal open={!!target} title="Phục hồi dữ liệu" onCancel={() => !restore.isPending && setTarget(null)}
        okText="Phục hồi" cancelText="Hủy" okButtonProps={{ danger: true, disabled: confirmName !== target?.name, loading: restore.isPending }}
        cancelButtonProps={{ disabled: restore.isPending }} onOk={onRestore} closable={!restore.isPending} maskClosable={false}>
        {target && (
          <>
            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
              message="Toàn bộ dữ liệu hiện tại của CSDL phân tích sẽ bị thay bằng dữ liệu trong bản sao lưu."
              description={`Bản sao lưu tạo lúc ${fmtDateTime(target.created_at)}, ${fmtInt(target.total_rows)} dòng. Tài khoản và mật khẩu cũng trở về trạng thái tại thời điểm đó. Nên tạo một bản sao lưu mới trước khi phục hồi.`} />
            <Typography.Paragraph>Gõ lại tên file <code>{target.name}</code> để xác nhận:</Typography.Paragraph>
            <Input value={confirmName} onChange={(e) => setConfirmName(e.target.value)} placeholder={target.name}
              aria-label="Tên file xác nhận" disabled={restore.isPending} />
            {restore.isPending && <div className="muted" style={{ marginTop: 8 }}>Đang phục hồi, thao tác có thể mất khoảng một phút…</div>}
          </>
        )}
      </Modal>
    </>
  );
}
