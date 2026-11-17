# Kế hoạch chuyển đổi sang dữ liệu Moodle 3.11 thật (Master Execution Plan)

Ngày lập: 16/11/2026. Trạng thái: **Cả 4 mốc đã duyệt. Từ 16/11/2026 `.env` trỏ vào dữ liệu thật** (`moodle_src_real`, `lms_analytics_real`, mốc tính 12/11/2026 15:00). Bản `.env` cũ lưu ở `var/env.mock.bak`.

Tài liệu liên quan: `ThongKe_BangDuLieu_DaCo_VaCanBoSung.docx` (thống kê 27 bảng đã có và 4 bảng còn thiếu).

## 0. Mục tiêu và nguyên tắc

Mục tiêu: thay dữ liệu mô phỏng trong CSDL nguồn bằng dữ liệu thật của khoa CNTT mà **không làm hỏng chức năng nào đang chạy** của Quản trị viên và Giảng viên.

| # | Quyết định kiến trúc | Lý do |
|---|---|---|
| K1 | **Blue-Green ở mức CSDL.** Giữ nguyên `moodle_src` + `lms_analytics` (Blue, dữ liệu giả). Tạo mới `moodle_src_real` + `lms_analytics_real` (Green). Chuyển đổi bằng 2 dòng `MOODLE_DB_NAME`, `ANALYTICS_DB_NAME` trong `.env` | Rollback chỉ là đổi lại `.env`. `database/migrate.py` đã tự tạo CSDL theo tên |
| K2 | **Một bộ mã chạy cả hai bộ dữ liệu.** Mọi thay đổi ETL là mở rộng có điều kiện, không rẽ nhánh mã riêng | Bộ kiểm thử hiện có trên Blue vẫn phải đạt sau khi sửa: đó là bằng chứng không hồi quy |
| K3 | **Nạp qua vùng đệm `stg` toàn trường, lọc phạm vi bằng cấu hình** | Mở rộng ra toàn trường chỉ cần nới phạm vi và nạp thêm file |

Nguyên tắc cố định: CSV nằm ngoài repo; không commit khi chưa được yêu cầu; chế độ gửi tin thật luôn tắt.

## 1. Kết quả khảo sát đã kiểm chứng (đọc mã nguồn và đo trên file CSV)

Các điểm dưới đây quyết định thiết kế. Tất cả đã được kiểm tra, không phải giả định.

| # | Phát hiện | Hệ quả cho kế hoạch |
|---|---|---|
| P1 | File danh mục CNTT chỉ có cấp 3–4 (41 dòng). **Thiếu danh mục cấp 1 (id 2, Khoa CNTT) và cấp 2 (id 4, 5, 6)**. `courses.sql` xác định Khoa bằng phần tử đầu của `path` | Nếu nạp nguyên trạng, ETL không tìm thấy môn nào. Phải bổ sung 4 danh mục cha (tên lấy từ đường dẫn danh mục của các môn), hoặc xin bảng `course_categories` đầy đủ |
| P2 | 142/173 môn có `enddate = 0`. Theo `courses.sql` hiện tại, 143 môn bị coi là "đang diễn ra", gồm cả môn từ 2024 | Sinh viên các môn cũ sẽ thành Đỏ hàng loạt (nhật ký chỉ có từ 13/09/2026). Cần quy tắc: môn không đặt ngày kết thúc chỉ tính khi thuộc học kỳ hiện tại. Kết quả: 39 môn bắt đầu từ 08/2026 |
| P3 | Dữ liệu giả không có môn nào `enddate = 0`, mọi môn bật `enablecompletion`, mọi môn có dữ liệu hoàn thành, `idnumber` đầy đủ | Các quy tắc mới ở P2, mục 4.4, 4.5 **không làm đổi kết quả trên Blue** |
| P4 | Mốc cuối của dữ liệu đợt 1: bài nộp 12/11/2026 14:48, điểm 15:08, ghi danh 13:32. Nhật ký tới 20:51 | Đề xuất `LMS_AS_OF = 2026-11-12T15:00:00+07:00` cho Green |
| P5 | Bảng fact lưu C1 theo số buổi, có ràng buộc `total_sessions = 0 ⇔ NO_DATA`. Sổ điểm chỉ cho tỷ lệ. Số buổi được hiển thị ở 6 chỗ trên giao diện và 1 cột báo cáo | Cần cột phân biệt nguồn (`attendance_source`) để giao diện không in "23/100 buổi" |
| P6 | `moodle_src` không có ràng buộc khóa ngoại giữa các bảng `mdl_*`, chỉ có ràng buộc duy nhất | Thứ tự nạp tự do; phải kiểm tra bản ghi mồ côi bằng báo cáo |
| P7 | Dòng đầu file `user` mới là 2 bản ghi bị dính nhau (tài khoản hệ thống id nhỏ) | Loại dòng này, ghi vào nhật ký dòng lỗi |
| P8 | Bộ kiểm thử hiện có (354 ca) chạy trên CSDL Blue thật, gồm cả ca sao lưu và khôi phục CSDL phân tích | Không sửa repo khi bộ kiểm thử đang chạy |

## 2. Phần 1 – Ánh xạ lược đồ và migration

### 2.1. Khác biệt giữa `moodle_src` hiện tại và file thật

| Bảng | `moodle_src` hiện tại | File thật | Cách xử lý |
|---|---|---|---|
| `user` | 27 cột | 15 cột, thứ tự tự chọn, không tiêu đề | Ánh xạ theo tên qua manifest; `password = ''`, `confirmed = 1` |
| `course` | 28 cột | 36 cột | Chỉ nạp cột bảng đích có |
| `course_categories` | đủ cấp | chỉ cấp 3–4 | Bổ sung 4 danh mục cha (P1) |
| `groups` | 11 cột | 8 cột (đã bỏ `enrolmentkey`, `picture`) | Cột thiếu dùng giá trị mặc định |
| `assign` | 26 cột | 30 cột | Nạp 26 cột trùng tên |
| `enrol` | 12 cột | 35 cột, có khóa ghi danh | Nạp 12 cột trùng tên, không nạp `password` |
| `sessions` | 9 cột, `sid` bắt buộc | 5 cột | `sid = 'csv-' || id` |
| `logstore_standard_log` | 21 cột | 21 cột | `ip`, `other` ghi NULL |
| Các bảng khác đang dùng | khớp | khớp số cột 3.11 | Nạp thẳng |

### 2.2. Migration cho CSDL nguồn (file mới, không sửa file đã áp dụng)

| File | Nội dung |
|---|---|
| `V006__gradebook.sql` | `mdl_scale`, `mdl_grade_categories`, `mdl_grade_items`, `mdl_grade_grades`, đủ cột theo install.xml 3.11 |
| `V007__quiz_assign_grades_groupings.sql` | `mdl_quiz` (không tạo cột `password`), `mdl_quiz_attempts`, `mdl_quiz_grades`, `mdl_assign_grades`, `mdl_groupings` |
| `V008__overrides_user_flags.sql` | `mdl_assign_overrides`, `mdl_assign_user_flags`, `mdl_quiz_overrides`: tạo sẵn, để rỗng |
| `V009__staging_ingest.sql` | Schema `stg`; `stg.scope_course`, `stg.ingest_batch`, `stg.reject` |

Các migration này chỉ thêm bảng mới. Vì dùng chung thư mục migration, Blue cũng nhận các bảng rỗng này; ETL trên Blue cho kết quả như cũ.

### 2.3. Migration cho CSDL phân tích

`V015__attendance_source.sql`: thêm cột `attendance_source` ('SESSIONS' | 'GRADEBOOK'), mặc định 'SESSIONS', vào `fact_student_risk_summary`. Thay đổi chỉ cộng thêm; cấu trúc và hợp đồng API cũ giữ nguyên.

## 3. Phần 2 – Pipeline nạp và làm sạch CSV

Thành phần: gói `ingest/` tách khỏi `etl/`.

1. **Manifest** (`ingest/manifest.py`): mỗi bảng khai báo file, thứ tự cột trong file, cột bỏ, điều kiện phạm vi, biểu thức ghi đè.
2. **Đọc file:** UTF-8, không dòng tiêu đề, đọc theo luồng. Chuỗi `NULL` thành NULL. Dòng sai số cột ghi vào `stg.reject` (chỉ số dòng và lý do, không lưu nội dung).
3. **Vùng đệm:** `COPY` vào `stg.<bảng>` với mọi cột kiểu text. `stg.ingest_batch` lưu mã băm file; file không đổi thì không đọc lại.
4. **Phạm vi:** `stg.scope_course` lấy 173 id từ `dlu_course_cntt.csv`. Lọc dây chuyền qua bảng cha đã nạp.
5. **Chuyển sang `mdl_*`:** một transaction cho cả đợt; lỗi thì hoàn tác toàn bộ. Sau đó đặt lại số tự tăng.
6. **Người dùng:** chỉ nạp `deleted = 0` và có ghi danh, vai trò hoặc nhóm trong phạm vi. Giữ nguyên `suspended` (ETL đã loại tài khoản bị khóa). Họ đệm vào `lastname`, tên vào `firstname` để hệ thống hiển thị đúng "Họ đệm Tên".
7. **MSSV:** không sửa dữ liệu nguồn. `enrolments.sql` lấy `idnumber`; nếu trống thì lấy cụm 7 chữ số trong `username`.
8. **Cột nhạy cảm không vào CSDL:** `logstore.ip/other`, `quiz.password`, `enrol.password`.
9. **Bảo vệ:** công cụ từ chối chạy nếu CSDL đích là `moodle_src`.
10. **Báo cáo sau nạp:** số dòng đọc / loại / nạp từng bảng, bản ghi mồ côi theo 15 quan hệ, khoảng thời gian từng bảng.

## 4. Phần 3 – Tái cấu trúc ETL và fallback

### 4.1. C1 Vắng học: lấy từ sổ điểm khi không có plugin

- Chọn nguồn theo từng môn: có buổi trong bảng plugin thì giữ luồng cũ; không có nhưng có mục điểm `itemmodule = 'attendance'` thì dùng sổ điểm; không có cả hai thì `NO_DATA`.
- Công thức: tỷ lệ có mặt = Σ(`finalgrade` − `grademin`) / Σ(`grademax` − `grademin`) trên các mục điểm danh đã có điểm. Lưu theo thang 100. Ngưỡng giữ 15% / 30%.
- Sinh viên chưa có điểm điểm danh thì `NO_DATA`, không coi là vắng 100%.
- Chỉ dùng điểm có thời điểm sửa không muộn hơn mốc tính, để không lấy số liệu tương lai khi tính lại lịch sử.
- Lý do hiển thị: "Chuyên cần 77% theo sổ điểm (vắng 23%)". Luật phụ "vắng ≥ n buổi" không áp dụng ở chế độ này; luật theo phần trăm vẫn chạy.

### 4.2. C2 Tương tác

Không đổi. Cơ chế đọc tăng dần theo `id` đã có sẵn (`max_log_id.sql`, `new_log_range.sql`).

### 4.3. C3 Thiếu bài tập

- Giữ logic bài nhóm hiện có (`groups`, `groups_members`).
- Thêm hạn hiệu lực theo quy tắc Moodle: `extensionduedate` > hạn riêng sinh viên > hạn riêng nhóm (`sortorder` nhỏ nhất) > `duedate`. Hai bảng nguồn đang rỗng nên kết quả như cũ; khi xin được dữ liệu chỉ cần nạp.

### 4.4. Phạm vi môn đang diễn ra

Sửa điều kiện trong `courses.sql`: môn có ngày kết thúc thì xét như cũ; môn **không đặt ngày kết thúc** chỉ tính khi bắt đầu trong học kỳ chứa mốc tính (dùng bảng tháng–học kỳ sẵn có trong `etl/config.py`).

### 4.5. Tỷ lệ hoàn thành

`completion.sql` chỉ tính môn bật `enablecompletion` và đã có ít nhất một bản ghi hoàn thành. Môn không thỏa thì tỷ lệ = NULL, giao diện hiện "Chưa có dữ liệu" thay vì 0%.

### 4.6. Lưu lượng

Số lượt đăng nhập bằng 0 vì file nhật ký không có sự kiện đăng nhập. Hợp đồng API giữ nguyên.

### 4.7. Giao diện và API (thay đổi chỉ cộng thêm)

Thêm trường `attendance_source` vào các phản hồi có số buổi. Bốn thành phần giao diện và một cột báo cáo hiển thị theo tỷ lệ khi nguồn là sổ điểm.

## 5. Phần 4 – Tích hợp, kiểm thử, rollback

**Trình tự trên Green:** migrate hai CSDL mới → nạp CSV → tạo tài khoản giảng viên (danh sách chỉ định, mật khẩu riêng) → backfill ETL từ 13/09/2026 đến mốc AS_OF → chạy API và giao diện trỏ vào Green ở cổng khác.

| Lớp | Nội dung | Tiêu chí đạt |
|---|---|---|
| T0 | Chạy bộ kiểm thử trên Blue trước khi sửa mã; lưu ảnh chụp OpenAPI | Làm mốc so sánh |
| T1 | Chạy lại sau mỗi giai đoạn sửa mã | Giống T0; OpenAPI chỉ được thêm |
| T2 | SQL độc lập trên nguồn Green so với bảng fact | Khớp 100% |
| T3 | Bất biến: Xanh + Vàng + Đỏ = tổng; tỷ lệ trong 0–100 | Không vi phạm |
| T4 | Soát tay 5 sinh viên mẫu | Trùng mức và lý do |
| T5 | e2e trên Green cho Đèn giao thông, Lưu lượng, Tiến độ lớp, Thống kê Khoa | Không lỗi |

**Rollback:** đổi `.env` về Blue; quay lại mã trước khi sửa; xóa và tạo lại Green từ CSV. Sao lưu Blue trước khi bắt đầu.

## 6. Phần 5 – Mốc phê duyệt

| Mốc | Việc làm trước mốc | Nội dung duyệt |
|---|---|---|
| **Mốc 1** | Soạn DDL V006–V009, V015 và manifest (chưa áp dụng) | Cấu trúc bảng nguồn, cột `attendance_source`, tên CSDL Green, cách xử lý 4 danh mục cha |
| **Mốc 2** | Áp dụng migration lên Green, nạp thử, báo cáo chất lượng | Số liệu nạp, dòng bị loại, mốc AS_OF |
| **Mốc 3** | Sửa ETL (C1, C3, phạm vi môn, hoàn thành), T1 đạt trên Blue | Công thức C1, phạm vi 39 môn, cách hiển thị |
| **Mốc 4** | Backfill Green, chạy T2–T5 | Chấp nhận chuyển `.env` sang Green; cập nhật SPEC và báo cáo Word |

## 7. Câu hỏi tham vấn cho Mốc 1

1. Đồng ý tạo 2 CSDL mới `moodle_src_real`, `lms_analytics_real` và giữ nguyên 2 CSDL dữ liệu giả?
2. Đồng ý thêm cột `attendance_source` (thay đổi chỉ cộng thêm) để hiển thị đúng chuyên cần lấy từ sổ điểm?
3. Bốn danh mục cha thiếu (Khoa CNTT và 3 chuyên ngành): bổ sung bằng tên suy ra từ dữ liệu, hay xin thầy/cô xuất bảng `course_categories` đầy đủ?
4. Bảng mới tạo đủ cột theo Moodle 3.11 (đề xuất), hay chỉ các cột ETL cần?
5. Giữ dữ liệu thô toàn trường trong `stg` (khoảng 1–1,5 GB), hay lọc CNTT ngay khi đọc file?
6. Chỉ tính cảnh báo cho 39 môn của học kỳ hiện tại, còn môn cũ chỉ nằm trong danh mục?

## Phụ lục. Việc đã lỡ làm trước khi kế hoạch được duyệt

- Đã tạo thư mục `ingest/` trong repo (5 file: `__init__.py`, `moodle311.py`, `manifest.py`, `loader.py`, `run.py`). Mã mới viết, **chưa chạy lần nào**, không file nào khác tham chiếu tới.
- Đã chạy bộ kiểm thử sẵn có của dự án trên dữ liệu giả để lấy mốc T0.
- Chưa tạo CSDL mới, chưa áp dụng migration, chưa sửa file nào của ETL, backend, frontend.

## 8. Nhật ký thực hiện

### Mốc 1 – đã duyệt (16/11/2026)

Quyết định của chủ dự án: làm theo các phương án đề xuất cho cả 6 câu hỏi; giữ gói `ingest/`; mốc thời gian lấy theo dữ liệu; bảng nào có thì nạp, bảng thiếu thì lập danh sách và để đó; phạm vi môn (vấn đề 39 môn) do người thực hiện tối ưu.

### Giai đoạn trước Mốc 2 – đã làm

- Thêm 4 migration CSDL nguồn (V006–V009) và sửa 1 dòng kiểm thử danh sách phiên bản migration.
- Tạo CSDL `moodle_src_real`, áp dụng V001–V009.
- Nạp 27 bảng từ CSV qua vùng đệm `stg` (39 giây cho bước chuyển, khoảng 40 giây đọc file).

| Bảng | Đọc từ file | Nạp vào `mdl_*` (phạm vi CNTT) |
|---|---|---|
| course | 9.058 | 173 |
| course_categories | 41 | 45 (thêm 4 danh mục cha) |
| course_sections / course_modules | 1.287 / 6.442 | 1.287 / 6.442 |
| context / role_assignments | 413.010 / 521.015 | 174 / 10.930 |
| enrol / user_enrolments | 18.546 / 521.715 | 345 / 10.851 |
| user | 44.564 (loại 1 dòng lỗi) | 2.995 |
| groups / groups_members / groupings | 1.240 / 281.478 / 4.802 | 1.240 / 3.653 / 2 |
| assign / assign_submission / assign_grades | 25.683 / 893.033 / 297.981 | 2.165 / 79.384 / 12.084 |
| grade_categories / grade_items / grade_grades | 166 / 2.725 / 3.227.303 | 166 / 2.725 / 163.913 |
| quiz / quiz_attempts / quiz_grades | 150 / 6.735 / 4.860 | 150 / 6.735 / 4.860 |
| logstore_standard_log | 362.904 | 362.904 |
| sessions / notifications | 3.048 / 20.703 | 247 / 7.835 |
| modules / role / scale | 32 / 12 / 10 | 32 / 12 / 10 |

Bản ghi tham chiếu tới người dùng không được nạp (tài khoản đã xóa hoặc không còn ghi danh trong phạm vi): 23 lượt ghi danh, 26 lượt gán vai trò, 193 bản nộp, 249 điểm, 1 lượt quiz, 898 dòng nhật ký. 12 bản nộp nhóm trỏ tới nhóm đã bị xóa. ETL chỉ tính sinh viên đang ghi danh hợp lệ nên các bản ghi này không ảnh hưởng kết quả.

Mốc cuối của dữ liệu trong phạm vi: bài nộp 12/11/2026 14:48; điểm 11/11/2026 18:10; nhật ký 12/11/2026 20:51. Mốc tính đề xuất: `2026-11-12T15:00:00+07:00`.

### Danh sách dữ liệu còn thiếu

> Cập nhật 16/11/2026: chủ dự án xác định các mục dưới đây là **thiếu vĩnh viễn**. Hệ thống dùng hẳn các bảng đang có với cách xử lý ở cột giữa; cột cuối chỉ còn giá trị tham khảo.

| Thiếu | Hệ thống xử lý khi chưa có | Khi có dữ liệu |
|---|---|---|
| `course_modules_completion` | Tỷ lệ hoàn thành hiện "Chưa có dữ liệu" | Đặt file vào thư mục dữ liệu, chạy lại `ingest.run` |
| `assign_overrides`, `assign_user_flags` | Dùng hạn nộp chung | Như trên |
| `quiz_overrides` | Dùng thời gian chung của quiz | Như trên |
| Bảng plugin điểm danh | C1 lấy từ sổ điểm (112 môn có mục điểm danh) | Cần migration và file riêng |
| Sự kiện đăng nhập trong nhật ký | Số lượt đăng nhập = 0 | Nạp thêm vào `logstore_standard_log` |
| `course_categories` cấp 1–2 | Dùng 4 danh mục cha suy ra từ dữ liệu | Thay bằng file đầy đủ |
| Nhật ký trước 13/09/2026 | Biểu đồ tuần đầu học kỳ trống | Nạp thêm |

### Kiểm thử mốc chuẩn T0 (dữ liệu giả, trước khi sửa mã ETL)

353 đạt, 1 không đạt (`test_ground_truth_precision_recall`), chạy 40 phút 52 giây. Ca không đạt có từ trước, không do thay đổi của đợt này.

### Thiết kế lại phạm vi môn (vấn đề 39 môn)

- Môn có ngày kết thúc: xét như cũ.
- Môn không đặt ngày kết thúc: chỉ tính cảnh báo khi bắt đầu trong học kỳ chứa mốc tính.
- Môn của các học kỳ trước vẫn có trong CSDL nguồn, dùng cho danh mục và các chức năng sinh viên sau này (lịch sử điểm, bài nộp).

### Mốc 2 – đã duyệt (16/11/2026)

Mốc tính của dữ liệu thật: `2026-11-12T15:00:00+07:00`.

### Giai đoạn trước Mốc 3 – đã làm

Thay đổi mã (một bộ mã chạy cả dữ liệu giả và dữ liệu thật):

| File | Thay đổi |
|---|---|
| `database/migrations/analytics/V015__attendance_source.sql` | Thêm cột `attendance_source` (mặc định 'SESSIONS') |
| `etl/extract/sql/courses.sql`, `etl/transform/semester.py`, `etl/extract/course_data.py` | Môn không đặt ngày kết thúc chỉ tính khi bắt đầu trong học kỳ chứa mốc tính |
| `etl/extract/sql/attendance_grades.sql` (mới) | Chuyên cần lấy từ mục điểm danh trong sổ điểm khi môn không có dữ liệu buổi |
| `etl/transform/student_risk.py`, `etl/transform/risk_rules.py` | Quy đổi sổ điểm về thang 100; câu lý do riêng; luật "vắng n buổi" bỏ qua khi nguồn là sổ điểm |
| `etl/extract/sql/assignments.sql` | Hạn hiệu lực: gia hạn > hạn riêng SV > hạn riêng nhóm > hạn chung |
| `etl/extract/sql/completion.sql` | Chỉ tính môn bật hoàn thành và đã có dữ liệu hoàn thành; còn lại = NULL |
| `etl/extract/sql/enrolments.sql` | MSSV lấy từ `idnumber`, trống thì lấy cụm 7 chữ số trong `username` |
| `backend/app/repositories/{teacher,rules,reports}.py`, `backend/app/schemas/teacher.py` | Trả thêm `attendance_source`; cột báo cáo hiển thị tỷ lệ khi nguồn là sổ điểm |
| `frontend/src/utils/format.js` và 3 thành phần | Hiển thị "theo sổ điểm" thay cho "x/100 buổi" |
| `tests/database/test_migrate_runner.py` | Cập nhật danh sách phiên bản migration |

Các migration chỉ cộng thêm (V006–V009 nguồn, V015 phân tích) đã được áp dụng cho cả hai môi trường; trên dữ liệu giả các bảng mới để rỗng.

Kết quả ETL trên dữ liệu thật (`lms_analytics_real`, backfill 13/09–12/11/2026, 186 giây):

| Chỉ số (ngày 12/11/2026) | Giá trị |
|---|---|
| Môn được tính / lượt ghi danh / sinh viên | 39 / 2.288 / 1.201 |
| Xanh / Vàng / Đỏ | 671 / 921 / 696 |
| C1 từ sổ điểm | 795 lượt (612 đạt, 41 cảnh báo, 142 nghiêm trọng); 1.493 lượt chưa có dữ liệu |
| Tỷ lệ hoàn thành | Chưa có dữ liệu ở cả 39 môn |
| Lưu lượng | 1.456 giờ, 360.169 sự kiện, 0 lượt đăng nhập |

Đối soát với truy vấn độc lập trên CSDL nguồn (khớp 100%): lượt ghi danh 2.288; bài đến hạn 16.492, đã nộp 10.282, nộp trễ 2.037; tổng lượt truy cập 331.705; chưa từng truy cập 192; tổng sự kiện lưu lượng 360.169. Bất biến Xanh + Vàng + Đỏ = sĩ số: 0 vi phạm.

Hợp đồng API so với trước khi sửa: 57 đường dẫn không đổi; 2 lược đồ (`RiskStudent`, `StudentDetailOut`) có thêm đúng 1 trường tùy chọn `attendance_source`.

### Mốc 3 – đã duyệt (16/11/2026)

### Giai đoạn trước Mốc 4 – đã làm

- Tạo tài khoản trên `lms_analytics_real`: 23 giảng viên (đồng bộ từ dữ liệu thật) và 1 tài khoản quản trị `admin` (tạo trực tiếp, vì dữ liệu thật không có tài khoản quản trị Moodle trong phạm vi). Mật khẩu là chuỗi ngẫu nhiên không lưu lại: phải đặt lại bằng `python -m backend.app.cli set-password --username <tên>` trước khi dùng.
- Kiểm tra API trên dữ liệu thật: 24 API GET không tham số và 17 API GET có tham số đều trả 200; báo cáo rủi ro và lưu lượng xem trước được.
- Kiểm tra giao diện (`frontend/e2e/real_data_probe.mjs`): 13 màn hình của quản trị và giảng viên, không có lỗi JavaScript, không có phản hồi API lỗi.

Quan sát trên giao diện với dữ liệu thật:

- Tuần đầu của biểu đồ xu hướng có tỷ lệ Đỏ rất cao: nhật ký bắt đầu đúng ngày 13/09 nên hôm đó hầu hết sinh viên chưa có lượt truy cập nào được ghi nhận.
- "Online hiện tại" = 0: file phiên đăng nhập chỉ chụp buổi tối 12/11, còn mốc tính là 15:00.
- Tỷ lệ hoàn thành hiện "Chưa có dữ liệu"; chuyên cần hiện dạng "50% (theo sổ điểm)".
- Trang quản trị chỉ có 1 khoa nên phần so sánh giữa các khoa chỉ có một cột.

### Cách chuyển web sang dữ liệu thật và cách quay lại

Sửa 3 dòng trong `.env` rồi khởi động lại backend và ETL:

```
MOODLE_DB_NAME=moodle_src_real
ANALYTICS_DB_NAME=lms_analytics_real
LMS_AS_OF=2026-11-12T15:00:00+07:00
```

Quay lại dữ liệu giả: đổi về `moodle_src`, `lms_analytics`, `2026-11-06T10:30:00+07:00`.

### Mốc 4 – đã duyệt (16/11/2026)

- Kiểm thử hồi quy trên dữ liệu giả sau khi sửa mã: 345 đạt, 1 không đạt (`test_ground_truth_precision_recall`, đã không đạt từ mốc chuẩn T0), 8 ca sao lưu/khôi phục không chạy lại.
- Đã đổi 3 dòng trong `.env` sang dữ liệu thật; bản cũ ở `var/env.mock.bak` (thư mục không đưa lên git).

Lưu ý sau khi chuyển: bộ kiểm thử tích hợp và e2e hiện có được viết cho dữ liệu giả. Muốn chạy lại chúng phải đổi `.env` về dữ liệu giả (hoặc đặt 3 biến môi trường tương ứng khi chạy).

### Sau Mốc 4 (16/11/2026)

- Đã cập nhật `SPEC/BAO_CAO_TIEN_DO.md` (mục 2.12, 3.9, 4, 5.1), thêm ghi chú dẫn ở đầu `SPEC/KE_HOACH_TRIEN_KHAI.md`, và sửa bản Word `docs/bao_cao/BaoCaoPhanTichThietKePhanMem.docx` (mục 1.4.2, 2.2, 3.1, 6.2, 6.5, 7.1.3, 7.3; xuất lại PDF, 108 trang). Bản Word trước khi sửa: `var/backup_bao_cao/`.
- Nguyên nhân ca `test_ground_truth_precision_recall` không đạt: `UnicodeEncodeError` khi in ma trận nhầm lẫn tiếng Việt ra đầu ra mã hóa cp1252 (kết quả pytest được chuyển hướng vào file). Chạy riêng với `PYTHONIOENCODING=utf-8` thì đạt: recall Đỏ 99,3%, precision Đỏ 86,5%. Chưa sửa mã kiểm thử.

Việc còn lại: đặt mật khẩu cho các tài khoản.

### Sau Mốc 4 – lần 2 (16/11/2026)

- Chủ dự án xác định dữ liệu thiếu là thiếu vĩnh viễn: không chờ nạp bổ sung; tài liệu và báo cáo Word ghi theo hướng này.
- Báo cáo Word cập nhật lên phiên bản 1.2 (xem `SPEC/BAO_CAO_TIEN_DO.md` mục 2.13).

### Gỡ bỏ dữ liệu mô phỏng (16/11/2026)

Chủ dự án yêu cầu chỉ giữ dữ liệu thật, không sao lưu dữ liệu mô phỏng. Đã xóa hai CSDL `moodle_src`, `lms_analytics` (và
`lms_analytics_etlbench`), mã sinh dữ liệu `mockdata/` và các kiểm thử chỉ dùng dữ liệu mô phỏng. Phương án quay lại
(rollback) bằng `.env` ở mục 5 không còn dùng được. Chi tiết: `SPEC/BAO_CAO_TIEN_DO.md` mục 2.14.

