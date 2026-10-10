/**
 * Hệ thống › Kênh gửi tin (chức năng 2 – quản trị): cấu hình hiện hành (đã che bí mật), chế độ gửi hiệu lực của từng kênh,
 * kiểm tra Moodle Web Service, gửi email thử, thống kê 30 ngày. Kết quả kiểm tra thành công là điều kiện 3 để được
 * gửi tới người nhận thật (cùng với MESSAGING_ALLOW_LIVE=true và dữ liệu thật).
 */
import { Alert, App, Button, Card, Col, Descriptions, Input, Row, Space, Table, Tag } from "antd";
import { useState } from "react";
import { errorMessage } from "../../api/client.js";
import { useChannelStatus, useChannelTest } from "../../api/hooks.js";
import { CHANNELS, MESSAGE_STATUS } from "../../theme/tokens.js";
import { fmtDateTime } from "../../utils/format.js";

const MODE = {
  FILE: ["Kiểm thử offline", "Email được ghi thành file .eml trong thư mục máy chủ"],
  REDIRECT: ["Kiểm thử chuyển hướng", "Gửi qua máy chủ thư thật nhưng mọi email tới hộp thư kiểm thử"],
  STUB: ["Moodle mô phỏng", "Gửi tới máy chủ Moodle 3.9 mô phỏng (tools/moodle_ws_stub)"],
  LIVE: ["Vận hành thật", "Gửi tới sinh viên"],
};

function ChannelCard({ channel, info, onTest, testing, testResult }) {
  const [to, setTo] = useState("");
  const [label, desc] = MODE[info.mode] ?? ["Không dùng được", ""];
  const check = info.last_check;
  return (
    <Card title={CHANNELS[channel].label} style={{ height: "100%" }}
      extra={<Tag color={info.mode === "LIVE" ? "green" : info.mode ? "gold" : "red"}>{label}</Tag>}>
      <div className="muted" style={{ marginBottom: 8 }}>{desc}</div>
      {info.warnings.map((w) => <Alert key={w} type="warning" style={{ marginBottom: 8 }} message={w} />)}
      <Descriptions size="small" column={1} items={[
        { key: "c", label: "Kiểm tra gần nhất", children: check
          ? <>{check.ok ? <Tag color="green">Thành công</Tag> : <Tag color="red">Lỗi</Tag>} {fmtDateTime(check.checked_at)}
            {check.checked_by_name && ` – ${check.checked_by_name}`}{!check.current_config && <Tag style={{ marginLeft: 6 }}>cấu hình đã đổi, cần kiểm tra lại</Tag>}</>
          : "chưa kiểm tra" },
        ...(check?.detail ? Object.entries(check.detail).filter(([, v]) => v != null && v !== "")
          .slice(0, 6).map(([k, v]) => ({ key: k, label: k, children: Array.isArray(v) ? v.join(", ") || "–" : String(v) })) : []),
      ]} />
      <Space style={{ marginTop: 12 }} wrap>
        {channel === "EMAIL" && <Input style={{ width: 260 }} placeholder="Địa chỉ nhận email thử" value={to} onChange={(e) => setTo(e.target.value)} />}
        <Button type="primary" loading={testing} disabled={channel === "EMAIL" && !to.includes("@")}
          onClick={() => onTest(channel === "EMAIL" ? { kind: "email", to } : { kind: "moodle" })}>
          {channel === "EMAIL" ? "Gửi email thử" : "Kiểm tra Moodle"}
        </Button>
      </Space>
      {testResult && (
        <Alert style={{ marginTop: 12 }} type={testResult.ok ? "success" : "error"}
          message={testResult.ok ? (channel === "EMAIL" ? `Đã gửi – Message-ID ${testResult.message_id}` : `Kết nối được: ${testResult.sitename} · ${testResult.release}`)
            : testResult.error} />
      )}
    </Card>
  );
}

export default function AdminChannels() {
  const { message } = App.useApp();
  const status = useChannelStatus();
  const test = useChannelTest();
  const [results, setResults] = useState({});
  async function onTest(args) {
    try {
      const res = await test.mutateAsync(args);
      setResults((r) => ({ ...r, [args.kind]: res }));
      if (!res.ok) message.error(res.error);
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  const d = status.data;
  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Alert type="info" message="Gửi tới người nhận thật chỉ khi đủ 3 điều kiện: MESSAGING_ALLOW_LIVE=true, hệ thống chạy dữ liệu thật (LMS_AS_OF trống), và kênh đã kiểm tra thành công với cấu hình hiện tại. Thiếu điều kiện nào, email tự chuyển về chế độ kiểm thử và Moodle thật bị từ chối." />
      </Col>
      {d && ["MOODLE", "EMAIL"].map((ch) => (
        <Col xs={24} lg={12} key={ch}>
          <ChannelCard channel={ch} info={d.channels[ch]} onTest={onTest} testing={test.isPending && test.variables?.kind === (ch === "EMAIL" ? "email" : "moodle")}
            testResult={results[ch === "EMAIL" ? "email" : "moodle"]} />
        </Col>
      ))}
      <Col xs={24} lg={12}>
        <Card title="Cấu hình hiện hành (đã che bí mật)" loading={status.isLoading}>
          {d && <Descriptions size="small" column={1} items={Object.entries(d.config).map(([k, v]) => ({ key: k, label: k,
            children: v == null ? "–" : typeof v === "boolean" ? (v ? "có" : "không") : String(v) }))} />}
          <div className="muted small" style={{ marginTop: 8 }}>Thay đổi trong file .env của máy chủ rồi khởi động lại dịch vụ; mật khẩu và token không bao giờ hiển thị.</div>
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="Thống kê gửi 30 ngày" loading={status.isLoading}>
          <Table size="small" pagination={false} rowKey={(r) => `${r.channel}-${r.origin}-${r.status}`} dataSource={d?.stats ?? []}
            columns={[
              { title: "Kênh", dataIndex: "channel", render: (v) => CHANNELS[v]?.label },
              { title: "Nguồn", dataIndex: "origin", render: (v) => (v === "AUTO" ? "Tự động" : "Giảng viên") },
              { title: "Trạng thái", dataIndex: "status", render: (v) => MESSAGE_STATUS[v]?.label ?? v },
              { title: "Số tin", dataIndex: "n", align: "right" },
            ]} />
        </Card>
      </Col>
    </Row>
  );
}
