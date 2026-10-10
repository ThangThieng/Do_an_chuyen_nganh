/**
 * Biểu đồ tròn tỷ lệ rủi ro (giữ nguyên theo góp ý 2 – cô đánh giá cao); nhấn lát cắt hoặc dòng chú thích để lọc bảng.
 * v1.2: bỏ icon; nút tiêu chí hiện ngưỡng ngắn gọn của LUẬT ĐANG ÁP DỤNG cho môn (rule từ API, không viết cứng).
 */
import { useMemo, useRef } from "react";
import { Doughnut, getElementAtEvent } from "react-chartjs-2";
import { CRITERIA, RISK, RISK_LEVELS } from "../theme/tokens.js";
import { fmtInt, fmtPercent, share } from "../utils/format.js";

const pct = (v) => `${Math.round(Number(v) * 100)}%`;

function thresholdHint(key, rule) {
  if (!rule) return null;
  const t = rule.thresholds;
  if (key === "attendance") return `≥${pct(t.absence_yellow)}`;
  if (key === "inactivity") return `>${t.inactive_yellow_days} ngày`;
  return `≥${pct(t.missing_yellow)}`;
}

export default function RiskDoughnut({ summary, selectedLevels = [], onToggleLevel, criterion, onCriterion, rule,
  centerLabel = "sinh viên" }) {
  const ref = useRef(null);
  const counts = RISK_LEVELS.map((l) => summary[l.toLowerCase()]);
  const { total } = summary;

  const { data, options } = useMemo(() => ({
    data: {
      labels: RISK_LEVELS.map((l) => RISK[l].label),
      datasets: [{
        data: counts,
        backgroundColor: RISK_LEVELS.map((l) => (selectedLevels.length && !selectedLevels.includes(l) ? RISK[l].tint : RISK[l].color)),
        borderColor: "#ffffff", borderWidth: 2, hoverOffset: 6,
      }],
    },
    options: {
      cutout: "62%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${fmtInt(ctx.parsed)} (${fmtPercent(share(ctx.parsed, total))})`,
          },
        },
      },
    },
  }), [counts.join(","), selectedLevels.join(","), total]); // eslint-disable-line react-hooks/exhaustive-deps

  const onClick = (event) => {
    if (!onToggleLevel) return;
    const [element] = getElementAtEvent(ref.current, event);
    if (element) onToggleLevel(RISK_LEVELS[element.index]);
  };

  return (
    <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: 176, height: 176, flex: "none" }}>
        <Doughnut ref={ref} data={data} options={options} onClick={onClick} style={{ cursor: onToggleLevel ? "pointer" : "default" }}
          role="img" aria-label="Biểu đồ tỷ lệ theo mức rủi ro" />
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", pointerEvents: "none", textAlign: "center" }}>
          <div>
            <div style={{ fontSize: 26, fontWeight: 650 }}>{fmtInt(total)}</div>
            <div className="muted" style={{ fontSize: 12 }}>{centerLabel}</div>
          </div>
        </div>
      </div>
      <div style={{ flex: 1, minWidth: 200 }}>
        {RISK_LEVELS.map((level, i) => {
          const active = selectedLevels.includes(level);
          return (
            <button type="button" key={level} onClick={() => onToggleLevel?.(level)} aria-pressed={active}
              disabled={!onToggleLevel} className="risk-legend-row"
              style={{ background: active ? RISK[level].tint : "transparent", cursor: onToggleLevel ? "pointer" : "default" }}>
              <span><span className="swatch" style={{ background: RISK[level].color }} aria-hidden />{RISK[level].label}</span>
              <span className="tabular"><b>{fmtInt(counts[i])}</b> <span className="muted">({fmtPercent(share(counts[i], total), 0)})</span></span>
            </button>
          );
        })}
        {summary.by_criterion && onCriterion && (
          <>
            <div className="muted" style={{ fontSize: 12, marginTop: 10, marginBottom: 4 }}>Theo tiêu chí</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {Object.entries(CRITERIA).map(([key, label]) => (
                <button type="button" key={key} onClick={() => onCriterion(criterion === key ? undefined : key)}
                  aria-pressed={criterion === key} className={`chip${criterion === key ? " on" : ""}`}
                  title={`Số sinh viên có điểm ${label.toLowerCase()} từ 1 (nhấn để lọc bảng)`}>
                  {label} <b>{fmtInt(summary.by_criterion[key])}</b>
                  {rule && <span className="chip-hint"> {thresholdHint(key, rule)}</span>}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
