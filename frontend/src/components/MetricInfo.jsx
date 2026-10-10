/**
 * Góp ý 4 – minh bạch nguồn dữ liệu và cách tính: liên kết "Nguồn & cách tính" mở ngăn bên phải gồm
 * (1) ý nghĩa, công thức, bảng Moodle nguồn, bảng phân tích, job ETL của chỉ số; (2) luật cảnh báo đang áp dụng
 * cho ĐÚNG phạm vi (môn có luật riêng thì hiện luật riêng); (3) dữ liệu đi qua những bước nào; (4) độ mới số liệu.
 * Mọi nội dung đọc từ API /meta/* – giao diện không tự viết công thức hay ngưỡng.
 *
 * metric: "risk_level" | ["risk_level", "risk_trend"] | { keys, courseId, note }
 *   note: ghi chú phạm vi (vd cấp Khoa: "3/12 môn của khoa dùng luật riêng") – để người xem biết khi so sánh (Mục 4.7).
 */
import { Alert, Button, Descriptions, Divider, Drawer, Skeleton, Table, Tag } from "antd";
import { useState } from "react";
import { useFreshness, useMetaMetrics, useRiskRule } from "../api/hooks.js";
import { RISK } from "../theme/tokens.js";
import { fmtDate, fmtDateTime } from "../utils/format.js";

const RISK_KEYS = new Set(["risk_level", "risk_score", "c1_attendance", "c2_inactivity", "c3_assignment", "risk_trend",
  "max_consecutive_missing"]);
const JOB_LABEL = {
  traffic: "Lưu lượng (5 phút)", course_progress: "Tiến độ môn (mỗi giờ)", student_risk: "Cảnh báo (2 giờ)",
  nightly: "Chốt số liệu đêm", maintenance: "Bảo trì tuần", backfill: "Nạp lịch sử",
  auto_prompt: "Nhắc tự động", message_dispatch: "Gửi tin",
};

const pct = (v) => `${Math.round(Number(v) * 1000) / 10}%`;

function normalize(metric) {
  if (typeof metric === "string") return { keys: [metric], courseId: undefined, note: undefined };
  if (Array.isArray(metric)) return { keys: metric, courseId: undefined, note: undefined };
  return { keys: metric.keys ?? [metric.key], courseId: metric.courseId, note: metric.note };
}

export function RuleTable({ rule }) {
  const t = rule.thresholds;
  const w = rule.weights;
  const rows = [
    { key: "c1", name: "C1 – Vắng học", one: `vắng từ ${pct(t.absence_yellow)} số buổi`, two: `từ ${pct(t.absence_red)}`,
      weight: pct(w.attendance) },
    { key: "c2", name: "C2 – Không tương tác",
      one: `quá ${t.inactive_yellow_days} ngày chưa vào, hoặc truy cập 14 ngày dưới ${pct(t.low_access_ratio)} trung vị lớp`,
      two: `quá ${t.inactive_red_days} ngày hoặc chưa từng vào`, weight: pct(w.inactivity) },
    { key: "c3", name: "C3 – Thiếu bài tập", one: `thiếu từ ${pct(t.missing_yellow)} số bài đã tới hạn`,
      two: `từ ${pct(t.missing_red)}`, weight: pct(w.assignment) },
  ];
  return (
    <Table size="small" pagination={false} rowKey="key" dataSource={rows}
      columns={[
        { title: "Tiêu chí", dataIndex: "name" },
        { title: "1 điểm", dataIndex: "one" },
        { title: "2 điểm", dataIndex: "two" },
        { title: "Trọng số", dataIndex: "weight", align: "right" },
      ]} />
  );
}

export function LevelRules({ rule }) {
  const lr = rule.level_rules;
  return (
    <ul style={{ paddingLeft: 18, margin: "8px 0" }}>
      <li><b style={{ color: RISK.RED.ink }}>Nguy cơ cao</b> khi
        {lr.red_if_inactivity_red ? " C2 = 2, hoặc" : ""} có từ {lr.red_min_red_criteria} tiêu chí đạt 2 điểm, hoặc tổng điểm
        từ {lr.red_min_total}{rule.extra_rules?.length ? ", hoặc khớp một luật bổ sung mức đỏ của môn" : ""}</li>
      <li><b style={{ color: RISK.YELLOW.ink }}>Cần lưu ý</b> khi tổng điểm từ 1 và không thuộc mức đỏ</li>
      <li><b style={{ color: RISK.GREEN.ink }}>An toàn</b> khi tổng điểm bằng 0</li>
    </ul>
  );
}

function MetricDrawer({ keys, courseId, note, onClose }) {
  const metrics = useMetaMetrics();
  const needsRule = keys.some((k) => RISK_KEYS.has(k));
  const rule = useRiskRule(courseId, needsRule);
  const fresh = useFreshness();
  const items = (metrics.data?.items ?? []).filter((m) => keys.includes(m.key));
  const r = rule.data;

  return (
    <Drawer open width={640} onClose={onClose} title="Nguồn dữ liệu & cách tính" destroyOnHidden
      styles={{ body: { padding: 0, overflow: "hidden" } }}>
      {/* Vùng cuộn nhận được tiêu điểm: người dùng bàn phím cuộn bằng phím mũi tên (WCAG scrollable-region-focusable) */}
      <div className="drawer-scroll" tabIndex={0} role="region" aria-label="Nội dung nguồn dữ liệu và cách tính">
      {metrics.isLoading ? <Skeleton active /> : items.map((m) => (
        <div key={m.key} style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 4px" }}>{m.name}</h4>
          <div className="muted" style={{ marginBottom: 6 }}>{m.description}</div>
          <Descriptions size="small" column={1} bordered
            items={[
              { key: "f", label: "Công thức", children: m.formula },
              { key: "u", label: "Đơn vị", children: m.unit },
              { key: "s", label: "Bảng Moodle nguồn", children: m.moodle_tables.length
                ? m.moodle_tables.map((t) => <Tag key={t} style={{ fontFamily: "Consolas, monospace" }}>{t}</Tag>) : "tổng hợp từ các chỉ số trên" },
              { key: "a", label: "Bảng phân tích", children: <code>{m.analytics_table}</code> },
              { key: "j", label: "Job ETL", children: `${m.etl_job} – ${m.schedule}` },
            ]} />
        </div>
      ))}

      {needsRule && (
        <>
          <Divider orientation="left" plain>Luật cảnh báo đang áp dụng</Divider>
          {rule.isLoading || !r ? <Skeleton active /> : (
            <>
              <Alert type={r.scope === "COURSE" ? "warning" : "info"} style={{ marginBottom: 10 }}
                message={r.scope === "COURSE"
                  ? `Môn dùng luật riêng (${r.label}${r.preset !== "CUSTOM" ? ` – mẫu ${r.preset_name}` : ""}), khác luật mặc định của trường`
                  : `Luật mặc định của trường (${r.label})`}
                description={r.differs_from_default?.length
                  ? <ul style={{ margin: 0, paddingLeft: 18 }}>{r.differs_from_default.map((d) => <li key={d}>{d}</li>)}</ul>
                  : undefined} />
              {note && <Alert type="info" showIcon={false} style={{ marginBottom: 10 }} message={note} />}
              <RuleTable rule={r} />
              <div style={{ marginTop: 10 }}>Điểm rủi ro = <code>{r.score_formula}</code>, từ 0 đến 100.</div>
              <LevelRules rule={r} />
              {r.extra_rules?.length > 0 && (
                <div>Luật bổ sung của môn (chỉ nâng mức, không hạ):
                  <ul style={{ paddingLeft: 18, margin: "4px 0" }}>{r.extra_rules.map((x) => <li key={x.text}>{x.text}</li>)}</ul>
                </div>
              )}
            </>
          )}
        </>
      )}

      <Divider orientation="left" plain>Dữ liệu đi qua những bước nào</Divider>
      <ol style={{ paddingLeft: 18, margin: 0 }}>
        {(metrics.data?.pipeline ?? []).map((step) => <li key={step}>{step}</li>)}
      </ol>

      <Divider orientation="left" plain>Độ mới của số liệu</Divider>
      {fresh.data ? (
        <Descriptions size="small" column={1}
          items={[
            { key: "asof", label: "Thời điểm tham chiếu", children: `${fmtDateTime(fresh.data.as_of)}${fresh.data.clock_frozen ? " (dữ liệu demo)" : ""}` },
            { key: "snap", label: "Snapshot cảnh báo mới nhất", children: fmtDate(fresh.data.latest_snapshot_date) },
            ...fresh.data.jobs.map((j) => ({ key: j.job_name, label: JOB_LABEL[j.job_name] ?? j.job_name,
              children: j.last_success_at ? fmtDateTime(j.last_success_at) : "chưa chạy" })),
          ]} />
      ) : <Skeleton active paragraph={{ rows: 3 }} />}
      <div className="muted" style={{ marginTop: 12 }}>
        Mức rủi ro là tín hiệu để giảng viên chú ý, không phải kết luận về kết quả học tập của sinh viên.
      </div>
      </div>
    </Drawer>
  );
}

export default function MetricInfo({ metric, compact = false, label }) {
  const [open, setOpen] = useState(false);
  const { keys, courseId, note } = normalize(metric);
  return (
    <>
      <Button type="link" size="small" className={compact ? "info-link compact" : "info-link"}
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}>
        {label ?? (compact ? "Cách tính" : "Nguồn & cách tính")}
      </Button>
      {open && <MetricDrawer keys={keys} courseId={courseId} note={note} onClose={() => setOpen(false)} />}
    </>
  );
}
