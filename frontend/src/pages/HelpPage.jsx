/**
 * Trợ giúp: hướng dẫn sử dụng theo vai trò, cách hệ thống xếp mức rủi ro, giới thiệu hệ thống.
 * v1.2: ngưỡng, trọng số và luật xếp mức ĐỌC TỪ API (/meta/risk-rule) – cùng luật mà ETL dùng, không viết cứng;
 * với giảng viên hiện luật của môn đang chọn (có thể là luật riêng của môn).
 */
import { Card, Col, Collapse, Descriptions, Row, Skeleton, Tag } from "antd";
import { useMatch } from "react-router-dom";
import { useFilters, useMetaMetrics, useRiskRule } from "../api/hooks.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { LevelRules, RuleTable } from "../components/MetricInfo.jsx";
import { fmtDateTime } from "../utils/format.js";

const APP_VERSION = "1.2.0";

const ADMIN_GUIDE = [
  {
    key: "overview", label: "Tổng quan – từ toàn trường xuống khoa, môn học, sinh viên",
    children: (
      <ol>
        <li>Trang Tổng quan là bức tranh toàn trường: thẻ KPI, biểu đồ tròn và đồ thị xu hướng mức rủi ro, so sánh giữa các khoa
          (quy mô, tỷ lệ tương tác, phân bố rủi ro) kèm bảng tóm tắt, và lưu lượng hệ thống.</li>
        <li>Nhấn vào cột hoặc dòng của một khoa để mở <b>trang Khoa</b>: so sánh các môn trong khoa và bảng môn học.</li>
        <li>Nhấn vào một môn để mở <b>trang Môn học</b>: biểu đồ rủi ro của lớp, bảng cảnh báo, danh sách sinh viên; nhấn một sinh viên để xem chi tiết.</li>
        <li>Thanh cấp xem (Toàn trường › Khoa › Môn học) ở đầu trang cho biết đang ở cấp nào; nút Back của trình duyệt và F5 giữ đúng cấp và học kỳ.</li>
        <li>Liên kết <b>Nguồn &amp; cách tính</b> trên mỗi biểu đồ cho biết số liệu lấy từ bảng Moodle nào và tính như thế nào.</li>
      </ol>
    ),
  },
  {
    key: "traffic", label: "Lưu lượng – theo dõi tải hệ thống",
    children: (
      <p>
        Chọn khoảng ngày để xem số lượt truy cập và số người online theo giờ trên biểu đồ hai trục. Thẻ <b>Online hiện tại</b> tự làm mới
        mỗi 60 giây; heatmap giờ × thứ cho thấy khung giờ đông nhất trong 1–12 tuần gần nhất. Số “lượt truy cập” được đếm từ nhật ký sự kiện
        của Moodle nên là chỉ số gần đúng của tải, không phải số HTTP request.
      </p>
    ),
  },
  {
    key: "reports", label: "Báo cáo – xem trước và xuất Excel/PDF",
    children: (
      <p>
        Chọn loại báo cáo, đặt bộ lọc rồi nhấn <b>Xem trước</b>. Khi số liệu đúng như mong muốn, nhấn <b>Xuất Excel</b> hoặc <b>Xuất PDF</b>.
        PDF giới hạn 5.000 dòng, Excel giới hạn 200.000 dòng.
      </p>
    ),
  },
  {
    key: "catalog", label: "Danh mục – môn học và giảng viên phụ trách",
    children: <p>Tra cứu môn học theo học kỳ và khoa, kèm giảng viên phụ trách và sĩ số. Danh mục được quản lý trong Moodle và nạp sang qua ETL, nên không sửa được tại đây.</p>,
  },
  {
    key: "system", label: "Hệ thống – người dùng, nhật ký ETL, sao lưu",
    children: (
      <ul>
        <li><b>Quản lý người dùng</b>: khóa/mở khóa tài khoản, đặt lại mật khẩu. Mật khẩu tạm chỉ hiện một lần; người dùng nên đổi ngay sau khi đăng nhập.</li>
        <li><b>Nhật ký ETL</b>: xem các lần chạy của tiến trình nạp dữ liệu, lọc các lần chạy lỗi để biết số liệu có bị chậm cập nhật hay không.</li>
        <li><b>Sao lưu &amp; phục hồi</b>: tạo bản sao lưu CSDL phân tích, tải về, hoặc phục hồi. Phục hồi thay toàn bộ dữ liệu hiện tại nên phải gõ lại tên file để xác nhận.</li>
        <li><b>Kênh gửi tin</b>: xem chế độ gửi email và tin nhắn Moodle, kiểm tra kết nối Moodle, gửi email thử. Tin chỉ tới sinh viên thật khi bật cờ cho phép, dùng dữ liệu thật và kênh đã kiểm tra thành công.</li>
      </ul>
    ),
  },
];

const TEACHER_GUIDE = [
  {
    key: "risk", label: "Cảnh báo – tìm sinh viên cần hỗ trợ",
    children: (
      <ol>
        <li>Chọn môn ở ô chọn môn trên thanh tiêu đề.</li>
        <li>Nhấn một thẻ đèn giao thông hoặc một lát cắt trên biểu đồ tròn để lọc bảng theo mức rủi ro.</li>
        <li>Bảng sắp xếp sẵn Đỏ → Vàng → Xanh, trong cùng mức thì điểm rủi ro cao đứng trước. Có thể lọc theo từng tiêu chí và xuất danh sách ra Excel/PDF.</li>
        <li>Đồ thị xu hướng cạnh biểu đồ tròn cho biết lớp đang tốt lên hay xấu đi theo từng tuần.</li>
        <li>Nhấn một dòng để xem lý do cảnh báo, bảng phân tích điểm rủi ro, so sánh với lớp, hoạt động theo tuần và bài tập.</li>
        <li>Nút <b>Gửi tin nhắn Moodle</b> / <b>Gửi email</b> mở trình soạn tin có sẵn số liệu của sinh viên; <b>Ghi chú</b>, <b>Hẹn gặp</b> ghi vào nhật ký can thiệp.</li>
      </ol>
    ),
  },
  {
    key: "progress", label: "Tiến độ lớp – lớp đang đi tới đâu",
    children: <p>Ba thanh tiến độ (hoàn thành hoạt động, nộp bài, chuyên cần), tiến độ từng chương, số sinh viên hoạt động theo ngày hoặc tuần và biểu đồ tỷ lệ tiến độ theo thời gian.</p>,
  },
  {
    key: "rules", label: "Thiết lập cảnh báo – luật riêng cho môn",
    children: (
      <ol>
        <li>Chọn mẫu phù hợp loại môn (Lý thuyết, Thực hành, Đồ án) rồi tinh chỉnh ngưỡng, trọng số, luật bổ sung (vd “bỏ nộp 2 bài liên tiếp → nguy cơ cao”).</li>
        <li>Khối <b>Tác động nếu áp dụng</b> cho biết bao nhiêu sinh viên đổi mức trước khi lưu.</li>
        <li><b>Lưu và áp dụng</b> tạo phiên bản mới, áp dụng ngay cho số liệu hôm nay; các ngày trước giữ luật cũ. <b>Khôi phục mặc định</b> quay về luật của trường.</li>
      </ol>
    ),
  },
  {
    key: "interventions", label: "Can thiệp – liên hệ và nhắc sinh viên",
    children: (
      <ol>
        <li><b>Cần liên hệ</b>: sinh viên Đỏ/Vàng chưa được liên hệ gần đây; chọn nhiều sinh viên rồi soạn tin – nội dung tự điền theo số liệu từng người, sửa được trước khi gửi.</li>
        <li><b>Đã gửi</b>: trạng thái từng tin và mã xác nhận (mã tin nhắn Moodle hoặc Message-ID email); duyệt tin chờ duyệt, gửi lại tin lỗi.</li>
        <li><b>Nhắc tự động</b>: đặt quy tắc (không truy cập quá n ngày, vừa chuyển sang Nguy cơ cao, quá hạn nộp bài), chọn tự gửi hoặc chờ duyệt; dùng <b>Chạy thử</b> để xem ai sẽ nhận.</li>
      </ol>
    ),
  },
];

const COMMON_GUIDE = [
  {
    key: "account", label: "Tài khoản – đổi mật khẩu, đăng xuất",
    children: <p>Mở menu tên người dùng ở góc phải thanh tiêu đề, chọn <b>Tài khoản &amp; đổi mật khẩu</b>. Mật khẩu mới cần ít nhất 8 ký tự, có cả chữ và số; sau khi đổi, các phiên đăng nhập khác của tài khoản bị đăng xuất.</p>,
  },
];

function lastCourse() {
  try {
    return sessionStorage.getItem("lms.lastCourse") ?? undefined;
  } catch {
    return undefined;
  }
}

export default function HelpPage() {
  const { user } = useAuth();
  const { data: filters } = useFilters();
  const match = useMatch("/teacher/courses/:courseId/*");
  const courseId = user.role === "TEACHER" ? (match?.params.courseId ?? lastCourse()) : undefined;
  const rule = useRiskRule(courseId);
  const metrics = useMetaMetrics();
  const guide = [...(user.role === "ADMIN" ? ADMIN_GUIDE : TEACHER_GUIDE), ...COMMON_GUIDE];
  const r = rule.data;
  const tables = [...new Set((metrics.data?.items ?? []).flatMap((m) => m.moodle_tables))];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={15}>
        <Card title={`Hướng dẫn sử dụng – ${user.role === "ADMIN" ? "Quản trị viên" : "Giảng viên"}`} className="help-body">
          <Collapse items={guide} defaultActiveKey={[guide[0].key]} />
        </Card>
        <Card title="Cách hệ thống xếp mức rủi ro" style={{ marginTop: 16 }} className="help-body">
          {!r ? <Skeleton active /> : (
            <>
              <p>
                {r.scope === "COURSE"
                  ? <>Môn đang chọn dùng <Tag color="orange">luật riêng {r.label}</Tag> do giảng viên đặt. </>
                  : <>Luật mặc định của trường <Tag>{r.label}</Tag>. </>}
                Mỗi sinh viên trong mỗi môn được chấm 0, 1 hoặc 2 điểm cho từng tiêu chí; điểm rủi ro 0–100 = <code>{r.score_formula}</code>.
              </p>
              <RuleTable rule={r} />
              <LevelRules rule={r} />
              {r.extra_rules?.length > 0 && <p>Luật bổ sung của môn: {r.extra_rules.map((x) => x.text).join("; ")}.</p>}
            </>
          )}
          <p className="muted">Mức rủi ro là tín hiệu để giảng viên chú ý, không phải kết luận về kết quả học tập của sinh viên.</p>
        </Card>
      </Col>
      <Col xs={24} xl={9}>
        <Card title="Giới thiệu hệ thống">
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Tên hệ thống">LMS Analytics – Trực quan hóa dữ liệu Moodle</Descriptions.Item>
            <Descriptions.Item label="Phiên bản">{APP_VERSION}</Descriptions.Item>
            <Descriptions.Item label="Đơn vị">Khoa Công nghệ Thông tin – Trường Đại học Đà Lạt</Descriptions.Item>
            <Descriptions.Item label="Nhóm thực hiện">
              Nguyễn Thăng Thiêng (2312755)<br />Nguyễn Ngọc Bảo Thịnh (2312757)<br />Chung Thiện Ý (2312804)
            </Descriptions.Item>
            <Descriptions.Item label="Nguồn dữ liệu">
              CSDL Moodle (lược đồ Moodle 3.9){filters?.as_of && " – dữ liệu mô phỏng 5 khoa"}. Các bảng được đọc:{" "}
              <span className="small">{tables.join(", ") || "…"}</span>
            </Descriptions.Item>
            <Descriptions.Item label="Thời điểm tham chiếu">{filters ? fmtDateTime(filters.as_of) : "–"}</Descriptions.Item>
          </Descriptions>
          <div className="muted" style={{ marginTop: 12, fontSize: 12 }}>
            Cần hỗ trợ về tài khoản hoặc số liệu, liên hệ quản trị viên hệ thống.
          </div>
        </Card>
      </Col>
    </Row>
  );
}
