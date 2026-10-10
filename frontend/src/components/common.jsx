/** Thành phần giao diện nhỏ dùng chung: huy hiệu rủi ro, thẻ KPI, khung biểu đồ có chế độ xem bảng. */
import { Alert, Card, Segmented, Skeleton, Table, Tooltip } from "antd";
import { useState } from "react";
import { errorText } from "../api/client.js";
import { RISK } from "../theme/tokens.js";
import { NO_DATA, fmtDecimal, fmtPercent } from "../utils/format.js";
import MetricInfo from "./MetricInfo.jsx";

/**
 * Đèn giao thông: nền màu nhạt + chữ (không bao giờ chỉ có màu – SPEC 5.4). Không dùng icon trang trí.
 * compact: chữ ngắn "Đỏ/Vàng/Xanh" (dòng lịch sử, bảng hẹp) – nhãn đầy đủ nằm ở title.
 */
export function RiskBadge({ level, compact = false }) {
  const risk = RISK[level];
  if (!risk) return null;
  return (
    <span className={`risk-badge${compact ? " compact" : ""}`} style={{ background: risk.tint, color: risk.ink }}
      title={risk.label}>
      {compact ? risk.short : risk.label}
    </span>
  );
}

/**
 * Chênh lệch so với kỳ trước. betterWhen: "down" (vd tỷ lệ đỏ – giảm là tốt) | "up".
 * unit: "pp" (điểm %), "sv" (sinh viên) hoặc "" .
 */
export function Delta({ value, unit = "pp", betterWhen = "down", suffix = "so với tuần trước" }) {
  if (value == null || Number.isNaN(Number(value))) return null;
  // Làm tròn theo đúng số chữ số hiển thị trước khi xét dấu: −0,04 điểm % hiển thị "±0,0", không tô màu tốt/xấu
  const v = unit === "pp" ? Math.round(Number(value) * 10) / 10 : Number(value);
  const good = v === 0 ? null : (v < 0) === (betterWhen === "down");
  const text = unit === "pp" ? `${fmtDecimal(Math.abs(v), 1)} điểm %` : `${Math.abs(v).toLocaleString("vi-VN")}${unit === "sv" ? " SV" : ""}`;
  const sign = v > 0 ? "+" : v < 0 ? "−" : "±";
  return (
    <span className={good == null ? "delta" : good ? "delta good" : "delta bad"}>
      {sign}{text}{suffix ? ` ${suffix}` : ""}
    </span>
  );
}

/** Thẻ KPI: một con số chính, một dòng phụ ngắn; thông tin thêm hiện khi rê chuột (detail). */
export function KpiCard({ label, value, hint, detail, loading, accent, info, children }) {
  const labelNode = (
    <div className="kpi-label">
      {label}
      {info && <MetricInfo metric={info} compact />}
    </div>
  );
  return (
    <Card size="small" style={{ height: "100%", borderTop: accent ? `3px solid ${accent}` : undefined }}>
      {detail ? <Tooltip title={detail} placement="topLeft">{labelNode}</Tooltip> : labelNode}
      {loading ? <Skeleton.Input active size="small" style={{ marginTop: 8 }} /> : <div className="kpi-value">{value}</div>}
      {hint && <div className="kpi-hint">{hint}</div>}
      {children}
    </Card>
  );
}

/** Tỷ lệ %: null hiển thị "Chưa có dữ liệu" (khác 0%). */
export function Rate({ value, digits = 1 }) {
  return value == null ? <span className="no-data">{NO_DATA}</span> : <span className="tabular">{fmtPercent(value, digits)}</span>;
}

/**
 * Khung biểu đồ: tiêu đề, phụ đề ngắn, liên kết "Nguồn & cách tính" (info = khóa chỉ số + phạm vi),
 * nút chuyển "Biểu đồ | Bảng" (mọi giá trị trên biểu đồ đều xem được dạng bảng), giữ khung cũ mờ đi khi đang tải lại.
 */
export function ChartCard({ title, subtitle, extra, table, loading, error, fetching, height, bare = false, info, children }) {
  const [view, setView] = useState("chart");
  let body;
  if (error) body = <Alert type="error" showIcon message={errorText(error)} />;
  else if (loading) body = <Skeleton active paragraph={{ rows: 6 }} />;
  else if (view === "table" && table) body = <Table size="small" scroll={{ x: "max-content" }} pagination={{ pageSize: 10, showSizeChanger: false }} {...table} />;
  else if (bare) body = <div className={fetching ? "is-fetching" : undefined}>{children}</div>;
  else body = <div className={`chart-box${fetching ? " is-fetching" : ""}`} style={height ? { height } : undefined}>{children}</div>;
  return (
    <Card
      title={title}
      extra={(
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {info && <MetricInfo metric={info} />}
          {extra}
          {table && (
            <Segmented size="small" value={view} onChange={setView}
              options={[{ label: "Biểu đồ", value: "chart" }, { label: "Bảng", value: "table" }]} />
          )}
        </div>
      )}
      style={{ height: "100%" }}
    >
      {subtitle && <div className="card-subtitle" style={{ marginTop: -8, marginBottom: 12 }}>{subtitle}</div>}
      {body}
    </Card>
  );
}
