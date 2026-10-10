// Tiện ích dùng chung cho các bản phác thảo (mockup) – cùng màu với frontend/src/theme/tokens.js
const RISK = {
  RED: { color: "#D64545", tint: "#FBEAEA", icon: "●", label: "Nguy cơ cao" },
  YELLOW: { color: "#E0A100", tint: "#FDF3D8", icon: "▲", label: "Cần lưu ý" },
  GREEN: { color: "#2E9D5B", tint: "#E3F3EA", icon: "✔", label: "An toàn" },
};
const BLUE = "#2a78d6", NEUTRAL = "#c9c8c0", INK = "#1f2937", MUTED = "#6b6a65", GRID = "#e1e0d9";
Chart.defaults.font.family = 'system-ui, "Segoe UI", Roboto, Arial, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = MUTED;
Chart.defaults.animation = false;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.boxHeight = 12;
Chart.defaults.maintainAspectRatio = false;
const ax = (o = {}) => ({ grid: { color: GRID }, border: { color: "#c3c2b7" }, ...o });
const pct = (v) => `${v.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;

// Vẽ nhãn giá trị trên đầu cột (chọn lọc)
const topLabels = {
  id: "topLabels",
  afterDatasetsDraw(chart, _, opts) {
    if (!opts || !opts.enabled) return;
    const { ctx } = chart;
    const meta = chart.getDatasetMeta(opts.dataset ?? 0);
    ctx.save();
    ctx.fillStyle = INK;
    ctx.font = "600 11px system-ui, Segoe UI, Arial";
    ctx.textAlign = opts.horizontal ? "left" : "center";
    meta.data.forEach((el, i) => {
      const v = chart.data.datasets[opts.dataset ?? 0].data[i];
      const t = opts.format ? opts.format(v, i) : v;
      if (opts.horizontal) ctx.fillText(t, el.x + 6, el.y + 4);
      else ctx.fillText(t, el.x, el.y - 6);
    });
    ctx.restore();
  },
};
// Đường tham chiếu ngang/dọc (trung bình)
const refLine = {
  id: "refLine",
  afterDatasetsDraw(chart, _, opts) {
    if (!opts || opts.value == null) return;
    const { ctx, chartArea: a } = chart;
    ctx.save();
    ctx.strokeStyle = "#52514e";
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.5;
    ctx.fillStyle = "#52514e";
    ctx.font = "11px system-ui, Segoe UI, Arial";
    if (opts.horizontal) {
      const x = chart.scales.x.getPixelForValue(opts.value);
      ctx.beginPath(); ctx.moveTo(x, a.top); ctx.lineTo(x, a.bottom); ctx.stroke();
      ctx.textAlign = "center"; ctx.fillText(opts.label, x, a.top - 5);
    } else {
      const y = chart.scales.y.getPixelForValue(opts.value);
      ctx.beginPath(); ctx.moveTo(a.left, y); ctx.lineTo(a.right, y); ctx.stroke();
      ctx.setLineDash([]); ctx.textAlign = "left"; ctx.fillText("- - " + opts.label, a.left + 2, a.top - 6);
    }
    ctx.restore();
  },
};
// Nhãn cuối đường (direct label)
const endLabels = {
  id: "endLabels",
  afterDatasetsDraw(chart, _, opts) {
    if (!opts || !opts.enabled) return;
    const { ctx } = chart;
    ctx.save();
    ctx.font = "600 11px system-ui, Segoe UI, Arial";
    ctx.fillStyle = INK;
    ctx.textAlign = "left";
    const items = chart.data.datasets.map((ds, i) => {
      const meta = chart.getDatasetMeta(i);
      const last = meta.data[meta.data.length - 1];
      return { x: last.x + 8, y: last.y + 4, t: `${ds.short ?? ds.label} ${pct(ds.data[ds.data.length - 1])}` };
    }).sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) if (items[i].y - items[i - 1].y < 14) items[i].y = items[i - 1].y + 14;
    items.forEach((it) => ctx.fillText(it.t, it.x, it.y));
    ctx.restore();
  },
};

function riskLegend(el, counts, total) {
  el.innerHTML = ["RED", "YELLOW", "GREEN"].map((k, i) => `
    <div class="lg-row"><span><span class="sw" style="background:${RISK[k].color}"></span>${RISK[k].label}</span>
    <span class="tab"><b>${counts[i].toLocaleString("vi-VN")}</b> <span class="muted">(${pct(100 * counts[i] / total)})</span></span></div>`).join("");
}

function doughnut(id, counts, centerTop, centerBottom) {
  new Chart(document.getElementById(id), {
    type: "doughnut",
    data: { labels: ["Nguy cơ cao", "Cần lưu ý", "An toàn"], datasets: [{ data: counts, backgroundColor: [RISK.RED.color, RISK.YELLOW.color, RISK.GREEN.color], borderColor: "#fff", borderWidth: 2 }] },
    options: { cutout: "62%", plugins: { legend: { display: false }, tooltip: { enabled: false } } },
  });
  const c = document.getElementById(id).parentElement.querySelector(".center");
  if (c) c.innerHTML = `<div><div class="big">${centerTop}</div><div class="muted small">${centerBottom}</div></div>`;
}

function riskTrend(id, labels, red, yellow, green, opts = {}) {
  const ds = [
    ["Nguy cơ cao", "Đỏ", red, RISK.RED.color, []],
    ["Cần lưu ý", "Vàng", yellow, RISK.YELLOW.color, [6, 4]],
    ["An toàn", "Xanh", green, RISK.GREEN.color, [2, 3]],
  ].map(([label, short, data, color, dash]) => ({
    label, short, data, borderColor: color, backgroundColor: color, borderDash: dash,
    borderWidth: 2, pointRadius: 3.5, pointBackgroundColor: color, pointBorderColor: "#fff", pointBorderWidth: 1.5, tension: 0.25,
  }));
  new Chart(document.getElementById(id), {
    type: "line",
    data: { labels, datasets: ds },
    options: {
      layout: { padding: { right: 86 } },
      plugins: {
        legend: { position: "top", align: "start", labels: { boxWidth: 18, boxHeight: 3 } },
        endLabels: { enabled: true },
        refLine: opts.ruleChangeAt ? undefined : undefined,
      },
      scales: { x: ax({ grid: { display: false } }), y: ax({ min: 0, max: opts.max ?? 100, ticks: { callback: (v) => `${v}%` } }) },
    },
    plugins: [endLabels],
  });
}
