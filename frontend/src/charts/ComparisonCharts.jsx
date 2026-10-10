/**
 * Góp ý 1 – Biểu đồ so sánh đặt cạnh bảng số:
 *   ComparisonColumns  một chỉ số theo từng mục (khoa / môn): cột dọc khi ít mục, thanh ngang khi nhiều mục hoặc tên dài,
 *                      đường tham chiếu (trung bình trường/khoa), nhãn giá trị ở đầu cột.
 *   VolumeColumns      quy mô: lượt ghi danh có / không tương tác (cột chồng).
 *   RiskShareBars      phân bố mức rủi ro 100% Đỏ/Vàng/Xanh theo từng mục.
 * Mọi cột cùng một màu (màu không dùng để phân biệt khoa/môn) nên số mục tăng bao nhiêu cũng không thiếu màu.
 * Trục luôn bắt đầu từ 0. Nhấn vào cột/thanh -> onSelect(item) (drill-down).
 * highlight(item) -> true: tô nổi mục đó, các mục khác nhạt đi (vd nhấn lát "Nguy cơ cao" của biểu đồ tròn toàn trường
 * -> nổi các khoa có tỷ lệ Nguy cơ cao trên trung bình – kế hoạch Mục 3.2); highlightNote: dòng giải thích trong tooltip.
 */
import { useMemo, useRef } from "react";
import { Bar, getElementAtEvent } from "react-chartjs-2";
import { CHROME, RISK, RISK_LEVELS, SERIES } from "../theme/tokens.js";
import { fmtInt, fmtPercent } from "../utils/format.js";
import { axis, vnNumber } from "./setup.js";

const AUTO_HORIZONTAL_ABOVE = 8;
const LINE_CHARS = 14;

/**
 * Nhãn trục của cột dọc: bỏ tiền tố "Khoa " lặp lại và ngắt thành nhiều dòng (~14 ký tự) để tên dài không đè nhau.
 * Tooltip vẫn hiện tên đầy đủ. Thanh ngang giữ nguyên tên (đủ chỗ).
 */
export function axisLabel(text, horizontal) {
  if (horizontal || text == null) return text;
  const words = String(text).replace(/^Khoa\s+/, "").split(/\s+/);
  const lines = [];
  for (const w of words) {
    const last = lines[lines.length - 1];
    if (last && (last + " " + w).length <= LINE_CHARS) lines[lines.length - 1] = `${last} ${w}`;
    else lines.push(w);
  }
  return lines.length > 1 ? lines : lines[0];
}

const fullTitle = (items, labelKey) => (ctx) => String(items[ctx[0].dataIndex]?.[labelKey] ?? "");

function isHorizontal(orientation, n) {
  return orientation === "horizontal" || (orientation === "auto" && n > AUTO_HORIZONTAL_ABOVE);
}

const valueLabels = {
  id: "valueLabels",
  afterDatasetsDraw(chart, _, opts) {
    if (!opts?.format) return;
    const { ctx } = chart;
    const meta = chart.getDatasetMeta(0);
    const values = chart.data.datasets[0].data;
    ctx.save();
    ctx.font = "600 11px system-ui, Segoe UI, Arial";
    ctx.fillStyle = CHROME.ink;
    meta.data.forEach((el, i) => {
      if (values[i] == null) return;
      const text = opts.format(values[i]);
      if (opts.horizontal) {
        ctx.textAlign = "left";
        ctx.fillText(text, el.x + 5, el.y + 4);
      } else {
        ctx.textAlign = "center";
        ctx.fillText(text, el.x, el.y - 6);
      }
    });
    ctx.restore();
  },
};

const referenceLine = {
  id: "referenceLine",
  afterDatasetsDraw(chart, _, opts) {
    if (opts?.value == null) return;
    const { ctx, chartArea: a, scales } = chart;
    ctx.save();
    ctx.strokeStyle = CHROME.secondary;
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (opts.horizontal) {
      const x = scales.x.getPixelForValue(opts.value);
      ctx.moveTo(x, a.top);
      ctx.lineTo(x, a.bottom);
    } else {
      const y = scales.y.getPixelForValue(opts.value);
      ctx.moveTo(a.left, y);
      ctx.lineTo(a.right, y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.font = "11px system-ui, Segoe UI, Arial";
    ctx.fillStyle = CHROME.secondary;
    ctx.textAlign = "left";
    ctx.fillText(`- - ${opts.label}`, a.left + 2, a.top - 22);     // hàng riêng phía trên nhãn giá trị của cột
    ctx.restore();
  },
};

/** Màu theo từng mục: mục không được tô nổi giảm độ đậm (alpha 25%). */
function colorsFor(items, color, highlight) {
  if (!highlight) return color;
  return items.map((i) => (highlight(i) ? color : `${color}40`));
}

function highlightFooter(items, highlight, note) {
  return (ctx) => (highlight && note && highlight(items[ctx[0].dataIndex]) ? note : "");
}

function useClick(items, onSelect) {
  const ref = useRef(null);
  const onClick = (event) => {
    if (!onSelect || !ref.current) return;
    const [el] = getElementAtEvent(ref.current, event);
    if (el) onSelect(items[el.index]);
  };
  return [ref, onClick];
}

export function ComparisonColumns({ items, labelKey, valueKey, label, format = (v) => fmtPercent(v, 1),
  max = 100, reference, orientation = "auto", onSelect, ariaLabel, highlight, highlightNote }) {
  const [ref, onClick] = useClick(items, onSelect);
  const horizontal = isHorizontal(orientation, items.length);
  const { data, options } = useMemo(() => ({
    data: {
      labels: items.map((i) => axisLabel(i[labelKey], horizontal)),
      datasets: [{
        label, data: items.map((i) => (i[valueKey] == null ? null : Number(i[valueKey]))),
        backgroundColor: colorsFor(items, SERIES.blue, highlight), borderRadius: 4, borderSkipped: "start",
        maxBarThickness: horizontal ? 18 : 40,
      }],
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      layout: { padding: { top: reference ? 34 : 16, right: horizontal ? 44 : 0 } },
      plugins: {
        legend: { display: false },
        valueLabels: { format, horizontal },
        referenceLine: reference ? { ...reference, horizontal } : undefined,
        tooltip: {
          callbacks: {
            title: fullTitle(items, labelKey),
            label: (ctx) => ` ${label}: ${ctx.raw == null ? "Chưa có dữ liệu" : format(ctx.raw)}`,
            afterBody: highlightFooter(items, highlight, highlightNote),
            footer: () => (onSelect ? "Nhấn để xem chi tiết" : ""),
          },
        },
      },
      scales: horizontal ? {
        x: axis({ min: 0, max, ticks: { callback: (v) => (max === 100 ? `${v}%` : vnNumber(v)) } }),
        y: axis({ grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false } }),
      } : {
        x: axis({ grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false, maxRotation: 0 } }),
        y: axis({ min: 0, max, ticks: { callback: (v) => (max === 100 ? `${v}%` : vnNumber(v)) } }),
      },
    },
  }), [items, labelKey, valueKey, label, format, max, reference, horizontal, onSelect, highlight, highlightNote]);
  return <Bar ref={ref} data={data} options={options} plugins={[valueLabels, referenceLine]} onClick={onClick}
    style={{ cursor: onSelect ? "pointer" : "default" }} role="img" aria-label={ariaLabel ?? label} />;
}

export function VolumeColumns({ items, labelKey, orientation = "auto", onSelect, highlight, highlightNote }) {
  const [ref, onClick] = useClick(items, onSelect);
  const horizontal = isHorizontal(orientation, items.length);
  const { data, options } = useMemo(() => ({
    data: {
      labels: items.map((i) => axisLabel(i[labelKey], horizontal)),
      datasets: [
        { label: "Có tương tác", data: items.map((i) => i.active), backgroundColor: colorsFor(items, SERIES.blue, highlight),
          borderColor: CHROME.surface, borderWidth: horizontal ? { right: 2 } : { top: 2 }, maxBarThickness: horizontal ? 18 : 40 },
        { label: "Không tương tác", data: items.map((i) => i.inactive), backgroundColor: colorsFor(items, CHROME.neutral, highlight),
          borderRadius: 4, borderSkipped: "start", maxBarThickness: horizontal ? 18 : 40 },
      ],
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", align: "start", labels: { usePointStyle: false, boxWidth: 12, boxHeight: 12 } },
        tooltip: {
          callbacks: {
            title: fullTitle(items, labelKey),
            label: (ctx) => ` ${ctx.dataset.label}: ${fmtInt(ctx.raw)} lượt`,
            footer: (ctx) => {
              const it = items[ctx[0].dataIndex];
              const note = highlightFooter(items, highlight, highlightNote)(ctx);
              return [`Tổng: ${fmtInt(it.enrolled)} lượt ghi danh${it.unique_students ? ` · ${fmtInt(it.unique_students)} sinh viên` : ""}`,
                ...(note ? [note] : [])];
            },
          },
        },
      },
      scales: horizontal ? {
        x: axis({ stacked: true, beginAtZero: true, ticks: { callback: vnNumber } }),
        y: axis({ stacked: true, grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false } }),
      } : {
        x: axis({ stacked: true, grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false, maxRotation: 0 } }),
        y: axis({ stacked: true, beginAtZero: true, ticks: { callback: vnNumber } }),
      },
    },
  }), [items, labelKey, horizontal, highlight, highlightNote]);
  return <Bar ref={ref} data={data} options={options} onClick={onClick} style={{ cursor: onSelect ? "pointer" : "default" }}
    role="img" aria-label="Biểu đồ quy mô lượt ghi danh có và không tương tác" />;
}

const RATE_KEY = { RED: "red_rate", YELLOW: "yellow_rate", GREEN: "green_rate" };
const COUNT_KEY = { RED: "red", YELLOW: "yellow", GREEN: "green" };

export function RiskShareBars({ items, labelKey, orientation = "auto", onSelect, countKeys = COUNT_KEY, highlight,
  highlightNote }) {
  const [ref, onClick] = useClick(items, onSelect);
  const horizontal = isHorizontal(orientation, items.length);
  const { data, options } = useMemo(() => ({
    data: {
      labels: items.map((i) => axisLabel(i[labelKey], horizontal)),
      datasets: RISK_LEVELS.map((lv, k) => ({
        label: RISK[lv].label,
        data: items.map((i) => (i[RATE_KEY[lv]] == null ? 0 : Number(i[RATE_KEY[lv]]))),
        backgroundColor: colorsFor(items, RISK[lv].color, highlight), maxBarThickness: horizontal ? 18 : 40,
        borderColor: CHROME.surface, borderWidth: k < 2 ? (horizontal ? { right: 2 } : { top: 2 }) : 0,
      })),
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", align: "start", labels: { usePointStyle: false, boxWidth: 12, boxHeight: 12 } },
        tooltip: {
          callbacks: {
            title: fullTitle(items, labelKey),
            label: (ctx) => {
              const it = items[ctx.dataIndex];
              const lv = RISK_LEVELS[ctx.datasetIndex];
              return ` ${RISK[lv].label}: ${fmtPercent(ctx.raw, 1)} (${fmtInt(it[countKeys[lv]])})`;
            },
            afterBody: highlightFooter(items, highlight, highlightNote),
            footer: () => (onSelect ? "Nhấn để xem chi tiết" : ""),
          },
        },
      },
      scales: horizontal ? {
        x: axis({ stacked: true, min: 0, max: 100, ticks: { callback: (v) => `${v}%` } }),
        y: axis({ stacked: true, grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false } }),
      } : {
        x: axis({ stacked: true, grid: { display: false }, ticks: { color: CHROME.ink, autoSkip: false, maxRotation: 0 } }),
        y: axis({ stacked: true, min: 0, max: 100, ticks: { callback: (v) => `${v}%` } }),
      },
    },
  }), [items, labelKey, horizontal, onSelect, countKeys, highlight, highlightNote]);
  return <Bar ref={ref} data={data} options={options} onClick={onClick} style={{ cursor: onSelect ? "pointer" : "default" }}
    role="img" aria-label="Biểu đồ phân bố mức rủi ro" />;
}

/** Chiều cao hợp lý cho biểu đồ (thanh ngang cần cao theo số mục). */
export function chartHeight(n, orientation = "auto", base = 240) {
  return isHorizontal(orientation, n) ? Math.max(base, n * 26 + 70) : base;
}
