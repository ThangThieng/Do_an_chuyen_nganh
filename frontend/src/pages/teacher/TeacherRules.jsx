/**
 * Chức năng 1 – Thiết lập ngưỡng, trọng số và luật cảnh báo riêng cho môn.
 * Chọn mẫu (Mặc định / Lý thuyết / Thực hành / Đồ án) rồi tinh chỉnh; mỗi thay đổi được XEM TRƯỚC tác động
 * (backend chấm lại cả lớp bằng đúng hàm của ETL, không ghi CSDL); lưu tạo phiên bản mới và áp dụng cho số liệu hôm nay.
 * Giới hạn an toàn do backend trả về (không viết cứng), kiểm tra ở cả giao diện và backend.
 */
import {
  Alert, App, Button, Card, Col, Empty, Input, InputNumber, Popconfirm, Row, Segmented, Select, Skeleton, Space, Table, Tag,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { errorMessage, errorText } from "../../api/client.js";
import { useCourseRules, usePreviewRules, useResetRules, useSaveRules } from "../../api/hooks.js";
import { RiskBadge } from "../../components/common.jsx";
import MetricInfo from "../../components/MetricInfo.jsx";
import { RISK, RISK_LEVELS, SERIES } from "../../theme/tokens.js";
import { fmtDateTime, fmtInt } from "../../utils/format.js";

const PCT_KEYS = ["absence_yellow", "absence_red", "missing_yellow", "missing_red", "low_access_ratio"];
const EXTRA_LABEL = {
  consecutive_missing: "Bỏ nộp bài liên tiếp", absent_sessions: "Vắng số buổi", absence_rate: "Tỷ lệ vắng",
  inactive_days: "Không truy cập", missing_count: "Thiếu bài",
};
const EXTRA_UNIT = { consecutive_missing: "bài", absent_sessions: "buổi", absence_rate: "%", inactive_days: "ngày", missing_count: "bài" };
const WEIGHT_LABEL = { attendance: "Vắng học", inactivity: "Không tương tác", assignment: "Thiếu bài tập" };

const toPct = (v) => Math.round(Number(v) * 1000) / 10;
const fromPct = (v) => Math.round(Number(v) * 10) / 1000;

function cleanParams(p) {
  return {
    thresholds: { ...p.thresholds },
    weights: { ...p.weights },
    extra_rules: (p.extra_rules ?? []).map(({ text, ...r }) => r),
  };
}

function clientErrors(p, bounds) {
  if (!bounds) return [];
  const errs = [];
  const t = p.thresholds;
  const b = bounds.thresholds;
  for (const [k, [lo, hi]] of Object.entries(b)) {
    const v = Number(t[k]);
    if (Number.isNaN(v) || v < lo || v > hi) errs.push(`${k}: phải từ ${PCT_KEYS.includes(k) ? `${toPct(lo)}%` : lo} đến ${PCT_KEYS.includes(k) ? `${toPct(hi)}%` : hi}`);
  }
  if (t.absence_red <= t.absence_yellow) errs.push("Ngưỡng vắng mức 2 phải lớn hơn mức 1");
  if (t.missing_red <= t.missing_yellow) errs.push("Ngưỡng thiếu bài mức 2 phải lớn hơn mức 1");
  if (t.inactive_red_days <= t.inactive_yellow_days) errs.push("Số ngày mức 2 phải lớn hơn mức 1");
  const [wlo, whi] = bounds.weight;
  const sum = Object.values(p.weights).reduce((a, v) => a + Number(v), 0);
  Object.entries(p.weights).forEach(([k, v]) => { if (v < wlo || v > whi) errs.push(`Trọng số ${WEIGHT_LABEL[k].toLowerCase()} phải từ ${toPct(wlo)}% đến ${toPct(whi)}%`); });
  if (Math.abs(sum - 1) > 0.001) errs.push(`Tổng trọng số phải bằng 100% (hiện ${toPct(sum)}%)`);
  if (p.extra_rules.length > bounds.max_extra_rules) errs.push(`Tối đa ${bounds.max_extra_rules} luật bổ sung`);
  p.extra_rules.forEach((r, i) => {
    const spec = bounds.extra_rule_types[r.type];
    const v = Number(r[spec.field]);
    if (Number.isNaN(v) || v < spec.min || v > spec.max) errs.push(`Luật bổ sung ${i + 1}: giá trị từ ${spec.min} đến ${spec.max}`);
  });
  return errs;
}

// Nhãn cho trình đọc màn hình (WCAG 2.1 – mọi ô nhập phải có tên)
const THRESHOLD_LABEL = {
  absence_yellow: "Ngưỡng vắng học mức cần lưu ý", absence_red: "Ngưỡng vắng học mức nguy cơ cao",
  inactive_yellow_days: "Số ngày chưa vào mức cần lưu ý", inactive_red_days: "Số ngày chưa vào mức nguy cơ cao",
  low_access_ratio: "Tỷ lệ truy cập so với trung vị lớp",
  missing_yellow: "Ngưỡng thiếu bài mức cần lưu ý", missing_red: "Ngưỡng thiếu bài mức nguy cơ cao",
};

function Pct({ value, onChange, disabled, label }) {
  return <InputNumber size="small" min={0} max={100} step={1} value={toPct(value)} disabled={disabled}
    onChange={(v) => onChange(fromPct(v ?? 0))} suffix="%" style={{ width: 96 }} aria-label={label} />;
}

function Days({ value, onChange, disabled, label }) {
  return <InputNumber size="small" min={1} max={60} value={value} disabled={disabled} onChange={(v) => onChange(v ?? 1)}
    suffix="ngày" style={{ width: 108 }} aria-label={label} />;
}

function Stack({ counts, total }) {
  return (
    <div className="stack-bar" aria-hidden>
      {RISK_LEVELS.map((lv) => (
        <span key={lv} style={{ width: `${total ? (100 * counts[lv]) / total : 0}%`, background: RISK[lv].color }} />
      ))}
    </div>
  );
}

export default function TeacherRules() {
  const { courseId } = useParams();
  const { message } = App.useApp();
  const rules = useCourseRules(courseId);
  const preview = usePreviewRules(courseId);
  const save = useSaveRules(courseId);
  const reset = useResetRules(courseId);
  const [preset, setPreset] = useState("DEFAULT");
  const [params, setParams] = useState(null);
  const [note, setNote] = useState("");
  const data = rules.data;
  const canEdit = !!data?.can_edit;

  useEffect(() => {
    if (!data) return;
    setPreset(data.active.scope === "COURSE" ? data.active.preset : "DEFAULT");
    setParams(cleanParams(data.active));
  }, [data]);

  const errors = useMemo(() => (params ? clientErrors(params, data?.bounds) : []), [params, data?.bounds]);
  useEffect(() => {
    if (!params || errors.length) return undefined;
    const timer = setTimeout(() => preview.mutate({ preset, params }), 400);
    return () => clearTimeout(timer);
  }, [JSON.stringify(params), errors.length]); // eslint-disable-line react-hooks/exhaustive-deps

  if (rules.error) return <Alert type="error" showIcon message="Không mở được thiết lập cảnh báo" description={errorText(rules.error)} />;
  if (!data || !params) return <Skeleton active paragraph={{ rows: 12 }} />;

  const choosePreset = (code) => {
    setPreset(code);
    if (code === "CUSTOM") return;
    const p = data.presets.find((x) => x.code === code);
    if (p) setParams(cleanParams(p.params));
  };
  const edit = (fn) => { setPreset("CUSTOM"); setParams((p) => fn(structuredClone(p))); };
  const setT = (k) => (v) => edit((p) => { p.thresholds[k] = v; return p; });
  const setW = (k) => (v) => edit((p) => { p.weights[k] = fromPct(v ?? 0); return p; });
  const t = params.thresholds;
  const weightSum = Object.values(params.weights).reduce((a, v) => a + Number(v), 0);
  const activities = data.attendance_activities ?? [];

  async function onSave() {
    try {
      const res = await save.mutateAsync({ preset, params, note: note || undefined });
      message.success(`Đã lưu luật ${res.active.label} và áp dụng cho ${fmtInt(res.applied.total)} sinh viên hôm nay`);
      setNote("");
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }
  async function onReset() {
    try {
      await reset.mutateAsync();
      message.success("Đã khôi phục luật mặc định của trường");
    } catch (err) {
      message.error(await errorMessage(err));
    }
  }

  const pv = preview.data;
  const presetDesc = data.presets.find((x) => x.code === preset)?.description;
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={14}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          {!canEdit && <Alert type="info" message="Chỉ giảng viên chính của môn được thay đổi luật cảnh báo; bạn có thể xem và xem trước." />}
          <Card title="Mẫu luật cho môn này" extra={<MetricInfo metric={{ keys: ["risk_level", "risk_score"], courseId }} />}>
            <Segmented className="wrap-segmented" value={preset} onChange={choosePreset} disabled={!canEdit}
              options={[...data.presets.map((p) => ({ value: p.code, label: p.name })), { value: "CUSTOM", label: "Tùy chỉnh" }]} />
            <div className="muted" style={{ marginTop: 8 }}>
              {presetDesc ?? "Đã chỉnh tay từ một mẫu."} Luật đang áp dụng: <b>{data.active.scope === "COURSE" ? `riêng của môn (${data.active.label})` : `mặc định của trường (${data.active.label})`}</b>.
            </div>
          </Card>

          <Card title="Ngưỡng và trọng số của 3 tiêu chí">
            <Table size="small" pagination={false} rowKey="k" scroll={{ x: "max-content" }}
              dataSource={[
                { k: "c1", name: "Vắng học", one: <>vắng từ <Pct value={t.absence_yellow} onChange={setT("absence_yellow")} label={THRESHOLD_LABEL.absence_yellow} disabled={!canEdit} /> số buổi</>,
                  two: <>từ <Pct value={t.absence_red} onChange={setT("absence_red")} label={THRESHOLD_LABEL.absence_red} disabled={!canEdit} /></>, w: "attendance" },
                { k: "c2", name: "Không tương tác",
                  one: <>quá <Days value={t.inactive_yellow_days} onChange={setT("inactive_yellow_days")} label={THRESHOLD_LABEL.inactive_yellow_days} disabled={!canEdit} /> chưa vào, hoặc truy cập 14 ngày dưới <Pct value={t.low_access_ratio} onChange={setT("low_access_ratio")} label={THRESHOLD_LABEL.low_access_ratio} disabled={!canEdit} /> trung vị lớp</>,
                  two: <>quá <Days value={t.inactive_red_days} onChange={setT("inactive_red_days")} label={THRESHOLD_LABEL.inactive_red_days} disabled={!canEdit} /> hoặc chưa từng vào</>, w: "inactivity" },
                { k: "c3", name: "Thiếu bài tập", one: <>thiếu từ <Pct value={t.missing_yellow} onChange={setT("missing_yellow")} label={THRESHOLD_LABEL.missing_yellow} disabled={!canEdit} /> số bài đã tới hạn</>,
                  two: <>từ <Pct value={t.missing_red} onChange={setT("missing_red")} label={THRESHOLD_LABEL.missing_red} disabled={!canEdit} /></>, w: "assignment" },
              ]}
              columns={[
                { title: "Tiêu chí", dataIndex: "name", width: 130 },
                { title: "Cần lưu ý (1 điểm)", dataIndex: "one" },
                { title: "Nguy cơ cao (2 điểm)", dataIndex: "two" },
                { title: "Trọng số", dataIndex: "w", align: "right",
                  render: (k) => <InputNumber size="small" min={0} max={100} value={toPct(params.weights[k])} onChange={setW(k)}
                    suffix="%" style={{ width: 96 }} disabled={!canEdit} aria-label={`Trọng số ${WEIGHT_LABEL[k]}`} /> },
              ]} />
            <div className="weight-bar" aria-hidden>
              {["attendance", "inactivity", "assignment"].map((k, i) => (
                <span key={k} style={{ width: `${toPct(params.weights[k])}%`, background: [SERIES.blue, SERIES.orange, SERIES.aqua][i] }} />
              ))}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Tổng trọng số {toPct(weightSum)}% (phải bằng 100%). Mỗi trọng số {toPct(data.bounds.weight[0])}–{toPct(data.bounds.weight[1])}%.
              Luật xếp mức chung của trường giữ nguyên để mức rủi ro so sánh được giữa các môn.
            </div>
          </Card>

          <Card title="Luật bổ sung của môn" extra={canEdit && (
            <Button size="small" disabled={params.extra_rules.length >= data.bounds.max_extra_rules}
              onClick={() => edit((p) => { p.extra_rules.push({ type: "consecutive_missing", count: 2, level: "RED" }); return p; })}>
              Thêm luật</Button>
          )}>
            {params.extra_rules.length ? params.extra_rules.map((r, i) => {
              const spec = data.bounds.extra_rule_types[r.type];
              const setR = (patch) => edit((p) => { p.extra_rules[i] = { ...p.extra_rules[i], ...patch }; return p; });
              return (
                <div className="rule-row" key={i}>
                  <Select size="small" value={r.type} disabled={!canEdit} style={{ width: 190 }} aria-label="Loại luật"
                    onChange={(type) => {
                      const next = data.bounds.extra_rule_types[type];
                      edit((p) => { p.extra_rules[i] = { type, level: p.extra_rules[i].level, [next.field]: next.min }; return p; });
                    }}
                    options={Object.keys(data.bounds.extra_rule_types).map((k) => ({ value: k, label: EXTRA_LABEL[k] }))} />
                  <span>từ</span>
                  <InputNumber size="small" min={spec.min} max={spec.max} value={r[spec.field]} disabled={!canEdit}
                    onChange={(v) => setR({ [spec.field]: v ?? spec.min })} suffix={EXTRA_UNIT[r.type]} style={{ width: 110 }}
                    aria-label={`Giá trị luật bổ sung ${i + 1}`} />
                  {r.type === "absent_sessions" && (
                    <Select size="small" style={{ width: 220 }} disabled={!canEdit} aria-label="Hoạt động điểm danh"
                      value={r.attendance_id ?? (r.attendance_name ? `name:${r.attendance_name}` : "all")}
                      onChange={(v) => setR(v === "all" ? { attendance_id: undefined, attendance_name: undefined }
                        : String(v).startsWith("name:") ? { attendance_id: undefined, attendance_name: v.slice(5) }
                          : { attendance_id: v, attendance_name: undefined })}
                      options={[{ value: "all", label: "mọi hoạt động điểm danh" },
                        ...activities.map((a) => ({ value: a.attendance_id, label: `${a.name} (${a.sessions} buổi)` })),
                        ...(r.attendance_name ? [{ value: `name:${r.attendance_name}`, label: `hoạt động có tên chứa “${r.attendance_name}”` }] : [])]} />
                  )}
                  <span>→</span>
                  <Select size="small" value={r.level} disabled={!canEdit} style={{ width: 130 }} aria-label="Mức"
                    onChange={(level) => setR({ level })}
                    options={[{ value: "RED", label: RISK.RED.label }, { value: "YELLOW", label: RISK.YELLOW.label }]} />
                  {canEdit && <Button size="small" type="link" danger onClick={() => edit((p) => { p.extra_rules.splice(i, 1); return p; })}>Xóa</Button>}
                </div>
              );
            }) : <span className="muted">Không có luật bổ sung.</span>}
            <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>Luật bổ sung chỉ nâng mức rủi ro, không hạ, và không đổi điểm 0–100.</div>
          </Card>
        </Space>
      </Col>

      <Col xs={24} xl={10}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Card title="Tác động nếu áp dụng">
            {errors.length > 0 && <Alert type="error" style={{ marginBottom: 12 }} message="Chưa hợp lệ"
              description={<ul style={{ margin: 0, paddingLeft: 18 }}>{errors.map((e) => <li key={e}>{e}</li>)}</ul>} />}
            {preview.isPending && !pv && <Skeleton active />}
            {preview.error && <Alert type="error" message={errorText(preview.error)} />}
            {pv && (
              <div className={preview.isPending ? "is-fetching" : undefined}>
                {[["Hiện tại", pv.before], ["Sau thay đổi", pv.after]].map(([label, c]) => (
                  <div className="impact-row" key={label}>
                    <span>{label}</span><Stack counts={c} total={pv.total} />
                    <span className="tabular small">{fmtInt(c.RED)} đỏ · {fmtInt(c.YELLOW)} vàng</span>
                  </div>
                ))}
                <div className="muted" style={{ margin: "10px 0 6px" }}>{fmtInt(pv.changed)} sinh viên đổi mức</div>
                <Table size="small" rowKey="user_id" dataSource={pv.changes} pagination={{ pageSize: 8, size: "small" }}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Không ai đổi mức" /> }}
                  columns={[
                    { title: "MSSV", dataIndex: "student_code" },
                    { title: "Họ tên", dataIndex: "student_name" },
                    { title: "Từ → sang", render: (_, r) => <Space size={4}><RiskBadge level={r.from_level} compact />→<RiskBadge level={r.to_level} compact /></Space> },
                    { title: "Do", dataIndex: "reasons", render: (v) => <span className="small">{v.slice(0, 2).join("; ")}</span> },
                  ]} />
              </div>
            )}
            {canEdit && (
              <>
                <div className="muted small" style={{ marginTop: 8 }}>Lý do thay đổi (lưu vào lịch sử)</div>
                <Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500}
                  placeholder="vd: Môn đồ án nộp báo cáo tiến độ hằng tuần" />
                <Space style={{ marginTop: 12 }} wrap>
                  <Button type="primary" onClick={onSave} loading={save.isPending} disabled={errors.length > 0}>Lưu và áp dụng</Button>
                  {data.active.scope === "COURSE" && (
                    <Popconfirm title="Khôi phục luật mặc định của trường cho môn này?" okText="Khôi phục" cancelText="Hủy" onConfirm={onReset}>
                      <Button loading={reset.isPending}>Khôi phục mặc định</Button>
                    </Popconfirm>
                  )}
                </Space>
                <div className="muted small" style={{ marginTop: 8 }}>
                  Áp dụng ngay cho số liệu hôm nay; các ngày trước giữ luật cũ (đồ thị xu hướng có vạch đánh dấu ngày đổi luật).
                </div>
              </>
            )}
          </Card>

          <Card title="Lịch sử phiên bản">
            <Table size="small" rowKey="rule_set_id" pagination={{ pageSize: 6, size: "small" }} dataSource={data.history}
              columns={[
                { title: "Phiên bản", render: (_, r) => <>{r.scope === "COURSE" ? `Riêng ${r.label}` : `Mặc định ${r.label}`}{r.is_active && r.rule_set_id === data.active.rule_set_id && <Tag color="green" style={{ marginLeft: 6 }}>đang dùng</Tag>}</> },
                { title: "Người đặt", dataIndex: "created_by_name", render: (v) => v ?? "Hệ thống" },
                { title: "Thời điểm", dataIndex: "created_at", render: fmtDateTime },
                { title: "Ghi chú", dataIndex: "note", render: (v) => <span className="small">{v}</span> },
              ]} />
          </Card>
        </Space>
      </Col>
    </Row>
  );
}
