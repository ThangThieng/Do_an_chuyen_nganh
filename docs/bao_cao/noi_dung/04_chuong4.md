# CHƯƠNG 4: THIẾT KẾ DỮ LIỆU

## 4.1. Sơ đồ logic hoàn chỉnh

Hệ thống làm việc với hai CSDL. CSDL nguồn `moodle_src` mô phỏng một phần CSDL Moodle 3.9; nhóm **không thiết kế** CSDL này mà giữ nguyên cấu trúc của Moodle để câu truy vấn trích xuất dùng được trên Moodle thật. CSDL phân tích `lms_analytics` là phần do nhóm thiết kế, gồm ba bảng fact và năm bảng phụ trợ trong schema `analytics`.

Sơ đồ logic của CSDL phân tích (Hình 4.1) dùng đường liền cho khóa ngoại thật, đường đứt cho khóa logic. Ba bảng fact không có khóa ngoại tới Moodle vì hai CSDL tách biệt; cột `course_id`, `user_id` mang đúng giá trị `mdl_course.id`, `mdl_user.id`. Cột `etl_run_id` của các bảng fact trỏ tới lần chạy ETL đã ghi dòng đó, với quy tắc `ON DELETE SET NULL`: có thể dọn nhật ký ETL cũ mà không mất số liệu.

Sơ đồ các bảng Moodle (Hình 4.2) chỉ ghi những cột ETL thực sự dùng. Quan hệ giữa các bảng Moodle là quan hệ logic: bản thân Moodle không khai báo khóa ngoại trong CSDL.

![Sơ đồ logic CSDL phân tích lms_analytics](docs/diagrams/png/erd_analytics.png){w=16}

![Các bảng Moodle được hệ thống đọc (CSDL moodle_src)](docs/diagrams/png/erd_moodle.png){w=16}

## 4.2. Ánh xạ từ sơ đồ lớp sang CSDL quan hệ

### 4.2.1. Ánh xạ cơ bản

Bảng: Ánh xạ lớp phân tích sang bảng dữ liệu
%w 24,34,42
| Lớp (mục 3.3.1) | Bảng | Ghi chú |
|---|---|---|
| Khoa, BoMon | `mdl_course_categories` | Cây danh mục của Moodle: khoa là danh mục cấp 1, bộ môn là cấp 2 |
| MonHoc | `mdl_course` | Năm học, học kỳ suy ra từ ngày bắt đầu môn |
| NguoiDung, SinhVien, GiangVien | `mdl_user` + `mdl_role_assignments` | Xem mục 4.2.2 |
| GhiDanh | `mdl_enrol` + `mdl_user_enrolments` | Moodle tách phương thức ghi danh và lượt ghi danh |
| BuoiHoc, DiemDanh | `mdl_attendance_sessions`, `mdl_attendance_log` | Thuộc plugin `mod_attendance` |
| BaiTap, BaiNop | `mdl_assign`, `mdl_assign_submission` | |
| SuKienTruyCap | `mdl_logstore_standard_log` | Bảng lớn nhất, đọc tăng dần theo `id` |
| TaiKhoanDashboard | `app_user` | `user_id` trùng `mdl_user.id` |
| AnhChupRuiRo | `fact_student_risk_summary` | Mỗi đối tượng là một dòng (sinh viên, môn, ngày) |
| TienDoMonNgay | `fact_course_progress_daily` | Mỗi đối tượng là một dòng (môn, ngày) |
| LuuLuongGio | `fact_server_traffic_hourly` | Mỗi đối tượng là một giờ |
| CanThiep | `intervention_log` | |
| LanChayETL | `etl_run_log` | |
| BanSaoLuu | Tệp zip trên đĩa, không phải bảng | Xem giải thích bên dưới |

Theo quy tắc ánh xạ cơ bản, mỗi lớp cần lưu trữ trở thành một bảng, mỗi thuộc tính thành một cột, mỗi đối tượng thành một dòng. Nhóm áp dụng quy tắc này cho các lớp nghiệp vụ, với một ngoại lệ có chủ đích: lớp `BanSaoLuu` không được lưu trong CSDL. Lý do là bản sao lưu phải còn nguyên khi chính CSDL bị thay thế trong lúc phục hồi. Nếu danh sách bản sao lưu nằm trong CSDL, lần phục hồi sẽ ghi đè luôn danh sách đó. Vì vậy mỗi bản sao lưu là một tệp tự mô tả (có `manifest.json`), và danh sách được dựng bằng cách đọc thư mục.

Khóa chính được chọn theo hai cách. Các bảng fact dùng **khóa tự nhiên ghép** (ví dụ `course_id, user_id, snapshot_date`), để lệnh `INSERT ... ON CONFLICT` của ETL tìm đúng dòng cần cập nhật; nhờ đó chạy lại job không sinh dòng trùng. Các bảng nhật ký (`etl_run_log`, `intervention_log`) dùng **khóa thay thế** tự tăng, vì một dòng nhật ký không có thuộc tính tự nhiên nào đủ để phân biệt.

### 4.2.2. Quan hệ kế thừa

Lớp `NguoiDung` có hai lớp con `SinhVien` và `GiangVien`. Có hai phương pháp ánh xạ: gộp tất cả vào một bảng kèm cột phân loại, hoặc tách mỗi lớp thành một bảng.

- Phía Moodle dùng một bảng `mdl_user` cho mọi người dùng, nhưng không có cột phân loại. Vai trò được gán theo từng môn qua `mdl_role_assignments`, vì cùng một người có thể là giảng viên ở môn này và sinh viên ở môn khác. Đây là biến thể của phương pháp gộp bảng, trong đó "loại đối tượng" phụ thuộc ngữ cảnh.
- Phía CSDL phân tích, bảng `app_user` gộp quản trị viên và giảng viên, phân biệt bằng cột `role`. Nhóm chọn phương pháp gộp vì hai vai trò có cùng tập thuộc tính, không phát sinh ô NULL thừa, và việc xác thực chỉ cần đọc một bảng ở mỗi yêu cầu.

### 4.2.3. Thuộc tính phức tạp và thuộc tính danh sách

Theo quy tắc ánh xạ, thuộc tính phức tạp và thuộc tính dạng danh sách nên được tách thành bảng phụ. Nhóm **cố ý không tách** năm thuộc tính sau:

Bảng: Các thuộc tính danh sách được lưu trong một cột
%w 22,30,48
| Cột | Nội dung | Lý do không tách bảng |
|---|---|---|
| `teacher_ids` (integer[]) | Mã các giảng viên phụ trách môn | Dùng để phân quyền ở mọi truy vấn của giảng viên. Toán tử `teacher_ids @> ARRAY[mã]` dùng được chỉ mục GIN, không cần kết thêm bảng |
| `risk_reasons` (jsonb) | Danh sách câu lý do cảnh báo | Chỉ hiển thị nguyên danh sách, không bao giờ truy vấn từng phần tử |
| `weekly_activity` (jsonb) | Lượt xem, thao tác, điểm danh theo từng tuần | Cửa sổ chi tiết cần cả chuỗi trong một lần đọc |
| `assignment_detail` (jsonb) | Trạng thái từng bài tập của sinh viên | Như trên |
| `section_progress` (jsonb) | Tỷ lệ hoàn thành theo chương của môn | Như trên |

Quyết định này có hai nhược điểm: CSDL không kiểm tra được từng phần tử bên trong (chỉ kiểm tra được giá trị là một mảng), và muốn sửa một phần tử phải ghi lại cả giá trị. Với hệ thống này, ETL luôn tính lại toàn bộ dòng ở mỗi lần chạy nên nhược điểm thứ hai không phát sinh. Trong khi đó, cửa sổ chi tiết sinh viên chỉ cần đọc một dòng thay vì kết bốn bảng. Kết quả đo ở Chương 6 cho thấy câu truy vấn chậm nhất của API chỉ mất 8,55 ms trên bộ dữ liệu gấp 10 lần dữ liệu thử.

### 4.2.4. Thuộc tính có giá trị rời rạc

Quy tắc ánh xạ khuyến nghị tách thuộc tính rời rạc thành bảng danh mục. Hệ thống có sáu thuộc tính loại này: `role`, `risk_level`, `attendance_status`, `action_type`, `status` của lần chạy ETL và `source` của mẫu online. Nhóm dùng ràng buộc `CHECK` hoặc kiểu miền (`DOMAIN`) thay cho bảng danh mục.

Mỗi giá trị trong các tập này gắn với một nhánh xử lý trong mã nguồn (mức RED có màu và biểu tượng riêng, WARN tương ứng đúng C1 = 1). Nếu đặt trong bảng danh mục, người dùng có thể thêm giá trị mà chương trình không biết xử lý; ràng buộc `CHECK` chặn điều đó ngay tại CSDL. Khi tập giá trị do người dùng tự định nghĩa thì bảng danh mục mới là lựa chọn phù hợp, như cách Moodle dùng `mdl_attendance_statuses` để mỗi môn tự đặt trạng thái điểm danh.

Bốn kiểu miền dùng chung:

Bảng: Các kiểu miền (DOMAIN) trong CSDL phân tích
%w 22,22,56
| Kiểu miền | Kiểu gốc | Ràng buộc |
|---|---|---|
| `academic_year_t` | VARCHAR(9) | Dạng `YYYY-YYYY`, năm sau bằng năm trước cộng 1 |
| `semester_t` | SMALLINT | 1, 2 hoặc 3 (học kỳ hè) |
| `percent_t` | NUMERIC(5,2) | Từ 0 đến 100 |
| `risk_level_t` | VARCHAR(6) | RED, YELLOW hoặc GREEN |

### 4.2.5. Phi chuẩn hóa có kiểm soát

Bảng fact lặp lại tên khoa, tên môn, họ tên và MSSV ở mỗi dòng. Nhóm chấp nhận vi phạm dạng chuẩn 3 ở đây để API không phải kết bảng khi hiển thị. Nguy cơ thường gặp của phi chuẩn hóa là dữ liệu lặp bị lệch nhau khi cập nhật. Hệ thống hạn chế nguy cơ này bằng hai cách: chỉ ETL được ghi vào bảng fact, và các ràng buộc `CHECK` kiểm tra quan hệ giữa các cột ngay trong CSDL, chẳng hạn:

- số sinh viên hoạt động trong ngày ≤ số hoạt động 7 ngày ≤ số đăng ký;
- lượt truy cập 7 ngày ≤ 14 ngày ≤ tổng;
- số bài thiếu = số bài tới hạn − số bài đã nộp;
- `absence_rate` là NULL khi và chỉ khi môn chưa có buổi điểm danh;
- `attendance_status` phải khớp điểm C1.

Bộ kiểm thử có 30 ca ghi thử dữ liệu vi phạm từng ràng buộc và yêu cầu CSDL phải từ chối.

## 4.3. Danh sách các bảng dữ liệu

Bảng: Danh sách bảng của CSDL phân tích
%w 6,30,46,18
| STT | Tên bảng | Diễn giải | Số dòng |
|---|---|---|---|
| 1 | `app_user` | Tài khoản đăng nhập Dashboard | 9 |
| 2 | `intervention_log` | Nhật ký can thiệp của giảng viên | 0 |
| 3 | `etl_run_log` | Nhật ký các lần chạy job ETL | 56 |
| 4 | `etl_watermark` | Mốc trích xuất tăng dần theo `id` nhật ký Moodle | 1 |
| 5 | `etl_online_snapshot` | Số người online theo khung 5 phút | 17.406 |
| 6 | `fact_server_traffic_hourly` | Lưu lượng truy cập theo giờ (FACT 3) | 1.451 |
| 7 | `fact_course_progress_daily` | Quy mô, tương tác, tiến độ của môn theo ngày (FACT 2) | 915 |
| 8 | `fact_student_risk_summary` | Chỉ số và mức rủi ro của sinh viên trong môn theo ngày (FACT 1) | 145.846 |

Số dòng lấy tại thời điểm viết báo cáo (01/10/2026) với dữ liệu mô phỏng từ 07/09 đến 06/11/2026. Bảng nhật ký can thiệp trống vì các can thiệp tạo trong lúc kiểm thử tự động được xóa sau mỗi lần chạy.

## 4.4. Mô tả từng bảng dữ liệu

Quy ước cột "Ràng buộc": **PK** – khóa chính; **FK** – khóa ngoại; **NN** – không được rỗng; **UQ** – duy nhất; **Tự sinh** – giá trị do CSDL tính.

### 4.4.1. Bảng app_user

Bảng: Mô tả bảng app_user
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `user_id` | integer | PK | Bằng `mdl_user.id`, để khớp với `teacher_ids` trong bảng fact |
| 2 | `username` | varchar(100) | NN, UQ | Tên đăng nhập (so sánh không phân biệt hoa thường) |
| 3 | `full_name` | varchar(255) | | Họ tên, đồng bộ từ Moodle |
| 4 | `email` | varchar(255) | | Email, đồng bộ từ Moodle |
| 5 | `role` | varchar(10) | NN, CHECK | ADMIN hoặc TEACHER |
| 6 | `password_hash` | varchar(255) | NN | Mật khẩu băm bcrypt |
| 7 | `is_active` | boolean | NN, mặc định true | false khi bị khóa |
| 8 | `created_at`, `updated_at` | timestamptz | NN | Thời điểm tạo, cập nhật (trigger tự cập nhật) |
| 9 | `password_changed_at` | timestamptz | | Lần đổi hoặc đặt lại mật khẩu gần nhất; token cấp trước thời điểm này bị từ chối |
| 10 | `last_login_at` | timestamptz | | Lần đăng nhập thành công gần nhất |

### 4.4.2. Bảng intervention_log

Bảng: Mô tả bảng intervention_log
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `id` | bigint | PK, tự sinh | Mã can thiệp |
| 2 | `course_id` | integer | NN | Môn học (khóa logic tới `mdl_course.id`) |
| 3 | `user_id` | integer | NN | Sinh viên (khóa logic tới `mdl_user.id`) |
| 4 | `teacher_id` | integer | NN, FK | Giảng viên ghi nhận, tham chiếu `app_user` (không cho xóa tài khoản đã có can thiệp) |
| 5 | `action_type` | varchar(20) | NN, CHECK | MESSAGE, EMAIL, NOTE hoặc MEETING |
| 6 | `content` | text | | Nội dung, tối đa 2.000 ký tự (kiểm tra ở API) |
| 7 | `risk_level_at_time` | risk_level_t | | Mức rủi ro của sinh viên lúc ghi nhận |
| 8 | `created_at` | timestamptz | NN | Thời điểm ghi nhận |

### 4.4.3. Bảng etl_run_log

Bảng: Mô tả bảng etl_run_log
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `run_id` | bigint | PK, tự sinh | Mã lần chạy |
| 2 | `job_name` | varchar(50) | NN | traffic, course_progress, student_risk, nightly, maintenance, backfill |
| 3 | `started_at` | timestamptz | NN | Thời điểm bắt đầu |
| 4 | `finished_at` | timestamptz | CHECK | Rỗng khi và chỉ khi đang chạy; không sớm hơn `started_at` |
| 5 | `status` | varchar(10) | NN, CHECK | RUNNING, SUCCESS hoặc FAILED |
| 6 | `rows_extracted` | integer | CHECK ≥ 0 | Số dòng đọc từ nguồn |
| 7 | `rows_loaded` | integer | CHECK ≥ 0 | Số dòng thực sự thay đổi ở đích |
| 8 | `error_message` | text | CHECK | Bắt buộc khi FAILED |

### 4.4.4. Bảng etl_watermark

Bảng: Mô tả bảng etl_watermark
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `job_name` | varchar(50) | PK | Tên job dùng mốc |
| 2 | `last_log_id` | bigint | NN, ≥ 0 | `id` lớn nhất của nhật ký Moodle đã xử lý; lần sau chỉ đọc phần mới hơn |
| 3 | `last_run_at` | timestamptz | | Lần cập nhật mốc gần nhất |

### 4.4.5. Bảng etl_online_snapshot

Bảng: Mô tả bảng etl_online_snapshot
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `slot_start` | timestamp | PK, CHECK | Đầu khung 5 phút (phút chia hết cho 5), giờ địa phương |
| 2 | `online_users` | integer | NN, ≥ 0 | Số người có hoạt động trong khung |
| 3 | `source` | varchar(10) | NN, CHECK | SESSIONS (từ phiên Moodle) hoặc LOGSTORE (suy ra từ nhật ký) |
| 4 | `etl_run_id` | bigint | FK | Lần chạy đã ghi |
| 5 | `updated_at` | timestamptz | NN | Thời điểm cập nhật |

Bảng này được thêm so với kế hoạch ban đầu. Kế hoạch tính trung bình số người online theo công thức cộng dồn; công thức đó đếm trùng khi một job chạy lại. Lưu riêng từng mẫu 5 phút rồi tính lại giá trị theo giờ giúp chạy lại bao nhiêu lần cũng cho cùng kết quả.

### 4.4.6. Bảng fact_server_traffic_hourly

Bảng: Mô tả bảng fact_server_traffic_hourly
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `stat_hour` | timestamp | PK, CHECK | Đầu giờ, giờ địa phương |
| 2 | `stat_date`, `hour_of_day`, `day_of_week` | date, smallint | Tự sinh | Tính từ `stat_hour`, không thể lệch nhau; thứ theo chuẩn ISO (1 = Thứ 2) |
| 3 | `total_requests` | integer | NN | Số sự kiện trong nhật ký Moodle của giờ đó (chỉ số gần đúng của lượng request) |
| 4 | `unique_users` | integer | NN, ≤ requests | Số người dùng khác nhau |
| 5 | `login_count`, `failed_login_count` | integer | NN | Số lần đăng nhập thành công, thất bại |
| 6 | `ws_requests` | integer | NN | Sự kiện đến từ web service (ứng dụng di động) |
| 7 | `peak_online_users` | integer | NN | Giá trị lớn nhất của các mẫu 5 phút trong giờ |
| 8 | `avg_online_users` | numeric(8,2) | NN, ≤ peak | Trung bình các mẫu 5 phút trong giờ |
| 9 | `online_sample_count` | smallint | NN | Số mẫu 5 phút đã dùng để tính hai cột trên |
| 10 | `is_peak_hour` | boolean | NN | true khi lượt truy cập vượt P90 của 28 ngày gần nhất |
| 11 | `etl_run_id`, `updated_at` | bigint, timestamptz | FK; NN | Lần chạy đã ghi; thời điểm cập nhật |

### 4.4.7. Bảng fact_course_progress_daily

Bảng: Mô tả bảng fact_course_progress_daily
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `course_id` | integer | PK | Môn học |
| 2 | `stat_date` | date | PK | Ngày số liệu |
| 3 | `faculty_id`, `faculty_name` | integer, varchar | NN | Khoa (danh mục cấp 1) |
| 4 | `category_id`, `category_name` | integer, varchar | NN | Bộ môn (danh mục trực tiếp của môn) |
| 5 | `course_shortname`, `course_fullname` | varchar(255) | NN | Mã và tên môn |
| 6 | `academic_year`, `semester` | academic_year_t, semester_t | NN | Năm học, học kỳ |
| 7 | `teacher_ids` | integer[] | NN, không chứa NULL | Mã giảng viên phụ trách |
| 8 | `total_enrolled_students` | integer | NN | Sinh viên đăng ký (QĐ4) |
| 9 | `active_students_day`, `active_students_7d` | integer | NN, CHECK | Sinh viên có hoạt động trong ngày, trong 7 ngày |
| 10 | `total_active_students` | integer | NN | Sinh viên có tương tác từ đầu môn (lũy kế) |
| 11 | `total_views_day`, `total_actions_day`, `submissions_day` | integer | NN | Lượt xem, thao tác ghi, bài nộp trong ngày |
| 12 | `total_assignments` | smallint | NN | Số bài tập đã tới hạn |
| 13 | `assignment_submission_rate` | percent_t | | Tỷ lệ nộp bài; NULL khi chưa có bài tới hạn |
| 14 | `attendance_rate` | percent_t | | Tỷ lệ có mặt; NULL khi chưa có buổi điểm danh |
| 15 | `avg_completion_rate` | percent_t | | Tỷ lệ hoàn thành hoạt động đã tới hạn; NULL khi chưa có |
| 16 | `avg_access_per_student` | numeric(8,2) | NN | Lượt truy cập trung bình mỗi sinh viên |
| 17 | `red_count`, `yellow_count`, `green_count` | integer | NN | Phân bố mức rủi ro trong ngày |
| 18 | `section_progress` | jsonb | NN, là mảng | Tiến độ từng chương |
| 19 | `etl_run_id`, `updated_at` | bigint, timestamptz | FK; NN | |

### 4.4.8. Bảng fact_student_risk_summary

Bảng: Mô tả bảng fact_student_risk_summary
%w 6,26,20,14,34
| STT | Thuộc tính | Kiểu | Ràng buộc | Diễn giải |
|---|---|---|---|---|
| 1 | `course_id`, `user_id`, `snapshot_date` | integer, integer, date | PK | Sinh viên trong môn tại một ngày |
| 2 | `faculty_id`, `faculty_name`, `course_shortname`, `course_fullname` | integer, varchar | NN | Thông tin khoa, môn (phi chuẩn hóa) |
| 3 | `academic_year`, `semester` | miền | NN | Năm học, học kỳ |
| 4 | `teacher_ids` | integer[] | NN | Dùng cho phân quyền (chỉ mục GIN) |
| 5 | `student_code`, `student_name`, `email` | varchar | `student_name` NN | MSSV (`mdl_user.idnumber`), họ tên, email |
| 6 | `total_access_count`, `access_count_7d`, `access_count_14d` | integer | NN, CHECK | Lượt truy cập tổng, 7 ngày, 14 ngày (7 ≤ 14 ≤ tổng) |
| 7 | `active_actions` | integer | NN | Số thao tác ghi (nộp bài, đăng bài) |
| 8 | `last_access_time`, `days_since_last_access` | timestamptz, integer | CHECK | Lần truy cập cuối, số ngày từ đó tới nay; cùng rỗng khi chưa từng truy cập |
| 9 | `total_sessions`, `attended_sessions`, `absent_sessions` | smallint | NN, CHECK | Số buổi đã điểm danh, có mặt, vắng |
| 10 | `absence_rate` | percent_t | CHECK | Tỷ lệ vắng; NULL khi và chỉ khi chưa có buổi nào |
| 11 | `attendance_status` | varchar(10) | NN, CHECK | NO_DATA, OK, WARN, CRITICAL; khớp điểm C1 |
| 12 | `total_assignments`, `submitted_assignments`, `missing_assignments_count`, `late_submissions` | smallint | NN, CHECK | Bài đã tới hạn, đã nộp, thiếu, nộp trễ |
| 13 | `completion_rate` | percent_t | | Tỷ lệ hoàn thành hoạt động đã tới hạn |
| 14 | `score_attendance`, `score_inactivity`, `score_assignment` | smallint | NN, 0–2 | Điểm C1, C2, C3 |
| 15 | `risk_score` | smallint | NN, 0–100 | Điểm rủi ro dùng để sắp xếp |
| 16 | `risk_level` | risk_level_t | NN | RED, YELLOW, GREEN |
| 17 | `risk_reasons` | jsonb | NN, là mảng | Các câu lý do |
| 18 | `weekly_activity` | jsonb | NN, là mảng | Hoạt động và điểm danh theo tuần |
| 19 | `assignment_detail` | jsonb | NN, là mảng | Trạng thái từng bài tập |
| 20 | `class_avg_access` | numeric(8,2) | ≥ 0 | Lượt truy cập trung bình của lớp, dùng để so sánh |
| 21 | `etl_run_id`, `updated_at` | bigint, timestamptz | FK; NN | |

Chỉ mục của bảng này được đặt theo đúng các truy vấn thường dùng: (`course_id`, `snapshot_date` giảm dần, `risk_level`, `risk_score` giảm dần) cho bảng cảnh báo; GIN trên `teacher_ids` cho phân quyền; (`user_id`, `snapshot_date` giảm dần) cho lịch sử; (`faculty_id`, `academic_year`, `semester`, `snapshot_date`) cho báo cáo; và một chỉ mục một phần chỉ chứa các dòng mức RED.
