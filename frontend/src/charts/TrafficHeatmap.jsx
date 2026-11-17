/**
 * Admin 1.2 – Heatmap giờ × thứ (chartjs-chart-matrix): thang tuần tự một màu xanh, nhạt = ít, đậm = nhiều.
 * Mục đích: quản trị viên thấy khung giờ đông người (cần tăng giám sát) và khung giờ vắng (nên bảo trì).
 * Mặc định tô theo số người đang online trung bình trong giờ; đổi được sang số người truy cập trong giờ hoặc số lượt
 * hoạt động. Dữ liệu ước tính từ nhật ký Moodle (mdl_logstore_standard_log) – xem HEATMAP_SCOPE_NOTE.
 */
import { useMemo } from "react";
import { Chart } from "react-chartjs-2";
import { CHROME, SEQUENTIAL_BLUE } from "../theme/tokens.js";
import { DOW_LABELS, fmtDecimal, fmtInt } from "../utils/format.js";

const HOURS = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, "0"));
const DAYS = DOW_LABELS.slice(1);

export const HEATMAP_METRICS = {
  online: { key: "avg_online_users", label: "Người online TB", unit: "người online", digits: 1 },
  visitors: { key: "avg_unique_users", label: "Người truy cập trong giờ", unit: "người truy cập", digits: 0 },
  events: { key: "avg_requests", label: "Lượt hoạt động", unit: "lượt hoạt động", digits: 0 },
};

export const HEATMAP_SCOPE_NOTE = "Màu càng đậm càng đông. Số người online ước tính từ nhật ký hoạt động trong các môn học.";

const fmt = (v, digits) => (digits ? fmtDecimal(v, digits) : fmtInt(v));

export default function TrafficHeatmap({ matrix, metric = "online" }) {
  const m = HEATMAP_METRICS[metric] ?? HEATMAP_METRICS.online;
  const { data, options, min, max } = useMemo(() => {
    const values = matrix.map((c) => Number(c[m.key] ?? 0));
    const lo = values.length ? Math.min(...values) : 0;
    const hi = values.length ? Math.max(...values) : 0;
    const colorOf = (v) => {
      if (hi === lo) return SEQUENTIAL_BLUE[6];
      const step = Math.floor(((v - lo) / (hi - lo)) * (SEQUENTIAL_BLUE.length - 1));
      return SEQUENTIAL_BLUE[Math.max(0, Math.min(SEQUENTIAL_BLUE.length - 1, step))];
    };
    return {
      min: lo,
      max: hi,
      data: {
        datasets: [{
          label: m.label,
          data: matrix.map((c) => ({ x: HOURS[c.hour_of_day], y: DAYS[c.day_of_week - 1], v: Number(c[m.key] ?? 0), cell: c })),
          backgroundColor: (ctx) => colorOf(ctx.raw?.v ?? lo),
          borderColor: CHROME.surface,
          borderWidth: 1,
          hoverBorderColor: CHROME.ink,
          hoverBorderWidth: 2,
          width: ({ chart }) => Math.max(0, (chart.chartArea?.width ?? 0) / 24 - 2),
          height: ({ chart }) => Math.max(0, (chart.chartArea?.height ?? 0) / 7 - 2),
        }],
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => `${items[0].raw.y}, ${items[0].raw.x}:00 – ${items[0].raw.x}:59`,
              label: (item) => ` Trung bình ${fmtDecimal(item.raw.cell.avg_online_users, 1)} người online`,
            },
          },
        },
        scales: {
          x: {
            type: "category", labels: HOURS, offset: true, grid: { display: false }, border: { display: false },
            ticks: { color: CHROME.muted, maxRotation: 0, autoSkip: false, callback: (_, i) => (i % 2 === 0 ? `${HOURS[i]}h` : "") },
          },
          y: { type: "category", labels: DAYS, offset: true, grid: { display: false }, border: { display: false }, ticks: { color: CHROME.secondary } },
        },
      },
    };
  }, [matrix, m]);

  return (
    <>
      <div className="chart-box" style={{ height: 300 }}>
        <Chart type="matrix" data={data} options={options} role="img" aria-label={`Heatmap ${m.label.toLowerCase()} theo giờ và thứ`} />
      </div>
      <div className="heat-scale" style={{ marginTop: 8 }}>
        <span>Vắng ({fmt(min, m.digits)})</span>
        <span className="heat-scale-bar" style={{ background: `linear-gradient(90deg, ${SEQUENTIAL_BLUE.join(", ")})` }} />
        <span>Đông ({fmt(max, m.digits)} {m.unit} TB)</span>
      </div>
    </>
  );
}

const span = (day, start, hours) => `${DAYS[day - 1]} ${HOURS[start]}:00–${HOURS[(start + hours) % 24]}:00`;

/**
 * Gợi ý vận hành từ ma trận heatmap (theo số người online trung bình):
 *   quiet – các khung `hours` giờ liền nhau vắng nhất (bảo trì), mỗi thứ tối đa một khung, không chồng lên nhau;
 *   busy  – các giờ đông nhất (tăng giám sát), kèm đỉnh online cao nhất từng gặp.
 */
export function operationHints(matrix, { hours = 3, top = 3 } = {}) {
  if (!matrix?.length) return { quiet: [], busy: [] };
  const cell = new Map(matrix.map((c) => [`${c.day_of_week}-${c.hour_of_day}`, c]));
  const at = (d, h) => cell.get(`${d}-${h}`);
  const windows = [];
  for (let d = 1; d <= 7; d += 1) {
    for (let h = 0; h + hours <= 24; h += 1) {
      const cells = Array.from({ length: hours }, (_, i) => at(d, h + i));
      if (cells.some((c) => !c)) continue;
      const avg = cells.reduce((s, c) => s + Number(c.avg_online_users), 0) / hours;
      const peak = Math.max(...cells.map((c) => Number(c.max_peak_online)));
      windows.push({ day: d, start: h, avg, peak, label: span(d, h, hours) });
    }
  }
  const byDay = new Map();
  windows.sort((a, b) => a.avg - b.avg || a.peak - b.peak).forEach((w) => { if (!byDay.has(w.day)) byDay.set(w.day, w); });
  const quiet = [...byDay.values()].sort((a, b) => a.avg - b.avg || a.peak - b.peak).slice(0, top);
  const busy = [...matrix].sort((a, b) => Number(b.avg_online_users) - Number(a.avg_online_users)).slice(0, top)
    .map((c) => ({ day: c.day_of_week, start: c.hour_of_day, avg: Number(c.avg_online_users),
      peak: Number(c.max_peak_online), label: span(c.day_of_week, c.hour_of_day, 1) }));
  return { quiet, busy };
}

/** Một dòng tóm tắt: giờ đông nhất và khung giờ vắng nhất (đủ để chọn giờ giám sát / bảo trì). */
export function OperationHints({ matrix }) {
  const { quiet, busy } = useMemo(() => operationHints(matrix, { top: 1 }), [matrix]);
  if (!quiet.length || !busy.length) return null;
  return (
    <div style={{ marginTop: 10 }}>
      Đông nhất: <b>{busy[0].label}</b> · Vắng nhất: <b>{quiet[0].label}</b>
    </div>
  );
}

export const heatmapTableColumns = [
  { title: "Thứ", dataIndex: "day_of_week", render: (d) => DAYS[d - 1], sorter: (a, b) => a.day_of_week - b.day_of_week },
  { title: "Giờ", dataIndex: "hour_of_day", render: (h) => `${HOURS[h]}:00`, sorter: (a, b) => a.hour_of_day - b.hour_of_day },
  { title: "Online TB", dataIndex: "avg_online_users", align: "right", render: (v) => fmtDecimal(v, 1), defaultSortOrder: "descend",
    sorter: (a, b) => a.avg_online_users - b.avg_online_users },
  { title: "Online cao nhất", dataIndex: "max_peak_online", align: "right", render: fmtInt, sorter: (a, b) => a.max_peak_online - b.max_peak_online },
  { title: "Người truy cập TB", dataIndex: "avg_unique_users", align: "right", render: fmtInt, sorter: (a, b) => a.avg_unique_users - b.avg_unique_users },
  { title: "Lượt hoạt động TB", dataIndex: "avg_requests", align: "right", render: fmtInt, sorter: (a, b) => a.avg_requests - b.avg_requests },
  { title: "% ngày là giờ cao điểm", dataIndex: "peak_share", align: "right", render: (v) => `${fmtDecimal(v, 0)}%` },
];


/** Dòng phụ đề "Trung bình dd/mm – dd/mm/yyyy"; nhật ký bắt đầu muộn hơn đầu khoảng đã chọn thì nói rõ. */
export function heatmapRange(data, dayjs) {
  if (!data) return undefined;
  const range = `Trung bình ${dayjs(data.from_date).format("DD/MM")} – ${dayjs(data.to_date).format("DD/MM/YYYY")}`;
  return data.limited ? `${range} · nhật ký chỉ có từ ${dayjs(data.from_date).format("DD/MM/YYYY")}, chưa đủ ${data.weeks} tuần` : range;
}
