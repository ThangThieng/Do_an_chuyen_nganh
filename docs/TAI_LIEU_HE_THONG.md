# HỆ THỐNG TRỰC QUAN HÓA DỮ LIỆU LMS MOODLE – TÀI LIỆU TỔNG HỢP

> Đồ án chuyên ngành – Khoa Công nghệ Thông tin, Trường Đại học Đà Lạt
> Cập nhật: 10/10/2026 – phiên bản 1.2 (góp ý giao diện, luật cảnh báo theo môn, trung tâm can thiệp, dữ liệu 5 khoa)
>
> Tài liệu khác: [Góp ý giao diện và kế hoạch v1.2](gop_y_giao_dien/TongHop_GopY_GiaoDien_va_KeHoach_v1.2.docx) · [Kế hoạch](../SPEC/KE_HOACH_TRIEN_KHAI.md) · [Tiến độ và các thay đổi so với kế hoạch](../SPEC/BAO_CAO_TIEN_DO.md) · [Kết quả kiểm thử](KET_QUA_KIEM_THU.md)

---

## MỤC LỤC

1. [Hệ thống làm được gì](#1-hệ-thống-làm-được-gì)
2. [Kiến trúc tổng thể](#2-kiến-trúc-tổng-thể)
3. [Công nghệ và cách cài đặt](#3-công-nghệ-và-cách-cài-đặt)
4. [Cơ sở dữ liệu](#4-cơ-sở-dữ-liệu)
5. [Tiến trình ETL](#5-tiến-trình-etl)
6. [API](#6-api)
7. [Giao diện web](#7-giao-diện-web)
8. [Hướng dẫn sử dụng web](#8-hướng-dẫn-sử-dụng-web)
9. [Minh chứng trực quan hóa dữ liệu](#9-minh-chứng-trực-quan-hóa-dữ-liệu)
10. [Kiểm thử và hiệu năng](#10-kiểm-thử-và-hiệu-năng)
11. [Hạn chế và hướng phát triển](#11-hạn-chế-và-hướng-phát-triển)

---

## 1. HỆ THỐNG LÀM ĐƯỢC GÌ

Hệ thống đọc dữ liệu thô của Moodle (khóa học, ghi danh, nhật ký truy cập, bài nộp, điểm danh, hoàn thành hoạt động), tổng hợp thành 3 bảng dữ liệu phân tích, rồi hiển thị thành biểu đồ cho hai nhóm người dùng:

| Người dùng | Câu hỏi họ cần trả lời | Màn hình đáp ứng |
|---|---|---|
| **Quản trị / Phòng đào tạo** | Toàn trường đang thế nào, khoa nào nổi bật, xu hướng tốt lên hay xấu đi? | Trang Tổng quan (cấp toàn trường): thẻ KPI, biểu đồ tròn + đồ thị xu hướng mức rủi ro, biểu đồ cột so sánh 5 khoa kèm bảng |
| | Trong một khoa, môn nào cần chú ý; trong một môn, sinh viên nào? | Trang Khoa → trang Môn học → cửa sổ chi tiết sinh viên (đi từ vĩ mô xuống vi mô, mỗi cấp một URL) |
| | Số liệu lấy từ đâu, tính thế nào? | Liên kết "Nguồn & cách tính" trên mọi biểu đồ: bảng Moodle nguồn, công thức, luật 3 tiêu chí đang áp dụng |
| | Hệ thống bị truy cập nhiều vào lúc nào, có bao nhiêu người đang online? | Trang Lưu lượng: biểu đồ đường 2 trục, heatmap giờ × thứ, thẻ thời gian thực |
| | Cần số liệu để báo cáo | Trang Báo cáo: xem trước và xuất Excel/PDF |
| **Giảng viên** | Sinh viên nào đang có nguy cơ bỏ học / trượt môn, vì lý do gì? | Trang Cảnh báo: đèn giao thông đỏ/vàng/xanh, biểu đồ tròn, bảng cảnh báo, cửa sổ chi tiết từng sinh viên |
| | Lớp học tiến tới đâu, chương nào sinh viên chưa theo kịp? | Trang Tiến độ lớp: thanh tiến độ, tiến độ theo chương, biểu đồ đường theo tuần |
| | Môn của tôi có đặc thù (thực hành, đồ án) – ngưỡng chung chưa hợp? | Trang Thiết lập cảnh báo: ngưỡng, trọng số, luật bổ sung riêng cho môn, xem trước tác động trước khi lưu |
| | Nhắc sinh viên thế nào cho nhanh và có bằng chứng? | Trang Can thiệp: soạn tin cá nhân hóa, gửi tin nhắn Moodle / email thật, nhắc tự động, lịch sử kèm mã xác nhận |

Ba tiêu chí xác định sinh viên nguy cơ (mỗi tiêu chí 0, 1 hoặc 2 điểm):

| Tiêu chí | 0 điểm | 1 điểm | 2 điểm |
|---|---|---|---|
| **C1 – Vắng học** | vắng < 15% số buổi | 15% – dưới 30% | từ 30% trở lên |
| **C2 – Không tương tác** | vào môn trong 7 ngày qua và lượt truy cập 14 ngày ≥ 50% trung vị lớp | 7–14 ngày chưa vào, hoặc truy cập thấp hơn 50% trung vị lớp | chưa từng vào, hoặc trên 14 ngày không vào |
| **C3 – Thiếu bài tập** | thiếu < 20% số bài đã tới hạn | 20% – dưới 60% | từ 60% trở lên |

Xếp mức: **ĐỎ** khi C2 = 2, hoặc có từ 2 tiêu chí đạt 2 điểm, hoặc tổng điểm ≥ 4 · **VÀNG** khi tổng ≥ 1 · **XANH** khi tổng = 0.
Điểm rủi ro = `làm tròn(100 × (0,35·C1 + 0,30·C2 + 0,35·C3) / 2)`, cho ra số 0–100 để sắp xếp danh sách.

Đây là **luật mặc định của trường** (bộ luật `v1.1`, lưu trong bảng `risk_rule_set`). Từ phiên bản 1.2, giảng viên chính của môn có thể đặt **luật riêng** cho môn (ngưỡng, trọng số trong giới hạn an toàn, và tối đa 5 luật bổ sung chỉ được *nâng* mức, ví dụ "bỏ nộp 2 bài liên tiếp → Nguy cơ cao"). Luật xếp mức chung giữ nguyên để mức rủi ro còn so sánh được giữa các môn; mỗi dòng kết quả ghi `rule_set_id` của bộ luật đã dùng, nên số liệu ngày cũ không bị chấm lại.

---

## 2. KIẾN TRÚC TỔNG THỂ

```
┌────────────────────┐   Đọc (chỉ SELECT)   ┌──────────────────────┐   COPY + UPSERT   ┌────────────────────┐
│  moodle_src        │ ───────────────────▶ │  ETL Python          │ ────────────────▶ │  lms_analytics     │
│  30 bảng mdl_*     │   SQL tĩnh, :as_of   │  extract → transform │                   │  3 bảng fact +     │
│  (nguồn Moodle)    │                      │  → load, APScheduler │                   │  bảng phụ trợ      │
└────────────────────┘                      └──────────────────────┘                   └─────────┬──────────┘
         ▲                                                                                       │ SQL < 10 ms
         │ sinh dữ liệu giả lập (mockdata/)                                                      ▼
         │                                                                              ┌────────────────────┐
         │                                                                              │  FastAPI           │
         │                                                                              │  JWT · phân quyền  │
         │                                                                              │  Excel · PDF       │
         │                                                                              └─────────┬──────────┘
         │                                                                                       │ REST /api/v1
         │                                                                                       ▼
         │                                                                              ┌────────────────────┐
         └───────────────── (không ghi ngược) ─────────────────────────────────────────  │  React + Chart.js  │
                                                                                        │  Admin · Giảng viên│
                                                                                        └────────────────────┘
```

Nguyên tắc thiết kế quan trọng:

- **Tách hai cơ sở dữ liệu.** ETL chỉ đọc Moodle, mọi kết quả ghi sang CSDL phân tích riêng. Kết nối tới Moodle đặt chế độ chỉ đọc và giới hạn thời gian truy vấn 60 giây, nên không thể làm hỏng hay làm chậm hệ thống học tập.
- **Phi chuẩn hóa để đọc nhanh.** Tên khoa, tên môn, MSSV, họ tên được ghi thẳng vào bảng fact, nên API không phải JOIN.
- **Phân quyền nằm trong dữ liệu.** Mỗi dòng fact có cột `teacher_ids` (mảng số nguyên) với index GIN. Giảng viên chỉ đọc được dòng có mã mình trong mảng.
- **Thời điểm tham chiếu `AS_OF`.** Toàn hệ thống (mock data, ETL, API, giao diện) coi "bây giờ" là giá trị biến `LMS_AS_OF`. Nhờ vậy dữ liệu demo luôn ở giữa học kỳ và dựng lại được lịch sử từng ngày. Để trống biến này thì hệ thống chạy theo thời gian thực.

---

## 3. CÔNG NGHỆ VÀ CÁCH CÀI ĐẶT

### 3.1 Công nghệ

| Lớp | Công nghệ | Vai trò |
|---|---|---|
| CSDL | PostgreSQL 18 | Cả CSDL nguồn `moodle_src` lẫn CSDL phân tích `lms_analytics` |
| Sinh dữ liệu | Python 3.11, NumPy, pandas, psycopg 3 | Tạo dữ liệu Moodle giả lập có quy luật hành vi và "đáp án" kiểm chứng |
| ETL | pandas, SQLAlchemy 2, psycopg 3, APScheduler | Trích xuất, tính toán, nạp, lập lịch |
| API | FastAPI, Pydantic, PyJWT, bcrypt, openpyxl, ReportLab, cachetools | REST, xác thực, phân quyền, xuất Excel/PDF |
| Giao diện | React 18, Vite 5, Chart.js 4 (react-chartjs-2, chart-matrix, plugin-annotation), Ant Design 5, React Query, axios | Dashboard |
| Kiểm thử | pytest, vitest, Playwright, axe-core, Locust | Dữ liệu, API, giao diện, khả năng tiếp cận, tải |
| Triển khai | Docker Compose, Nginx | Demo một lệnh |

### 3.2 Cách chạy nhanh nhất: Docker

Chỉ cần Docker Desktop.

```powershell
Copy-Item docker/.env.example docker/.env
# Mở docker/.env và điền 2 giá trị:
#   BACKEND_JWT_SECRET    – chuỗi ngẫu nhiên >= 32 ký tự
#   BACKEND_SEED_PASSWORD – mật khẩu ban đầu cho tài khoản, >= 8 ký tự
docker compose --env-file docker/.env up --build -d
docker compose --env-file docker/.env logs -f init     # chờ dòng "[init] Hoàn tất."
```

Mở <http://localhost:8080>. Sáu dịch vụ trong `docker-compose.yml`:

| Dịch vụ | Việc |
|---|---|
| `db` | PostgreSQL 18, dữ liệu nằm trong volume `pgdata`, không mở cổng ra ngoài |
| `init` | Chạy một lần: migrate 2 CSDL → sinh mock data → ETL backfill → tạo tài khoản. Chạy lại thì tự bỏ qua nếu đã có dữ liệu |
| `etl` | APScheduler chạy các job theo lịch |
| `backend` | FastAPI (2 worker) |
| `moodle-stub` | Máy chủ Moodle 3.9 mô phỏng cho kênh tin nhắn (`core_message_send_instant_messages`), ghi vào `moodle_src`. Bỏ đi khi trỏ `MOODLE_WS_URL` tới Moodle thật |
| `web` | Nginx phục vụ bản build React và chuyển tiếp `/api` sang backend |

Xóa sạch để làm lại: `docker compose --env-file docker/.env down -v`.

### 3.3 Cách chạy khi phát triển

Cần Python 3.11, Node 20+, PostgreSQL 18 cài sẵn trên máy.

```powershell
Copy-Item .env.example .env      # điền mật khẩu PostgreSQL và BACKEND_JWT_SECRET
.\scripts\lms.ps1 setup          # cài thư viện Python + npm, migrate 2 CSDL
.\scripts\lms.ps1 seed           # dựng cấu trúc Moodle giả lập: 5 khoa, 58 môn, 3.000 SV, 28 GV (~1 phút)
.\scripts\lms.ps1 mock           # sinh hành vi học tập tới thời điểm AS_OF – 6,4 triệu dòng nhật ký (~7 phút)
.\scripts\lms.ps1 etl-backfill   # nạp lịch sử 3 bảng fact 07/09 → 06/11/2026 (~32 phút)
$env:BACKEND_SEED_PASSWORD = "<mật khẩu>"; .\scripts\lms.ps1 users
.\scripts\lms.ps1 api            # cửa sổ 1 – http://localhost:8000/api/docs
.\scripts\lms.ps1 web            # cửa sổ 2 – http://localhost:5173
.\scripts\lms.ps1 moodle-stub    # cửa sổ 3 – máy chủ Moodle 3.9 mô phỏng :8091 (gửi tin nhắn Moodle)
```

Trên Linux/macOS dùng `make setup`, `make seed`, `make mock`, `make etl-backfill`, `make api`, `make web`.

### 3.4 Các biến cấu hình chính (`.env`)

| Biến | Ý nghĩa |
|---|---|
| `ANALYTICS_DB_*`, `MOODLE_DB_*` | Kết nối hai CSDL (host, port, tên, user, mật khẩu) |
| `APP_TIMEZONE` | Múi giờ, mặc định `Asia/Ho_Chi_Minh` |
| `LMS_AS_OF` | Thời điểm tham chiếu, mặc định `2026-11-06T10:30:00+07:00` (tuần 9 của học kỳ demo). Để trống = thời gian thực |
| `BACKEND_JWT_SECRET` | Khóa ký JWT, bắt buộc, ≥ 32 ký tự |
| `BACKEND_JWT_EXPIRE_MINUTES` | Hạn token, mặc định 480 phút |
| `BACKEND_CORS_ORIGINS` | Các origin được gọi API |
| `BACKEND_PDF_FONT` | Font TrueType có dấu tiếng Việt cho PDF (mặc định Arial trên Windows, DejaVu trên Linux) |
| `MAIL_TRANSPORT` | Kênh email: `file` (ghi file `.eml` vào `MAIL_FILE_DIR`, mặc định), `smtp`, `off` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM` | Máy chủ thư của trường (mật khẩu chỉ nằm trong `.env`, không bao giờ ghi vào CSDL, log hay API) |
| `MAIL_DELIVERY`, `MAIL_REDIRECT_TO` | `redirect` (mặc định): mọi email tới hộp thư kiểm thử; `live`: gửi tới sinh viên khi đủ điều kiện |
| `MOODLE_WS_URL`, `MOODLE_WS_TOKEN`, `MOODLE_WS_ENV` | Moodle Web Service để gửi tin nhắn; `MOODLE_WS_ENV=stub` cho máy chủ mô phỏng, `live` cho Moodle thật |
| `MESSAGING_ALLOW_LIVE` | Cờ cho phép gửi tới người nhận thật (mặc định `false`). Chỉ có hiệu lực khi `LMS_AS_OF` trống **và** kênh đã kiểm tra thành công với đúng cấu hình hiện tại |
| `MESSAGING_QUIET_HOURS` | Khung giờ không gửi tin tự động, mặc định `22-6` |

---

## 4. CƠ SỞ DỮ LIỆU

### 4.1 Hai cơ sở dữ liệu

| CSDL | Vai trò | Quy mô hiện tại (dữ liệu demo) |
|---|---|---|
| `moodle_src` | Bản rút gọn của Moodle 3.9: 30 bảng `mdl_*` giữ **đúng tên bảng, tên cột, kiểu dữ liệu, giá trị mặc định và tên index** của Moodle thật | 2,6 GB · 6.385.738 dòng nhật ký · 3.000 sinh viên · 58 môn · 13.105 lượt ghi danh |
| `lms_analytics` | CSDL phân tích: 3 bảng fact + bộ luật cảnh báo, hàng đợi gửi tin, bảng phụ trợ | 1,25 GB · 770.314 dòng cảnh báo · 3.538 dòng tiến độ · 1.450 dòng lưu lượng |

Vì các câu SQL trích xuất viết theo đúng cấu trúc Moodle thật, khi có Moodle thật chỉ cần đổi thông tin kết nối trong `.env` là ETL chạy được, không phải sửa mã.

### 4.2 Cách xem cơ sở dữ liệu

```powershell
# Trạng thái migration
python -m database.migrate status --target analytics
python -m database.migrate status --target moodle

# Vào psql (mật khẩu trong .env)
psql -U postgres -d lms_analytics
```

Vài truy vấn xem nhanh:

```sql
-- Các bảng và dung lượng
SELECT relname, n_live_tup AS so_dong, pg_size_pretty(pg_total_relation_size(relid)) AS dung_luong
FROM pg_stat_user_tables WHERE schemaname = 'analytics' ORDER BY n_live_tup DESC;

-- Phân bố đèn giao thông của ngày mới nhất
SELECT risk_level, COUNT(*) FROM analytics.fact_student_risk_summary
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary)
GROUP BY risk_level;

-- Lịch sử chạy ETL
SELECT job_name, status, started_at, finished_at - started_at AS thoi_gian, rows_loaded
FROM analytics.etl_run_log ORDER BY run_id DESC LIMIT 10;
```

### 4.3 CSDL nguồn `moodle_src` – 30 bảng

| Nhóm | Bảng |
|---|---|
| Danh mục và khóa học | `mdl_course_categories`, `mdl_course`, `mdl_course_sections` |
| Người dùng và vai trò | `mdl_user`, `mdl_role`, `mdl_role_assignments`, `mdl_context` |
| Ghi danh | `mdl_enrol`, `mdl_user_enrolments`, `mdl_groups`, `mdl_groups_members` |
| Nhật ký và phiên | `mdl_logstore_standard_log`, `mdl_sessions`, `mdl_user_lastaccess` |
| Hoạt động | `mdl_modules`, `mdl_course_modules`, `mdl_course_modules_completion`, `mdl_assign`, `mdl_assign_submission`, `mdl_page`, `mdl_forum` |
| Điểm danh (plugin mod_attendance) | `mdl_attendance`, `mdl_attendance_sessions`, `mdl_attendance_statuses`, `mdl_attendance_log` |
| Nhắn tin (v1.2, migration moodle V005) | `mdl_user_preferences`, `mdl_message_conversations`, `mdl_message_conversation_members`, `mdl_messages`, `mdl_notifications` – nơi máy chủ Moodle mô phỏng ghi tin; ETL không đọc |

Dữ liệu giả lập mô phỏng học kỳ 1 năm học 2026-2027 (bắt đầu 07/09/2026, 15 tuần) của **5 khoa** (v1.2 – kế hoạch chương 6):

| Khoa | Bộ môn | Môn (loại) | Sinh viên | Hồ sơ Xanh/Vàng/Đỏ · hệ số truy cập |
|---|---|---|---:|---|
| Công nghệ Thông tin | 4 | 15 môn IT001–IT015 (LT 6, TH 7, ĐA 2) | 600 | 65/20/15% · 1,00 |
| Kinh tế – Quản trị kinh doanh | 3 | 12 môn KT101–KT112 | 850 | 70/19/11% · 0,90 |
| Ngoại ngữ | 2 | Tiếng Anh 1 chia 4 lớp NN101_N01–N04 (SV mọi khoa) + 8 môn NN201–NN208 | 500 | 75/17/8% · 1,15 |
| Luật | 2 | 10 môn LU101–LU110 | 550 | 66/20/14% · 0,85 |
| Sinh học | 2 | 9 môn SH101–SH109 | 500 | 58/22/20% · 0,80 |

Mỗi sinh viên học 3–5 môn của khoa mình; khoảng 40% sinh viên các khoa khác học thêm một lớp Tiếng Anh 1. MSSV 7 chữ số theo khoa (2212001…, 2222001…, 2232001…, 2242001…, 2252001…), `mdl_user.department` ghi khoa, `institution` = "Trường Đại học Đà Lạt". 28 giảng viên (8 của CNTT giữ nguyên tài khoản demo, 5 cho mỗi khoa khác), một số môn có trợ giảng; tài khoản dịch vụ `lmsanalytics` gửi tin nhắn Moodle; 1% sinh viên đặt `message_blocknoncontacts = 0` (Moodle 3.9: chỉ nhận tin từ danh bạ) để có ca Moodle từ chối tin. Cấu trúc hoạt động theo loại môn: Lý thuyết – 3 bài lớn và 1 hoạt động "Điểm danh"; Thực hành – báo cáo hằng tuần và 2 hoạt động "Điểm danh lý thuyết" + "Điểm danh thực hành"; Đồ án – báo cáo tiến độ hằng tuần + báo cáo cuối kỳ, hoạt động "Gặp giảng viên hướng dẫn".

Hành vi học tập giữ mô hình cũ (trọng số giờ trong ngày, thứ trong tuần, cao điểm giữa kỳ và 48 giờ trước hạn nộp, sinh viên "bỏ dần" từ tuần 7, phiên ứng dụng di động) và nhân thêm hệ số truy cập theo khoa ở bảng trên để các khoa thực sự khác nhau khi so sánh.

Các trường hợp đặc biệt được tạo có chủ ý để kiểm tra ETL xử lý đúng: sinh viên bị khóa, bị xóa, ghi danh bị tạm dừng, ghi danh hết hạn giữa kỳ, phương thức ghi danh bị tắt, bài nộp theo nhóm, buổi điểm danh theo nhóm, môn chưa có buổi điểm danh, sinh viên chưa từng truy cập, sinh viên "bỏ dần", đăng nhập lỗi, truy cập từ ứng dụng di động.

File `mockdata/output/ground_truth_profiles.csv` lưu "đáp án" hồ sơ hành vi của từng cặp sinh viên–môn, dùng để chấm độ chính xác của luật rủi ro.

### 4.4 CSDL phân tích `lms_analytics`

Toàn bộ nằm trong schema `analytics`, tạo bằng 7 migration có kiểm tra checksum:

| Migration | Nội dung |
|---|---|
| V001 | Schema, 4 domain dùng chung, trigger `set_updated_at`, các bảng `etl_run_log`, `etl_watermark`, `app_user` |
| V002 | `fact_student_risk_summary` (FACT 1) |
| V003 | `fact_course_progress_daily` (FACT 2) |
| V004 | `fact_server_traffic_hourly` (FACT 3) |
| V005 | `intervention_log`, view `v_student_risk_latest` |
| V006 | `etl_online_snapshot`, ràng buộc `attendance_status` khớp điểm tiêu chí C1 |
| V007 | Tỷ lệ chưa có dữ liệu lưu `NULL` thay vì 0 |

#### Sơ đồ quan hệ

```
                          ┌──────────────────┐
                          │ etl_run_log      │  mỗi lần chạy job ETL
                          │ run_id (PK)      │
                          └────────┬─────────┘
            etl_run_id (FK, ON DELETE SET NULL) │
        ┌─────────────────────────┼─────────────────────────┬───────────────────────┐
        ▼                         ▼                         ▼                       ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│fact_student_risk_    │ │fact_course_progress_ │ │fact_server_traffic_│ │etl_online_snapshot │
│summary               │ │daily                 │ │hourly              │ │slot_start (PK)     │
│PK(course_id,user_id, │ │PK(course_id,         │ │PK(stat_hour)       │ │online_users        │
│   snapshot_date)     │ │   stat_date)         │ │                    │ │source              │
└──────────────────────┘ └──────────────────────┘ └────────────────────┘ └────────────────────┘

┌──────────────────┐        ┌────────────────────┐        ┌──────────────────┐
│ app_user         │◀───────│ intervention_log   │        │ etl_watermark    │
│ user_id (PK)     │  FK    │ course_id, user_id │        │ job_name (PK)    │
│ = mdl_user.id    │        │ action_type, nội dung│      │ last_log_id      │
└──────────────────┘        └────────────────────┘        └──────────────────┘
```

Ba bảng fact **không** có khóa ngoại tới Moodle vì là hai CSDL khác nhau; liên kết bằng khóa logic (`course_id`, `user_id` chính là `mdl_course.id`, `mdl_user.id`).

#### FACT 1 – `fact_student_risk_summary`

Mỗi dòng là ảnh chụp của một sinh viên trong một môn vào một ngày. Đây là bảng phục vụ màn hình cảnh báo của giảng viên.

| Nhóm cột | Cột | Ghi chú |
|---|---|---|
| Khóa | `snapshot_date`, `course_id`, `user_id` | Khóa chính là (`course_id`, `user_id`, `snapshot_date`) |
| Chiều phi chuẩn hóa | `faculty_id`, `faculty_name`, `course_shortname`, `course_fullname`, `academic_year`, `semester`, `teacher_ids`, `student_code`, `student_name`, `email` | API không cần JOIN |
| Tiêu chí 2 – tương tác | `total_access_count`, `access_count_7d`, `access_count_14d`, `active_actions`, `last_access_time`, `days_since_last_access` | `days_since_last_access` = NULL nghĩa là chưa từng vào môn |
| Tiêu chí 1 – điểm danh | `total_sessions`, `attended_sessions`, `absent_sessions`, `absence_rate`, `attendance_status` | `absence_rate` = NULL khi môn chưa có buổi điểm danh |
| Tiêu chí 3 – bài tập | `total_assignments`, `submitted_assignments`, `missing_assignments_count`, `late_submissions`, `completion_rate` | `total_assignments` chỉ đếm bài **đã tới hạn** |
| Kết quả đánh giá | `score_attendance`, `score_inactivity`, `score_assignment`, `risk_score`, `risk_level`, `risk_reasons` | `risk_reasons` là mảng JSON câu chữ tiếng Việt |
| Dữ liệu cho cửa sổ chi tiết | `weekly_activity`, `assignment_detail`, `class_avg_access` | JSONB, giúp Modal không phải hỏi ngược Moodle |

Ví dụ một dòng (rút gọn):

```json
{
  "snapshot_date": "2026-11-06", "course_id": 2, "user_id": 42,
  "course_shortname": "IT001", "student_code": "2212032", "student_name": "Bùi Mai Oanh",
  "total_sessions": 18, "absent_sessions": 9, "absence_rate": 50.00, "attendance_status": "CRITICAL",
  "total_assignments": 3, "submitted_assignments": 0, "missing_assignments_count": 3,
  "days_since_last_access": null, "access_count_14d": 0,
  "score_attendance": 2, "score_inactivity": 2, "score_assignment": 2,
  "risk_score": 100, "risk_level": "RED",
  "risk_reasons": ["Vắng 9/18 buổi (50%)", "Chưa từng truy cập môn học", "Thiếu 3/3 bài tập"],
  "weekly_activity": [{"week": 1, "views": 0, "actions": 0, "sessions": 2, "present": 2, "attended": true}, "..."],
  "assignment_detail": [{"name": "Bài tập 1", "status": "missing", "late": false}, "..."]
}
```

Index: `(course_id, snapshot_date DESC, risk_level, risk_score DESC)` cho bảng cảnh báo; GIN trên `teacher_ids` cho phân quyền; `(user_id, snapshot_date DESC)` cho lịch sử; `(faculty_id, academic_year, semester, snapshot_date)` cho báo cáo; index một phần chỉ chứa dòng `risk_level = 'RED'`.

#### FACT 2 – `fact_course_progress_daily`

Mỗi dòng là số liệu của một môn trong một ngày: `total_enrolled_students`, `active_students_day`, `active_students_7d`, `total_active_students`, `total_views_day`, `total_actions_day`, `submissions_day`, `total_assignments`, `assignment_submission_rate`, `attendance_rate`, `avg_completion_rate`, `avg_access_per_student`, `red_count`, `yellow_count`, `green_count`, và `section_progress` (JSONB: tiến độ từng chương).

#### FACT 3 – `fact_server_traffic_hourly`

Mỗi dòng là một giờ: `total_requests`, `unique_users`, `login_count`, `failed_login_count`, `ws_requests` (truy cập từ ứng dụng di động), `peak_online_users`, `avg_online_users`, `online_sample_count`, `is_peak_hour`. Ba cột `stat_date`, `hour_of_day`, `day_of_week` là cột sinh tự động từ `stat_hour` nên không bao giờ lệch nhau.

#### Ràng buộc toàn vẹn

Schema tự bảo vệ dữ liệu, không phụ thuộc vào việc ETL có đúng hay không. Ví dụ:

- `active_students_day ≤ active_students_7d ≤ total_enrolled_students`
- `access_count_7d ≤ access_count_14d ≤ total_access_count`
- `missing_assignments_count = total_assignments − submitted_assignments`
- `attended_sessions + absent_sessions ≤ total_sessions`
- `attendance_status = 'NO_DATA'` khi và chỉ khi `total_sessions = 0`; `OK`/`WARN`/`CRITICAL` phải khớp `score_attendance` 0/1/2
- `absence_rate IS NULL` khi và chỉ khi `total_sessions = 0`
- `avg_online_users ≤ peak_online_users`; `unique_users ≤ total_requests`
- Mọi tỷ lệ nằm trong 0–100 (domain `percent_t`), năm học đúng dạng `YYYY-YYYY` với năm sau = năm trước + 1

Có 30 test tự động thử ghi dữ liệu sai vào từng ràng buộc và bắt buộc CSDL phải từ chối.

---

## 5. TIẾN TRÌNH ETL

### 5.1 Luồng một job

1. Xin khóa `pg_try_advisory_lock`; nếu job trùng đang chạy thì bỏ lượt này (không bao giờ chạy chồng).
2. Ghi một dòng `etl_run_log` trạng thái `RUNNING`.
3. **Extract**: chạy các câu SQL tĩnh trong `etl/extract/sql/` trên Moodle, trong **một transaction REPEATABLE READ** nên mọi bảng đọc trên cùng một ảnh chụp.
4. **Transform** bằng pandas: tính chỉ số từng sinh viên, chấm điểm rủi ro, dựng JSONB cho biểu đồ.
5. **Load**: `COPY` vào bảng tạm rồi `INSERT ... ON CONFLICT DO UPDATE ... WHERE giá trị cũ IS DISTINCT FROM giá trị mới`; watermark cập nhật trong cùng transaction.
6. Ghi `etl_run_log` thành `SUCCESS` hoặc `FAILED` kèm thông báo lỗi.

Chạy lại một job không tạo bản ghi trùng và không làm đổi dữ liệu nếu nguồn không đổi — điều này được kiểm chứng bằng test so sánh checksum toàn bảng.

### 5.2 Các job và lịch chạy

| Job | Lịch | Việc chính |
|---|---|---|
| `traffic` | mỗi 5 phút | Tổng hợp nhật ký mới theo watermark; chụp số người online từ `mdl_sessions` |
| `course_progress` | phút thứ 5 mỗi giờ | Số liệu trong ngày của các môn đang diễn ra |
| `student_risk` | 07:15–21:15, mỗi 2 giờ | Snapshot cảnh báo của hôm nay (ghi đè) |
| `nightly` | 01:00 | Chốt số liệu hôm qua lúc 23:59:59, tính lại 24 giờ lưu lượng, đánh dấu giờ cao điểm (vượt P90 của 28 ngày) |
| `maintenance` | Chủ nhật 03:00 | Snapshot cũ hơn 180 ngày chỉ giữ bản cuối tuần; `VACUUM ANALYZE` |
| `backfill` | thủ công | Nạp lại lịch sử từ một ngày tới `AS_OF` |

Chạy tất cả tự động: `python -m etl.scheduler` (hoặc dịch vụ `etl` trong Docker).

### 5.3 Vài quyết định kỹ thuật đáng chú ý

- **Lần truy cập cuối tính từ nhật ký**, không lấy từ `mdl_user_lastaccess`, vì bảng đó chỉ giữ giá trị hiện tại nên không dựng lại được lịch sử.
- **Tỷ lệ hoàn thành chỉ tính hoạt động đã tới hạn**; nếu tính cả các tuần chưa học thì giữa kỳ lớp nào cũng "thấp".
- **Danh sách ghi danh viết dạng `EXISTS`** thay vì JOIN nhiều bảng: dạng JOIN khiến PostgreSQL ước lượng sai và quét nhật ký cho từng sinh viên, gây quá thời gian.
- **Mẫu người online lưu riêng theo khung 5 phút** rồi mới tính max/trung bình theo giờ, nhờ đó chạy lại job không bị đếm trùng.

---

## 6. API

Tiền tố `/api/v1`. Tài liệu tương tác (Swagger) tại `/api/docs`.

| Nhóm | Endpoint | Vai trò |
|---|---|---|
| Xác thực | `POST /auth/login`, `GET /auth/me` | – |
| Dùng chung | `GET /filters`, `GET /etl/status`, `GET /health` | Mọi vai trò (health không cần đăng nhập) |
| Admin 1.1 | `GET /admin/overview/kpis`, `/admin/enrollment/by-faculty`, `/admin/enrollment/faculties/{id}/courses`, `/admin/enrollment/courses/{id}/students` | ADMIN |
| Admin 1.2 | `GET /admin/traffic/hourly`, `/admin/traffic/realtime`, `/admin/traffic/heatmap` | ADMIN |
| Admin 1.3 | `GET /admin/reports/preview`, `GET /admin/reports/export` | ADMIN |
| Giảng viên 2.1 | `GET /teacher/courses`, `/teacher/courses/{id}/risk-summary`, `/students`, `/students/{uid}`, `POST /students/{uid}/interventions`, `GET /export` | TEACHER |
| Giảng viên 2.2 | `GET /teacher/courses/{id}/progress`, `/students/{uid}/compare` | TEACHER |
| Tài khoản (v1.1) | `POST /auth/change-password` | Mọi vai trò |
| Tổng quan v1.2 | `GET /admin/compare/faculties`, `/admin/risk-trend` (toàn trường hoặc `faculty_id`, theo tuần/ngày), `/admin/courses/{id}/risk-summary`, `/risk-students`, `/students/{uid}` (xem, không can thiệp) | ADMIN |
| Minh bạch v1.2 | `GET /meta/metrics` (danh mục chỉ số: công thức, bảng Moodle nguồn), `/meta/risk-rule` (luật đang áp dụng, của trường hoặc của môn), `/meta/freshness`, `/meta/channels` | Mọi vai trò |
| Luật theo môn v1.2 | `GET/PUT/DELETE /teacher/courses/{id}/risk-rules`, `POST …/risk-rules/preview`; `GET /teacher/courses/{id}/risk-trend` | TEACHER (lưu/khôi phục: chỉ GV chính) |
| Can thiệp v1.2 | `GET /teacher/courses/{id}/contact-list`; `GET/POST/PUT/DELETE /teacher/message-templates`; `POST …/messages/preview`, `POST/GET …/messages`, `POST …/messages/{id}/approve\|cancel\|retry`; `GET/POST/PUT/DELETE …/auto-prompts`, `POST …/auto-prompts/{id}/dry-run\|run` | TEACHER |
| Kênh gửi tin v1.2 | `GET /admin/channels`, `POST /admin/channels/test-moodle`, `POST /admin/channels/test-email` | ADMIN |
| Hệ thống (v1.1) | `GET /admin/users`, `POST /admin/users/{id}/active`, `POST /admin/users/{id}/reset-password`, `GET /admin/etl/runs`, `GET /admin/catalog/courses`, `GET/POST /admin/backups`, `GET /admin/backups/{name}/download`, `POST /admin/backups/{name}/restore`, `DELETE /admin/backups/{name}` | ADMIN |

Bảo mật:

- Mật khẩu băm **bcrypt**; token **JWT HS256** hết hạn sau 8 giờ.
- Vai trò đọc lại từ CSDL ở **mỗi request**, không tin trường `role` trong token, nên khóa tài khoản là mất quyền ngay.
- Đổi hoặc đặt lại mật khẩu ghi `password_changed_at`; token phát hành trước thời điểm đó bị từ chối (v1.1).
- Giảng viên truy cập môn của người khác nhận **403**; môn không tồn tại nhận **404**; chưa đăng nhập hoặc token sai/hết hạn nhận **401**.
- Mọi truy vấn dữ liệu của giảng viên đều kèm điều kiện `teacher_ids @> ARRAY[mã giảng viên]`.
- Đăng nhập sai quá 5 lần trong 5 phút (theo IP + tên đăng nhập) bị chặn tạm, trả **429**.
- SQL luôn dùng tham số bind; tên cột sắp xếp lấy từ danh sách cho phép; ký tự đại diện trong ô tìm kiếm được thoát.
- Response API có `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.

Mỗi response đều có `data_updated_at` — thời điểm ETL chạy thành công gần nhất, để giao diện nói rõ dữ liệu cũ hay mới.

---

## 7. GIAO DIỆN WEB

```
frontend/src/
├── api/            client.js (axios + JWT + tải file), hooks.js (React Query cho từng endpoint)
├── auth/           đăng nhập, tự hết phiên khi token hết hạn
├── routes/         ProtectedRoute – chặn theo vai trò
├── theme/tokens.js màu đèn giao thông, màu chuỗi dữ liệu, màu khung
├── utils/format.js định dạng vi-VN, "Chưa có dữ liệu" cho giá trị NULL
├── charts/         TrafficDualAxisChart, TrafficHeatmap, RiskDoughnut, RiskTrendChart, ComparisonCharts, StudentCharts
├── components/     AppHeader, TermFilterBar, LevelBreadcrumb, RiskOverviewPanel, CourseTables, RiskStudentTable,
│                   StudentDetailModal, ScoreBreakdown, MessageComposer, MetricInfo, common (RiskBadge, KpiCard, ChartCard)
├── layouts/        AdminLayout, TeacherLayout
└── pages/          LoginPage · HelpPage
                    admin/{AdminOverview, AdminFaculty, AdminCourse, AdminTraffic, AdminReports, AdminChannels, …}
                    teacher/{TeacherRisk, TeacherProgress, TeacherRules, TeacherInterventions}
```

Quy ước hiển thị áp dụng thống nhất:

- Mức rủi ro **luôn có chữ** kèm màu: `Nguy cơ cao`, `Cần lưu ý`, `An toàn`. Người mù màu đỏ–lục không phân biệt được hai màu đỏ và xanh của đề tài (đo được ΔE = 3,5 khi mô phỏng), nên chữ là kênh nhận biết chính. Từ v1.2 bỏ các biểu tượng trang trí (●, ▲, ✔, ⬇, ▸…) theo góp ý giảm nhiễu.
- Mọi biểu đồ chính có liên kết **"Nguồn & cách tính"** mở ngăn bên phải: ý nghĩa, công thức, bảng Moodle nguồn, bảng phân tích, job ETL, độ mới số liệu — nội dung lấy từ API, cùng nguồn với ETL.
- Mọi biểu đồ có **tooltip** và nút **"Biểu đồ | Bảng"** để xem đúng số liệu đó dưới dạng bảng.
- Biểu đồ đường có **đường dóng dọc** theo vị trí chuột, tooltip liệt kê tất cả chuỗi tại thời điểm đó.
- Giá trị `NULL` hiển thị **"Chưa có dữ liệu"**, không hiển thị 0%.
- Số và ngày theo định dạng Việt Nam (1.234.567 · 41,67% · 06/11/2026).
- "Hôm nay" lấy theo `AS_OF` của máy chủ, không theo đồng hồ máy người dùng.

---

## 8. HƯỚNG DẪN SỬ DỤNG WEB

### 8.1 Đăng nhập

![Trang đăng nhập](images/report/mh01_dang_nhap_loi.png)

Tài khoản demo (mật khẩu là `BACKEND_SEED_PASSWORD` đã đặt khi cài):

| Tài khoản | Vai trò | Thấy gì |
|---|---|---|
| `admin` | Quản trị | Tổng quan (Toàn trường › Khoa › Môn), Lưu lượng, Báo cáo, Danh mục, Hệ thống (gồm Kênh gửi tin) |
| `gv.tranminhhung`, `gv.nguyenthilan`, … (28 giảng viên của 5 khoa) | Giảng viên | Cảnh báo, Tiến độ, Thiết lập cảnh báo, Can thiệp của **các môn mình dạy** |

Ảnh trên là trường hợp nhập sai mật khẩu: hệ thống chỉ báo "Sai tên đăng nhập hoặc mật khẩu", không tiết lộ tài khoản có tồn tại hay không.

### 8.2 Trang Tổng quan – cấp Toàn trường (Quản trị)

![Trang tổng quan](images/report/mh02_tong_quan.png)

Trang tổng quan là **bức tranh lớn** (góp ý 3 – vĩ mô trước, vi mô sau). Thanh cấp xem `Toàn trường › Khoa › Môn học › Sinh viên` ở đầu trang cho biết đang ở cấp nào.

1. **Hàng bộ lọc**: Năm học, Học kỳ; chọn Khoa sẽ chuyển sang trang của khoa đó. Nút **Xuất báo cáo** xuất Excel/PDF theo học kỳ đang chọn.
2. **Sáu thẻ KPI**: tổng môn học, lượt ghi danh (kèm số sinh viên khác nhau), sinh viên có tương tác, người đang online, giờ cao điểm hôm nay, số sinh viên nguy cơ cao (kèm thay đổi so với tuần trước).
3. **Biểu đồ tròn + đồ thị xu hướng** mức rủi ro toàn trường (góp ý 2): biểu đồ tròn giữ nguyên, đặt cạnh đường xu hướng Đỏ/Vàng/Xanh theo tuần hoặc theo ngày; vạch dọc đánh dấu ngày một môn đổi luật cảnh báo.
4. **So sánh giữa các Khoa** (góp ý 1): ba biểu đồ cột – quy mô (lượt ghi danh), tỷ lệ tương tác (kèm đường trung bình toàn trường), phân bố mức rủi ro (cột 100%) – và bảng tóm tắt cùng số liệu. Nhấn cột hoặc dòng khoa để xuống cấp Khoa.
5. **Hoạt động hệ thống**: biểu đồ lưu lượng 2 trục và heatmap giờ × thứ.

### 8.3 Cấp Khoa, cấp Môn học và tới từng sinh viên

![Cấp khoa](images/report/mh02_cap_khoa.png)

- **Trang Khoa** (`/admin/faculties/{id}`): KPI của khoa, biểu đồ tròn + xu hướng của khoa, biểu đồ so sánh các môn trong khoa (chọn chỉ số: tỷ lệ tương tác, nộp bài, chuyên cần, % nguy cơ cao; đường tham chiếu là trung bình khoa) và phân bố mức rủi ro theo môn; bảng môn học lọc được theo bộ môn.
- **Trang Môn học** (`/admin/courses/{id}`): ba thẻ Đỏ/Vàng/Xanh, biểu đồ tròn + xu hướng của lớp, bảng cảnh báo và danh sách tất cả sinh viên (lọc có/không tương tác, tìm theo MSSV, họ tên, email). Nhấn một sinh viên để xem chi tiết (quản trị chỉ xem, không gửi tin).
- Nút Back của trình duyệt và F5 giữ đúng cấp và học kỳ (học kỳ nằm trên URL `?ay=…&sem=…`).

![Nguồn & cách tính](images/report/mh02_nguon_va_cach_tinh.png)

**Nguồn & cách tính** (góp ý 4): mỗi biểu đồ có liên kết mở ngăn giải thích – chỉ số nghĩa là gì, công thức, lấy từ bảng Moodle nào (ví dụ `mdl_logstore_standard_log`, `mdl_attendance_log`, `mdl_assign_submission`), qua bảng phân tích và job ETL nào, cập nhật lúc nào; với mức rủi ro có bảng 3 tiêu chí kèm ngưỡng, trọng số và luật xếp mức **đang áp dụng** (của trường hoặc của môn).

### 8.4 Trang Lưu lượng (Quản trị)

![Trang lưu lượng](images/report/mh03_luu_luong.png)

Chọn khoảng ngày (có sẵn các mốc nhanh: hôm nay, 7, 30, 90 ngày). Thẻ **Online hiện tại** tự làm mới mỗi 60 giây. Bảng **Top 10 giờ đông nhất** cho biết chính xác giờ nào tải cao nhất. Heatmap chọn được 1–12 tuần.

### 8.5 Trang Báo cáo (Quản trị)

![Trang báo cáo](images/report/mh04_bao_cao.png)

Chọn một trong ba loại báo cáo (quy mô đào tạo, cảnh báo sinh viên, lưu lượng), đặt bộ lọc, nhấn **Xem trước** để kiểm tra dữ liệu rồi **Xuất Excel** hoặc **Xuất PDF**. File Excel giữ kiểu số và ngày nên mở ra lọc, tính toán được ngay; file PDF khổ ngang, lặp tiêu đề mỗi trang, tô màu mức rủi ro.

### 8.6 Trang Cảnh báo (Giảng viên)

![Trang cảnh báo](images/report/mh09_canh_bao.png)

1. Chọn môn ở thanh tiêu đề.
2. Ba thẻ đèn giao thông: nhấn để lọc bảng theo mức.
3. Biểu đồ tròn: nhấn lát cắt hoặc dòng chú thích để lọc; bên dưới là số sinh viên theo từng tiêu chí (vắng học, không tương tác, thiếu bài tập) cũng nhấn để lọc được.
4. Bảng cảnh báo sắp xếp mặc định ĐỎ → VÀNG → XANH, trong cùng mức thì điểm cao trước. Có ô tìm kiếm, bộ lọc mức và tiêu chí, sắp xếp theo từng cột, và nút xuất danh sách ra Excel/PDF.
5. Đồ thị **Diễn biến mức rủi ro theo tuần** (hoặc theo ngày) cạnh các thẻ cho biết lớp đang tốt lên hay xấu đi; thẻ hiện thay đổi so với tuần trước.
6. Nhấn vào một dòng để mở cửa sổ chi tiết.

### 8.7 Cửa sổ chi tiết sinh viên

![Cửa sổ chi tiết sinh viên](images/report/mh10_chi_tiet_sinh_vien.png)

Cửa sổ này trả lời câu hỏi "vì sao em này bị đánh dấu đỏ":

- Dòng **Lý do** viết bằng câu chữ: "Vắng 9/18 buổi (50%) · Chưa từng truy cập môn học · Thiếu 3/3 bài tập".
- **Biểu đồ so sánh** sinh viên với trung bình lớp.
- **Biểu đồ đường hoạt động theo tuần**, chấm tròn đặc là tuần đi học đủ, chấm rỗng là tuần có buổi vắng.
- **Danh sách bài tập** với trạng thái đúng hạn / trễ hạn / thiếu / chưa tới hạn.
- **Lịch sử cảnh báo** và **các can thiệp trước đây**.
- **Bảng phân tích điểm rủi ro**: từng tiêu chí được mấy điểm, nhân trọng số bao nhiêu, cộng lại ra điểm; luật bổ sung nào của môn đã khớp.
- Bốn nút hành động: **Gửi tin nhắn Moodle** và **Gửi email** mở trình soạn tin có sẵn số liệu của sinh viên và gửi thật qua kênh đã cấu hình; **Ghi chú**, **Hẹn gặp** ghi vào nhật ký can thiệp. Mọi hành động đều lưu kèm mức rủi ro tại thời điểm đó.

### 8.8 Trang Tiến độ lớp (Giảng viên)

![Trang tiến độ lớp](images/report/mh11_tien_do_lop.png)

Ba thanh tiến độ (hoàn thành hoạt động, nộp bài, chuyên cần), tiến độ từng chương/tuần, biểu đồ số sinh viên hoạt động theo tuần hoặc theo ngày, và biểu đồ tỷ lệ tiến độ theo thời gian.

### 8.9 Trên điện thoại

![Giao diện trên điện thoại](images/report/mh09_dien_thoai.png)

Giao diện dùng được ở màn hình 390 px: các thẻ xếp dọc, bảng cuộn ngang trong khung riêng, trang không bị cuộn ngang.

---

### 8.10 Các màn hình bổ sung ở phiên bản 1.1

- **Hệ thống › Quản lý người dùng:** khóa/mở khóa, đặt lại mật khẩu (mật khẩu tạm hiện một lần).
- **Hệ thống › Nhật ký ETL:** trạng thái từng job và các lần chạy, lọc theo job/trạng thái.
- **Hệ thống › Sao lưu & phục hồi:** tạo, tải, xóa bản sao lưu; phục hồi yêu cầu gõ lại tên tệp. Dòng lệnh: `python -m backend.app.cli backup | list-backups | restore --file <tên>`.
- **Danh mục:** môn học, bộ môn, giảng viên phụ trách, sĩ số (chỉ tra cứu).
- **Tài khoản & đổi mật khẩu**, **Trợ giúp** cho cả hai vai trò.

### 8.11 Các màn hình bổ sung ở phiên bản 1.2

![Thiết lập cảnh báo](images/report/mh14_thiet_lap_canh_bao.png)

**Giảng viên › Thiết lập cảnh báo** (chức năng 1): chọn mẫu theo loại môn (Mặc định, Lý thuyết, Thực hành, Đồ án) hoặc tùy chỉnh ngưỡng của 3 tiêu chí, trọng số (mỗi trọng số 10–60%, tổng 100%) và tối đa 5 luật bổ sung (bỏ nộp n bài liên tiếp; vắng n buổi của một hoạt động điểm danh, ví dụ "Điểm danh thực hành"; vắng từ x%; không truy cập n ngày; thiếu n bài). Khối **Tác động nếu áp dụng** chấm lại cả lớp bằng đúng hàm của ETL và liệt kê ai đổi mức **trước khi lưu**. **Lưu và áp dụng** tạo phiên bản mới (lịch sử giữ đủ, có lý do thay đổi), áp dụng ngay cho số liệu hôm nay; **Khôi phục mặc định** quay về luật của trường. Chỉ giảng viên chính (editingteacher) được lưu; trợ giảng xem và xem trước.

![Can thiệp](images/report/mh15_can_thiep_can_lien_he.png)

**Giảng viên › Can thiệp** (chức năng 2), bốn thẻ:

- **Cần liên hệ**: sinh viên Đỏ/Vàng chưa được liên hệ trong 3/7/14 ngày, lý do chính, lần liên hệ gần nhất; chọn nhiều em rồi **Soạn tin** – mỗi em một bản nội dung đã điền số liệu riêng (tên, số buổi vắng, số bài thiếu, số ngày chưa vào…), sửa được trước khi gửi. Dải thông báo luôn nói rõ chế độ gửi hiện hành (offline, chuyển hướng hay thật).
- **Đã gửi**: trạng thái từng tin (chờ duyệt, chờ gửi, đã gửi, lỗi, đã hủy), **mã xác nhận** do máy chủ nhận trả về (mã tin nhắn trong `mdl_messages` hoặc Message-ID email); duyệt tin chờ duyệt, gửi lại tin lỗi.
- **Nhắc tự động**: quy tắc "không truy cập quá n ngày", "vừa chuyển sang Nguy cơ cao", "quá hạn nộp bài"; chọn tự gửi hoặc chờ duyệt, thời gian chờ giữa hai lần nhắc; **Chạy thử** cho biết ai sẽ nhận mà không tạo tin. Job `auto_prompt` chạy sau mỗi lần tính rủi ro, job `message_dispatch` gửi hàng đợi mỗi phút (thử lại sau 1, 5, 15 phút với lỗi tạm thời; tin tự động tạo trong giờ yên lặng 22:00–06:00 được hẹn gửi 07:00).
- **Mẫu tin nhắn**: 4 mẫu hệ thống và mẫu riêng của giảng viên, dùng các biến như `{ten_sv}`, `{so_buoi_vang}`, `{bai_chua_nop}`, `{tinh_hinh}` (18 biến, điền từ snapshot cảnh báo mới nhất).

![Kênh gửi tin](images/report/mh16_kenh_gui_tin.png)

**Quản trị › Hệ thống › Kênh gửi tin**: cấu hình hiện hành (đã che mật khẩu, token), chế độ hiệu lực của từng kênh, **Kiểm tra Moodle** (gọi `core_webservice_get_site_info`, kiểm tra quyền gọi `core_message_send_instant_messages`), **Gửi email thử**, thống kê gửi 30 ngày. Dòng lệnh tương đương: `python -m backend.app.cli messaging-check [--send-test-email địa_chỉ] [--save]`.

**Chốt chặn gửi thật.** Tin chỉ tới người nhận thật khi đủ ba điều kiện: `MESSAGING_ALLOW_LIVE=true`, hệ thống chạy dữ liệu thật (`LMS_AS_OF` trống) và kênh đã kiểm tra thành công với **đúng cấu hình hiện tại** (dấu vân tay cấu hình). Thiếu một điều kiện thì email tự chuyển sang hộp thư kiểm thử, còn Moodle thật bị từ chối – dữ liệu demo (email `@student.dlu.edu.vn` có thể là hộp thư thật) không bao giờ đi ra ngoài.

**Chứng minh gửi được.** Mức 1: kiểm thử tự động gửi qua máy chủ SMTP cục bộ (aiosmtpd) và đọc lại thư nhận được. Mức 2: gửi qua HTTP tới máy chủ Moodle 3.9 mô phỏng (`python -m tools.moodle_ws_stub`, cùng định dạng tham số `messages[0][touserid]…` và cùng phản hồi `msgid` như Moodle thật), tin nằm trong `mdl_messages` và xem được ở `http://127.0.0.1:8091/stub/inbox`. Mức 3 (khi có Moodle/SMTP thật): kiểm tra kênh ở trang trên, gửi một tin tới tài khoản kiểm thử, đối chiếu mã xác nhận với hộp thư của người nhận.

Ảnh chụp đầy đủ các màn hình: `docs/images/report/` (tạo lại bằng `node frontend/e2e/report_shots.mjs`).

## 9. MINH CHỨNG TRỰC QUAN HÓA DỮ LIỆU

Phần này trả lời câu hỏi: **mỗi biểu đồ lấy dữ liệu từ đâu, tính thế nào, và làm sao biết nó đúng.**

### 9.1 Bảng đối chiếu yêu cầu đề tài → màn hình → dữ liệu

| Yêu cầu | Biểu đồ trên web | Dữ liệu lấy từ | Nguồn gốc trong Moodle |
|---|---|---|---|
| **1.1** Thống kê Khoa → Môn → Sinh viên | Thẻ KPI, biểu đồ cột so sánh khoa/môn, trang Khoa → trang Môn → sinh viên | `fact_course_progress_daily` (`total_enrolled_students`, `total_active_students`) và `fact_student_risk_summary` ở cấp sinh viên | Ghi danh còn hiệu lực (`mdl_user_enrolments` + `mdl_enrol` + vai trò student) và nhật ký `mdl_logstore_standard_log` |
| **1.2** Lưu lượng và người truy cập | Đường 2 trục, heatmap giờ × thứ, thẻ online thời gian thực | `fact_server_traffic_hourly`, `etl_online_snapshot` | Số sự kiện trong `mdl_logstore_standard_log` theo giờ; `mdl_sessions` cho người online |
| **1.3** Xuất báo cáo đa chiều | Trang Báo cáo + Excel/PDF | Cả 3 bảng fact | – |
| **2.1** Cảnh báo sinh viên nguy cơ | Đèn giao thông, biểu đồ tròn, bảng cảnh báo, cửa sổ chi tiết | `fact_student_risk_summary` | Điểm danh (`mdl_attendance_*`), nhật ký truy cập, bài nộp (`mdl_assign_submission`) |
| **2.2** Tiến độ và tương tác lớp | Thanh tiến độ, tiến độ theo chương, đường theo tuần, biểu đồ so sánh cá nhân với lớp | `fact_course_progress_daily`, `fact_student_risk_summary` | Hoàn thành hoạt động (`mdl_course_modules_completion`), bài nộp, điểm danh |

### 9.2 Đường đi của một con số: "SV nguy cơ cao: 1.863"

```
mdl_attendance_log ─┐
mdl_logstore_...   ─┼─ extract (SQL, tại AS_OF) ─▶ chỉ số từng SV ─▶ chấm điểm C1,C2,C3 ─▶ risk_level
mdl_assign_sub...  ─┘                                                             │
                                                                                   ▼
                                       fact_student_risk_summary (1 dòng/SV/môn/ngày)
                                                                                   │ đếm theo môn
                                                                                   ▼
                                       fact_course_progress_daily.red_count
                                                                                   │ cộng theo khoa/học kỳ
                                                                                   ▼
                                       API /admin/overview/kpis → thẻ "SV nguy cơ cao"
```

Kiểm chứng số này bằng SQL trực tiếp:

```sql
SELECT COUNT(*) FROM analytics.fact_student_risk_summary
WHERE snapshot_date = DATE '2026-11-06' AND risk_level = 'RED';       -- 1.863

SELECT SUM(red_count) FROM analytics.fact_course_progress_daily
WHERE stat_date = DATE '2026-11-06';                                   -- 1.863
```

Có test tự động so đúng hai con số này với giá trị API trả về.

### 9.3 Từng biểu đồ

#### a) Biểu đồ đường 2 trục – Lưu lượng truy cập

- **Trục trái (nét liền)**: số sự kiện trong `mdl_logstore_standard_log` gom theo giờ địa phương.
- **Trục phải (nét đứt)**: số người online trung bình, tính từ các mẫu 5 phút chụp `mdl_sessions`.
- **Vùng tô nền đỏ nhạt**: các giờ có `is_peak_hour = true`, tức lưu lượng vượt phân vị 90 của 28 ngày gần nhất.
- Tooltip hiện đủ: requests, online trung bình, online cao nhất, số người dùng hoạt động, số lượt đăng nhập và đăng nhập lỗi.
- Đề tài yêu cầu biểu đồ 2 trục. Để tránh đọc nhầm hai thang đo, mỗi đường có kiểu nét riêng, tiêu đề trục ghi rõ đại lượng, legend ghi rõ "trục trái"/"trục phải".

Kiểm chứng: test đối soát cộng số sự kiện trực tiếp trên Moodle theo từng giờ và so với bảng fact, **sai lệch bằng 0**.

#### b) Biểu đồ cột so sánh giữa các khoa / các môn (v1.2, góp ý 1)

Thay cho biểu đồ cột chồng và bảng phân cấp của v1.1. Ở cấp toàn trường: ba biểu đồ cột cạnh bảng tóm tắt – **quy mô** (lượt ghi danh, chia có/không tương tác), **tỷ lệ tương tác** (đường ngang là trung bình toàn trường) và **phân bố mức rủi ro** (cột 100% Đỏ/Vàng/Xanh; quy mô các khoa khác nhau nên so tỷ lệ chứ không so số tuyệt đối). Ở cấp khoa: so sánh các môn theo chỉ số chọn được, nằm ngang khi nhiều môn. Nhấn cột để xuống cấp dưới. "Có tương tác" nghĩa là sinh viên có ít nhất một sự kiện trong môn kể từ ngày bắt đầu môn học.

Kiểm chứng: tổng lượt ghi danh, số tương tác và số Đỏ của các khoa bằng đúng thẻ KPI toàn trường; số sinh viên có tương tác đếm ở cấp sinh viên khớp `total_active_students` ở cấp môn – test kiểm tra cho **mọi môn**.

#### c) Đồ thị xu hướng mức rủi ro (v1.2, góp ý 2)

Ba đường Đỏ/Vàng/Xanh theo tuần học (điểm cuối mỗi tuần) hoặc theo ngày, cho toàn trường, một khoa hoặc một môn, đặt cạnh biểu đồ tròn. Vạch dọc đánh dấu ngày một môn đổi bộ luật cảnh báo, để không nhầm thay đổi do luật với thay đổi do hành vi sinh viên. Dữ liệu là chuỗi snapshot hằng ngày trong `fact_course_progress_daily`.

Kiểm chứng: điểm cuối của đồ thị bằng đúng biểu đồ tròn cùng cấp (test kiểm tra cho toàn trường, khoa và môn).

#### d) Heatmap giờ × thứ

Ma trận 7 × 24 ô, màu xanh nhạt tới đậm theo số requests trung bình. Dùng thang **một màu** (không phải cầu vồng) vì đây là đại lượng có thứ tự. Bảng số liệu kèm theo cho biết chính xác trung bình mỗi ô và tỷ lệ ngày ô đó là giờ cao điểm. Heatmap chỉ tính các ngày trọn vẹn, không tính hôm nay đang dở dang.

#### e) Biểu đồ tròn mức rủi ro (Giảng viên)

Ba lát: đỏ, vàng, xanh, mỗi lát kèm tên mức và số sinh viên, ở giữa là tổng sĩ số. Nhấn lát cắt để lọc bảng. Bên dưới là số sinh viên theo từng tiêu chí; tổng ba tiêu chí thường lớn hơn số sinh viên vì một em có thể vi phạm nhiều tiêu chí.

Kiểm chứng: đỏ + vàng + xanh = số sinh viên đang học của môn (test kiểm tra), và số đỏ khớp `red_count` trong bảng tiến độ.

#### f) Bảng cảnh báo (đèn giao thông)

Mỗi dòng là một sinh viên với: mức rủi ro (chữ + màu), MSSV, họ tên, tỷ lệ vắng kèm số buổi, lần truy cập cuối ("16 ngày trước" / "Chưa truy cập"), số bài đã nộp trên số bài tới hạn, điểm rủi ro, và các lý do dạng thẻ chữ. Đây chính là bảng "đèn giao thông" mà đề tài yêu cầu: giảng viên nhìn một lượt biết ai cần gọi trước.

#### g) Biểu đồ so sánh sinh viên với trung bình lớp

Trong cửa sổ chi tiết, mỗi chỉ số một cặp thanh: sinh viên (xanh) và trung bình lớp (xám). Các chỉ số phần trăm (nộp bài, chuyên cần, hoàn thành) nằm trong một biểu đồ, các chỉ số đếm lượt (truy cập 14 ngày, tổng lượt truy cập) nằm ở biểu đồ riêng — để không trộn hai đơn vị khác nhau trên cùng một trục.

#### h) Biểu đồ đường hoạt động theo tuần

Số lượt xem và số thao tác theo từng tuần học. Điểm trên đường mang thêm thông tin điểm danh: chấm đặc là tuần đi học đủ, chấm rỗng là tuần có buổi vắng, không có chấm là tuần không có buổi điểm danh. Nhờ vậy một hình cho thấy cả xu hướng tương tác lẫn chuyên cần.

#### i) Thanh tiến độ lớp và tiến độ theo chương

Ba thanh tổng quan (hoàn thành hoạt động, nộp bài, chuyên cần) và danh sách từng chương/tuần với thanh riêng. Khi môn chưa có dữ liệu để tính (chưa có buổi điểm danh, chưa có bài tới hạn), hệ thống ghi **"Chưa có dữ liệu"** thay vì vẽ thanh 0% — tránh hiểu nhầm "không ai đi học".

#### j) Biểu đồ tỷ lệ tiến độ theo thời gian

Ba đường cùng đơn vị phần trăm theo tuần hoặc theo ngày. Khoảng trống trên đường nghĩa là thời điểm đó chưa có dữ liệu để tính, chứ không phải bằng 0.

### 9.4 Vì sao tin được các con số

| Cách kiểm chứng | Nội dung | Kết quả |
|---|---|---|
| **Đối soát với Moodle** | Với 5 môn lấy ngẫu nhiên (mỗi khoa một môn), chạy lại SQL viết độc lập trên `moodle_src` (không dùng lại SQL của ETL) rồi so với bảng fact: số sinh viên ghi danh, số có tương tác, số buổi vắng từng sinh viên, số bài thiếu từng sinh viên, số request từng giờ | **Sai lệch bằng 0** |
| **Đối chiếu "đáp án"** | So mức rủi ro hệ thống tính với hồ sơ hành vi đã gieo khi sinh dữ liệu (12.583 cặp sinh viên–môn, 5 khoa) | **Recall 99,3% · Precision 86,7%** cho nhóm ĐỎ |
| **Điểm tái lập được từ luật** | Với MỌI dòng cảnh báo hôm nay, chấm lại bằng bộ luật đã lưu (`rule_set_id`) | Điểm và mức trùng 100% |
| **Chấm lại khi đổi luật = ETL** | Lưu luật riêng cho môn rồi chạy lại ETL từ Moodle cùng ngày | ETL không phải sửa dòng nào (trùng từng dòng) |
| **Tính nhất quán giữa các bảng** | Đỏ + vàng + xanh = số sinh viên ghi danh của môn, cho mọi môn | Đạt |
| **Chạy lại không đổi số** | Chạy lại từng job hai lần liên tiếp, so checksum toàn bảng | Không dòng nào thay đổi |
| **Cập nhật tăng dần đúng** | Chèn thêm 1.000 dòng nhật ký rồi chạy job | Chỉ đúng một giờ bị cập nhật, watermark tăng đúng |
| **Giao diện hiện đúng số của API** | Playwright mở web thật, đọc số trên màn hình và so với truy vấn CSDL | Đạt |

Ma trận nhầm lẫn giữa "đáp án" và kết quả hệ thống tại ngày 06/11/2026:

| Đáp án \ Hệ thống | XANH | VÀNG | ĐỎ |
|---|---|---|---|
| GREEN | 8.001 | 464 | 0 |
| YELLOW | 221 | 2.022 | 247 |
| RED | 0 | 12 | **1.616** |

Nghĩa là trong 1.628 cặp sinh viên–môn thực sự thuộc nhóm nguy cơ, hệ thống bắt được 1.616; 12 cặp còn lại vẫn được cảnh báo ở mức VÀNG chứ không bị bỏ sót hoàn toàn. Luật mặc định hiệu chỉnh trên dữ liệu 1 khoa (Precision 85,3%) vẫn đạt mục tiêu ≥ 80% trên dữ liệu 5 khoa – không cần đổi luật.

---

## 10. KIỂM THỬ VÀ HIỆU NĂNG

Chi tiết và số liệu đầy đủ: [KET_QUA_KIEM_THU.md](KET_QUA_KIEM_THU.md).

Tóm tắt:

| Nhóm | Số lượng | Kết quả |
|---|---|---|
| pytest (CSDL, ETL, mock data, tích hợp, API, gửi tin, bảo mật, sao lưu) | 355 | Tất cả đạt |
| vitest (hàm định dạng, gộp dữ liệu biểu đồ, nhãn trục) | 10 | Tất cả đạt |
| Playwright E2E (luồng Admin/GV, luật theo môn, gửi tin, phân quyền, responsive 4 kích thước × 7 trang, WCAG) | 57 | Tất cả đạt |

Hiệu năng trên dữ liệu 5 khoa (máy Intel i5-12450H, 16 GB RAM, PostgreSQL 18 local, đo 10/10/2026):

| Hạng mục | Mục tiêu | Kết quả |
|---|---|---|
| 94 câu SQL của Dashboard, gồm mọi API v1.2 (770.314 dòng cảnh báo) | ≤ 100 ms, không Seq Scan bảng lớn | chậm nhất **8,9 ms**, không Seq Scan |
| API với 50 người dùng đồng thời (5 phút, gồm API v1.2) | p95 < 500 ms, p99 < 1 s, lỗi < 0,1% | p95 **28 ms**, p99 **50 ms**, **0 lỗi** trong 8.832 request |
| Gửi 200 tin (100 SV × 2 kênh, file .eml + Moodle mô phỏng) | < 30 giây | Đạt (kiểm thử tự động) |
| ETL backfill 61 ngày | – | **31,4 phút** (45,4 triệu dòng trích xuất) |
| Sinh dữ liệu mô phỏng 5 khoa | – | **6,9 phút** |

Số đo dữ liệu 1 khoa / x10 của phiên bản 1.0 (và chi tiết từng phép đo): [KET_QUA_KIEM_THU.md](KET_QUA_KIEM_THU.md).

Trong quá trình đo tải đã phát hiện và sửa hai lỗi hiệu năng thật. Ở v1.2: phép đếm "sinh viên duy nhất" quét toàn bảng cảnh báo (700 ms, tới 2–3 giây khi đồng thời) – viết lại để tra theo chỉ mục và thêm chỉ mục phủ (migration V014), còn 7 ms. Ở v1.0: uvicorn mặc định đóng kết nối nhàn rỗi sau 5 giây, trùng với khoảng nghỉ 2–5 giây của người dùng, khiến vài request lẻ phải chờ TCP hết giờ tới 30–69 giây (trong khi PostgreSQL không có truy vấn nào quá 1 giây). Đặt `--timeout-keep-alive 65` thì request chậm nhất còn 0,55 giây; thiết lập này đã đưa vào `docker-compose.yml`.

---

## 11. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

**Hạn chế cần nêu rõ khi báo cáo:**

1. `mdl_logstore_standard_log` ghi **sự kiện nghiệp vụ**, không phải HTTP request. Con số "requests" là chỉ số gần đúng của tải hệ thống. Muốn số thật phải đọc access log của Nginx/Apache.
2. Dữ liệu hiện tại là **giả lập** cho 5 khoa (58 môn, 3.000 sinh viên) theo đúng lược đồ Moodle 3.9, không phải dữ liệu thật của trường. Khi có dữ liệu thật chỉ cần trỏ `MOODLE_DB_*` sang bản sao CSDL Moodle của trường, để trống `LMS_AS_OF` và chạy backfill – không phải sửa mã (kế hoạch v1.2, chương 8).
3. Gửi tin nhắn Moodle và email đã chạy thật qua Moodle Web Service và SMTP, nhưng mới chứng minh với máy chủ Moodle mô phỏng và máy chủ SMTP cục bộ; gửi tới Moodle/SMTP thật của trường cần token và tài khoản thư do nhà trường cấp.
4. Bộ đếm chặn đăng nhập sai nằm trong bộ nhớ một tiến trình; khi chạy nhiều worker cần chuyển sang Redis hoặc bảng CSDL.
5. Màu đèn giao thông theo đề tài không phân biệt được với người mù màu đỏ–lục; hệ thống bù bằng biểu tượng và chữ ở mọi chỗ.
6. Chưa khảo sát ý kiến giảng viên thật (phần này cần người dùng thật tham gia).

**Hướng phát triển:**

1. Thêm mô hình học máy (hồi quy logistic hoặc random forest) dự báo nguy cơ trên chính các đặc trưng đã có trong bảng fact.
2. Viết Moodle Local Plugin để nhúng dashboard thẳng vào Moodle.
3. Đọc access log của web server để có số lưu lượng thật.
4. Khảo sát giảng viên dùng thử luật theo môn và nhắc tự động để hiệu chỉnh các mẫu luật (Lý thuyết, Thực hành, Đồ án).
