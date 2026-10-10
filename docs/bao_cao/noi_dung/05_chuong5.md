# CHƯƠNG 5: THIẾT KẾ MÀN HÌNH

## 5.1. Sơ đồ liên kết màn hình

### 5.1.1. Nguyên tắc thiết kế giao diện

Giao diện theo ba nguyên tắc của tài liệu yêu cầu. Thứ nhất, các chỉ số chính đặt thành thẻ KPI ở hàng trên cùng để nắm tình hình trong vài giây. Thứ hai, mức rủi ro dùng màu đèn giao thông (đỏ – nguy cơ cao, vàng – cần lưu ý, xanh – an toàn) nhưng luôn kèm biểu tượng (● ▲ ✔) và chữ, vì theo kiểm tra mô phỏng của nhóm, người mù màu đỏ – lục gần như không phân biệt được hai màu đỏ và xanh của đề tài. Thứ ba, người dùng đi từ biểu đồ tổng quát xuống cấp môn, cấp sinh viên bằng cách nhấn vào.

Mỗi màn hình trả lời bốn câu hỏi định vị: mục đang chọn trên thanh menu được tô sáng và mỗi khung có tiêu đề (*tôi đang ở đâu*); breadcrumb ở bảng phân cấp và bộ lọc hiển thị trên nội dung (*tôi đến đây bằng cách nào*); nút thao tác đặt cạnh nội dung chúng tác động (*tôi làm được gì*); menu luôn hiển thị, các nút "Xem SV", "Chi tiết" dẫn xuống cấp dưới (*tôi đi tiếp đâu được*).

Về nhập liệu, giao diện dùng ô chọn thay cho gõ phím (năm học, học kỳ, khoa, loại báo cáo, mức rủi ro), khóa nút chưa dùng được, kiểm tra định dạng khi rời ô và kiểm tra quan hệ giữa các ô khi nhấn Lưu. Về kết xuất, biểu đồ dùng để thấy xu hướng, còn mọi biểu đồ có nút chuyển sang dạng bảng khi cần con số chính xác.

### 5.1.2. Sơ đồ liên kết và cấu trúc thực đơn

![Sơ đồ liên kết màn hình](docs/diagrams/png/screen_flow.png){w=15}

Bảng: Ánh xạ cấu trúc thực đơn năm nhánh sang hệ thống
%w 18,44,38
| Nhánh | Mục trong hệ thống | Ghi chú |
|---|---|---|
| Hệ thống | Quản lý người dùng, Nhật ký ETL, Sao lưu & phục hồi; Tài khoản & đổi mật khẩu, Đăng xuất (menu tài khoản) | Chỉ quản trị viên thấy menu "Hệ thống" |
| Danh mục | Danh mục môn học | Chỉ tra cứu; khoa, môn, phân công được quản lý trong Moodle |
| Nghiệp vụ | Tổng quan, Lưu lượng; Cảnh báo, Tiến độ lớp | Màn hình dùng hằng ngày |
| Báo cáo thống kê | Báo cáo; nút Xuất danh sách ở trang Cảnh báo | |
| Trợ giúp | Hướng dẫn theo vai trò, cách xếp mức rủi ro, giới thiệu | |

Sao lưu và phục hồi được đặt ở nhánh "Hệ thống" thay vì "Trợ giúp & Tiện ích" vì chỉ quản trị viên được dùng, trong khi nhánh Trợ giúp dành cho mọi người dùng.

## 5.2. Danh sách các màn hình

Bảng: Danh sách màn hình
%w 9,26,16,33,16
| Mã | Tên màn hình | Vai trò | Ý nghĩa | Use case |
|---|---|---|---|---|
| MH01 | Đăng nhập | Mọi người dùng | Xác thực, chuyển tới phân hệ đúng vai trò | UC01 |
| MH02 | Tổng quan | Quản trị viên | KPI, lưu lượng, cột chồng theo khoa, bảng phân cấp, heatmap | UC04 |
| MH03 | Lưu lượng | Quản trị viên | Lưu lượng theo giờ, người online, giờ cao điểm | UC05 |
| MH04 | Báo cáo | Quản trị viên | Xem trước và xuất ba biểu mẫu | UC06 |
| MH05 | Danh mục môn học | Quản trị viên | Môn, bộ môn, giảng viên phụ trách | UC07 |
| MH06 | Quản lý người dùng | Quản trị viên | Khóa/mở khóa, đặt lại mật khẩu | UC08 |
| MH07 | Nhật ký ETL | Quản trị viên | Trạng thái và lịch sử chạy job | UC09 |
| MH08 | Sao lưu & phục hồi | Quản trị viên | Tạo, tải, xóa, phục hồi bản sao lưu | UC10, UC11 |
| MH09 | Cảnh báo sinh viên | Giảng viên | Đèn giao thông, biểu đồ tròn, bảng cảnh báo | UC12, UC15 |
| MH10 | Chi tiết sinh viên | Giảng viên | Lý do, so sánh, hoạt động theo tuần, can thiệp | UC13, UC14 |
| MH11 | Tiến độ lớp | Giảng viên | Thanh tiến độ, tiến độ theo chương, biểu đồ theo thời gian | UC16 |
| MH12 | Tài khoản & đổi mật khẩu | Mọi người dùng | Thông tin tài khoản, đổi mật khẩu | UC02 |
| MH13 | Trợ giúp | Mọi người dùng | Hướng dẫn theo vai trò, luật xếp mức, giới thiệu | UC03 |

## 5.3. Mô tả các màn hình

Ảnh chụp từ hệ thống đang chạy với dữ liệu mô phỏng tại thời điểm tham chiếu 06/11/2026 10:30; góc phải thanh tiêu đề ghi thời điểm này và thời điểm ETL chạy thành công gần nhất.

### 5.3.1. MH01 – Đăng nhập

![Màn hình đăng nhập](docs/images/report/mh01_dang_nhap.png){w=12}

Khi sai mật khẩu, hệ thống chỉ báo chung "Sai tên đăng nhập hoặc mật khẩu", không cho biết tên đăng nhập có tồn tại hay không; biểu mẫu bị khóa trong lúc chờ phản hồi để tránh gửi hai lần.

### 5.3.2. MH02 – Tổng quan

![Màn hình Tổng quan của quản trị viên](docs/images/report/mh02_tong_quan.png){w=14}

Bảng: Các thành phần của màn hình Tổng quan
%w 6,26,20,48
| STT | Thành phần | Kiểu | Ý nghĩa |
|---|---|---|---|
| 1 | Năm học, Học kỳ, Khoa | Ô chọn | Bộ lọc cho toàn trang |
| 2 | Làm mới, Export | Nút, menu thả | Tải lại số liệu; xuất nhanh báo cáo theo bộ lọc |
| 3 | Sáu thẻ KPI | Thẻ | Tổng môn học, SV đăng ký, SV tương tác, online hiện tại, giờ cao điểm hôm nay, SV nguy cơ cao |
| 4 | Lưu lượng truy cập | Biểu đồ đường hai trục | Lượt truy cập (trục trái), người online trung bình (trục phải); vùng tô nền là giờ cao điểm |
| 5 | SV đăng ký và tương tác theo khoa | Biểu đồ cột chồng | Nhấn cột để mở danh sách môn của khoa |
| 6 | Thống kê phân cấp | Bảng + breadcrumb | Khoa ▸ Môn ▸ Sinh viên |
| 7 | Heatmap giờ × thứ | Biểu đồ nhiệt | Trung bình 4 tuần gần nhất |

![Bảng phân cấp ở cấp sinh viên](docs/images/report/mh02_drill_sinh_vien.png){w=13}

Ở cấp sinh viên, người dùng lọc "Có tương tác" hoặc "Không tương tác", tìm theo MSSV, họ tên, email; breadcrumb "Tất cả › Khoa › Môn" cho phép quay lại cấp trên.

### 5.3.3. MH03 – Lưu lượng

![Màn hình Lưu lượng](docs/images/report/mh03_luu_luong.png){w=14}

Bốn thẻ cho biết người online hiện tại (tự làm mới mỗi 60 giây), lượt truy cập hôm nay, giờ đông nhất và người online trung bình. Biểu đồ hai trục dùng nét liền cho lượt truy cập, nét đứt cho người online và ghi rõ đại lượng thuộc trục nào; bảng "Top 10 giờ đông nhất" cho con số chính xác.

### 5.3.4. MH04 – Báo cáo

![Màn hình Báo cáo với bảng xem trước](docs/images/report/mh04_bao_cao.png){w=14}

Ô lọc thay đổi theo loại báo cáo; ô "Môn học" chỉ bật sau khi chọn khoa. Ô trống trong bảng xem trước hiển thị "–" (chưa có dữ liệu để tính), khác với 0%.

### 5.3.5. MH05 – Danh mục môn học

![Màn hình Danh mục môn học](docs/images/report/mh05_danh_muc.png){w=14}

### 5.3.6. MH06 – Quản lý người dùng

![Màn hình Quản lý người dùng](docs/images/report/mh06_nguoi_dung.png){w=14}

Dòng của chính người đang đăng nhập không có nút thao tác. Mỗi thao tác qua hộp thoại xác nhận nêu rõ hậu quả; mật khẩu tạm sau khi đặt lại hiện một lần kèm nút sao chép.

### 5.3.7. MH07 – Nhật ký ETL

![Màn hình Nhật ký ETL](docs/images/report/mh07_nhat_ky_etl.png){w=14}

### 5.3.8. MH08 – Sao lưu & phục hồi

![Màn hình Sao lưu & phục hồi](docs/images/report/mh08_sao_luu.png){w=14}

Mở rộng một dòng để xem số dòng từng bảng. Hộp thoại phục hồi chỉ bật nút Phục hồi khi gõ đúng tên tệp; trong lúc phục hồi, các nút bị khóa và hộp thoại không đóng được.

### 5.3.9. MH09 – Cảnh báo sinh viên

![Màn hình Cảnh báo sinh viên của giảng viên](docs/images/report/mh09_canh_bao.png){w=14}

Bảng: Các thành phần của màn hình Cảnh báo sinh viên
%w 6,26,20,48
| STT | Thành phần | Kiểu | Ý nghĩa |
|---|---|---|---|
| 1 | Chọn môn | Ô chọn có tìm kiếm | Chỉ liệt kê môn giảng viên phụ trách |
| 2 | Ba thẻ đèn giao thông | Thẻ nhấn được | Số và tỷ lệ sinh viên mỗi mức; nhấn để lọc bảng |
| 3 | Tỷ lệ rủi ro | Biểu đồ tròn | Nhấn lát cắt để lọc; kèm số sinh viên theo từng tiêu chí |
| 4 | Tìm MSSV/tên, Mức, Tiêu chí, Xuất danh sách | Ô tìm, ô chọn, menu | Lọc bảng; xuất Excel/PDF theo bộ lọc |
| 5 | Bảng cảnh báo | Bảng | Mức, MSSV, họ tên, vắng, truy cập cuối, bài tập, điểm, lý do, nút Chi tiết |

Trên điện thoại (rộng 390 px), các thẻ xếp dọc, bảng cuộn ngang trong khung riêng và trang không bị cuộn ngang.

### 5.3.10. MH10 – Chi tiết sinh viên

![Cửa sổ Chi tiết sinh viên](docs/images/report/mh10_chi_tiet_sinh_vien.png){w=13}

Dòng lý do viết bằng câu chữ. Biểu đồ so sánh tách thành hai nhóm (tỷ lệ phần trăm và số lượt truy cập) để các thanh so sánh được với nhau. Biểu đồ theo tuần dùng chấm đặc cho tuần có mặt đủ, chấm rỗng cho tuần có buổi vắng. Bốn nút cuối cửa sổ ghi nhận hành động can thiệp.

### 5.3.11. MH11 – Tiến độ lớp

![Màn hình Tiến độ lớp](docs/images/report/mh11_tien_do_lop.png){w=14}

Khi một tỷ lệ chưa tính được, thanh tiến độ được thay bằng lý do cụ thể ("Môn chưa có buổi điểm danh"); biểu đồ theo thời gian để khoảng trống ở ngày chưa có dữ liệu thay vì nối xuống 0.

### 5.3.12. MH12 – Tài khoản & đổi mật khẩu

![Màn hình Tài khoản & đổi mật khẩu, đang báo lỗi kiểm tra dữ liệu](docs/images/report/mh12_doi_mat_khau.png){w=14}

Ảnh chụp cho thấy hai mức kiểm tra: ô "Mật khẩu mới" báo lỗi khi rời ô (thiếu chữ số), ô "Nhập lại" báo lỗi khi nhấn Lưu vì không khớp.

### 5.3.13. MH13 – Trợ giúp

![Trang Trợ giúp của quản trị viên](docs/images/report/mh13_tro_giup_quan_tri.png){w=14}

Nội dung hướng dẫn thay đổi theo vai trò; phần luật xếp mức giống nhau cho cả hai vai trò và nhắc rằng mức rủi ro là tín hiệu để giảng viên chú ý, không phải kết luận về kết quả học tập.
