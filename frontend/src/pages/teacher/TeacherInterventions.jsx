/**
 * Chức năng 2 – Trung tâm can thiệp của một môn:
 *   Cần liên hệ   sinh viên Đỏ/Vàng chưa được liên hệ gần đây → chọn nhiều → soạn tin cá nhân hóa
 *   Đã gửi        lịch sử gửi kèm mã xác nhận (msgid / Message-ID), duyệt tin chờ duyệt, gửi lại tin lỗi, hủy
 *   Nhắc tự động  quy tắc: không truy cập quá n ngày, vừa chuyển sang Nguy cơ cao, quá hạn nộp bài; chạy thử
 *   Mẫu tin nhắn  mẫu hệ thống (chỉ đọc) + mẫu riêng của giảng viên, danh sách biến
 */
import {
  Alert, App, Button, Card, Drawer, Form, Input, InputNumber, List, Modal, Popconfirm, Select, Space, Switch, Table, Tabs, Tag,
  Tooltip,
} from "antd";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { errorMessage } from "../../api/client.js";
import {
  useAutoPromptMutation, useAutoPrompts, useChannelModes, useContactList, useMessageAction, useMessageTemplates,
  useMessages, useTemplateMutation,
} from "../../api/hooks.js";
import { RiskBadge } from "../../components/common.jsx";
import MessageComposer from "../../components/MessageComposer.jsx";
import { CHANNELS, MESSAGE_STATUS, RISK } from "../../theme/tokens.js";
import { fmtDateTime, fmtDaysSince, fmtInt } from "../../utils/format.js";

const MODE_LABEL = { FILE: "file .eml", REDIRECT: "chuyển hướng", LIVE: "thật", STUB: "Moodle mô phỏng" };
const PURPOSE = { RISK_HIGH: "Nguy cơ cao", INACTIVE: "Không truy cập", MISSING_WORK: "Thiếu bài", CHECK_IN: "Hỏi thăm", GENERAL: "Chung" };

function StatusTag({ status, nextAttempt }) {
  const s = MESSAGE_STATUS[status] ?? { label: status };
  const tone = s.tone ? RISK[s.tone] : null;
  const text = status === "QUEUED" && nextAttempt ? `${s.label} ${fmtDateTime(nextAttempt).slice(-5)}` : s.label;
  return <Tag style={tone ? { color: tone.ink, background: tone.tint, borderColor: tone.color } : undefined}>{text}</Tag>;
}

// ----------------------------------------------------------------------------- Cần liên hệ
function ContactTab({ courseId }) {
  const [levels, setLevels] = useState(["RED", "YELLOW"]);
  const [days, setDays] = useState(7);
  const [selected, setSelected] = useState([]);
  const [compose, setCompose] = useState(null);
  const list = useContactList(courseId, { levels, not_contacted_days: days });
  const rows = list.data?.items ?? [];
  const picked = rows.filter((r) => selected.includes(r.user_id));
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select mode="multiple" value={levels} onChange={(v) => setLevels(v.length ? v : ["RED"])} style={{ minWidth: 220 }}
          aria-label="Mức" options={[{ value: "RED", label: RISK.RED.label }, { value: "YELLOW", label: RISK.YELLOW.label }]} />
        <Select value={days} onChange={setDays} style={{ width: 230 }} aria-label="Khoảng chưa liên hệ"
          options={[{ value: 3, label: "Chưa liên hệ trong 3 ngày" }, { value: 7, label: "Chưa liên hệ trong 7 ngày" },
            { value: 14, label: "Chưa liên hệ trong 14 ngày" }, { value: 0, label: "Hiện tất cả" }]} />
        {/* Chụp danh sách SV lúc mở trình soạn: sau khi gửi, bảng bỏ chọn nhưng trình soạn vẫn hiện kết quả của đúng các SV đó */}
        <Button type="primary" disabled={!picked.length} onClick={() => setCompose({ channels: ["MOODLE", "EMAIL"], students: picked })}>
          Soạn tin cho {picked.length} sinh viên đã chọn</Button>
      </Space>
      {/* Cuộn ngang bằng khung bọc: scroll.x của Ant Design sinh hàng đo aria-hidden chứa ô chọn nhận tiêu điểm (WCAG) */}
      <div className="table-scroll">
      <Table rowKey="user_id" size="middle" loading={list.isFetching} dataSource={rows}
        rowSelection={{ selectedRowKeys: selected, onChange: setSelected,
          columnTitle: (node) => <span aria-label="Chọn tất cả sinh viên trên trang">{node}</span>,
          getCheckboxProps: (r) => ({ "aria-label": `Chọn ${r.student_name} (${r.student_code ?? r.user_id})` }) }}
        pagination={{ pageSize: 20, showTotal: (t) => `${fmtInt(t)} sinh viên` }}
        columns={[
          { title: "Mức", dataIndex: "risk_level", render: (v) => <RiskBadge level={v} />, width: 120 },
          { title: "MSSV", dataIndex: "student_code" },
          { title: "Họ tên", dataIndex: "student_name" },
          { title: "Lý do chính", dataIndex: "main_reason" },
          { title: "Truy cập cuối", dataIndex: "days_since_last_access", render: fmtDaysSince },
          { title: "Liên hệ gần nhất", dataIndex: "last_contact_at",
            render: (v, r) => (v ? `${fmtDateTime(v)} · ${r.last_contact_origin === "AUTO" ? "tự động" : r.last_contact_action === "EMAIL" ? "email" : r.last_contact_action === "MESSAGE" ? "Moodle" : "ghi nhận"}`
              : <span className="muted">chưa có</span>) },
        ]} />
      </div>
      {compose && <MessageComposer courseId={courseId} students={compose.students} defaultChannels={compose.channels}
        onClose={() => setCompose(null)} onSent={() => setSelected([])} />}
    </>
  );
}

// ----------------------------------------------------------------------------- Đã gửi
function SentTab({ courseId }) {
  const { message } = App.useApp();
  const [filters, setFilters] = useState({ page: 1, page_size: 20 });
  const [view, setView] = useState(null);
  const msgs = useMessages(courseId, filters);
  const action = useMessageAction(courseId);
  const counts = msgs.data?.counts ?? {};
  async function run(messageId, act) {
    try {
      const res = await action.mutateAsync({ messageId, action: act });
      if (act === "cancel") message.success("Đã hủy tin");
      else if (res.sent) message.success("Đã gửi");
      else message.warning(res.results?.[0]?.error ?? "Chưa gửi được, sẽ thử lại");
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear placeholder="Trạng thái" aria-label="Lọc theo trạng thái" style={{ width: 200 }} value={filters.status}
          onChange={(status) => setFilters((f) => ({ ...f, status, page: 1 }))}
          options={Object.entries(MESSAGE_STATUS).map(([value, s]) => ({ value, label: `${s.label} (${counts[value] ?? 0})` }))} />
        <Select allowClear placeholder="Nguồn" aria-label="Lọc theo nguồn" style={{ width: 160 }} value={filters.origin}
          onChange={(origin) => setFilters((f) => ({ ...f, origin, page: 1 }))}
          options={[{ value: "MANUAL", label: "Giảng viên gửi" }, { value: "AUTO", label: "Tự động" }]} />
        <Select allowClear placeholder="Kênh" aria-label="Lọc theo kênh" style={{ width: 170 }} value={filters.channel}
          onChange={(channel) => setFilters((f) => ({ ...f, channel, page: 1 }))}
          options={Object.entries(CHANNELS).map(([value, c]) => ({ value, label: c.label }))} />
      </Space>
      <Table rowKey="message_id" size="middle" loading={msgs.isFetching} dataSource={msgs.data?.items ?? []} scroll={{ x: "max-content" }}
        onRow={(r) => ({ onClick: () => setView(r), style: { cursor: "pointer" } })}
        pagination={{ current: filters.page, pageSize: filters.page_size, total: msgs.data?.total ?? 0,
          onChange: (page, page_size) => setFilters((f) => ({ ...f, page, page_size })) }}
        columns={[
          { title: "Tạo lúc", dataIndex: "created_at", render: fmtDateTime },
          { title: "Sinh viên", dataIndex: "recipient_name" },
          { title: "Kênh", dataIndex: "channel", render: (v) => CHANNELS[v]?.label },
          { title: "Nguồn", dataIndex: "origin", render: (v, r) => (v === "AUTO" ? <Tooltip title={r.rule_name}>Tự động</Tooltip> : r.sender_name) },
          { title: "Trạng thái", dataIndex: "status", render: (v, r) => <StatusTag status={v} nextAttempt={r.next_attempt_at} /> },
          { title: "Chế độ", dataIndex: "delivery_mode", render: (v) => (v ? MODE_LABEL[v] : "–") },
          { title: "Mã xác nhận", dataIndex: "provider_ref",
            render: (v, r) => (v ? <code className="small">{r.channel === "MOODLE" ? `tin #${v}` : v}</code> : r.last_error ? <span className="small">{r.last_error}</span> : "–") },
          { title: "", key: "act", render: (_, r) => (
            <Space onClick={(e) => e.stopPropagation()}>
              {r.status === "PENDING_REVIEW" && <Button size="small" type="primary" onClick={() => run(r.message_id, "approve")}>Duyệt gửi</Button>}
              {r.status === "FAILED" && <Button size="small" onClick={() => run(r.message_id, "retry")}>Gửi lại</Button>}
              {["PENDING_REVIEW", "QUEUED"].includes(r.status) && (
                <Popconfirm title="Hủy tin này?" okText="Hủy tin" cancelText="Không" onConfirm={() => run(r.message_id, "cancel")}>
                  <Button size="small" danger>Hủy</Button>
                </Popconfirm>
              )}
            </Space>
          ) },
        ]} />
      <div className="muted small">Mã xác nhận do máy chủ nhận trả về: mã tin nhắn trong Moodle (bảng mdl_messages) hoặc Message-ID của email – bằng chứng tin đã được gửi đi.</div>
      <Drawer open={!!view} onClose={() => setView(null)} width={560} title={view ? `Tin #${view.message_id} – ${view.recipient_name}` : ""}>
        {view && (
          <>
            <List size="small" dataSource={[
              ["Kênh", CHANNELS[view.channel]?.label], ["Người nhận", view.recipient], ["Thực tế gửi tới", view.delivered_to ?? "–"],
              ["Trạng thái", <StatusTag key="s" status={view.status} nextAttempt={view.next_attempt_at} />],
              ["Số lần thử", view.attempts], ["Gửi lúc", view.sent_at ? fmtDateTime(view.sent_at) : "–"],
              ["Mã xác nhận", view.provider_ref ?? "–"], ["Lỗi cuối", view.last_error ?? "–"],
              ...(view.status === "SENT" && view.provider_meta?.view_url ? [["Xem như sinh viên", (
                <a key="v" href={view.provider_meta.view_url} target="_blank" rel="noreferrer">
                  {view.delivery_mode === "STUB" ? "Mở hộp tin trên Moodle mô phỏng" : "Mở hội thoại trên Moodle"}
                </a>
              )]] : []),
            ]} renderItem={([k, v]) => <List.Item><span className="muted" style={{ width: 140, display: "inline-block" }}>{k}</span>{v}</List.Item>} />
            {view.subject && <div style={{ marginTop: 12 }}><b>{view.subject}</b></div>}
            <div className="message-body">{view.body}</div>
          </>
        )}
      </Drawer>
    </>
  );
}

// ----------------------------------------------------------------------------- Nhắc tự động
function RuleForm({ courseId, rule, triggers, templates, onClose }) {
  const { message } = App.useApp();
  const mutation = useAutoPromptMutation(courseId);
  const [form] = Form.useForm();
  const trigger = Form.useWatch("trigger_type", form) ?? rule?.trigger_type ?? "INACTIVE_DAYS";
  const spec = triggers.find((t) => t.code === trigger);
  async function submit(values) {
    const body = { ...values, params: spec?.param ? { [spec.param]: values.param } : {} };
    delete body.param;
    try {
      await mutation.mutateAsync({ ruleId: rule?.rule_id, body });
      message.success("Đã lưu quy tắc");
      onClose();
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  const initial = rule ? { ...rule, param: spec?.param ? rule.params?.[spec.param] : undefined }
    : { name: "Nhắc khi không truy cập", trigger_type: "INACTIVE_DAYS", param: 7, channels: ["MOODLE", "EMAIL"],
      template_id: templates.find((t) => t.purpose === "INACTIVE")?.template_id, send_mode: "REVIEW", cooldown_days: 7, is_active: true };
  return (
    <Modal open title={rule ? "Sửa quy tắc nhắc tự động" : "Thêm quy tắc nhắc tự động"} onCancel={onClose} onOk={() => form.submit()}
      okText="Lưu" cancelText="Hủy" confirmLoading={mutation.isPending} destroyOnHidden width={560}>
      <Form form={form} layout="vertical" initialValues={initial} onFinish={submit}>
        <Form.Item name="name" label="Tên quy tắc" rules={[{ required: true, max: 120 }]}><Input /></Form.Item>
        <Form.Item name="trigger_type" label="Điều kiện">
          <Select options={triggers.map((t) => ({ value: t.code, label: t.name }))} />
        </Form.Item>
        {spec?.param && (
          <Form.Item name="param" label={spec.param === "days" ? "Số ngày không truy cập" : "Số ngày sau hạn nộp"}
            rules={[{ required: true }]}><InputNumber min={spec.lo} max={spec.hi} /></Form.Item>
        )}
        <Form.Item name="channels" label="Kênh" rules={[{ required: true, type: "array", min: 1 }]}>
          <Select mode="multiple" options={Object.entries(CHANNELS).map(([value, c]) => ({ value, label: c.label }))} />
        </Form.Item>
        <Form.Item name="template_id" label="Mẫu tin" rules={[{ required: true }]}>
          <Select options={templates.map((t) => ({ value: t.template_id, label: t.name }))} />
        </Form.Item>
        <Form.Item name="send_mode" label="Cách gửi">
          <Select options={[{ value: "REVIEW", label: "Chờ giảng viên duyệt" }, { value: "AUTO", label: "Tự động gửi" }]} />
        </Form.Item>
        <Form.Item name="cooldown_days" label="Mỗi sinh viên tối đa 1 tin trong (ngày)"><InputNumber min={1} max={60} /></Form.Item>
        <Form.Item name="is_active" label="Bật" valuePropName="checked"><Switch /></Form.Item>
      </Form>
    </Modal>
  );
}

function AutoTab({ courseId }) {
  const { message } = App.useApp();
  const prompts = useAutoPrompts(courseId);
  const templates = useMessageTemplates();
  const mutation = useAutoPromptMutation(courseId);
  const [editing, setEditing] = useState(null);
  const [dry, setDry] = useState(null);
  const triggers = prompts.data?.triggers ?? [];
  async function act(rule, action) {
    try {
      const res = await mutation.mutateAsync({ ruleId: rule.rule_id, action });
      if (action === "dry-run") setDry({ rule, res });
      else message.success(`Đã tạo ${res.created} tin (${res.matched} sinh viên khớp, ${res.skipped_cooldown} trong thời gian chờ)`);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  async function toggle(rule, isActive) {
    try {
      await mutation.mutateAsync({ ruleId: rule.rule_id, body: { ...rule, is_active: isActive } });
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" onClick={() => setEditing({})} disabled={!templates.data}>Thêm quy tắc</Button>
      </Space>
      <List loading={prompts.isLoading} dataSource={prompts.data?.items ?? []} locale={{ emptyText: "Chưa có quy tắc nhắc tự động" }}
        renderItem={(r) => (
          <Card size="small" style={{ marginBottom: 10 }}
            title={<Space>{r.name}{!r.is_active && <Tag>Đang tắt</Tag>}</Space>}
            extra={<Switch checked={r.is_active} onChange={(v) => toggle(r, v)} aria-label="Bật/tắt quy tắc" />}>
            <div className="small">
              Điều kiện: {triggers.find((t) => t.code === r.trigger_type)?.name}
              {r.params?.days != null && ` (${r.params.days} ngày)`}{r.params?.days_after != null && ` (${r.params.days_after} ngày sau hạn)`}
              {" · "}Kênh: {r.channels.map((c) => CHANNELS[c].label).join(", ")} · Mẫu: {r.template_name}
              {" · "}Gửi: <b>{r.send_mode === "AUTO" ? "tự động" : "chờ duyệt"}</b> · tối đa 1 tin/{r.cooldown_days} ngày mỗi sinh viên
            </div>
            <div className="muted small" style={{ marginTop: 4 }}>
              {r.last_run_at ? `Lần chạy gần nhất ${fmtDateTime(r.last_run_at)} · ${r.last_run_summary?.matched ?? 0} khớp · tạo ${r.last_run_summary?.created ?? 0} tin` : "Chưa chạy"}
              {" · "}đã gửi {r.sent} · chờ duyệt {r.pending_review}
            </div>
            <Space style={{ marginTop: 8 }} wrap>
              <Button size="small" onClick={() => act(r, "dry-run")}>Chạy thử (không gửi)</Button>
              <Popconfirm title="Tạo tin cho các sinh viên khớp điều kiện ngay bây giờ?" okText="Chạy" cancelText="Hủy" onConfirm={() => act(r, "run")}>
                <Button size="small" disabled={!r.is_active}>Chạy ngay</Button>
              </Popconfirm>
              <Button size="small" onClick={() => setEditing(r)}>Sửa</Button>
            </Space>
          </Card>
        )} />
      <div className="muted small">Hệ thống tự chạy các quy tắc đang bật sau mỗi lần cập nhật cảnh báo (07:15–21:15, 2 giờ/lần); không gửi tự động trong khung giờ yên lặng 22:00–06:00 (tin tạo trong khung này được hẹn gửi 07:00).</div>
      {editing && templates.data && <RuleForm courseId={courseId} rule={editing.rule_id ? editing : null} triggers={triggers}
        templates={templates.data.items} onClose={() => setEditing(null)} />}
      <Modal open={!!dry} onCancel={() => setDry(null)} footer={null} title={dry ? `Chạy thử: ${dry.rule.name}` : ""} width={620}>
        {dry && (
          <>
            <Alert type="info" style={{ marginBottom: 12 }}
              message={`${dry.res.matched} sinh viên khớp điều kiện; ${dry.res.skipped_cooldown} đã nhận tin của quy tắc này trong thời gian chờ; ${dry.res.recipients.length} sẽ nhận tin nếu chạy bây giờ.`} />
            <Table size="small" rowKey="user_id" dataSource={dry.res.recipients} pagination={{ pageSize: 8 }}
              columns={[{ title: "MSSV", dataIndex: "student_code" }, { title: "Họ tên", dataIndex: "student_name" },
                { title: "Mức", dataIndex: "risk_level", render: (v) => <RiskBadge level={v} compact /> }]} />
          </>
        )}
      </Modal>
    </>
  );
}

// ----------------------------------------------------------------------------- Mẫu tin
function TemplatesTab() {
  const { message } = App.useApp();
  const templates = useMessageTemplates();
  const mutation = useTemplateMutation();
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  async function submit(values) {
    try {
      await mutation.mutateAsync({ templateId: editing.template_id && !editing.is_system ? editing.template_id : undefined, body: values });
      message.success("Đã lưu mẫu");
      setEditing(null);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  const vars = templates.data?.variables ?? [];
  return (
    <>
      <Table rowKey="template_id" size="middle" loading={templates.isLoading} dataSource={templates.data?.items ?? []} pagination={false}
        columns={[
          { title: "Tên", dataIndex: "name", render: (v, r) => <Space>{v}{r.is_system ? <Tag>Hệ thống</Tag> : <Tag color="blue">Của tôi</Tag>}</Space> },
          { title: "Dùng cho", dataIndex: "purpose", render: (v) => PURPOSE[v] },
          { title: "Tiêu đề", dataIndex: "subject" },
          { title: "", key: "act", render: (_, r) => (
            <Space>
              <Button size="small" onClick={() => setEditing(r.is_system ? { ...r, name: `${r.name} (bản của tôi)` } : r)}>
                {r.is_system ? "Tạo bản sao" : "Sửa"}</Button>
              {!r.is_system && (
                <Popconfirm title="Xóa mẫu này?" okText="Xóa" cancelText="Không"
                  onConfirm={() => mutation.mutate({ templateId: r.template_id, remove: true })}>
                  <Button size="small" danger>Xóa</Button>
                </Popconfirm>
              )}
            </Space>
          ) },
        ]} />
      <Modal open={!!editing} onCancel={() => setEditing(null)} onOk={() => form.submit()} okText="Lưu" cancelText="Hủy" width={720}
        confirmLoading={mutation.isPending} title={editing?.template_id && !editing.is_system ? "Sửa mẫu tin" : "Tạo mẫu tin"} destroyOnHidden>
        {editing && (
          <Form form={form} layout="vertical" initialValues={editing} onFinish={submit}>
            <Form.Item name="name" label="Tên mẫu" rules={[{ required: true, max: 120 }]}><Input /></Form.Item>
            <Form.Item name="purpose" label="Dùng cho"><Select options={Object.entries(PURPOSE).map(([value, label]) => ({ value, label }))} /></Form.Item>
            <Form.Item name="subject" label="Tiêu đề" rules={[{ required: true, max: 200 }]}><Input /></Form.Item>
            <Form.Item name="body" label="Nội dung" rules={[{ required: true, max: 5000 }]}><Input.TextArea autoSize={{ minRows: 8 }} /></Form.Item>
            <div className="muted small">Biến dùng được: {vars.map((v) => <Tooltip key={v.name} title={v.label}><code style={{ marginRight: 6 }}>{`{${v.name}}`}</code></Tooltip>)}</div>
          </Form>
        )}
      </Modal>
    </>
  );
}

export default function TeacherInterventions() {
  const { courseId } = useParams();
  const modes = useChannelModes();
  const ch = modes.data?.channels ?? {};
  const banner = Object.entries(ch).map(([k, m]) => `${CHANNELS[k].label}: ${m.available ? m.mode_label : `không dùng được (${m.warnings.join("; ")})`}`);
  return (
    <Card>
      {banner.length > 0 && <Alert type={Object.values(ch).some((m) => m.mode === "LIVE") ? "info" : "warning"} style={{ marginBottom: 12 }}
        message={banner.join(" · ")} />}
      <Tabs items={[
        { key: "contact", label: "Cần liên hệ", children: <ContactTab courseId={courseId} /> },
        { key: "sent", label: "Đã gửi", children: <SentTab courseId={courseId} /> },
        { key: "auto", label: "Nhắc tự động", children: <AutoTab courseId={courseId} /> },
        { key: "templates", label: "Mẫu tin nhắn", children: <TemplatesTab /> },
      ]} destroyOnHidden />
    </Card>
  );
}
