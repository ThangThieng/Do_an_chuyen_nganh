/**
 * Góp ý 2 – Biểu đồ tròn + đồ thị xu hướng cho một phạm vi (toàn trường / khoa / môn): một thành phần dùng ở mọi cấp.
 * summary: {red, yellow, green, total} của snapshot hiện tại; trend: tham số useRiskTrend.
 * focusLevel / onFocusLevel (tùy chọn): nhấn lát cắt hoặc dòng chú thích để chọn một mức – trang cha dùng để tô nổi
 * các khoa/môn có tỷ lệ mức đó cao (kế hoạch Mục 3.2). Nhấn lại để bỏ chọn.
 * ruleNote: ghi chú về luật riêng trong phạm vi (cấp Khoa/Toàn trường), hiện trong ngăn "Nguồn & cách tính".
 */
import { Card, Col, Row, Segmented } from "antd";
import { useState } from "react";
import { useRiskTrend } from "../api/hooks.js";
import RiskDoughnut from "../charts/RiskDoughnut.jsx";
import RiskTrendChart, { trendTableColumns } from "../charts/RiskTrendChart.jsx";
import { ChartCard } from "./common.jsx";
import MetricInfo from "./MetricInfo.jsx";

export default function RiskOverviewPanel({ title, summary, loading, trend, courseId, centerLabel = "lượt ghi danh",
  footnote, focusLevel, onFocusLevel, ruleNote }) {
  const [granularity, setGranularity] = useState("week");
  const query = useRiskTrend({ ...trend, granularity });
  const info = { keys: ["risk_level", "risk_score"], courseId, note: ruleNote };
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={`Phân bố mức rủi ro${title ? ` – ${title}` : ""}`} loading={loading} style={{ height: "100%" }}
          extra={<MetricInfo metric={info} />}>
          {summary && <RiskDoughnut summary={summary} centerLabel={centerLabel}
            selectedLevels={focusLevel ? [focusLevel] : []}
            onToggleLevel={onFocusLevel ? (lv) => onFocusLevel(focusLevel === lv ? null : lv) : undefined} />}
          {footnote && <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>{footnote}</div>}
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <ChartCard title="Xu hướng mức rủi ro theo thời gian" info={{ keys: ["risk_trend", "risk_level"], courseId, note: ruleNote }}
          extra={<Segmented size="small" value={granularity} onChange={setGranularity}
            options={[{ label: "Theo tuần", value: "week" }, { label: "Theo ngày", value: "day" }]} />}
          loading={query.isLoading} error={query.error} fetching={query.isFetching} height={250}
          table={{ rowKey: "period", dataSource: query.data?.series ?? [], columns: trendTableColumns }}>
          {query.data && <RiskTrendChart series={query.data.series} ruleChanges={query.data.rule_changes}
            granularity={granularity} />}
        </ChartCard>
      </Col>
    </Row>
  );
}
