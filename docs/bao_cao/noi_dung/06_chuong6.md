# CHƯƠNG 6: CÀI ĐẶT VÀ THỬ NGHIỆM

## 6.1. Môi trường và công nghệ

Bảng: Công nghệ sử dụng
%w 18,42,40
| Lớp | Công nghệ | Vai trò |
|---|---|---|
| CSDL | PostgreSQL 18 | CSDL nguồn `moodle_src` và CSDL phân tích `lms_analytics` |
| Sinh dữ liệu, ETL | Python 3.11, pandas, SQLAlchemy 2, psycopg 3, APScheduler | Dữ liệu mô phỏng; trích xuất, tính toán, nạp, lập lịch |
| API | FastAPI, Pydantic, PyJWT, bcrypt, openpyxl, ReportLab | REST, xác thực, phân quyền, xuất Excel/PDF |
| Giao diện | React 18, Vite, Chart.js 4, Ant Design 5, React Query | Dashboard |
| Kiểm thử | pytest, vitest, Playwright, axe-core, Locust | Dữ liệu, API, giao diện, khả năng tiếp cận, tải |
| Triển khai | Docker Compose, Nginx | Chạy toàn bộ hệ thống bằng một lệnh |

Máy phát triển và đo: Intel Core i5-12450H (12 luồng), 16 GB RAM, Windows 11. Mã nguồn gồm khoảng 12.900 dòng Python, JavaScript và SQL; API có 33 endpoint, giao diện có 13 màn hình.

## 6.2. Dữ liệu thử nghiệm

Dữ liệu mô phỏng học kỳ 1 năm học 2026–2027 của Khoa Công nghệ Thông tin: 4 bộ môn, 15 môn, 8 giảng viên, 500 sinh viên (mỗi sinh viên học 4–6 môn), khoảng 1,2 triệu dòng nhật ký. Hành vi sinh theo ba hồ sơ (chăm chỉ 65%, trung bình 20%, có nguy cơ 15%), có trọng số theo giờ, theo thứ và tăng mạnh 48 giờ trước hạn nộp bài. Bộ dữ liệu được gieo sẵn các trường hợp đặc biệt: sinh viên bị khóa hoặc bị xóa, ghi danh hết hạn giữa kỳ, bài nộp theo nhóm, môn chưa có buổi điểm danh, sinh viên chưa từng truy cập. Hồ sơ đã gieo cho từng cặp sinh viên – môn được lưu làm "đáp án" để chấm độ chính xác của luật rủi ro.

Tại thời điểm tham chiếu 06/11/2026 10:30 có 2.383 cặp sinh viên – môn: 408 mức đỏ, 667 mức vàng, 1.308 mức xanh.

## 6.3. Cài đặt và triển khai

Hệ thống chạy bằng Docker Compose: điền khóa ký JWT và mật khẩu ban đầu vào `docker/.env`, chạy `docker compose --env-file docker/.env up --build -d`, rồi mở `http://localhost:8080`. Khi phát triển, có thể chạy trực tiếp bằng tập lệnh `scripts/lms.ps1` (Windows) hoặc `Makefile` (Linux/macOS). Lệnh `python -m backend.app.cli` hỗ trợ đồng bộ tài khoản từ Moodle, đặt mật khẩu, sao lưu và phục hồi khi giao diện web không chạy được.

Phiên bản cuối (1.1) được kiểm tra trên Docker ngày 01/10/2026 theo hai cách:

- Nâng cấp tại chỗ trên bản đang chạy: dịch vụ `init` áp dụng migration V008 lên dữ liệu có sẵn và bỏ qua bước sinh dữ liệu.
- Cài mới từ volume trống: toàn bộ quá trình tạo CSDL, sinh dữ liệu, nạp lịch sử 61 ngày (146 giây) và tạo tài khoản mất 201 giây.

Ở cả hai cách, 32/32 ca kiểm thử giao diện (E2E) đều đạt.

## 6.4. Kiểm thử chức năng và phân quyền

Bảng: Tổng hợp kiểm thử tự động (chạy ngày 01/10/2026)
%w 20,12,68
| Nhóm | Số ca | Nội dung |
|---|---|---|
| pytest | 284 | Ràng buộc CSDL, migration, dữ liệu mô phỏng, luật rủi ro, ETL (có đối soát với Moodle), API (xác thực, phân quyền, quản trị, giảng viên, báo cáo, bảo mật), đổi mật khẩu, quản lý người dùng, sao lưu và phục hồi |
| vitest | 8 | Hàm định dạng số, ngày và gộp dữ liệu biểu đồ |
| Playwright | 32 | Luồng quản trị viên và giảng viên trên trình duyệt thật, phân quyền, 4 kích thước màn hình, WCAG 2.1 AA, các màn hình hệ thống |

Tất cả các ca đều đạt. Một số ca tiêu biểu:

- Phân quyền: giảng viên gọi API môn của giảng viên khác nhận 403; giảng viên gọi `/admin/*` và quản trị viên gọi `/teacher/*` đều nhận 403; không có token nhận 401.
- Đổi mật khẩu: token cấp trước khi đổi nhận 401, token mới dùng được, mật khẩu cũ không đăng nhập được. Khóa tài khoản làm token còn hạn bị từ chối ngay.
- Sao lưu và phục hồi khứ hồi: tạo bản sao lưu, thêm và xóa dữ liệu, phục hồi, rồi so mã băm MD5 nội dung của tám bảng với trước khi sao lưu; kết quả trùng khớp. Bản sao lưu khác phiên bản cấu trúc hoặc có số dòng không khớp bị từ chối và dữ liệu giữ nguyên.
- Bảo mật: chuỗi tấn công SQL trong ô tìm kiếm được coi là văn bản; tên tệp dạng `..%2F.env` nhận 404; đăng nhập sai 5 lần trong 5 phút nhận 429.

## 6.5. Kiểm thử tính đúng đắn của dữ liệu

Với 5 môn lấy ngẫu nhiên, ca kiểm thử viết lại truy vấn độc lập trên Moodle rồi so với bảng fact: số sinh viên ghi danh và có tương tác, số buổi điểm danh và buổi vắng, số bài tới hạn và bài thiếu của từng sinh viên, lượt truy cập theo giờ. Sai lệch ở mọi chỉ số bằng 0. Chạy lại cả ba job trên cùng dữ liệu không làm thay đổi dòng nào; chèn thêm 1.000 dòng nhật ký vào một giờ thì chỉ giờ đó được cập nhật. 30 ca ghi dữ liệu sai (mức rủi ro lạ, tỷ lệ 120%, số bài thiếu không khớp…) đều bị CSDL từ chối.

So mức rủi ro hệ thống tính với hồ sơ đã gieo trên 2.383 cặp sinh viên – môn:

Bảng: Ma trận so sánh mức rủi ro với đáp án
%w 28,24,24,24
| Đáp án \ Hệ thống | XANH | VÀNG | ĐỎ |
|---|---|---|---|
| Chăm chỉ | 1.279 | 247 | 0 |
| Trung bình | 29 | 412 | 60 |
| Có nguy cơ | 0 | 8 | 348 |

Độ phủ (recall) của mức đỏ là 97,8% (mục tiêu ≥ 90%), độ chính xác (precision) 85,3% (mục tiêu ≥ 80%); không sinh viên nhóm có nguy cơ nào bị xếp xuống mức xanh. Luật gốc trong kế hoạch (đỏ khi một tiêu chí bằng 2 hoặc tổng từ 3) chỉ cho độ chính xác 62,9%, vì ở tuần 9 mỗi môn mới có 3–4 bài tới hạn nên thiếu 2 bài đã thành C3 = 2; luật hiện tại chỉ đổi điều kiện xếp mức đỏ, giữ nguyên ngưỡng từng tiêu chí. Các con số này đo trên dữ liệu mô phỏng, trong đó hành vi của từng hồ sơ do nhóm thực hiện đặt ra; chúng cho thấy luật hoạt động nhất quán với giả định, chưa chứng minh được độ chính xác với sinh viên thật.

## 6.6. Kiểm thử hiệu năng

Phép đo thực hiện ngày 17/09/2026 trên hai bộ dữ liệu: bộ x1 (145.846 dòng cảnh báo) và bộ x10 (nhân 10 lần bảng fact, 1.458.460 dòng cảnh báo, 150 môn).

Bảng: Kết quả đo hiệu năng so với mục tiêu
%w 30,40,18,12
| Mục tiêu | Kết quả đo | Công cụ | Đạt |
|---|---|---|---|
| Mỗi câu SQL ≤ 100 ms | Chậm nhất 1,71 ms (x1), 8,55 ms (x10) | EXPLAIN ANALYZE | Có |
| API p95 < 500 ms, p99 < 1 s, 50 người dùng | x1: p95 16 ms, p99 230 ms; x10: p95 22 ms, p99 37 ms; 0 lỗi / 20.302 yêu cầu | Locust | Có |
| Biểu đồ đầu < 1 s, LCP < 2,5 s | 335–409 ms; 360–428 ms | Playwright | Có |
| ETL: lưu lượng < 30 s, rủi ro < 5 phút, chốt ngày < 20 phút | 0,10 s; 60,05 s; 60,12 s | etl_bench | Có |
| Excel 10.000 dòng, PDF 500 dòng < 5 s | Excel 23.830 dòng 4,48 s; PDF 408 dòng 0,53 s | export_bench | Có |

Locust và API chạy cùng một máy nên số đo là cận trên. Giá trị p99 230 ms của bộ x1 đến từ các lần đăng nhập, vì bcrypt tốn khoảng 230 ms mỗi lần băm để chống dò mật khẩu. Với hồ sơ máy yếu (CPU chậm 4 lần), biểu đồ đầu tiên hiển thị sau 1,4–2,1 giây, vượt mục tiêu do gói JavaScript khoảng 924 KB. Sao lưu và phục hồi dữ liệu thử (khoảng 165.700 dòng) mất 2,2 giây và 38,4 giây trên Windows, 3,0 giây và 14,7 giây trong container Docker.

## 6.7. Các lỗi phát hiện nhờ kiểm thử

- Tranh chấp giữ kết nối: vài yêu cầu lẻ mất 30–69 giây khi đo tải, trong khi không có truy vấn nào quá 1 giây. Máy chủ uvicorn đóng kết nối nhàn rỗi sau 5 giây, trùng khoảng nghỉ giữa các thao tác của người dùng; đặt thời gian giữ kết nối 65 giây thì yêu cầu chậm nhất còn 0,55 giây.
- Phục hồi dữ liệu qua API bị chờ khóa 30 giây rồi lỗi khi chạy trên Docker: giao dịch đọc bảng tài khoản ở bước xác thực còn mở nên lệnh xóa dữ liệu phải chờ. Nhóm sửa bằng cách kết thúc giao dịch ngay sau khi xác thực và bổ sung ca kiểm thử phục hồi qua API.
- Bốn lỗi tương phản màu và nhãn trợ năng do axe-core phát hiện, cùng hai lỗi giao diện ở trang Trợ giúp (bảng tràn ngang, giảng viên mất liên kết quay lại trang Cảnh báo); tất cả đã được sửa.
