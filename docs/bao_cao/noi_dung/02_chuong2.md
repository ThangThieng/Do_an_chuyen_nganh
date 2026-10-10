# CHƯƠNG 2: XÁC ĐỊNH VÀ MÔ HÌNH HÓA YÊU CẦU PHẦN MỀM

## 2.1. Danh sách yêu cầu chức năng

Yêu cầu chức năng được xếp theo bốn nhóm: lưu trữ, tra cứu, tính toán và kết xuất. Phần lớn yêu cầu của hệ thống thuộc nhóm tra cứu và kết xuất vì dữ liệu gốc do Moodle tạo ra; phần tính toán nặng nhất (chấm điểm rủi ro, tổng hợp tiến độ) do tiến trình ETL đảm nhận theo lịch.

### 2.1.1. Phân hệ Quản trị hệ thống

Bảng: Yêu cầu chức năng của phân hệ Quản trị
%w 7,9,44,14,26
| STT | Mã | Tên yêu cầu | Loại | Quy định |
|---|---|---|---|---|
| 1 | YC01 | Thống kê quy mô đào tạo phân cấp Khoa – Môn – Sinh viên theo năm học, học kỳ, khoa | Tra cứu | QĐ4, QĐ8 |
| 2 | YC02 | Theo dõi lượt truy cập, người dùng online theo giờ, xác định giờ cao điểm | Tra cứu | QĐ5 |
| 3 | YC03 | Xem trước và xuất báo cáo Excel/PDF theo bộ lọc | Kết xuất | QĐ6 |
| 4 | YC04 | Tra cứu danh mục môn học và giảng viên phụ trách | Tra cứu | – |
| 5 | YC05 | Khóa, mở khóa tài khoản; đặt lại mật khẩu | Lưu trữ | QĐ2 |
| 6 | YC06 | Xem nhật ký các lần chạy ETL | Tra cứu | – |
| 7 | YC07 | Tạo, tải về, xóa bản sao lưu | Kết xuất | QĐ7 |
| 8 | YC08 | Phục hồi dữ liệu từ bản sao lưu | Lưu trữ | QĐ7 |

YC01–YC03 là ba chức năng Admin 1.1–1.3 của tài liệu yêu cầu. YC04–YC08 được bổ sung để hệ thống có đủ các nhánh Hệ thống và Danh mục của cấu trúc thực đơn chuẩn (mục 5.1).

### 2.1.2. Phân hệ Giảng viên

Bảng: Yêu cầu chức năng của phân hệ Giảng viên
%w 7,9,44,14,26
| STT | Mã | Tên yêu cầu | Loại | Quy định |
|---|---|---|---|---|
| 1 | YC09 | Xem danh sách cảnh báo sinh viên của môn phụ trách, lọc theo mức và tiêu chí | Tra cứu | QĐ1, QĐ8 |
| 2 | YC10 | Xem chi tiết một sinh viên: lý do, so sánh với trung bình lớp, hoạt động theo tuần | Tra cứu | QĐ1, QĐ8 |
| 3 | YC11 | Ghi nhận hành động can thiệp | Lưu trữ | QĐ9 |
| 4 | YC12 | Xuất danh sách cảnh báo của môn ra Excel/PDF | Kết xuất | QĐ6 |
| 5 | YC13 | Xem tiến độ và mức tương tác của lớp theo ngày hoặc tuần | Tra cứu | QĐ4 |

### 2.1.3. Chức năng chung và chức năng tự động

Bảng: Yêu cầu chức năng chung và chức năng do hệ thống tự thực hiện
%w 7,9,44,14,26
| STT | Mã | Tên yêu cầu | Loại | Quy định |
|---|---|---|---|---|
| 1 | YC14 | Đăng nhập, đăng xuất | Tra cứu | QĐ3 |
| 2 | YC15 | Đổi mật khẩu | Lưu trữ | QĐ2 |
| 3 | YC16 | Xem hướng dẫn sử dụng | Tra cứu | – |
| 4 | YC17 | Tính chỉ số, chấm điểm và xếp mức rủi ro cho từng sinh viên trong từng môn | Tính toán | QĐ1, QĐ4 |
| 5 | YC18 | Tổng hợp tiến độ môn theo ngày và lưu lượng theo giờ | Tính toán | QĐ4, QĐ5 |

### 2.1.4. Quy định nghiệp vụ

Bảng: Danh sách quy định
%w 8,18,74
| Mã | Tên | Nội dung |
|---|---|---|
| QĐ1 | Luật cảnh báo rủi ro | Mỗi sinh viên trong mỗi môn được chấm ba tiêu chí, mỗi tiêu chí 0–2 điểm.<br>• C1 Vắng học: dưới 15% số buổi → 0; 15% đến dưới 30% → 1; từ 30% → 2; môn chưa có buổi điểm danh → 0.<br>• C2 Không tương tác: chưa từng vào môn hoặc hơn 14 ngày không vào → 2; hơn 7 ngày không vào hoặc lượt truy cập 14 ngày dưới 50% trung vị lớp → 1; còn lại → 0.<br>• C3 Thiếu bài tập (chỉ tính bài đã tới hạn): dưới 20% → 0; 20% đến dưới 60% → 1; từ 60% → 2.<br>Xếp mức: ĐỎ khi C2 = 2, hoặc từ hai tiêu chí bằng 2, hoặc tổng từ 4; VÀNG khi tổng từ 1; XANH khi tổng bằng 0. Điểm rủi ro = làm tròn(100 × (0,35·C1 + 0,30·C2 + 0,35·C3) / 2). |
| QĐ2 | Mật khẩu | Ít nhất 8 ký tự, có chữ và số, không quá 72 byte, khác mật khẩu hiện tại. Đổi hoặc đặt lại mật khẩu làm mọi phiên đăng nhập cũ mất hiệu lực. Quản trị viên không tự khóa, không tự đặt lại mật khẩu của chính mình. |
| QĐ3 | Đăng nhập | Sai quá 5 lần trong 5 phút (theo IP và tên đăng nhập) thì tạm chặn. Phiên hết hạn sau 480 phút. Tài khoản bị khóa bị từ chối ngay ở yêu cầu kế tiếp. |
| QĐ4 | Sinh viên đăng ký, có tương tác | Đăng ký: có vai trò student trong môn, tài khoản không bị xóa hay khóa, phương thức và lượt ghi danh đang bật, đã bắt đầu và chưa hết hạn tại thời điểm tham chiếu. Có tương tác: có ít nhất một dòng nhật ký trong môn kể từ ngày môn bắt đầu. |
| QĐ5 | Online, giờ cao điểm | Online là có hoạt động trong khung 5 phút. Giờ cao điểm là giờ có lượt truy cập vượt phân vị 90 của 28 ngày gần nhất. |
| QĐ6 | Giới hạn xuất tệp | PDF tối đa 5.000 dòng, Excel tối đa 200.000 dòng. |
| QĐ7 | Sao lưu, phục hồi | Mỗi lúc chỉ một thao tác. Chỉ phục hồi bản cùng phiên bản cấu trúc CSDL. Phải gõ lại đúng tên tệp để xác nhận phục hồi. |
| QĐ8 | Phân quyền dữ liệu | Giảng viên chỉ xem dữ liệu các môn có mã mình trong danh sách phụ trách. Quản trị viên không dùng chức năng của giảng viên và ngược lại. |
| QĐ9 | Can thiệp | Loại hành động: tin nhắn Moodle, email, ghi chú, hẹn gặp. Nội dung tối đa 2.000 ký tự. Lưu kèm mức rủi ro của sinh viên lúc ghi nhận. |

Ba biểu mẫu kết xuất (BM1 – quy mô đào tạo và tương tác, BM2 – cảnh báo sinh viên, BM3 – lưu lượng theo giờ) có chung bố cục: tiêu đề, dòng mô tả bộ lọc và thời điểm dữ liệu, bảng số liệu.

## 2.2. Bảng trách nhiệm cho từng loại yêu cầu

### 2.2.1. Yêu cầu nghiệp vụ

Bảng: Bảng trách nhiệm yêu cầu nghiệp vụ
%w 6,20,30,34,10
| STT | Nghiệp vụ | Người dùng | Phần mềm | Ghi chú |
|---|---|---|---|---|
| 1 | Thống kê phân cấp | Chọn học kỳ, khoa; nhấn vào khoa, môn | Lấy số liệu mới nhất từng môn, cộng theo khoa, hiển thị KPI, biểu đồ, bảng | YC01 |
| 2 | Theo dõi lưu lượng | Chọn khoảng ngày (≤ 92 ngày) | Đọc số liệu theo giờ, đánh dấu giờ cao điểm, làm mới người online mỗi 60 giây | YC02 |
| 3 | Xuất báo cáo | Chọn loại, bộ lọc, định dạng | Kiểm tra giới hạn dòng, dựng tệp Excel/PDF | YC03, YC12 |
| 4 | Quản lý người dùng | Chọn tài khoản, xác nhận thao tác | Cập nhật trạng thái; sinh mật khẩu tạm, hiển thị một lần | YC05 |
| 5 | Sao lưu, phục hồi | Tạo bản sao lưu; hoặc chọn bản và gõ lại tên | Xuất dữ liệu ra tệp zip; kiểm tra phiên bản, nạp lại trong một giao dịch | YC07, YC08 |
| 6 | Cảnh báo sinh viên | Chọn môn, lọc mức, tiêu chí | Hiển thị danh sách xếp Đỏ → Vàng → Xanh kèm lý do | YC09 |
| 7 | Chi tiết, can thiệp | Mở chi tiết, chọn hành động | Hiển thị biểu đồ so sánh; lưu nhật ký can thiệp | YC10, YC11 |
| 8 | Tiến độ lớp | Chọn xem theo ngày hoặc tuần | Hiển thị thanh tiến độ và biểu đồ theo thời gian | YC13 |
| 9 | Tổng hợp số liệu | Không thao tác (chạy theo lịch) | Đọc Moodle, tính chỉ số, nạp CSDL phân tích, ghi nhật ký | YC17, YC18 |

### 2.2.2. Yêu cầu tiến hóa

Các tham số dưới đây nằm trong tệp cấu hình (`.env`, `etl/config.py`); người quản trị kỹ thuật sửa rồi khởi động lại dịch vụ.

Bảng: Bảng trách nhiệm yêu cầu tiến hóa
%w 6,26,36,32
| STT | Nghiệp vụ | Tham số cần thay đổi | Miền giá trị |
|---|---|---|---|
| 1 | Chấm điểm rủi ro | Ngưỡng vắng, ngưỡng thiếu bài, số ngày không truy cập, tỷ lệ so với trung vị lớp | Tỷ lệ 0–1; số ngày nguyên dương |
| 2 | Xếp mức rủi ro | Điều kiện mức ĐỎ | Có thể đặt lại luật gốc: một tiêu chí bằng 2 hoặc tổng từ 3 |
| 3 | Điểm rủi ro | Trọng số C1, C2, C3 | Số thực không âm |
| 4 | Giờ cao điểm | Phân vị, số ngày so sánh | Mặc định P90, 28 ngày |
| 5 | Xuất báo cáo | Số dòng tối đa PDF, Excel | Số nguyên dương |
| 6 | Đăng nhập | Thời gian hiệu lực phiên | Số phút |
| 7 | Nguồn dữ liệu | Kết nối CSDL Moodle; thời điểm tham chiếu | Chuỗi kết nối; mốc thời gian hoặc để trống |

### 2.2.3. Yêu cầu hiệu quả

Bảng: Bảng trách nhiệm yêu cầu hiệu quả
%w 6,26,46,22
| STT | Nghiệp vụ | Tốc độ xử lý | Ghi chú |
|---|---|---|---|
| 1 | Mở trang Dashboard | Biểu đồ đầu tiên dưới 1 giây, LCP dưới 2,5 giây | Cache trình duyệt trống |
| 2 | Truy vấn API | Mỗi câu SQL ≤ 100 ms; p95 < 500 ms, p99 < 1 s với 50 người dùng | Cả dữ liệu gấp 10 lần |
| 3 | Tổng hợp lưu lượng | Dưới 30 giây mỗi lần | 5 phút/lần |
| 4 | Chấm điểm rủi ro | Dưới 5 phút mỗi lần | 2 giờ/lần trong ngày |
| 5 | Chốt số liệu ngày | Dưới 20 phút | 01:00 hằng ngày |
| 6 | Xuất báo cáo | Excel 10.000 dòng, PDF 500 dòng dưới 5 giây | – |

### 2.2.4. Yêu cầu tiện dụng

Bảng: Bảng trách nhiệm yêu cầu tiện dụng
%w 6,22,36,36
| STT | Nghiệp vụ | Mức độ dễ học | Mức độ dễ sử dụng |
|---|---|---|---|
| 1 | Xem tổng quan | Thẻ KPI đặt trên cùng | Mọi biểu đồ chuyển được sang dạng bảng |
| 2 | Nhận biết mức rủi ro | Luôn có biểu tượng và chữ (● Nguy cơ cao, ▲ Cần lưu ý, ✔ An toàn), không chỉ dựa vào màu | Nhấn thẻ đèn hoặc lát cắt biểu đồ để lọc bảng |
| 3 | Hiểu lý do cảnh báo | Lý do viết thành câu, ví dụ "Vắng 9/18 buổi (50%)" | Mở chi tiết bằng một lần nhấn |
| 4 | Thao tác có rủi ro | Hộp thoại nói rõ hậu quả | Nút Phục hồi chỉ bật khi gõ đúng tên tệp |

### 2.2.5. Yêu cầu bảo mật

Bảng: Bảng phân quyền chức năng
%w 6,52,14,14,14
| STT | Nghiệp vụ | Quản trị viên | Giảng viên | Bộ lập lịch ETL |
|---|---|---|---|---|
| 1 | Đăng nhập, đổi mật khẩu, trợ giúp | X | X | |
| 2 | Thống kê phân cấp, lưu lượng, báo cáo toàn khoa, danh mục | X | | |
| 3 | Quản lý người dùng, nhật ký ETL, sao lưu, phục hồi | X | | |
| 4 | Cảnh báo, chi tiết, can thiệp, tiến độ (môn phụ trách) | | X | |
| 5 | Đọc CSDL Moodle, ghi CSDL phân tích | | | X |

Mật khẩu được băm bằng bcrypt. Mỗi yêu cầu mang JWT và được đối chiếu lại với bảng tài khoản, nên tài khoản bị khóa hoặc vừa đổi mật khẩu bị từ chối ngay. Mọi câu SQL dùng tham số bind; kết nối tới Moodle ở chế độ chỉ đọc.

### 2.2.6. Yêu cầu an toàn

Bảng: Bảng trách nhiệm yêu cầu an toàn
%w 6,24,34,36
| STT | Nghiệp vụ | Đối tượng | Ghi chú |
|---|---|---|---|
| 1 | Phục hồi | Toàn bộ CSDL phân tích | Lỗi giữa chừng thì giữ nguyên dữ liệu cũ |
| 2 | Hủy thật sự | Bản sao lưu | Xóa tệp sau khi xác nhận |
| 3 | Không cho phép xóa | Tài khoản, nhật ký can thiệp, nhật ký ETL | Tài khoản chỉ khóa; nhật ký giữ làm vết |
| 4 | Không cho phép ghi | CSDL Moodle | ETL chỉ đọc, giới hạn truy vấn 60 giây |

Về tương thích, câu truy vấn trích xuất viết theo đúng tên bảng, tên cột của Moodle 3.9 nên khi có CSDL Moodle thật chỉ cần đổi thông tin kết nối; giao diện chạy trên Chrome, Edge và dùng được ở màn hình rộng 390 px.

## 2.3. Mô hình hóa yêu cầu

### 2.3.1. Mô hình Use case

Bảng: Danh sách tác nhân
%w 6,24,70
| STT | Tác nhân | Mô tả |
|---|---|---|
| 1 | Người dùng | Tác nhân tổng quát; Quản trị viên và Giảng viên kế thừa từ tác nhân này |
| 2 | Quản trị viên | Người quản lý đào tạo, quản trị hệ thống; xem số liệu toàn khoa |
| 3 | Giảng viên | Người phụ trách môn học; chỉ thấy dữ liệu các môn của mình |
| 4 | Bộ lập lịch ETL | Tác nhân thời gian, kích hoạt các job tổng hợp dữ liệu |
| 5 | Moodle LMS | Hệ thống bên ngoài, cung cấp dữ liệu nguồn ở chế độ chỉ đọc |

![Sơ đồ use case tổng quát](docs/diagrams/png/uc_tong_quat.png){w=12}

![Sơ đồ use case phân hệ Quản trị](docs/diagrams/png/uc_quan_tri.png){w=13}

Trong phân hệ Quản trị, mọi use case đều bao hàm (include) việc đăng nhập vì API kiểm tra token và vai trò ở từng yêu cầu. Xem danh sách môn của khoa, rồi sinh viên của môn, là phần mở rộng (extend) của thống kê phân cấp, chỉ xảy ra khi người dùng chủ động nhấn vào. Xem trước báo cáo là tùy chọn nên cũng là extend; xác nhận tên bản sao lưu là bắt buộc trong mỗi lần phục hồi nên là include.

![Sơ đồ use case phân hệ Giảng viên](docs/diagrams/png/uc_giang_vien.png){w=15}

![Sơ đồ use case của tiến trình ETL](docs/diagrams/png/uc_etl.png){w=13}

Tiến trình ETL được mô hình như một nhóm use case riêng với tác nhân thời gian, vì dữ liệu giảng viên nhìn thấy phụ thuộc vào lần chạy ETL gần nhất.

Các bảng dưới đây đặc tả những use case chính. Các use case tra cứu UC03, UC05, UC07, UC09, UC16 có cùng luồng "mở màn hình, chọn bộ lọc, hệ thống hiển thị kết quả"; UC15 giống UC06 nhưng chỉ trong môn của giảng viên; UC02 được mô tả bằng sơ đồ tuần tự ở mục 3.4.2.

Bảng: Đặc tả use case UC01 – Đăng nhập
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Người dùng |
| Tiền điều kiện | Tài khoản đã được đồng bộ từ Moodle và đang hoạt động |
| Hậu điều kiện | Có phiên đăng nhập hạn 480 phút; thời điểm đăng nhập được ghi lại |
| Luồng chính | 1. Nhập tên đăng nhập, mật khẩu.<br>2. Hệ thống kiểm tra số lần đăng nhập sai gần đây.<br>3. Hệ thống so khớp mật khẩu băm và trạng thái tài khoản.<br>4. Hệ thống cấp token, chuyển tới trang Tổng quan (quản trị viên) hoặc trang Cảnh báo của môn đầu tiên (giảng viên). |
| Luồng phụ | 1a. Bỏ trống ô: báo lỗi tại ô.<br>2a. Sai quá 5 lần trong 5 phút: từ chối, báo số giây phải chờ.<br>3a. Sai mật khẩu, không có tài khoản hoặc bị khóa: thông báo chung "Sai tên đăng nhập hoặc mật khẩu". |

Bảng: Đặc tả use case UC04 – Thống kê phân cấp Khoa – Môn – Sinh viên
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Quản trị viên |
| Tiền điều kiện | Đã đăng nhập với vai trò quản trị; ETL đã nạp số liệu |
| Luồng chính | 1. Hệ thống mở trang Tổng quan với học kỳ của dữ liệu mới nhất, hiển thị sáu thẻ KPI, biểu đồ lưu lượng, biểu đồ cột chồng theo khoa, bảng phân cấp, heatmap.<br>2. Quản trị viên đổi năm học, học kỳ, khoa; mọi thành phần cập nhật theo.<br>3. Nhấn vào một khoa: hiển thị các môn của khoa.<br>4. Nhấn "Xem SV": hiển thị sinh viên của môn, lọc có/không tương tác, tìm theo MSSV, họ tên. |
| Luồng phụ | Tỷ lệ chưa có dữ liệu để tính hiển thị "Chưa có dữ liệu" thay vì 0%. |

Bảng: Đặc tả use case UC06 – Xuất báo cáo Excel/PDF
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Quản trị viên |
| Hậu điều kiện | Tệp báo cáo được lưu về máy người dùng |
| Luồng chính | 1. Chọn loại báo cáo BM1, BM2 hoặc BM3 và đặt bộ lọc.<br>2. Nhấn "Xuất Excel" hoặc "Xuất PDF".<br>3. Hệ thống truy vấn, dựng tệp có dòng mô tả bộ lọc và thời điểm dữ liệu. |
| Luồng phụ | 1a (mở rộng). Nhấn "Xem trước": hiển thị bảng phân trang 20–200 dòng.<br>3a. Vượt giới hạn QĐ6: báo lỗi, đề nghị thu hẹp bộ lọc. |

Bảng: Đặc tả use case UC08 – Quản lý người dùng
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Quản trị viên |
| Luồng chính | 1. Mở Hệ thống › Quản lý người dùng; hệ thống hiển thị tài khoản kèm vai trò, số môn phụ trách, trạng thái, lần đăng nhập và đổi mật khẩu gần nhất.<br>2. Lọc theo vai trò hoặc tìm theo tên. |
| Điểm mở rộng | Khóa/mở khóa: xác nhận, hệ thống cập nhật trạng thái; tài khoản bị khóa bị từ chối ngay.<br>Đặt lại mật khẩu: xác nhận, hệ thống sinh mật khẩu tạm 12 ký tự, hiển thị một lần; phiên cũ mất hiệu lực. |
| Luồng phụ | Thao tác lên chính tài khoản đang đăng nhập: giao diện không hiển thị nút; API từ chối nếu vẫn gửi. |

Bảng: Đặc tả use case UC10, UC11 – Sao lưu và phục hồi dữ liệu
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Quản trị viên |
| Tiền điều kiện | Không có thao tác sao lưu hoặc phục hồi khác đang chạy |
| Luồng sao lưu | 1. Nhấn "Tạo bản sao lưu".<br>2. Hệ thống đọc tám bảng trong một ảnh chụp dữ liệu, ghi CSV từng bảng và tệp mô tả `manifest.json` vào tệp zip.<br>3. Thông báo tên tệp, số dòng, dung lượng. |
| Luồng phục hồi | 1. Nhấn "Phục hồi" ở một bản sao lưu; gõ lại đúng tên tệp (include "Xác nhận tên bản sao lưu").<br>2. Hệ thống kiểm tra phiên bản cấu trúc.<br>3. Trong một giao dịch: xóa dữ liệu tám bảng, nạp lại từng bảng, đối chiếu số dòng, đặt lại bộ đếm khóa tự tăng.<br>4. Thông báo số dòng đã nạp; mọi màn hình tải lại số liệu. |
| Luồng phụ | Khác phiên bản, số dòng không khớp hoặc lỗi bất kỳ: hủy giao dịch, dữ liệu giữ nguyên. |

Bảng: Đặc tả use case UC12 – Xem cảnh báo sinh viên nguy cơ
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Giảng viên |
| Tiền điều kiện | Được phân công ít nhất một môn |
| Luồng chính | 1. Chọn môn ở thanh tiêu đề (include "Chọn môn học phụ trách").<br>2. Hệ thống kiểm tra giảng viên có phụ trách môn.<br>3. Hệ thống hiển thị ba thẻ đèn giao thông, biểu đồ tròn, số sinh viên theo tiêu chí và bảng cảnh báo xếp Đỏ → Vàng → Xanh. |
| Luồng phụ | 1a. Chưa được phân công môn: thông báo, không hiển thị bảng.<br>2a. Môn của giảng viên khác: từ chối truy cập. |

Bảng: Đặc tả use case UC13, UC14 – Xem chi tiết sinh viên, ghi nhận can thiệp
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Giảng viên |
| Hậu điều kiện | (UC14) Một dòng nhật ký can thiệp kèm mức rủi ro lúc ghi |
| Luồng chính | 1. Nhấn "Chi tiết" ở một dòng.<br>2. Hệ thống hiển thị lý do, biểu đồ so sánh với trung bình lớp, hoạt động theo tuần, bài tập, lịch sử cảnh báo và can thiệp.<br>3. (UC14) Chọn một trong bốn hành động, nhập nội dung; hệ thống lưu và hiển thị ngay trong lịch sử. |
| Luồng phụ | 3a. "Gửi tin nhắn Moodle": hệ thống báo chỉ ghi nhật ký, chưa gửi tin nhắn thật.<br>3b. "Email": cung cấp liên kết mở ứng dụng thư.<br>3c. Nội dung quá 2.000 ký tự: báo lỗi tại ô. |

Bảng: Đặc tả use case UC17 – Đồng bộ và tổng hợp dữ liệu (ETL)
%w 22,78
| Thành phần | Nội dung |
|---|---|
| Tác nhân | Bộ lập lịch ETL (chính); Moodle LMS (phụ) |
| Hậu điều kiện | Bảng fact được cập nhật; nhật ký ghi một lần chạy SUCCESS hoặc FAILED |
| Luồng chính | 1. Đến lịch, job xin khóa riêng và ghi nhật ký RUNNING.<br>2. Job đọc Moodle trong một giao dịch chỉ đọc.<br>3. Job tính chỉ số, chấm điểm theo QĐ1.<br>4. Job nạp qua bảng tạm, chỉ cập nhật dòng có giá trị thay đổi.<br>5. Job ghi SUCCESS kèm số dòng đọc, ghi; trả khóa. |
| Luồng phụ | 1a. Job cùng loại đang chạy: bỏ qua lượt.<br>2a–4a. Có lỗi: ghi FAILED kèm thông báo; thử lại sau 1, 5, 15 phút (job lưu lượng không thử lại vì lượt kế tiếp tự bù). |

### 2.3.2. Sơ đồ luồng dữ liệu (DFD)

Các DFD dùng hình chữ nhật cho tác nhân ngoài, hình tròn cho khối xử lý, mũi tên có nhãn cho luồng dữ liệu và cặp đường song song cho bộ nhớ phụ. Luồng dữ liệu theo quy ước: D1 – người dùng gửi vào, D2 – thiết bị nhập, D3 – đọc từ bộ nhớ phụ, D4 – ghi xuống bộ nhớ phụ, D5 – thiết bị xuất, D6 – trả về người dùng.

Tên bộ nhớ phụ trên sơ đồ là tên nghiệp vụ: TÀI KHOẢN (`app_user`), TIẾN ĐỘ MÔN THEO NGÀY (`fact_course_progress_daily`), CẢNH BÁO SINH VIÊN (`fact_student_risk_summary`), LƯU LƯỢNG THEO GIỜ (`fact_server_traffic_hourly`), MẪU NGƯỜI ONLINE (`etl_online_snapshot`), NHẬT KÝ ETL (`etl_run_log`), NHẬT KÝ CAN THIỆP (`intervention_log`), CSDL PHÂN TÍCH (cả tám bảng), CSDL MOODLE (`moodle_src`).

#### a) DFD mức ngữ cảnh

![DFD mức ngữ cảnh](docs/diagrams/png/dfd_ngu_canh.png){w=15}

Moodle chỉ có luồng đi vào hệ thống; hệ thống không ghi ngược dữ liệu nào về Moodle ở mọi mức chi tiết.

#### b) Đăng nhập (YC14)

![DFD Đăng nhập](docs/diagrams/png/dfd_dang_nhap.png){w=9}

D1: tên đăng nhập, mật khẩu. D3: tài khoản trùng tên (mật khẩu băm, vai trò, trạng thái). D4: thời điểm đăng nhập. D6: token hoặc thông báo lỗi.

Thuật toán: (1) nhận D1; (2) nếu vượt QĐ3 thì trả D6 lỗi; (3) đọc D3, so khớp mật khẩu băm và trạng thái, sai thì tăng bộ đếm và trả D6 lỗi; (4) ghi D4; (5) tạo token, trả D6.

#### c) Đổi mật khẩu (YC15)

![DFD Đổi mật khẩu](docs/diagrams/png/dfd_doi_mat_khau.png){w=9}

D1: mật khẩu hiện tại, mật khẩu mới. D3: mật khẩu băm hiện tại. D4: mật khẩu băm mới và thời điểm đổi. D6: token mới hoặc lý do từ chối.

Thuật toán: (1) nhận D1; (2) đọc D3, so khớp mật khẩu hiện tại; (3) kiểm tra QĐ2; (4) ghi D4; (5) tạo token mới, trả D6.

#### d) Thống kê phân cấp (YC01)

![DFD Thống kê phân cấp](docs/diagrams/png/dfd_thong_ke_phan_cap.png){w=9}

D1: năm học, học kỳ, khoa; khoa hoặc môn được chọn; bộ lọc sinh viên. D3: dòng tiến độ mới nhất của từng môn; danh sách sinh viên của môn. D6: thẻ KPI, dữ liệu biểu đồ cột chồng, bảng phân cấp.

Thuật toán: (1) nhận D1, chưa chọn học kỳ thì lấy học kỳ của dữ liệu mới nhất; (2) đọc D3 là dòng mới nhất của từng môn; (3) cộng số sinh viên đăng ký, tương tác và số lượng từng mức rủi ro theo khoa; (4) khi chọn môn, đọc danh sách sinh viên, lọc và phân trang; (5) trả D6. Lấy dòng mới nhất của từng môn thay vì một ngày chung giúp môn kết thúc sớm không biến mất khỏi thống kê.

#### e) Theo dõi lưu lượng (YC02)

![DFD Theo dõi lưu lượng](docs/diagrams/png/dfd_luu_luong.png){w=9}

D1: khoảng ngày, số tuần heatmap. D3: số liệu theo giờ, mẫu online 5 phút. D6: biểu đồ hai trục, 10 giờ đông nhất, heatmap, người online hiện tại.

Thuật toán: (1) nhận D1, kiểm tra khoảng không quá 92 ngày; (2) đọc D3; (3) tính trung bình giờ × thứ, chỉ dùng ngày trọn vẹn; (4) lấy mẫu online gần nhất; (5) trả D6.

#### f) Xuất báo cáo (YC03, YC12)

![DFD Xuất báo cáo](docs/diagrams/png/dfd_xuat_bao_cao.png){w=10}

D1: loại báo cáo, bộ lọc, định dạng. D3: dữ liệu thỏa bộ lọc. D5: tệp Excel hoặc PDF. D6: tên tệp hoặc lý do lỗi.

Thuật toán: (1) nhận D1; (2) đọc D3, lấy tối đa giới hạn cộng một dòng; (3) vượt QĐ6 thì trả D6 lỗi; (4) dựng tệp theo biểu mẫu kèm dòng mô tả bộ lọc; (5) xuất D5, trả D6. Với YC12, bộ lọc luôn gồm môn học và mã giảng viên đang đăng nhập.

#### g) Quản lý người dùng (YC05)

![DFD Quản lý người dùng](docs/diagrams/png/dfd_quan_ly_nguoi_dung.png){w=9}

D1: tài khoản, thao tác. D3: danh sách tài khoản, số môn phụ trách. D4: trạng thái mới hoặc mật khẩu băm mới. D6: danh sách cập nhật, mật khẩu tạm (một lần).

Thuật toán: (1) nhận D1; (2) thao tác lên chính mình thì từ chối; (3) đọc D3 kiểm tra tài khoản tồn tại; (4) đặt lại mật khẩu thì sinh chuỗi ngẫu nhiên 12 ký tự có chữ và số; (5) ghi D4, trả D6.

#### h) Phục hồi dữ liệu (YC08)

![DFD Phục hồi dữ liệu](docs/diagrams/png/dfd_phuc_hoi.png){w=10}

D1: tên bản sao lưu, tên gõ lại. D2: nội dung tệp sao lưu. D3: phiên bản cấu trúc hiện tại; số dòng sau khi nạp. D4: dữ liệu mới của tám bảng. D6: số dòng đã nạp hoặc lý do từ chối.

Thuật toán: (1) nhận D1, kiểm tra tên gõ lại; (2) đọc tệp mô tả trong D2; (3) đọc D3, so sánh phiên bản; (4) mở giao dịch, xóa dữ liệu tám bảng; (5) nạp từng bảng (bảng cha trước) thành D4, đối chiếu số dòng; (6) đặt lại bộ đếm khóa tự tăng, xác nhận giao dịch; (7) trả D6. Lỗi ở bước (4)–(6) hủy toàn bộ giao dịch.

#### i) Xem cảnh báo sinh viên (YC09)

![DFD Xem cảnh báo sinh viên](docs/diagrams/png/dfd_canh_bao.png){w=9}

D1: môn, mức rủi ro, tiêu chí, từ khóa, sắp xếp, trang. D3: danh sách giảng viên của môn; ảnh chụp rủi ro mới nhất. D6: số lượng theo mức, theo tiêu chí và bảng cảnh báo.

Thuật toán: (1) nhận D1; (2) đọc D3, người gọi không phụ trách môn thì từ chối; (3) đọc ảnh chụp ngày gần nhất với điều kiện mã giảng viên nằm trong danh sách phụ trách; (4) lọc, sắp xếp, phân trang; (5) trả D6.

#### j) Ghi nhận can thiệp (YC11)

![DFD Ghi nhận can thiệp](docs/diagrams/png/dfd_can_thiep.png){w=9}

D1: loại hành động, nội dung. D3: mức rủi ro hiện tại của sinh viên. D4: dòng nhật ký can thiệp. D6: mã và thời điểm ghi nhận.

Thuật toán: (1) nhận D1, kiểm tra QĐ9; (2) kiểm tra quyền với môn; (3) đọc D3, sinh viên không còn trong lớp thì từ chối; (4) ghi D4 kèm mức rủi ro vừa đọc; (5) trả D6.

#### k) Chấm điểm rủi ro (YC17)

![DFD Chấm điểm rủi ro](docs/diagrams/png/dfd_etl_rui_ro.png){w=10}

D1: tín hiệu kích hoạt và thời điểm tham chiếu. D3 (CSDL MOODLE): khóa học, ghi danh, nhật ký, điểm danh, bài tập, hoàn thành hoạt động. D3 (CẢNH BÁO SINH VIÊN): dòng hiện có để so sánh. D4: ảnh chụp rủi ro, nhật ký lần chạy. D6: kết quả lần chạy.

Thuật toán: (1) nhận D1, xin khóa job, job đang chạy thì kết thúc; (2) ghi D4 trạng thái RUNNING; (3) đọc D3 từ Moodle trong một giao dịch chỉ đọc; (4) với mỗi cặp sinh viên – môn, tính số buổi vắng, số ngày chưa truy cập, lượt truy cập 7 và 14 ngày, số bài tới hạn và bài thiếu; (5) tính trung vị lớp, chấm C1–C3, xếp mức theo QĐ1, ghép lý do; (6) ghi D4 những dòng thay đổi, xóa dòng của sinh viên không còn ghi danh; (7) ghi SUCCESS hoặc FAILED, trả khóa, trả D6.

#### l) Các yêu cầu tra cứu còn lại

Sáu yêu cầu dưới đây có cùng dạng DFD tra cứu (chỉ có D1, D3, D6; riêng sao lưu có thêm D5), nên được tóm tắt trong bảng.

Bảng: Luồng dữ liệu của các yêu cầu tra cứu còn lại
%w 20,26,30,24
| Yêu cầu | D1 | D3 | D6 (D5) |
|---|---|---|---|
| YC04 Danh mục môn học | Học kỳ, khoa | Dòng tiến độ mới nhất từng môn; họ tên giảng viên | Danh sách môn kèm giảng viên |
| YC06 Nhật ký ETL | Job, trạng thái | Các lần chạy | Bảng lần chạy, trạng thái từng job |
| YC07 Sao lưu | Lệnh tạo | Dữ liệu tám bảng, phiên bản cấu trúc | D5: tệp zip; D6: tên tệp, số dòng |
| YC10 Chi tiết sinh viên | Môn, sinh viên | Chỉ số, lý do, hoạt động tuần, bài tập, lịch sử, can thiệp | Nội dung cửa sổ chi tiết, số liệu so sánh |
| YC13 Tiến độ lớp | Môn, gộp theo ngày/tuần | Dòng tiến độ theo ngày | Thẻ, thanh tiến độ, chuỗi theo thời gian |
| YC16 Hướng dẫn | Vai trò | – | Nội dung hướng dẫn |

Khi gộp tiến độ theo tuần (YC13), các tỷ lệ lấy giá trị ngày cuối tuần, còn lượt xem, thao tác, bài nộp được cộng dồn; cộng dồn tỷ lệ theo ngày sẽ cho kết quả sai.
