/**
 * Góp ý 2 – Đồ thị xu hướng mức rủi ro: 3 đường % Đỏ/Vàng/Xanh theo tuần học (hoặc theo ngày), chốt tại ngày cuối
 * mỗi tuần. Nhãn giá trị ở cuối đường (không chồng nhau), tooltip đủ 3 mức + số tuyệt đối, vạch dọc mảnh tại ngày
 * luật cảnh báo đổi (để không hiểu nhầm thay đổi do luật là thay đổi thật).
 */
import { useMemo } from "react";
import { Line } from "react-chartjs-2";
import { CHROME, RISK, RISK_LEVELS } from "../theme/tokens.js";
import { fmtDate, fmtInt, fmtPercent } from "../utils/format.js";
import { axis, crosshair } from "./setup.js";

const DASH = { RED: [], YELLOW: [6, 4], GREEN: [2, 3] };
const RATE_KEY = { RED: "red_rate", YELLOW: "yellow_rate", GREEN: "green_rate" };
const COUNT_KEY = { RED: "red", YELLOW: "yellow", GREEN: "green" };

/** Nhãn cuối đường: "Đỏ 14,0%", dời xuống nếu chồng nhau. */
const endLabels = {
  id: "riskEndLabels",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const items = chart.data.datasets.map((ds, i) => {
      const meta = chart.getDatasetMeta(i);
      let idx = ds.data.length - 1;
      while (idx >= 0 && ds.data[idx] == null) idx -= 1;
      if (idx < 0 || meta.hidden) return null;
      const el = meta.data[idx];
      return { x: el.x + 8, y: el.y + 4, text: `${ds.short} ${fmtPercent(ds.data[idx], 1)}` };
    }).filter(Boolean).sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i += 1) {
      if (items[i].y - items[i - 1].y < 14) items[i].y = items[i - 1].y + 14;
    }
    ctx.save();
    ctx.font = "600 11px system-ui, Segoe UI, Arial";
    ctx.fillStyle = CHROME.ink;
    items.forEach((it) => ctx.fillText(it.text, it.x, it.y));
    ctx.restore();
  },
};

/** Vạch dọc nét đứt tại kỳ có đổi luật. */
const ruleMarks = {
  id: "ruleMarks",
  afterDatasetsDraw(chart, _, opts) {
    const marks = opts?.indexes ?? [];
    if (!marks.length) return;
    const { ctx, chartArea: a, scales } = chart;
    ctx.save();
    ctx.strokeStyle = CHROME.secondary;
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1;
    ctx.font = "11px system-ui, Segoe UI, Arial";
    ctx.fillStyle = CHROME.secondary;
    marks.forEach((i) => {
      const x = scales.x.getPixelForValue(i);
      ctx.beginPath();
      ctx.moveTo(x, a.top);
      ctx.lineTo(x, a.bottom);
      ctx.stroke();
      ctx.fillText("đổi luật", x + 3, a.top + 10);
    });
    ctx.restore();
  },
};

export default function RiskTrendChart({ series, ruleChanges = [], granularity = "week" }) {
  const { data, options, plugins } = useMemo(() => {
    const changeIdx = [...new Set(ruleChanges.map((c) => series.findIndex(
      (p) => c.date >= p.period_start && c.date <= p.period_end)).filter((i) => i >= 0))];
    return {
      data: {
        labels: series.map((p) => p.period),
        datasets: RISK_LEVELS.map((lv) => ({
          label: RISK[lv].label, short: RISK[lv].short,
          data: series.map((p) => (p[RATE_KEY[lv]] == null ? null : Number(p[RATE_KEY[lv]]))),
          borderColor: RISK[lv].color, backgroundColor: RISK[lv].color, borderDash: DASH[lv],
          pointRadius: granularity === "week" ? 3 : 0, pointBackgroundColor: RISK[lv].color,
          pointBorderColor: "#fff", pointBorderWidth: 1.5, tension: 0.25, spanGaps: false,
        })),
      },
      options: {
        layout: { padding: { right: 78, top: 4 } },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top", align: "start", labels: { usePointStyle: false, boxWidth: 18, boxHeight: 3 } },
          ruleMarks: { indexes: changeIdx },
          tooltip: {
            callbacks: {
              title: (ctx) => {
                const p = series[ctx[0].dataIndex];
                return granularity === "week" ? `Tuần ${p.period.replace("T", "")} (${fmtDate(p.period_start)} – ${fmtDate(p.period_end)}) · số liệu ngày ${fmtDate(p.stat_date)}`
                  : fmtDate(p.stat_date);
              },
              label: (ctx) => {
                const p = series[ctx.dataIndex];
                const lv = RISK_LEVELS[ctx.datasetIndex];
                return ` ${RISK[lv].label}: ${fmtPercent(ctx.raw, 1)} (${fmtInt(p[COUNT_KEY[lv]])}/${fmtInt(p.total)})`;
              },
              footer: (ctx) => {
                const p = series[ctx[0].dataIndex];
                const changes = ruleChanges.filter((c) => c.date >= p.period_start && c.date <= p.period_end);
                return changes.length ? ["Đổi luật:", ...changes.slice(0, 4).map((c) => `${fmtDate(c.date)} ${c.label}`)] : [];
              },
            },
          },
        },
        scales: {
          x: axis({ grid: { display: false }, ticks: { maxTicksLimit: 16, maxRotation: 0 } }),
          y: axis({ min: 0, max: 100, ticks: { callback: (v) => `${v}%`, stepSize: 20 } }),
        },
      },
      plugins: [crosshair, endLabels, ruleMarks],
    };
  }, [series, ruleChanges, granularity]);

  return <Line data={data} options={options} plugins={plugins} role="img"
    aria-label="Đồ thị xu hướng tỷ lệ sinh viên theo mức rủi ro" />;
}

export const trendTableColumns = [
  { title: "Kỳ", dataIndex: "period" },
  { title: "Ngày số liệu", dataIndex: "stat_date", render: fmtDate },
  { title: "Nguy cơ cao", dataIndex: "red_rate", align: "right", render: (v, r) => `${fmtPercent(v, 1, "–")} (${fmtInt(r.red)})` },
  { title: "Cần lưu ý", dataIndex: "yellow_rate", align: "right", render: (v, r) => `${fmtPercent(v, 1, "–")} (${fmtInt(r.yellow)})` },
  { title: "An toàn", dataIndex: "green_rate", align: "right", render: (v, r) => `${fmtPercent(v, 1, "–")} (${fmtInt(r.green)})` },
  { title: "Tổng", dataIndex: "total", align: "right", render: fmtInt },
];
