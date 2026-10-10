/**
 * Trang Tổng quan – cấp Toàn trường (Macro), v1.2 theo góp ý của cô:
 *   KPI → Phân bố + xu hướng mức rủi ro toàn trường (góp ý 2) → So sánh giữa các Khoa: 3 biểu đồ cột + bảng (góp ý 1)
 *   → Hoạt động hệ thống (lưu lượng, heatmap – giữ nguyên). Không còn danh sách môn/sinh viên tại trang này (góp ý 3):
 *   nhấn một Khoa để mở trang Khoa (URL riêng).
 */
import { useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Col, Dropdown, Row, Segmented, Table } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { downloadFile, errorMessage } from "../../api/client.js";
import {
  useFacultyCompare, useKpis, useTrafficHeatmap, useTrafficHourly, useTrafficRealtime,
} from "../../api/hooks.js";
import { ComparisonColumns, RiskShareBars, VolumeColumns, chartHeight } from "../../charts/ComparisonCharts.jsx";
import TrafficDualAxisChart, { PeakLegend, trafficTableColumns } from "../../charts/TrafficDualAxisChart.jsx";
import TrafficHeatmap, { heatmapTableColumns } from "../../charts/TrafficHeatmap.jsx";
import { ChartCard, Delta, KpiCard } from "../../components/common.jsx";
import LevelBreadcrumb from "../../components/LevelBreadcrumb.jsx";
import MetricInfo from "../../components/MetricInfo.jsx";
import RiskOverviewPanel from "../../components/RiskOverviewPanel.jsx";
import TermFilterBar from "../../components/TermFilterBar.jsx";
import { RISK } from "../../theme/tokens.js";
import { fmtDecimal, fmtHour, fmtInt, fmtPercent } from "../../utils/format.js";
import useTerm from "../../utils/useTerm.js";

const MANY_FACULTIES = 8;
const TOP_FACULTIES = 10;

const EXPORTS = [
  { key: "enrollment:xlsx", label: "Báo cáo quy mô & tương tác – Excel" },
  { key: "enrollment:pdf", label: "Báo cáo quy mô & tương tác – PDF" },
  { key: "risk:xlsx", label: "Báo cáo cảnh báo sinh viên – Excel" },
  { key: "risk:pdf", label: "Báo cáo cảnh báo sinh viên – PDF" },
];

export default function AdminOverview() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { term, setTerm, search, filters } = useTerm();
  const [range, setRange] = useState("24h");
  const [exporting, setExporting] = useState(false);
  const [focusLevel, setFocusLevel] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const kpis = useKpis(term);
  const compare = useFacultyCompare(term);
  const realtime = useTrafficRealtime();
  const asOf = filters ? dayjs(filters.as_of) : null;
  const week = useTrafficHourly(asOf?.subtract(6, "day").format("YYYY-MM-DD"), asOf?.format("YYYY-MM-DD"));
  const heatmap = useTrafficHeatmap(4);

  const k = kpis.data;
  const school = compare.data?.school;
  const allFaculties = compare.data?.items ?? [];
  // Hơn 8 khoa: biểu đồ tự chuyển thanh ngang; mặc định hiện 10 khoa đầu (theo quy mô) kèm "Xem tất cả" (Mục 3.2)
  const faculties = !showAll && allFaculties.length > MANY_FACULTIES ? allFaculties.slice(0, TOP_FACULTIES) : allFaculties;
  const rateKey = focusLevel ? `${focusLevel.toLowerCase()}_rate` : null;
  const highlight = rateKey && school?.[rateKey] != null
    ? (f) => f[rateKey] != null && Number(f[rateKey]) > Number(school[rateKey]) : undefined;
  const highlightNote = focusLevel && school
    ? `Tỷ lệ ${RISK[focusLevel].label.toLowerCase()} cao hơn trung bình toàn trường (${fmtPercent(school[rateKey])})` : undefined;
  const trafficItems = range === "24h" ? realtime.data?.series_24h : week.data?.items;
  const trafficQuery = range === "24h" ? realtime : week;
  const openFaculty = (f) => navigate(`/admin/faculties/${f.faculty_id}${search}`);

  async function onExport({ key }) {
    const [reportType, format] = key.split(":");
    setExporting(true);
    try {
      const name = await downloadFile("/admin/reports/export", { report_type: reportType, format, ...term }, `bao_cao.${format}`);
      message.success(`Đã tải ${name}`);
    } catch (err) {
      message.error(await errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const redDelta = k?.red_rate_prev_week == null ? null : Number(k.red_rate) - Number(k.red_rate_prev_week);
  const onlyOne = allFaculties.length === 1;
  const customCourses = allFaculties.reduce((n, f) => n + (f.custom_rule_courses ?? 0), 0);

  return (
    <>
      <LevelBreadcrumb level="school" search={search} />
      <div className="filter-bar">
        <TermFilterBar filters={filters} term={term} onTermChange={setTerm} facultyId={undefined}
          onFacultyChange={(id) => id && navigate(`/admin/faculties/${id}${search}`)} />
        <span className="spacer" />
        <Button onClick={() => queryClient.invalidateQueries()}>Làm mới</Button>
        <Dropdown menu={{ items: EXPORTS, onClick: onExport }} disabled={!term}>
          <Button type="primary" loading={exporting}>Xuất báo cáo</Button>
        </Dropdown>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="Tổng môn học" loading={!k} value={fmtInt(k?.total_courses)}
            hint={`${fmtInt(faculties.length)} khoa`} detail={`Năm học ${term?.academic_year ?? ""} · HK${term?.semester ?? ""}`} />
        </Col>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="SV đăng ký" loading={!k} value={fmtInt(k?.total_enrolled)} hint={`${fmtInt(k?.unique_students)} sinh viên`}
            detail="Số lớn là lượt ghi danh (một sinh viên học nhiều môn được tính nhiều lần); số nhỏ là số sinh viên khác nhau"
            info="enrolled" />
        </Col>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="SV tương tác" loading={!k} value={fmtInt(k?.total_active)} hint={fmtPercent(k?.active_rate)}
            detail="Lượt ghi danh có ít nhất một hoạt động trong môn từ đầu học kỳ" info="active_rate" />
        </Col>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="Online hiện tại" loading={!k} value={fmtInt(k?.current_online)}
            hint={k?.current_online_at ? `lúc ${fmtHour(k.current_online_at)}` : "chưa có mẫu"}
            detail={k ? `Trung bình hôm nay ${fmtDecimal(k.avg_online_users_today, 0)} người` : undefined} />
        </Col>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="Peak hôm nay" loading={!k}
            value={k?.peak_requests_today ? `${fmtInt(k.peak_requests_today.value)} req` : "–"}
            hint={k?.peak_requests_today ? `lúc ${k.peak_requests_today.hour}` : "chưa có dữ liệu"} />
        </Col>
        <Col xs={24} sm={12} lg={8} xxl={4}>
          <KpiCard label="SV nguy cơ cao" loading={!k} accent={RISK.RED.color} value={fmtInt(k?.red_students)}
            hint={<>{fmtPercent(k?.red_rate)} · <Delta value={redDelta} /></>} info="risk_level"
            detail="Tỷ lệ tính trên lượt ghi danh; so với số liệu 7 ngày trước" />
        </Col>

        <Col span={24}>
          <RiskOverviewPanel title="toàn trường" loading={!school}
            summary={school ? { red: school.red, yellow: school.yellow, green: school.green, total: school.enrolled } : null}
            trend={{ term }} focusLevel={focusLevel} onFocusLevel={setFocusLevel}
            ruleNote={school ? `${customCourses}/${school.course_count} môn trong trường dùng luật cảnh báo riêng do giảng viên đặt; số Đỏ/Vàng/Xanh của các môn đó được chấm theo luật riêng.` : undefined} />
        </Col>

        <Col span={24}>
          <Card title="So sánh giữa các Khoa"
            extra={<MetricInfo metric={{ keys: ["enrolled", "unique_students", "active_rate", "risk_level"],
              note: school ? `${customCourses}/${school.course_count} môn dùng luật cảnh báo riêng (cột "Môn dùng luật riêng" trong bảng).` : undefined }} />}
            loading={compare.isLoading}>
            {onlyOne && <div className="muted" style={{ marginBottom: 8 }}>Học kỳ này mới có dữ liệu của 1 khoa.</div>}
            {highlightNote && (
              <div className="focus-note" style={{ marginBottom: 8 }}>
                Đang tô nổi các khoa có tỷ lệ <b>{RISK[focusLevel].label.toLowerCase()}</b> cao hơn trung bình toàn trường
                ({fmtPercent(school[rateKey])}). <a role="button" onClick={() => setFocusLevel(null)}>Bỏ chọn</a>
              </div>
            )}
            <Row gutter={[24, 16]}>
              <Col xs={24} lg={8}>
                <div className="chart-title">Quy mô (lượt ghi danh)</div>
                <div style={{ height: chartHeight(faculties.length) }}>
                  <VolumeColumns items={faculties} labelKey="faculty_name" onSelect={openFaculty}
                    highlight={highlight} highlightNote={highlightNote} />
                </div>
              </Col>
              <Col xs={24} lg={8}>
                <div className="chart-title">Tỷ lệ tương tác</div>
                <div style={{ height: chartHeight(faculties.length) }}>
                  <ComparisonColumns items={faculties} labelKey="faculty_name" valueKey="active_rate" label="Tỷ lệ tương tác"
                    reference={school?.active_rate != null ? { value: Number(school.active_rate), label: `TB toàn trường ${fmtPercent(school.active_rate)}` } : undefined}
                    onSelect={openFaculty} highlight={highlight} highlightNote={highlightNote} />
                </div>
              </Col>
              <Col xs={24} lg={8}>
                <div className="chart-title">Phân bố mức rủi ro</div>
                <div style={{ height: chartHeight(faculties.length) }}>
                  <RiskShareBars items={faculties} labelKey="faculty_name" onSelect={openFaculty}
                    highlight={highlight} highlightNote={highlightNote} />
                </div>
              </Col>
            </Row>
            <Table style={{ marginTop: 16 }} size="middle" rowKey="faculty_id" pagination={false} dataSource={faculties}
              scroll={{ x: "max-content" }}
              onRow={(row) => ({ onClick: () => openFaculty(row), style: { cursor: "pointer" } })}
              rowClassName={(row) => (highlight?.(row) ? "row-focus" : "")}
              columns={[
                { title: "Khoa", dataIndex: "faculty_name", render: (v) => <b>{v}</b> },
                { title: "Số môn", dataIndex: "course_count", align: "right" },
                { title: "Lượt ghi danh", dataIndex: "enrolled", align: "right", render: fmtInt },
                { title: "SV duy nhất", dataIndex: "unique_students", align: "right", render: fmtInt },
                { title: "Tỷ lệ tương tác", dataIndex: "active_rate", align: "right", render: (v) => fmtPercent(v) },
                { title: "Nộp bài", dataIndex: "avg_submission_rate", align: "right", render: (v) => fmtPercent(v, 1, "–") },
                { title: "Chuyên cần", dataIndex: "avg_attendance_rate", align: "right", render: (v) => fmtPercent(v, 1, "–") },
                { title: "% Nguy cơ cao", dataIndex: "red_rate", align: "right",
                  render: (v) => <span style={{ color: RISK.RED.ink }}>{fmtPercent(v)}</span> },
                { title: "So với tuần trước", dataIndex: "red_rate_delta_week", align: "right",
                  render: (v) => <Delta value={v} suffix="" /> },
                { title: "Môn dùng luật riêng", dataIndex: "custom_rule_courses", align: "right", responsive: ["xl"] },
              ]} />
            {allFaculties.length > MANY_FACULTIES && (
              <a role="button" style={{ display: "inline-block", marginTop: 8 }} onClick={() => setShowAll((v) => !v)}>
                {showAll ? `Chỉ hiện ${TOP_FACULTIES} khoa lớn nhất` : `Xem tất cả ${allFaculties.length} khoa`}
              </a>
            )}
          </Card>
        </Col>

        <Col span={24}><div className="section-title">Hoạt động hệ thống</div></Col>
        <Col span={24}>
          <ChartCard
            title="Lưu lượng truy cập"
            subtitle={<>Requests và người dùng online trung bình theo giờ <PeakLegend inline /></>}
            info="traffic"
            extra={<Segmented size="small" value={range} onChange={setRange} options={[{ label: "24 giờ", value: "24h" }, { label: "7 ngày", value: "7d" }]} />}
            loading={!trafficItems && trafficQuery.isLoading} error={trafficQuery.error} fetching={trafficQuery.isFetching}
            table={{ rowKey: "stat_hour", dataSource: trafficItems ?? [], columns: trafficTableColumns }}
          >
            {trafficItems && <TrafficDualAxisChart items={trafficItems} labelFormat={range === "24h" ? "HH:mm" : "DD/MM HH:mm"} />}
          </ChartCard>
        </Col>
        <Col span={24}>
          <ChartCard
            title="Heatmap giờ × thứ (4 tuần)"
            subtitle={heatmap.data ? `Trung bình ${dayjs(heatmap.data.from_date).format("DD/MM")} – ${dayjs(heatmap.data.to_date).format("DD/MM/YYYY")}` : undefined}
            loading={heatmap.isLoading} error={heatmap.error} fetching={heatmap.isFetching} bare
            table={{ rowKey: (r) => `${r.day_of_week}-${r.hour_of_day}`, dataSource: heatmap.data?.matrix ?? [], columns: heatmapTableColumns }}
          >
            {heatmap.data && <TrafficHeatmap matrix={heatmap.data.matrix} />}
          </ChartCard>
        </Col>
      </Row>
    </>
  );
}
