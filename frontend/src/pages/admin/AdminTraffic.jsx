/** Admin 1.2 – Lưu lượng: khoảng ngày có sẵn mốc · thẻ thời gian thực (tự làm mới 60s) · dual-axis · top giờ cao điểm · heatmap. */
import { Card, Col, DatePicker, Row, Select, Table } from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { useFilters, useTrafficHeatmap, useTrafficHourly, useTrafficRealtime } from "../../api/hooks.js";
import TrafficDualAxisChart, { PeakLegend, trafficColumnsFor } from "../../charts/TrafficDualAxisChart.jsx";
import TrafficHeatmap, {
  HEATMAP_SCOPE_NOTE, OperationHints, heatmapRange, heatmapTableColumns,
} from "../../charts/TrafficHeatmap.jsx";
import { ChartCard, KpiCard } from "../../components/common.jsx";
import { fmtDateTime, fmtDecimal, fmtHour, fmtInt } from "../../utils/format.js";

const MAX_DAYS = 92;

export default function AdminTraffic() {
  const { data: filters } = useFilters();
  const asOf = filters ? dayjs(filters.as_of) : null;
  const [range, setRange] = useState(null);
  const [weeks, setWeeks] = useState(4);

  useEffect(() => {
    if (asOf && !range) setRange([asOf.subtract(6, "day").startOf("day"), asOf.startOf("day")]);
  }, [asOf, range]);

  const from = range?.[0]?.format("YYYY-MM-DD");
  const to = range?.[1]?.format("YYYY-MM-DD");
  const hourly = useTrafficHourly(from, to);
  const realtime = useTrafficRealtime();
  const heatmap = useTrafficHeatmap(weeks);
  const items = hourly.data?.items;

  const stats = useMemo(() => {
    if (!items?.length) return null;
    // "Đông nhất" theo số người online cùng lúc (tải thực tế lên hệ thống), cùng số thì xét lượt hoạt động
    const busier = (a, b) => b.peak_online_users - a.peak_online_users || b.total_requests - a.total_requests;
    const total = items.reduce((s, i) => s + i.total_requests, 0);
    const top = [...items].sort(busier).slice(0, 10);
    return { peak: top[0], total, avgOnline: items.reduce((s, i) => s + Number(i.avg_online_users), 0) / items.length, top };
  }, [items]);

  const presets = asOf ? [
    { label: "Hôm nay", value: [asOf.startOf("day"), asOf.startOf("day")] },
    { label: "7 ngày gần nhất", value: [asOf.subtract(6, "day").startOf("day"), asOf.startOf("day")] },
    { label: "30 ngày gần nhất", value: [asOf.subtract(29, "day").startOf("day"), asOf.startOf("day")] },
    { label: "90 ngày gần nhất", value: [asOf.subtract(89, "day").startOf("day"), asOf.startOf("day")] },
  ] : [];
  const days = range ? range[1].diff(range[0], "day") + 1 : 0;
  const rt = realtime.data;

  return (
    <>
      <div className="filter-bar">
        <b>Khoảng thời gian:</b>
        <DatePicker.RangePicker
          aria-label="Khoảng thời gian" value={range} format="DD/MM/YYYY" presets={presets} allowClear={false}
          onChange={(value) => value && setRange(value)}
          disabledDate={(d) => !!asOf && d.isAfter(asOf, "day")}
        />
        <span className="muted">{days > MAX_DAYS ? `Tối đa ${MAX_DAYS} ngày` : `${days} ngày · ${items ? fmtInt(items.length) : "–"} giờ`}</span>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard label="Online hiện tại" loading={!rt} value={fmtInt(rt?.current_online)}
            hint={rt?.current_online_at ? `lúc ${fmtHour(rt.current_online_at)}${rt.current_online_source === "LOGSTORE" ? " · ước tính từ nhật ký" : ""}` : "Chưa có mẫu"}
            detail="Số người dùng có hoạt động trong 5 phút gần nhất; tự làm mới mỗi 60 giây" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard label="Lượt hoạt động hôm nay" loading={!rt} value={fmtInt(rt?.requests_so_far)} hint={rt ? `giờ này ${fmtInt(rt.requests_current_hour)}` : undefined}
            detail={rt ? `Số sự kiện trong nhật ký Moodle từ 00:00 tới hiện tại; riêng giờ ${fmtHour(rt.current_hour)} có ${fmtInt(rt.requests_current_hour)} lượt` : undefined} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard label="Giờ đông người nhất trong khoảng" loading={!stats && hourly.isLoading}
            value={stats ? `${fmtInt(stats.peak.peak_online_users)} người online` : "–"}
            hint={stats ? `lúc ${fmtDateTime(stats.peak.stat_hour)} · ${fmtInt(stats.peak.total_requests)} lượt hoạt động` : undefined} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiCard label="Online trung bình trong khoảng" loading={!stats && hourly.isLoading}
            value={stats ? fmtDecimal(stats.avgOnline, 1) : "–"} hint={stats ? `Tổng ${fmtInt(stats.total)} lượt hoạt động` : undefined} />
        </Col>

        <Col span={24}>
          <ChartCard
            title="Lưu lượng truy cập theo giờ"
            subtitle={<>Lượt hoạt động = số sự kiện trong nhật ký Moodle (các môn học), không phải số lượt tải trang <PeakLegend inline /></>}
            loading={hourly.isLoading} error={hourly.error} fetching={hourly.isFetching} height={360}
            table={{ rowKey: "stat_hour", dataSource: items ?? [], columns: trafficColumnsFor(items) }}
          >
            {items && <TrafficDualAxisChart items={items} labelFormat={days <= 1 ? "HH:mm" : "DD/MM HH:mm"} />}
          </ChartCard>
        </Col>

        <Col xs={24} xl={9}>
          <Card title="Top 10 giờ đông người nhất" style={{ height: "100%" }}>
            <Table
              size="small" rowKey="stat_hour" pagination={false} dataSource={stats?.top ?? []} loading={hourly.isLoading}
              columns={[
                { title: "#", render: (_, __, i) => i + 1, width: 40 },
                { title: "Giờ", dataIndex: "stat_hour", render: fmtDateTime },
                { title: "Online cao nhất", dataIndex: "peak_online_users", align: "right", render: fmtInt },
                { title: "Lượt hoạt động", dataIndex: "total_requests", align: "right", render: fmtInt },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <ChartCard
            title="Giờ đông / giờ vắng"
            subtitle={heatmapRange(heatmap.data, dayjs)}
            extra={(
              <Select size="small" value={weeks} onChange={setWeeks} aria-label="Số tuần" style={{ width: 110 }}
                options={[1, 2, 4, 8, 12].map((w) => ({ value: w, label: `${w} tuần` }))} />
            )}
            loading={heatmap.isLoading} error={heatmap.error} fetching={heatmap.isFetching} bare
            table={{ rowKey: (r) => `${r.day_of_week}-${r.hour_of_day}`, dataSource: heatmap.data?.matrix ?? [], columns: heatmapTableColumns }}
          >
            {heatmap.data && (
              <>
                <TrafficHeatmap matrix={heatmap.data.matrix} metric="online" />
                <OperationHints matrix={heatmap.data.matrix} />
                <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>{HEATMAP_SCOPE_NOTE}</div>
              </>
            )}
          </ChartCard>
        </Col>
      </Row>
    </>
  );
}
