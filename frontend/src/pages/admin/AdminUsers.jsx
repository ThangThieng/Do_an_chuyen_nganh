/** Hệ thống › Quản lý người dùng: danh sách tài khoản, khóa/mở khóa, đặt lại mật khẩu (mật khẩu tạm hiện một lần). */
import { Alert, App, Button, Card, Input, Modal, Popconfirm, Segmented, Space, Table, Tag, Typography } from "antd";
import { useMemo, useState } from "react";
import { errorMessage, errorText } from "../../api/client.js";
import { useResetPassword, useSetUserActive, useUsers } from "../../api/hooks.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { fmtDateTime, fmtInt } from "../../utils/format.js";

const ROLE_TAG = { ADMIN: <Tag color="geekblue">Quản trị viên</Tag>, TEACHER: <Tag color="cyan">Giảng viên</Tag> };

export default function AdminUsers() {
  const { message } = App.useApp();
  const { user: me } = useAuth();
  const { data, isLoading, error } = useUsers();
  const setActive = useSetUserActive();
  const reset = useResetPassword();
  const [role, setRole] = useState("ALL");
  const [search, setSearch] = useState("");
  const [issued, setIssued] = useState(null);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data ?? []).filter((u) => (role === "ALL" || u.role === role)
      && (!q || [u.username, u.full_name, u.email].some((v) => v?.toLowerCase().includes(q))));
  }, [data, role, search]);

  async function toggle(u) {
    try {
      await setActive.mutateAsync({ userId: u.user_id, isActive: !u.is_active });
      message.success(`${u.is_active ? "Đã khóa" : "Đã mở khóa"} tài khoản ${u.username}`);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  async function resetPassword(u) {
    try {
      setIssued(await reset.mutateAsync(u.user_id));
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  const columns = [
    { title: "Tên đăng nhập", dataIndex: "username", sorter: (a, b) => a.username.localeCompare(b.username) },
    { title: "Họ tên", dataIndex: "full_name", render: (v) => v ?? "–" },
    { title: "Email", dataIndex: "email", render: (v) => v ?? "–" },
    { title: "Vai trò", dataIndex: "role", render: (v) => ROLE_TAG[v] },
    { title: "Số môn phụ trách", dataIndex: "course_count", align: "right", render: (v, u) => (u.role === "TEACHER" ? fmtInt(v) : "–") },
    {
      title: "Trạng thái", dataIndex: "is_active",
      render: (v) => (v ? <Tag color="green">Đang hoạt động</Tag> : <Tag color="red">Đã khóa</Tag>),
    },
    { title: "Đăng nhập gần nhất", dataIndex: "last_login_at", render: (v) => (v ? fmtDateTime(v) : "Chưa đăng nhập") },
    { title: "Đổi mật khẩu gần nhất", dataIndex: "password_changed_at", render: (v) => (v ? fmtDateTime(v) : "–") },
    {
      title: "Thao tác", key: "actions", fixed: "right",
      render: (_, u) => (u.user_id === me.id ? <span className="muted">Tài khoản của bạn</span> : (
        <Space>
          <Popconfirm
            title={u.is_active ? `Khóa tài khoản ${u.username}?` : `Mở khóa tài khoản ${u.username}?`}
            description={u.is_active ? "Người dùng sẽ bị đăng xuất ngay và không đăng nhập lại được." : undefined}
            okText={u.is_active ? "Khóa" : "Mở khóa"} cancelText="Hủy" okButtonProps={{ danger: u.is_active }}
            onConfirm={() => toggle(u)}>
            <Button size="small" danger={u.is_active}>{u.is_active ? "Khóa" : "Mở khóa"}</Button>
          </Popconfirm>
          <Popconfirm
            title={`Đặt lại mật khẩu cho ${u.username}?`}
            description="Mật khẩu cũ và mọi phiên đăng nhập của người dùng này mất hiệu lực."
            okText="Đặt lại" cancelText="Hủy" onConfirm={() => resetPassword(u)}>
            <Button size="small">Đặt lại mật khẩu</Button>
          </Popconfirm>
        </Space>
      )),
    },
  ];

  return (
    <>
      <div className="filter-bar">
        <b>Quản lý người dùng</b>
        <Segmented value={role} onChange={setRole}
          options={[{ label: "Tất cả", value: "ALL" }, { label: "Quản trị viên", value: "ADMIN" }, { label: "Giảng viên", value: "TEACHER" }]} />
        <Input.Search allowClear placeholder="Tìm theo tên đăng nhập, họ tên, email" style={{ width: 320 }}
          value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm người dùng" />
      </div>
      <Card title="Tài khoản Dashboard" extra={data && <span className="muted">{fmtInt(rows.length)} / {fmtInt(data.length)} tài khoản</span>}>
        {error && <Alert type="error" showIcon message={errorText(error)} style={{ marginBottom: 12 }} />}
        <Table rowKey="user_id" size="small" loading={isLoading} columns={columns} dataSource={rows}
          scroll={{ x: "max-content" }} pagination={{ pageSize: 20, hideOnSinglePage: true }}
          rowClassName={(u) => (u.is_active ? "" : "row-inactive")} />
        <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          Tài khoản được tạo từ Moodle bằng lệnh <code>python -m backend.app.cli sync-users</code>: người có vai trò giảng dạy
          trong ít nhất một môn là Giảng viên. Hệ thống không cho tạo tài khoản tùy ý vì mã tài khoản phải trùng với mã người dùng Moodle
          để phân quyền dữ liệu theo môn.
        </div>
      </Card>

      <Modal open={!!issued} title="Mật khẩu tạm đã được tạo" onCancel={() => setIssued(null)}
        footer={<Button type="primary" onClick={() => setIssued(null)}>Đã ghi lại</Button>}>
        {issued && (
          <>
            <p>Mật khẩu tạm của <b>{issued.username}</b>:</p>
            <Typography.Paragraph copyable={{ text: issued.temporary_password, tooltips: ["Sao chép", "Đã sao chép"] }}
              style={{ fontSize: 20, fontFamily: "Consolas, monospace", letterSpacing: 1 }}>
              {issued.temporary_password}
            </Typography.Paragraph>
            <Alert type="warning" showIcon
              message="Mật khẩu này chỉ hiển thị một lần. Hãy gửi cho người dùng qua kênh riêng và đề nghị họ đổi mật khẩu ngay sau khi đăng nhập." />
          </>
        )}
      </Modal>
    </>
  );
}
