/**
 * Chức năng 2 – Trình soạn tin cá nhân hóa: chọn kênh (tin nhắn Moodle / email), chọn mẫu, xem trước từng sinh viên
 * (biến được điền từ số liệu cảnh báo mới nhất), sửa trực tiếp, gửi và xem kết quả từng tin kèm mã xác nhận.
 * Dải thông báo luôn cho biết chế độ gửi hiện hành (offline / chuyển hướng / thật) để không ai nhầm.
 */
import { Alert, App, Button, Checkbox, Drawer, Input, InputNumber, List, Select, Skeleton, Space, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { errorMessage } from "../api/client.js";
import { useChannelModes, useMessageTemplates, usePreviewMessages, useSendMessages } from "../api/hooks.js";
import { CHANNELS } from "../theme/tokens.js";
import { RiskBadge } from "./common.jsx";

const MODE_TEXT = {
  FILE: "Chế độ kiểm thử offline: email được ghi thành file .eml trên máy chủ, không gửi ra ngoài.",
  REDIRECT: "Chế độ kiểm thử chuyển hướng: email gửi qua máy chủ thư thật nhưng tới hộp thư kiểm thử",
  STUB: "Tin nhắn Moodle gửi tới máy chủ Moodle 3.9 mô phỏng.",
  LIVE: "Chế độ vận hành thật: tin được gửi tới sinh viên.",
};

function newRequestId() {
  return (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`).replace(/[^A-Za-z0-9-]/g, "");
}

function ModeBanner({ modes, channels }) {
  if (!modes) return null;
  const lines = channels.map((ch) => {
    const m = modes.channels?.[ch];
    if (!m) return null;
    if (!m.available) return { type: "error", text: `${CHANNELS[ch].label}: không dùng được – ${m.warnings.join("; ")}` };
    const text = m.mode === "REDIRECT" ? `${MODE_TEXT.REDIRECT} ${m.redirect_to}.` : MODE_TEXT[m.mode];
    return { type: m.mode === "LIVE" ? "info" : "warning", text: `${CHANNELS[ch].label}: ${text}${m.warnings.length ? ` (${m.warnings.join("; ")})` : ""}` };
  }).filter(Boolean);
  return lines.map((l) => <Alert key={l.text} type={l.type} showIcon={false} style={{ marginBottom: 8 }} message={l.text} />);
}

export default function MessageComposer({ courseId, students, defaultChannels = ["MOODLE"], defaultPurpose = "RISK_HIGH",
  onClose, onSent }) {
  const { message } = App.useApp();
  const templates = useMessageTemplates();
  const modes = useChannelModes();
  const preview = usePreviewMessages(courseId);
  const send = useSendMessages(courseId);
  const [channels, setChannels] = useState(defaultChannels);
  const [templateId, setTemplateId] = useState();
  const [contactDays, setContactDays] = useState(7);
  const [index, setIndex] = useState(0);
  const [edits, setEdits] = useState({});
  const [result, setResult] = useState(null);
  const [requestId] = useState(newRequestId);
  const userIds = useMemo(() => students.map((s) => s.user_id), [students]);

  useEffect(() => {
    if (templateId || !templates.data) return;
    const items = templates.data.items;
    setTemplateId((items.find((t) => t.purpose === defaultPurpose) ?? items[0])?.template_id);
  }, [templates.data, templateId, defaultPurpose]);

  useEffect(() => {
    // Đã gửi xong (đang hiện kết quả) hoặc chưa có sinh viên/kênh/mẫu: không gọi xem trước
    if (result || !templateId || !channels.length || !userIds.length) return;
    setEdits({});
    preview.mutate({ user_ids: userIds, channels, template_id: templateId, contact_days: contactDays });
  }, [templateId, channels.join(","), contactDays, userIds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // Một bản nội dung cho mỗi sinh viên (dùng cho cả hai kênh); lỗi theo từng kênh
  const perStudent = useMemo(() => {
    const map = new Map();
    for (const d of preview.data?.drafts ?? []) {
      const cur = map.get(d.user_id) ?? { ...d, errors: {} };
      if (d.error) cur.errors[d.channel] = d.error;
      if (!cur.body && d.body) Object.assign(cur, { subject: d.subject, body: d.body });
      map.set(d.user_id, cur);
    }
    return [...map.values()];
  }, [preview.data]);
  const current = perStudent[index];
  const value = current ? { subject: current.subject ?? "", body: current.body ?? "", ...(edits[current.user_id] ?? {}) } : null;
  const setValue = (patch) => setEdits((e) => ({ ...e, [current.user_id]: { ...value, ...patch } }));

  const blocked = channels.some((ch) => modes.data?.channels?.[ch] && !modes.data.channels[ch].available);
  const items = perStudent.flatMap((p) => channels.filter((ch) => !p.errors[ch]).map((ch) => {
    const v = { subject: p.subject ?? "", body: p.body ?? "", ...(edits[p.user_id] ?? {}) };
    return { user_id: p.user_id, channel: ch, subject: v.subject, body: v.body };
  }));
  const skipped = perStudent.flatMap((p) => Object.entries(p.errors).map(([ch, err]) => `${p.student_name} (${CHANNELS[ch].label}): ${err}`));

  async function onSend() {
    try {
      const res = await send.mutateAsync({ request_id: requestId, template_id: templateId, items });
      setResult(res);
      if (res.failed || res.retry) message.warning(`Đã gửi ${res.sent}/${res.created} tin; ${res.failed} lỗi, ${res.retry} chờ thử lại`);
      else message.success(`Đã gửi ${res.sent} tin`);
      onSent?.(res);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  const names = Object.fromEntries(students.map((s) => [s.user_id, s.student_name]));
  return (
    <Drawer open width={720} onClose={onClose} destroyOnHidden
      title={`Soạn tin – ${students.length === 1 ? students[0].student_name : `${students.length} sinh viên`}`}
      extra={!result && <Button type="primary" onClick={onSend} loading={send.isPending}
        disabled={!items.length || blocked || preview.isPending}>Gửi {items.length} tin</Button>}>
      {result ? (
        <>
          <Alert type={result.failed ? "warning" : "success"} style={{ marginBottom: 12 }}
            message={`Đã gửi ${result.sent} tin · ${result.retry} chờ thử lại · ${result.failed} lỗi`}
            description="Mã xác nhận là mã tin nhắn Moodle (msgid) hoặc Message-ID của email – tra được ở hộp thư người nhận. Xem toàn bộ ở menu Can thiệp › Đã gửi." />
          <List size="small" dataSource={result.results} renderItem={(r) => (
            <List.Item>
              <Space wrap>
                <Tag color={r.status === "SENT" ? "green" : r.status === "QUEUED" ? "gold" : "red"}>
                  {r.status === "SENT" ? "Đã gửi" : r.status === "QUEUED" ? "Chờ thử lại" : "Lỗi"}</Tag>
                <span className="muted">tin #{r.message_id}</span>
                {r.provider_ref && <code>{r.provider_ref}</code>}
                {r.error && <span>{r.error}</span>}
              </Space>
            </List.Item>
          )} />
          <Button style={{ marginTop: 12 }} onClick={onClose}>Đóng</Button>
        </>
      ) : (
        <>
          <Space wrap style={{ marginBottom: 12 }}>
            <Checkbox.Group value={channels} onChange={setChannels}
              options={Object.entries(CHANNELS).map(([value, c]) => ({ value, label: c.label }))} />
            <Select style={{ width: 260 }} value={templateId} onChange={setTemplateId} loading={templates.isLoading}
              aria-label="Mẫu tin" options={(templates.data?.items ?? []).map((t) => ({ value: t.template_id,
                label: `${t.name}${t.is_system ? "" : " (của tôi)"}` }))} />
            <span>Hạn liên hệ sau</span>
            <InputNumber min={1} max={30} value={contactDays} onChange={(v) => setContactDays(v || 7)} suffix="ngày" style={{ width: 120 }}
              aria-label="Hạn liên hệ sau số ngày" />
          </Space>
          <ModeBanner modes={modes.data} channels={channels} />
          {preview.isPending || !current ? <Skeleton active paragraph={{ rows: 8 }} /> : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                <span className="muted">Xem trước {index + 1}/{perStudent.length}:</span>
                <b>{names[current.user_id] ?? current.student_name}</b>
                <RiskBadge level={current.risk_level} compact />
                <span style={{ marginLeft: "auto" }} />
                <Button size="small" disabled={index === 0} onClick={() => setIndex(index - 1)}>Trước</Button>
                <Button size="small" disabled={index >= perStudent.length - 1} onClick={() => setIndex(index + 1)}>Sau</Button>
              </div>
              {Object.entries(current.errors).map(([ch, err]) => (
                <Alert key={ch} type="error" style={{ marginBottom: 8 }} message={`${CHANNELS[ch].label}: ${err} – tin này sẽ không được gửi`} />
              ))}
              <div className="muted" style={{ fontSize: 12 }}>Tiêu đề {channels.includes("MOODLE") ? "(email; với Moodle là dòng đầu tin nhắn)" : ""}</div>
              <Input value={value.subject} onChange={(e) => setValue({ subject: e.target.value })} maxLength={255} style={{ marginBottom: 8 }}
                aria-label="Tiêu đề tin" />
              <div className="muted" style={{ fontSize: 12 }}>Nội dung – đã điền số liệu cảnh báo mới nhất, sửa trực tiếp được</div>
              <Input.TextArea value={value.body} onChange={(e) => setValue({ body: e.target.value })} autoSize={{ minRows: 9, maxRows: 18 }}
                aria-label="Nội dung tin"
                maxLength={5000} showCount />
              {skipped.length > 0 && (
                <Alert style={{ marginTop: 12 }} type="warning" message={`${skipped.length} tin không gửi được`}
                  description={<ul style={{ margin: 0, paddingLeft: 18 }}>{skipped.slice(0, 8).map((x) => <li key={x}>{x}</li>)}</ul>} />
              )}
            </>
          )}
        </>
      )}
    </Drawer>
  );
}
