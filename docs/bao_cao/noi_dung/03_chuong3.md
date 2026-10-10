# CHƯƠNG 3: THIẾT KẾ HỆ THỐNG

## 3.1. Kiến trúc hệ thống

Hệ thống có hai loại công việc với tính chất trái ngược. Đọc và tổng hợp dữ liệu Moodle là việc nặng nhưng chỉ cần làm định kỳ; hiển thị Dashboard phải nhanh nhưng chỉ đọc những con số đã tính sẵn. Vì vậy nhóm tách hệ thống thành hai nhánh độc lập, gặp nhau ở một CSDL phân tích. Nhánh xử lý dữ liệu (ETL) chạy theo lịch, đọc Moodle ở chế độ chỉ đọc, tính toán và ghi kết quả vào CSDL phân tích. Nhánh phục vụ người dùng gồm giao diện React và API FastAPI, chỉ truy vấn CSDL phân tích. Bên trong ứng dụng web là kiến trúc nhiều tầng: trình bày (React), dịch vụ (router FastAPI), truy cập dữ liệu (repository chứa câu SQL) và lưu trữ (PostgreSQL).

![Sơ đồ kiến trúc thành phần của hệ thống](docs/diagrams/png/comp_kien_truc.png){w=16}

Cách tách này đáp ứng hai yêu cầu của đề tài: Dashboard phản hồi dưới 1 giây và không làm chậm máy chủ Moodle. Đổi lại, số liệu không tức thời: cảnh báo có thể trễ tối đa khoảng 2 giờ, lưu lượng tối đa 5 phút. Với mục đích cảnh báo sớm theo tuần học, độ trễ này chấp nhận được; mọi màn hình đều ghi thời điểm ETL cập nhật gần nhất.

Bốn nguyên tắc được giữ xuyên suốt:

- Hai CSDL tách biệt: `moodle_src` là nguồn, `lms_analytics` là đích; hệ thống không ghi vào nguồn.
- Một nguồn thời gian chung: toàn hệ thống coi "bây giờ" là giá trị `LMS_AS_OF` (dữ liệu mô phỏng đặt ở 06/11/2026 10:30, tuần 9 của học kỳ); để trống thì chạy theo thời gian thực.
- Phân quyền nằm trong dữ liệu: mỗi dòng bảng fact lưu mảng mã giảng viên phụ trách, mọi truy vấn của giảng viên đều có điều kiện trên mảng này.
- Chạy lại không làm sai số liệu: mỗi job chỉ cập nhật dòng có giá trị thay đổi.

## 3.2. Mô tả các thành phần trong hệ thống

Bảng: Các thành phần chính của hệ thống
%w 14,26,60
| Tầng | Thành phần | Trách nhiệm |
|---|---|---|
| Trình bày | `pages`, `layouts` | 13 màn hình; layout và menu riêng cho Quản trị viên, Giảng viên |
| Trình bày | `charts`, `components` | Biểu đồ Chart.js (đường hai trục, cột chồng, heatmap, tròn, so sánh), bảng phân cấp, cửa sổ chi tiết sinh viên |
| Trình bày | `api` | Gắn token vào mỗi yêu cầu, tự đăng xuất khi nhận mã 401, lưu đệm và làm mới dữ liệu (React Query) |
| Dịch vụ | `routers` | 33 endpoint REST: xác thực, dùng chung, quản trị, báo cáo, giảng viên, hệ thống |
| Dịch vụ | `core` | Cấu hình, kết nối CSDL, xác thực JWT, giới hạn đăng nhập sai, bộ nhớ đệm 60 giây cho thẻ KPI |
| Dữ liệu | `repositories`, `services` | Câu SQL dùng tham số bind; dựng tệp Excel, PDF; sao lưu và phục hồi |
| ETL | `extract`, `transform`, `load` | Đọc Moodle trong một giao dịch REPEATABLE READ; tính chỉ số và luật rủi ro; nạp qua bảng tạm rồi cập nhật có điều kiện |
| ETL | `jobs`, `scheduler` | Sáu job: lưu lượng, tiến độ môn, rủi ro, chốt ngày, bảo trì, nạp lịch sử |
| Lưu trữ | `database/migrations` | Tám migration có kiểm tra checksum cho CSDL phân tích, bốn migration cho CSDL nguồn |

## 3.3. Sơ đồ lớp

### 3.3.1. Sơ đồ lớp mức phân tích

![Sơ đồ lớp mức phân tích](docs/diagrams/png/class_phan_tich.png){w=16}

Sơ đồ dùng đủ các loại quan hệ giữa lớp:

- Kế thừa: `SinhVien` và `GiangVien` kế thừa lớp trừu tượng `NguoiDung`.
- Tập hợp: `Khoa` chứa `BoMon`, `BoMon` chứa `MonHoc`; môn học vẫn tồn tại khi chuyển sang bộ môn khác.
- Hợp thành: `MonHoc` hợp thành từ `BuoiHoc` và `BaiTap`; `BaiTap` từ `BaiNop`; `BuoiHoc` từ `DiemDanh`. Buổi học hay bài nộp không có nghĩa khi môn học hoặc bài tập chứa nó bị xóa.
- Lớp liên kết: `GhiDanh` gắn thời điểm bắt đầu, kết thúc, trạng thái vào quan hệ nhiều – nhiều giữa `SinhVien` và `MonHoc`.
- Liên kết và phụ thuộc: `AnhChupRuiRo` gắn một sinh viên với một môn tại một ngày và dùng kiểu liệt kê `MucRuiRo`; `CanThiep` gắn giảng viên, sinh viên và môn; `LanChayETL` tạo ra các ảnh chụp, dòng tiến độ, dòng lưu lượng.

Phương thức `tinhDiem()` và `xepMuc()` của `AnhChupRuiRo` thể hiện luật QĐ1; các phương thức của `TaiKhoanDashboard` ứng với UC01, UC02, UC08.

### 3.3.2. Sơ đồ lớp mức thiết kế

Khi cài đặt, mã nguồn được tổ chức theo mô-đun: router nhận yêu cầu, repository chạy câu SQL, service xử lý việc nặng (xuất tệp, sao lưu). Dữ liệu truyền giữa các tầng là các lớp dữ liệu (`dataclass`) và lớp mô tả dữ liệu vào/ra của API (Pydantic `BaseModel`). Các lớp phân tích như `AnhChupRuiRo` hay `TaiKhoanDashboard` không được cài đặt thành lớp Python có phương thức riêng.

Lý do là phần lớn nghiệp vụ tổng hợp trên hàng trăm nghìn dòng, viết bằng SQL và pandas chạy nhanh hơn nhiều so với nạp từng đối tượng vào bộ nhớ; ngoài ra FastAPI dùng lớp Pydantic để tự kiểm tra dữ liệu vào và sinh tài liệu API. Ánh xạ từ mức phân tích xuống mã nguồn:

- `tinhDiem()`, `xepMuc()` → hàm `score_student()` trong `etl/transform/risk_rules.py`, kết quả là một dòng của `fact_student_risk_summary`.
- Phương thức của `TaiKhoanDashboard` → các endpoint `/auth/login`, `/auth/change-password`, `/admin/users/...`; tài khoản trong mỗi yêu cầu là lớp `CurrentUser`.
- `BanSaoLuu.phucHoi()` → hàm `restore_backup()`; thông tin bản sao lưu là lớp `BackupInfo`.
- `LanChayETL` → lớp `JobContext` khi đang chạy và bảng `etl_run_log` khi đã lưu.
- Lớp `Stamped` là lớp cha của mọi dữ liệu trả về từ API, mang `data_updated_at` để giao diện luôn hiển thị được thời điểm cập nhật.

![Sơ đồ lớp mức thiết kế (các lớp có trong mã nguồn)](docs/diagrams/png/class_thiet_ke.png){w=16}

## 3.4. Sơ đồ tuần tự

### 3.4.1. Đăng nhập

![Sơ đồ tuần tự Đăng nhập](docs/diagrams/png/seq_dang_nhap.png){w=16}

Khi tên đăng nhập không tồn tại, máy chủ vẫn so khớp với một mật khẩu băm giả để thời gian phản hồi gần bằng trường hợp sai mật khẩu, tránh lộ tên đăng nhập nào có thật. Bộ đếm đăng nhập sai được kiểm tra trước khi đọc CSDL nên các yêu cầu đã bị chặn không tốn công băm mật khẩu.

### 3.4.2. Đổi mật khẩu

![Sơ đồ tuần tự Đổi mật khẩu](docs/diagrams/png/seq_doi_mat_khau.png){w=13}

JWT là token không trạng thái nên không thể "thu hồi" trực tiếp. Hệ thống lưu thời điểm đổi mật khẩu và từ chối mọi token phát hành sớm hơn; phiên hiện tại nhận token mới ngay trong phản hồi.

### 3.4.3. Xem chi tiết sinh viên và ghi nhận can thiệp

![Sơ đồ tuần tự Xem chi tiết sinh viên và ghi nhận can thiệp](docs/diagrams/png/seq_chi_tiet_can_thiep.png){w=16}

Quyền truy cập được kiểm tra hai lớp: giảng viên phải có tên trong danh sách phụ trách môn (không có thì trả 403), và câu truy vấn dữ liệu luôn có điều kiện trên mảng mã giảng viên.

### 3.4.4. Job chấm điểm rủi ro

![Sơ đồ tuần tự job chấm điểm rủi ro](docs/diagrams/png/seq_etl_rui_ro.png){w=16}

Toàn bộ dữ liệu Moodle được đọc trong một giao dịch REPEATABLE READ để nhật ký và bài nộp được đọc trên cùng một ảnh chụp, dù Moodle vẫn đang ghi.

### 3.4.5. Phục hồi dữ liệu

![Sơ đồ tuần tự Phục hồi dữ liệu](docs/diagrams/png/seq_phuc_hoi.png){w=16}

## 3.5. Sơ đồ trạng thái và sơ đồ hoạt động

![Sơ đồ trạng thái mức rủi ro của sinh viên trong một môn](docs/diagrams/png/state_muc_rui_ro.png){w=15}

Mức rủi ro được tính lại ở mỗi lần chạy job nên sinh viên có thể chuyển qua lại giữa ba trạng thái; mỗi ngày lưu một ảnh chụp riêng để cửa sổ chi tiết hiển thị lịch sử chuyển mức.

![Sơ đồ trạng thái một lần chạy ETL](docs/diagrams/png/state_lan_chay_etl.png){w=11}

![Sơ đồ trạng thái tài khoản](docs/diagrams/png/state_tai_khoan.png){w=12}

![Sơ đồ hoạt động xếp mức rủi ro](docs/diagrams/png/act_xep_muc_rui_ro.png){w=11}

Phép so sánh tỷ lệ với ngưỡng dùng phân số chính xác (`Fraction`) thay cho số thực dấu phẩy động, để trường hợp vắng đúng 3/10 buổi được xếp đúng vào mức "từ 30% trở lên".

## 3.6. Sơ đồ triển khai

![Sơ đồ triển khai bằng Docker Compose](docs/diagrams/png/deploy_docker.png){w=14}

Hệ thống gồm năm dịch vụ: `db` (PostgreSQL 18 chứa hai CSDL), `init` (chạy một lần: tạo cấu trúc, sinh dữ liệu mô phỏng, nạp lịch sử, tạo tài khoản), `etl` (bộ lập lịch), `backend` (API hai tiến trình) và `web` (Nginx phục vụ giao diện, chuyển tiếp `/api`). Chỉ cổng web được mở ra ngoài. Bản sao lưu nằm trong volume riêng `backups` nên không mất khi tạo lại container.
