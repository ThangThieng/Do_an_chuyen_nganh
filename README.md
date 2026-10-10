# LMS Analytics — Trực quan hóa dữ liệu hệ thống LMS Moodle

> Đồ án chuyên ngành: *Trực quan hóa dữ liệu hệ thống LMS Moodle phục vụ công tác quản lý và hỗ trợ giảng dạy*
> Khoa Công nghệ Thông tin — Trường Đại học Đà Lạt

Hệ thống đọc dữ liệu thô từ Moodle, chạy tiến trình ETL để tính toán sẵn các chỉ số, rồi hiển thị lên dashboard cho hai nhóm người dùng:

- **Quản trị viên** — nhìn từ toàn trường xuống khoa, môn, sinh viên; so sánh các khoa; theo dõi lưu lượng; xuất báo cáo
  Excel/PDF; biết mỗi con số lấy từ bảng Moodle nào và tính thế nào.
- **Giảng viên** — nhận cảnh báo "đèn giao thông" kèm xu hướng theo tuần, đặt luật cảnh báo riêng cho môn, gửi tin nhắn
  Moodle / email cá nhân hóa và nhắc tự động sinh viên, theo dõi tiến độ lớp.

Phiên bản **1.2** (10/2026) hoàn thành theo [kế hoạch góp ý giao diện](docs/gop_y_giao_dien/TongHop_GopY_GiaoDien_va_KeHoach_v1.2.docx):
so sánh khoa/môn, xu hướng rủi ro, điều hướng 4 cấp, minh bạch nguồn dữ liệu, luật cảnh báo theo môn, trung tâm can thiệp
đa kênh, dữ liệu mô phỏng 5 khoa theo chuẩn Moodle 3.9.

```
Moodle (moodle_src)  ──ETL Python──▶  PostgreSQL lms_analytics  ──FastAPI──▶  React + Chart.js
   30 bảng mdl_*         5 phút /          3 bảng fact + luật,      JWT, RBAC      Admin · Giảng viên
   5 khoa, 58 môn        giờ / đêm         hàng đợi gửi tin         Excel/PDF
   6,4 triệu dòng log         │
        ▲                     └── gửi tin nhắn Moodle (Web Service) / email (SMTP) ──▶ sinh viên
```

---

## Mục lục

| # | Phần | Dành cho ai |
|---|---|---|
| [1](#1-công-nghệ-sử-dụng) | Công nghệ sử dụng | Người đọc muốn biết dự án dùng gì |
| [2](#2-yêu-cầu-hệ-thống) | Yêu cầu hệ thống | Người sắp cài |
| [3](#3-hướng-dẫn-cài-đặt-và-chạy) | **Hướng dẫn cài đặt và chạy** | Lập trình viên |
| [4](#4-hướng-dẫn-sử-dụng-web) | **Hướng dẫn sử dụng web** | Người dùng cuối |
| [5](#5-tài-khoản-đăng-nhập) | Tài khoản đăng nhập | Ai cũng cần |
| [6](#6-những-gì-không-đi-theo-gói) | Những gì KHÔNG đi theo gói | Người vừa clone về |
| [7](#7-cách-web-hoạt-động) | Cách web hoạt động | Người muốn hiểu kiến trúc |
| [8](#8-cách-xem-cơ-sở-dữ-liệu) | Cách xem cơ sở dữ liệu | Người kiểm tra dữ liệu |
| [9](#9-cấu-trúc-dự-án--tác-dụng-từng-file) | Cấu trúc dự án — tác dụng từng file | Người sắp sửa code |
| [10](#10-kiểm-thử) | Kiểm thử | Người muốn kiểm chứng |
| [11](#11-xử-lý-sự-cố) | Xử lý sự cố | Khi gặp lỗi |

---

## 1. Công nghệ sử dụng

### Tầng cơ sở dữ liệu

| Công nghệ | Phiên bản | Vai trò trong dự án |
|---|---|---|
| **PostgreSQL** | 18 | Hai CSDL: `moodle_src` (nguồn, mô phỏng Moodle) và `lms_analytics` (kho phân tích) |
| **psycopg** | 3.2 | Driver PostgreSQL cho Python, dùng `COPY` để nạp hàng loạt |
| **SQLAlchemy Core** | 2.0 | Quản lý connection pool, viết SQL có tham số bind |

Migration tự viết (`database/migrate.py`), không dùng Alembic — file SQL đặt tên `V001__*.sql` và áp dụng tăng dần, ghi lại checksum vào bảng `schema_migrations`.

### Tầng ETL

| Công nghệ | Phiên bản | Vai trò |
|---|---|---|
| **Python** | 3.11+ | Ngôn ngữ chính |
| **pandas** | 2.2 | Gộp, tính toán chỉ số trên bảng dữ liệu |
| **NumPy** | 1.26 | Sinh dữ liệu giả lập, tính vector hóa |
| **APScheduler** | 3.10 | Lập lịch chạy job tự động (5 phút / giờ / đêm / tuần) |

### Tầng API

| Công nghệ | Phiên bản | Vai trò |
|---|---|---|
| **FastAPI** | 0.115 | Framework REST API, tự sinh tài liệu Swagger |
| **Uvicorn** | 0.30+ | ASGI server chạy FastAPI |
| **Pydantic** | v2 (theo FastAPI) | Kiểm tra kiểu dữ liệu request/response |
| **PyJWT** | 2.9 | Ký và xác thực token JWT (HS256) |
| **bcrypt** | 4.2 | Băm mật khẩu một chiều |
| **cachetools** | 5.5 | Cache TTL 60 giây cho endpoint KPI |
| **httpx** | 0.27 | Gọi Moodle Web Service (`core_message_send_instant_messages`) |
| **python-multipart** | 0.0.x | Đọc form của Moodle REST ở máy chủ Moodle mô phỏng |
| **openpyxl** | 3.1 | Xuất báo cáo Excel (chế độ write-only) |
| **ReportLab** | 4.2 | Xuất báo cáo PDF khổ A4 ngang |

### Tầng giao diện

| Công nghệ | Phiên bản | Vai trò |
|---|---|---|
| **React** | 18.3 | Thư viện giao diện |
| **Vite** | 5.4 | Công cụ build và dev server (hot-reload) |
| **Ant Design** | 5.21 | Bộ thành phần giao diện (bảng, modal, bộ lọc) — tiếng Việt |
| **Chart.js** | 4.4 | Vẽ biểu đồ |
| **react-chartjs-2** | 5.2 | Cầu nối Chart.js với React |
| **chartjs-chart-matrix** | 2.0 | Vẽ heatmap giờ × thứ |
| **chartjs-plugin-annotation** | 3.1 | Tô vùng giờ cao điểm trên biểu đồ |
| **TanStack React Query** | 5.59 | Quản lý dữ liệu từ API, cache, tự làm mới 60 giây |
| **React Router** | 6.27 | Định tuyến theo vai trò |
| **axios** | 1.7 | Gọi HTTP, gắn JWT, tải file Excel/PDF |
| **dayjs** | 1.11 | Xử lý ngày giờ |

### Kiểm thử và đo đạc

| Công nghệ | Vai trò |
|---|---|
| **pytest** | Kiểm thử Python: đơn vị, tích hợp, API |
| **httpx** | HTTP client cho TestClient của FastAPI |
| **Vitest** | Kiểm thử đơn vị JavaScript |
| **Playwright** | Kiểm thử đầu-cuối trên trình duyệt thật |
| **axe-core** | Kiểm tra khả năng tiếp cận WCAG 2.1 A/AA |
| **Locust** | Kiểm thử tải API (50 người dùng đồng thời) |
| **aiosmtpd** | Máy chủ thư cục bộ trong kiểm thử – chứng minh gửi email bằng đúng mã SMTP khi vận hành |

### Đóng gói

| Công nghệ | Vai trò |
|---|---|
| **Docker + Docker Compose** | Demo trọn gói 6 dịch vụ bằng một lệnh (gồm máy chủ Moodle mô phỏng) |
| **Nginx** | Phục vụ bản build React, proxy `/api` sang backend |

---

## 2. Yêu cầu hệ thống

### Cách 1 — Chạy trực tiếp (khuyến nghị khi phát triển)

| Phần mềm | Phiên bản tối thiểu | Ghi chú khi cài |
|---|---|---|
| PostgreSQL | 18 | Nhớ kỹ mật khẩu user `postgres` đặt lúc cài |
| Python | 3.11 | Tick **"Add Python to PATH"** |
| Node.js | 18 (bản LTS) | Đã kèm npm |
| Git | bất kỳ | Để clone dự án |

Dung lượng đĩa cần: khoảng **5 GB** (mã nguồn + thư viện ~170 MB, hai CSDL 3,9 GB với dữ liệu mô phỏng 5 khoa).

### Cách 2 — Chạy bằng Docker

Chỉ cần **Docker Desktop**. Không cần cài PostgreSQL, Python hay Node.js.

---

## 3. Hướng dẫn cài đặt và chạy

> Phần này dành cho người sẽ chạy hoặc sửa mã nguồn.
> Nếu chỉ muốn biết cách **dùng** dashboard, xem [Phần 4](#4-hướng-dẫn-sử-dụng-web).

### 3.1 Tải mã nguồn

```powershell
git clone https://github.com/ThangThieng/Do_an_chuyen_nganh.git
cd Do_an_chuyen_nganh
```

### 3.2 Tạo file cấu hình `.env`

File `.env` chứa mật khẩu nên **không** được đưa lên Git. Bạn tự tạo từ file mẫu:

```powershell
Copy-Item .env.example .env
notepad .env
```

Điền 4 giá trị:

```ini
ANALYTICS_DB_PASSWORD=<mật khẩu postgres trên MÁY BẠN>
MOODLE_DB_PASSWORD=<mật khẩu postgres trên MÁY BẠN>
BACKEND_JWT_SECRET=<sinh bằng lệnh bên dưới>
LMS_AS_OF=2026-11-06T10:30:00+07:00
```

Sinh khóa JWT ngẫu nhiên:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> ⚠️ **`LMS_AS_OF` phải đúng y hệt dòng trên.** Đây là "thời điểm tham chiếu" đóng băng đồng hồ của toàn hệ thống. Dữ liệu giả lập mô phỏng học kỳ 1 năm học 2026–2027 (bắt đầu 07/09/2026), và mốc `2026-11-06` là tuần 9. Đặt sai giá trị này, dữ liệu sinh ra sẽ khác và không đối chiếu được với tài liệu.

### 3.3 Cài đặt và dựng dữ liệu

Chạy lần lượt, đợi từng lệnh xong hẳn. Tổng thời gian khoảng **45 phút** (đo trên Intel i5-12450H, 16 GB RAM).

```powershell
# 1. Cài thư viện Python + npm, tạo bảng trong 2 CSDL               (~3 phút)
.\scripts\lms.ps1 setup

# 2. Sinh cấu trúc Moodle: 5 khoa, 58 môn, 3.000 SV, 28 giảng viên    (~1 phút)
.\scripts\lms.ps1 seed

# 3. Sinh hành vi học tập: 6,4 triệu dòng log truy cập              (~7 phút)
.\scripts\lms.ps1 mock

# 4. Chạy ETL nạp lịch sử 3 bảng fact (07/09 → 06/11/2026)          (~32 phút)
.\scripts\lms.ps1 etl-backfill

# 5. Tạo 29 tài khoản đăng nhập (1 quản trị + 28 giảng viên)
$env:BACKEND_SEED_PASSWORD = "Lms@2026demo"
.\scripts\lms.ps1 users
```

Trên Linux/macOS dùng `make setup`, `make seed`, … (xem [Makefile](Makefile)).

### 3.4 Chạy hệ thống

Mở **hai cửa sổ PowerShell**, cùng ở thư mục dự án:

```powershell
# ───── Cửa sổ 1: Backend API ─────
.\scripts\lms.ps1 api
```
→ API chạy ở `http://localhost:8000`, tài liệu Swagger ở `http://localhost:8000/api/docs`

```powershell
# ───── Cửa sổ 2: Frontend ─────
.\scripts\lms.ps1 web
```
→ Mở trình duyệt vào **`http://localhost:5173`**

Frontend tự chuyển tiếp mọi request `/api` sang `http://127.0.0.1:8000` nhờ cấu hình proxy trong [frontend/vite.config.js](frontend/vite.config.js) — không cần sửa CORS.

```powershell
# ───── Cửa sổ 3 (để gửi tin nhắn Moodle): máy chủ Moodle 3.9 mô phỏng ─────
.\scripts\lms.ps1 moodle-stub
```
→ `http://localhost:8091` — hộp tin của một sinh viên: `http://localhost:8091/stub/inbox?userid=<mdl_user.id>`.
Email ở chế độ mặc định được ghi thành file `.eml` trong `var/mail_outbox/` (mở bằng Outlook/Thunderbird).
Muốn job nhắc tự động và gửi hàng đợi chạy theo lịch: `.\scripts\lms.ps1 etl` (cửa sổ 4).

### 3.5 Bảng tra cứu toàn bộ lệnh

| Lệnh tắt | Lệnh đầy đủ tương đương | Tác dụng |
|---|---|---|
| `lms.ps1 setup` | `pip install -r requirements.txt` + `npm install` + `python -m database.migrate up` | Cài thư viện, tạo bảng |
| `lms.ps1 seed` | `python -m mockdata.seed_structure --reset` | Sinh cấu trúc Moodle |
| `lms.ps1 mock` | `python -m mockdata.generate_activity --reset` | Sinh hành vi học tập |
| `lms.ps1 etl-backfill` | `python -m etl.jobs.backfill --from 2026-09-07` | Nạp lịch sử 3 bảng fact |
| `lms.ps1 users` | `python -m backend.app.cli sync-users` | Tạo/cập nhật tài khoản |
| `lms.ps1 api` | `python -m uvicorn backend.app.main:app --port 8000` | Chạy Backend |
| `lms.ps1 web` | `cd frontend; npm run dev` | Chạy Frontend |
| `lms.ps1 moodle-stub` | `python -m tools.moodle_ws_stub` | Máy chủ Moodle 3.9 mô phỏng :8091 (kênh tin nhắn) |
| `lms.ps1 etl` | `python -m etl.scheduler` | ETL theo lịch: tính rủi ro, nhắc tự động, gửi hàng đợi mỗi phút |
| `lms.ps1 messaging-check` | `python -m backend.app.cli messaging-check [--send-test-email <địa chỉ>]` | In cấu hình kênh gửi tin (che bí mật), thử kết nối SMTP/Moodle |
| `lms.ps1 test` | `python -m pytest -q` + `npm test` | Kiểm thử |
| `lms.ps1 e2e` | `npx playwright test` | Kiểm thử giao diện thật |
| `lms.ps1 bench` | `python -m perf.build_x10` + `explain_queries` | Đo hiệu năng |
| `lms.ps1 docker` | `docker compose up --build -d` | Demo bằng Docker |

### 3.6 Chạy bằng Docker (không cần cài PostgreSQL/Python/Node)

```powershell
Copy-Item docker/.env.example docker/.env
notepad docker/.env
```

Điền hai giá trị:
```ini
BACKEND_JWT_SECRET=<chuỗi ngẫu nhiên >= 32 ký tự>
BACKEND_SEED_PASSWORD=Lms@2026demo
```

Rồi chạy:
```powershell
docker compose --env-file docker/.env up --build -d
docker compose --env-file docker/.env logs -f init    # chờ dòng "[init] Hoàn tất." (~40–50 phút với dữ liệu 5 khoa)
```

Mở **`http://localhost:8080`**.

Compose gồm 6 dịch vụ:

| Dịch vụ | Vai trò |
|---|---|
| `db` | PostgreSQL 18, cổng **không** mở ra máy |
| `init` | Chạy một lần: migrate → seed → mock → ETL backfill → tạo tài khoản |
| `etl` | APScheduler chạy nền |
| `backend` | FastAPI, 2 worker |
| `moodle-stub` | Máy chủ Moodle 3.9 mô phỏng cho kênh tin nhắn, mở cổng **8091** để xem hộp tin sinh viên. Bỏ khi trỏ `MOODLE_WS_URL` tới Moodle thật |
| `web` | Nginx phục vụ bản build React và proxy `/api` |

Dữ liệu nằm trong volume `pgdata`. Lệnh `docker compose down -v` xóa sạch để làm lại từ đầu.

> ⚠️ **Hai cách chạy dùng hai CSDL hoàn toàn tách biệt.** Đổi mật khẩu ở bản local không ảnh hưởng bản Docker và ngược lại. Bản local chạy ở cổng **5173**, bản Docker ở cổng **8080**.

---

## 4. Hướng dẫn sử dụng web

> Phần này dành cho người dùng cuối — quản trị viên và giảng viên.
> Không cần biết lập trình.

### 4.1 Đăng nhập

![Trang đăng nhập](docs/images/report/mh01_dang_nhap_loi.png)

Nhập tên đăng nhập và mật khẩu (xem [Phần 5](#5-tài-khoản-đăng-nhập)). Hệ thống tự đưa bạn tới trang phù hợp với vai trò:

- Tài khoản **quản trị** → trang Tổng quan
- Tài khoản **giảng viên** → trang Cảnh báo của môn đầu tiên

Khi nhập sai, hệ thống chỉ báo *"Sai tên đăng nhập hoặc mật khẩu"* mà không nói rõ sai ở đâu — đây là chủ ý, để không tiết lộ tài khoản nào có tồn tại. Nhập sai nhiều lần liên tiếp sẽ bị tạm khóa vài phút.

---

### PHẦN DÀNH CHO QUẢN TRỊ VIÊN

### 4.2 Trang Tổng quan – cấp Toàn trường

![Trang tổng quan](docs/images/report/mh02_tong_quan.png)

Mọi trang quản trị đi theo **4 cấp**, từ bức tranh lớn tới từng sinh viên. Thanh cấp xem ở đầu trang cho biết đang ở đâu:

```
Toàn trường  ›  Khoa  ›  Môn học  ›  Sinh viên
/admin          /admin/faculties/:id   /admin/courses/:id   ?student=:id (cửa sổ chi tiết)
```

Nút Back của trình duyệt và F5 luôn giữ đúng cấp và học kỳ (học kỳ nằm trên URL `?ay=…&sem=…`).

Trang Tổng quan, từ trên xuống:

**① Bộ lọc** — Năm học · Học kỳ; chọn một Khoa sẽ mở trang của khoa đó. Nút **Xuất báo cáo** xuất Excel/PDF theo học kỳ.

**② Sáu thẻ KPI**

| Thẻ | Ý nghĩa |
|---|---|
| Tổng môn học | Số môn đang diễn ra trong học kỳ, kèm số khoa |
| SV đăng ký | Lượt ghi danh còn hiệu lực (một SV học 4 môn tính 4 lượt), kèm **số sinh viên khác nhau** |
| SV tương tác | Lượt ghi danh có ít nhất một hoạt động trong môn, kèm tỷ lệ % |
| Online hiện tại | Người dùng hoạt động trong 5 phút gần nhất, tự làm mới mỗi 60 giây |
| Peak hôm nay | Giờ có nhiều truy cập nhất hôm nay |
| SV nguy cơ cao | Số lượt ghi danh mức ĐỎ, kèm tỷ lệ và **thay đổi so với tuần trước** |

Rê chuột lên tên thẻ để xem giải thích; liên kết **Cách tính** mở ngăn nguồn dữ liệu.

**③ Phân bố mức rủi ro + Xu hướng theo thời gian** — biểu đồ tròn Đỏ/Vàng/Xanh đặt cạnh đồ thị 3 đường % theo tuần học
(hoặc theo ngày). **Nhấn một lát cắt** để tô nổi các khoa có tỷ lệ mức đó cao hơn trung bình toàn trường. Vạch dọc trên đồ
thị đánh dấu ngày một môn đổi luật cảnh báo.

**④ So sánh giữa các Khoa** — ba biểu đồ cột: quy mô (lượt ghi danh có / không tương tác), tỷ lệ tương tác (đường nét đứt
là trung bình toàn trường), phân bố mức rủi ro (cột 100%), và bảng tóm tắt cùng số liệu (thứ tự khoa giống nhau ở cả 4).
**Nhấn cột hoặc dòng** để mở trang Khoa. Hơn 8 khoa thì tự chuyển sang thanh ngang và hiện 10 khoa lớn nhất kèm "Xem tất cả".

**⑤ Hoạt động hệ thống** — lưu lượng 2 trục (24 giờ / 7 ngày) và heatmap giờ × thứ của 4 tuần.

> Mọi biểu đồ có nút **"Biểu đồ | Bảng"** để xem cùng số liệu dạng bảng, và liên kết **"Nguồn & cách tính"**.

### 4.3 Trang Khoa, trang Môn học và tới từng sinh viên

![Trang khoa](docs/images/report/mh02_cap_khoa.png)

**Trang Khoa** — KPI của khoa luôn kèm số toàn trường để so sánh; biểu đồ tròn + xu hướng của khoa; **So sánh các môn
trong khoa** (chọn chỉ số Tỷ lệ tương tác / Nộp bài / Chuyên cần, xếp từ thấp lên cao, đường nét đứt là trung bình khoa;
môn chưa có dữ liệu ghi "chưa có dữ liệu" thay vì vẽ 0%) và phân bố mức rủi ro theo môn; ô tìm môn, lọc theo bộ môn.
Bảng môn học có cột **% Nguy cơ cao**, **Luật cảnh báo** (Mặc định / Riêng) và nút **Xem SV**.

![Trang môn học](docs/images/report/mh02_cap_mon_hoc.png)

**Trang Môn học** — ba thẻ Đỏ/Vàng/Xanh kèm thay đổi so với tuần trước, biểu đồ tròn + xu hướng của lớp, hai thẻ:
*Bảng cảnh báo* (điểm từng tiêu chí, lý do) và *Tất cả sinh viên* (lọc Có / Không tương tác, tìm MSSV, họ tên, email).
Nhấn một sinh viên để mở cửa sổ chi tiết. Quản trị viên **chỉ xem**: không gửi tin, không đổi luật của môn.

![Nguồn & cách tính](docs/images/report/mh02_nguon_va_cach_tinh.png)

**Nguồn & cách tính** — ngăn bên phải trả lời "số này ở đâu ra": ý nghĩa và công thức chỉ số, **bảng Moodle nguồn**
(vd `mdl_logstore_standard_log`, `mdl_attendance_log`, `mdl_assign_submission`), bảng phân tích và job ETL, luật 3 tiêu
chí **đang áp dụng** cho đúng phạm vi (môn có luật riêng thì hiện luật riêng và điểm khác mặc định), đường đi của dữ liệu và
thời điểm cập nhật. Nội dung đọc từ API – cùng nguồn với ETL, không viết cứng trên giao diện.

### 4.4 Trang Lưu lượng

![Trang lưu lượng](docs/images/report/mh03_luu_luong.png)

| Thành phần | Cách dùng |
|---|---|
| Chọn khoảng ngày | Có sẵn mốc nhanh: hôm nay, 7 ngày, 30 ngày, 90 ngày |
| Thẻ **Online hiện tại** | Số người hoạt động trong 5 phút gần nhất, giờ lấy mẫu; tự làm mới mỗi 60 giây |
| Biểu đồ 2 trục | Requests/giờ và người online |
| **Top 10 giờ đông nhất** | Cho biết chính xác giờ nào tải cao nhất |
| Heatmap | Chọn được 1–12 tuần |

### 4.5 Trang Báo cáo

![Trang báo cáo](docs/images/report/mh04_bao_cao.png)

Quy trình 4 bước:

1. **Chọn loại báo cáo** — quy mô đào tạo / cảnh báo sinh viên / lưu lượng truy cập
2. **Đặt bộ lọc** — năm học, học kỳ, khoa, môn, mức rủi ro…
3. **Nhấn "Xem trước"** — bảng dữ liệu hiện ra có phân trang, kiểm tra trước khi xuất
4. **Nhấn "Xuất Excel" hoặc "Xuất PDF"**

| Định dạng | Đặc điểm |
|---|---|
| **Excel** | Giữ nguyên kiểu số và kiểu ngày, mở ra lọc và tính toán được ngay |
| **PDF** | Khổ A4 ngang, lặp tiêu đề mỗi trang, tô màu theo mức rủi ro |

---

### PHẦN DÀNH CHO GIẢNG VIÊN

### 4.6 Trang Cảnh báo

![Trang cảnh báo](docs/images/report/mh09_canh_bao.png)

**Bước 1 — Chọn môn** ở thanh tiêu đề. Danh sách chỉ hiện các môn bạn dạy.

**Bước 2 — Ba thẻ đèn giao thông.** Nhấn vào một thẻ để lọc bảng bên dưới theo mức đó.

| Mức | Hiển thị | Ý nghĩa |
|---|---|---|
| Đỏ | `Nguy cơ cao` | Cần liên hệ ngay |
| Vàng | `Cần lưu ý` | Theo dõi thêm |
| Xanh | `An toàn` | Bình thường |

Dưới mỗi thẻ là thay đổi so với tuần trước; bên cạnh là đồ thị **Diễn biến mức rủi ro theo tuần** (tuần 1 tính từ ngày bắt
đầu môn) cho biết lớp đang tốt lên hay xấu đi.

> Mức rủi ro **luôn có chữ đi kèm màu**, không bao giờ chỉ dùng màu – người mù màu đỏ–lục không phân biệt được hai màu
> này (ΔE chỉ 3,5). Từ v1.2 bỏ các biểu tượng trang trí (●, ▲, ✔, ⬇…) theo góp ý giảm nhiễu.

**Bước 3 — Biểu đồ tròn.** Nhấn một lát cắt hoặc một dòng chú thích để lọc. Bên dưới là số sinh viên theo từng tiêu chí (vắng học / không tương tác / thiếu bài tập) kèm ngưỡng của luật đang áp dụng — cũng nhấn để lọc được. Dòng cuối khối ghi luật đang dùng: mặc định của trường hay riêng của môn.

**Bước 4 — Bảng cảnh báo.** Mặc định sắp xếp ĐỎ → VÀNG → XANH, trong cùng mức thì điểm cao lên trước. Bảng có:
- Ô tìm kiếm theo MSSV / họ tên
- Bộ lọc theo mức và theo tiêu chí
- Sắp xếp theo từng cột
- Cột điểm từng tiêu chí (C1, C2, C3) và chú giải công thức điểm
- Nút **Xuất danh sách** ra Excel / PDF

**Bước 5 — Nhấn vào một dòng** để mở cửa sổ chi tiết (đường dẫn có `?student=…`, F5 mở lại đúng sinh viên).

### 4.7 Cửa sổ chi tiết sinh viên

![Cửa sổ chi tiết sinh viên](docs/images/report/mh10_chi_tiet_sinh_vien.png)

Cửa sổ này trả lời câu hỏi **"vì sao em này bị đánh dấu đỏ?"**

| Thành phần | Nội dung |
|---|---|
| **Dòng Lý do** | Viết bằng câu chữ rõ ràng: *"Vắng 9/18 buổi (50%) · Chưa từng truy cập môn học · Thiếu 3/3 bài tập"* |
| **Phân tích điểm rủi ro** | Từng tiêu chí: số liệu thực tế → so với ngưỡng → 0/1/2 điểm → nhân trọng số → đóng góp; tổng; luật nào xếp em vào mức này |
| **Biểu đồ so sánh** | Đối chiếu sinh viên này với trung bình lớp |
| **Biểu đồ hoạt động theo tuần** | Chấm tròn **đặc** = tuần đi học đủ, chấm **rỗng** = tuần có buổi vắng |
| **Danh sách bài tập** | Trạng thái đúng hạn / trễ hạn / thiếu / chưa tới hạn |
| **Lịch sử cảnh báo** | Mức rủi ro thay đổi qua các tuần |
| **Can thiệp trước đây** | Những lần giảng viên đã liên hệ |

**Bốn nút hành động** ở cuối cửa sổ: **Gửi tin nhắn Moodle** · **Gửi email** (mở trình soạn tin có sẵn số liệu của em,
gửi thật qua kênh đã cấu hình, xem mục 4.12) · **Ghi chú** · **Hẹn gặp**.

Mỗi hành động được ghi vào nhật ký can thiệp kèm mức rủi ro tại thời điểm đó, để sau này biết đã làm gì và kết quả ra sao.

### 4.8 Trang Tiến độ lớp

![Trang tiến độ lớp](docs/images/report/mh11_tien_do_lop.png)

| Thành phần | Cho biết điều gì |
|---|---|
| Ba thanh tiến độ | Hoàn thành hoạt động · Nộp bài · Chuyên cần |
| Tiến độ từng chương/tuần | Lớp đang học tới đâu, chương nào bị bỏ lại |
| Biểu đồ sinh viên hoạt động | Theo tuần hoặc theo ngày |
| Biểu đồ tỷ lệ tiến độ | Xu hướng theo thời gian |

### 4.9 Dùng trên điện thoại

![Giao diện trên điện thoại](docs/images/report/mh09_dien_thoai.png)

Giao diện dùng được từ màn hình rộng 390 px trở lên: các thẻ xếp dọc, bảng cuộn ngang trong khung riêng, trang không bao giờ bị cuộn ngang.

### 4.10 Quy ước hiển thị cần biết

| Quy ước | Giải thích |
|---|---|
| **"Chưa có dữ liệu"** | Khác hẳn "0%". Ví dụ môn chưa có buổi điểm danh nào thì tỷ lệ chuyên cần là "chưa có dữ liệu", không phải "vắng 0%" |
| **"Cập nhật lúc…"** trên header | Thời điểm ETL chạy lần cuối, không phải giờ hiện tại của máy bạn |
| **Nút "Biểu đồ \| Bảng"** | Mọi biểu đồ đều xem được ở dạng bảng số liệu |
| **Màu luôn kèm chữ** | "Nguy cơ cao / Cần lưu ý / An toàn" — bảo đảm người mù màu vẫn đọc được |
| **"Nguồn & cách tính"** | Liên kết trên mọi biểu đồ: bảng Moodle nguồn, công thức, luật đang áp dụng, độ mới số liệu |
| **"Luật riêng"** | Môn có luật cảnh báo do giảng viên đặt; số Đỏ/Vàng/Xanh của môn đó chấm theo luật riêng |

### 4.11 Thiết lập cảnh báo (giảng viên)

![Thiết lập cảnh báo](docs/images/report/mh14_thiet_lap_canh_bao.png)

Menu **Thiết lập cảnh báo** – đặt luật cảnh báo riêng cho môn đang chọn:

1. Chọn **mẫu** theo loại môn: Mặc định của trường · Lý thuyết · Thực hành · Đồ án, hoặc chỉnh tay (thành "Tùy chỉnh").
2. Chỉnh **ngưỡng** 3 tiêu chí và **trọng số** (mỗi trọng số 10–60%, tổng 100%); thêm tối đa 5 **luật bổ sung**, ví dụ
   *"Bỏ nộp 2 bài liên tiếp → Nguy cơ cao"*, *"Vắng 2 buổi của hoạt động Điểm danh thực hành → Nguy cơ cao"*,
   *"Vắng từ 25% → Nguy cơ cao"*. Luật bổ sung chỉ **nâng** mức, không hạ.
3. Khối **Tác động nếu áp dụng** cho biết ngay bao nhiêu sinh viên đổi mức và đổi vì luật nào – **trước khi lưu**.
4. **Lưu và áp dụng** (ghi lý do) tạo phiên bản mới và áp dụng ngay cho số liệu hôm nay; các ngày trước giữ luật cũ.
   **Khôi phục mặc định** quay về luật của trường. Lịch sử phiên bản luôn giữ đủ.

Giá trị ngoài giới hạn an toàn bị báo lỗi ngay và không lưu được. Chỉ **giảng viên chính** (vai trò editingteacher trong
Moodle) được lưu; trợ giảng xem và xem trước. Luật xếp mức chung của trường không đổi để mức rủi ro so sánh được giữa các môn.

### 4.12 Can thiệp – gửi tin và nhắc tự động (giảng viên)

![Can thiệp](docs/images/report/mh15_can_thiep_can_lien_he.png)

Menu **Can thiệp** có 4 thẻ:

| Thẻ | Dùng để |
|---|---|
| **Cần liên hệ** | Sinh viên Đỏ/Vàng chưa được liên hệ trong 3/7/14 ngày, lý do chính, lần liên hệ gần nhất. Chọn nhiều em → **Soạn tin** |
| **Đã gửi** | Trạng thái từng tin (chờ duyệt, chờ gửi, đã gửi, lỗi, đã hủy) và **mã xác nhận**: mã tin trong `mdl_messages` hoặc Message-ID email. Duyệt / hủy / gửi lại; liên kết **Xem như sinh viên** mở hộp tin của em |
| **Nhắc tự động** | Quy tắc: không truy cập quá n ngày · vừa chuyển sang Nguy cơ cao · quá hạn nộp bài. Tự gửi hoặc chờ duyệt, thời gian chờ giữa hai lần nhắc; **Chạy thử** xem ai sẽ nhận mà không gửi |
| **Mẫu tin nhắn** | 4 mẫu hệ thống và mẫu riêng; biến như `{ten_sv}`, `{so_buoi_vang}`, `{bai_chua_nop}`, `{tinh_hinh}` được điền từ số liệu cảnh báo mới nhất |

Trình soạn tin hiện **từng bản xem trước cho từng sinh viên** (sửa được) và một dải thông báo nói rõ chế độ gửi hiện hành.
Không gửi tự động trong 22:00–06:00 (tin tạo trong khung này được hẹn gửi 07:00).

> 🔒 **Chốt chặn gửi thật.** Tin chỉ tới sinh viên thật khi đủ 3 điều kiện: `MESSAGING_ALLOW_LIVE=true`, hệ thống chạy dữ
> liệu thật (`LMS_AS_OF` để trống) và kênh đã được kiểm tra thành công ở trang Kênh gửi tin. Với dữ liệu demo, email luôn
> ghi file `.eml` (hoặc chuyển hướng về hộp thư kiểm thử) và tin nhắn Moodle đi tới máy chủ mô phỏng.

### 4.13 Kênh gửi tin (quản trị viên)

![Kênh gửi tin](docs/images/report/mh16_kenh_gui_tin.png)

**Hệ thống › Kênh gửi tin**: cấu hình hiện hành (mật khẩu, token luôn che), chế độ hiệu lực của từng kênh, nút
**Kiểm tra Moodle** (gọi `core_webservice_get_site_info`) và **Gửi email thử**, thống kê gửi 30 ngày. Cách cấu hình với
Moodle và máy chủ thư của trường: [docs/TAI_LIEU_HE_THONG.md](docs/TAI_LIEU_HE_THONG.md) mục 8.11 và kế hoạch v1.2 mục 5.10.

---

## 5. Tài khoản đăng nhập

Mật khẩu mặc định của **tất cả** tài khoản: `Lms@2026demo`
(chính là giá trị `BACKEND_SEED_PASSWORD` bạn đặt ở bước 3.3)

### Quản trị viên

| Tên hiển thị | Username | Vai trò | Xem được gì |
|---|---|---|---|
| Quản trị Hệ thống | `admin` | ADMIN | Tổng quan (Toàn trường › Khoa › Môn) · Lưu lượng · Báo cáo · Danh mục · Hệ thống (gồm Kênh gửi tin) |

### Giảng viên

28 giảng viên của 5 khoa. "(trợ giảng)" = vai trò `teacher` trong Moodle: xem và xem trước luật cảnh báo nhưng không
lưu được; các môn còn lại là giảng viên chính (`editingteacher`). Số SV = tổng lượt ghi danh các môn phụ trách.

| Khoa | Tên hiển thị | Username | Môn phụ trách | Số SV |
|---|---|---|---|---:|
| Công nghệ Thông tin | Trần Minh Hùng | `gv.tranminhhung` | IT001 · IT002 | 385 |
| Công nghệ Thông tin | Nguyễn Thị Lan | `gv.nguyenthilan` | IT003 · IT010 | 299 |
| Công nghệ Thông tin | Lê Quốc Bảo | `gv.lequocbao` | IT004 · IT005 | 266 |
| Công nghệ Thông tin | Phạm Thu Hà | `gv.phamthuha` | IT006 · IT011 | 379 |
| Công nghệ Thông tin | Võ Thanh Tâm | `gv.vothanhtam` | IT007 · IT008 | 277 |
| Công nghệ Thông tin | Đặng Ngọc Ánh | `gv.dangngocanh` | IT009 · IT012 | 361 |
| Công nghệ Thông tin | Bùi Đức Thắng | `gv.buiducthang` | IT004 (trợ giảng) · IT013 · IT014 | 377 |
| Công nghệ Thông tin | Hồ Hải Yến | `gv.hohaiyen` | IT001 (trợ giảng) · IT009 (trợ giảng) · IT015 | 571 |
| Kinh tế – Quản trị kinh doanh | Nguyễn Văn Khánh | `gv.nguyenvankhanh` | KT106 · KT107 · KT112 | 880 |
| Kinh tế – Quản trị kinh doanh | Trần Thị Mỹ | `gv.tranthimy` | KT108 · KT109 · KT110 | 842 |
| Kinh tế – Quản trị kinh doanh | Lê Hoàng Nam | `gv.lehoangnam` | KT101 · KT111 | 512 |
| Kinh tế – Quản trị kinh doanh | Phạm Ngọc Quỳnh | `gv.phamngocquynh` | KT103 · KT104 | 632 |
| Kinh tế – Quản trị kinh doanh | Đoàn Minh Trí | `gv.doanminhtri` | KT102 · KT105 · KT110 (trợ giảng) | 748 |
| Ngoại ngữ | Nguyễn Thùy Trang | `gv.nguyenthuytrang` | NN101_N01 · NN202 · NN207 | 657 |
| Ngoại ngữ | Lê Thanh Thảo | `gv.lethanhthao` | NN101_N02 · NN203 · NN208 | 701 |
| Ngoại ngữ | Hoàng Diệu Linh | `gv.hoangdieulinh` | NN101_N03 · NN204 | 468 |
| Ngoại ngữ | Trần Quốc Việt | `gv.tranquocviet` | NN101_N04 · NN205 | 496 |
| Ngoại ngữ | Võ Thu Hương | `gv.vothuhuong` | NN201 · NN203 (trợ giảng) · NN206 | 767 |
| Luật | Phạm Văn Thắng | `gv.phamvanthang` | LU103 · LU106 | 435 |
| Luật | Nguyễn Thị Hoa | `gv.nguyenthihoa` | LU107 · LU109 | 364 |
| Luật | Đặng Quang Huy | `gv.dangquanghuy` | LU105 · LU108 | 557 |
| Luật | Bùi Ngọc Mai | `gv.buingocmai` | LU101 · LU102 | 415 |
| Luật | Lê Đình Khôi | `gv.ledinhkhoi` | LU104 · LU108 (trợ giảng) · LU110 | 607 |
| Sinh học | Huỳnh Thanh Sơn | `gv.huynhthanhson` | SH101 · SH102 | 434 |
| Sinh học | Nguyễn Kim Ngân | `gv.nguyenkimngan` | SH104 · SH107 | 431 |
| Sinh học | Trần Văn Lộc | `gv.tranvanloc` | SH106 · SH109 | 474 |
| Sinh học | Phan Thị Yến | `gv.phanthiyen` | SH103 · SH105 | 396 |
| Sinh học | Ngô Quang Trường | `gv.ngoquangtruong` | SH102 (trợ giảng) · SH108 | 389 |

Tài khoản nên dùng để demo: `gv.hohaiyen` (3 môn, nhiều dữ liệu nhất của CNTT), `gv.nguyenthilan` (giảng viên chính cả 2
môn – thử được đầy đủ Thiết lập cảnh báo và Can thiệp), hoặc bất kỳ giảng viên khoa khác để so sánh.

### Đổi mật khẩu

```powershell
# Một tài khoản
python -m backend.app.cli set-password --username admin

# Tất cả tài khoản
$env:BACKEND_SEED_PASSWORD = "<mật khẩu mới>"
python -m backend.app.cli sync-users --reset-password
```

> 🔐 Mật khẩu **không bao giờ** được lưu dạng plaintext. CSDL chỉ chứa `password_hash` — chuỗi bcrypt 60 ký tự bắt đầu bằng `$2b$12$`. Bcrypt là hàm một chiều nên không thể khôi phục mật khẩu đã quên, chỉ có thể đặt lại.

---

## 6. Những gì KHÔNG đi theo gói

Sau khi `git clone`, hệ thống **chưa chạy được ngay**. Sáu thứ dưới đây cố ý không có trong repo và bạn phải tự tạo:

| Thứ thiếu | Dung lượng | Vì sao không có | Cách tạo lại |
|---|---:|---|---|
| **`.env`** | vài KB | Chứa mật khẩu và khóa JWT — đưa lên Git là lộ bí mật | `Copy-Item .env.example .env` rồi điền (mục 3.2) |
| **`docker/.env`** | vài KB | Như trên | `Copy-Item docker/.env.example docker/.env` |
| **`frontend/node_modules`** | **160 MB** | Thư viện tải về, `package-lock.json` đã ghi đủ phiên bản | `cd frontend && npm install` |
| **CSDL `moodle_src`** | **2,6 GB** | Nằm trong PostgreSQL, không nằm trong thư mục dự án | `lms.ps1 seed` + `lms.ps1 mock` |
| **CSDL `lms_analytics`** | **1,25 GB** | Như trên | `lms.ps1 setup` + `lms.ps1 etl-backfill` |
| **`frontend/dist`** | 1,5 MB | Bản build, sinh ra từ mã nguồn | `npm run build` |

Nhờ vậy repo chỉ nặng khoảng **7 MB** thay vì gần 1 GB.

### Vì sao không cần gửi kèm cơ sở dữ liệu?

File [mockdata/config.py](mockdata/config.py) đặt `RANDOM_SEED = 2026` **cố định**. Mọi máy chạy `seed` + `mock` với cùng `LMS_AS_OF` sẽ sinh ra dữ liệu **giống hệt nhau, từng dòng một**.

Kiểm chứng bằng lệnh sau — kết quả phải khớp với bảng bên dưới:

```powershell
python -c "import sys; sys.path.insert(0,'.'); import psycopg; from database.config import load_db_config; conn=psycopg.connect(**load_db_config('ANALYTICS_DB').conninfo()); print(conn.execute(\"SELECT risk_level, count(*) FROM analytics.fact_student_risk_summary WHERE snapshot_date='2026-11-06' GROUP BY 1 ORDER BY 1\").fetchall())"
```

| Mức rủi ro | Số lượng phải ra |
|---|---:|
| 🟢 GREEN | 1.308 |
| 🔴 RED | 408 |
| 🟡 YELLOW | 667 |

Ra số khác nghĩa là `LMS_AS_OF` trong `.env` chưa đúng.

---

## 7. Cách web hoạt động

### 7.1 Kiến trúc 5 tầng

```
┌────────────────────────────────────────────────────────────────┐
│ ① NGUỒN — moodle_src (2,6 GB, 30 bảng mdl_*)                   │
│   mdl_logstore_standard_log ....... 1.215.209 dòng             │
│   mdl_attendance_log .............. 36.933 dòng                │
│   mdl_assign_submission ........... 7.272 dòng                 │
│   ❌ Dữ liệu thô, muốn biết ai nguy cơ phải JOIN 12 bảng       │
└───────────────────────────┬────────────────────────────────────┘
                            │ CHỈ ĐỌC (read-only + timeout)
                 ┌──────────▼───────────┐
                 │ ② ETL — Python       │
                 │   Extract  (SQL)     │
                 │   Transform (pandas) │  ← chấm điểm đèn giao thông
                 │   Load  (COPY+UPSERT)│
                 └──────────┬───────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│ ③ KHO PHÂN TÍCH — lms_analytics (1,25 GB)                      │
│   fact_student_risk_summary ... 770.314 dòng  ✅ đã chấm điểm  │
│   fact_course_progress_daily ..   3.538 dòng  ✅ đã gộp        │
│   fact_server_traffic_hourly ..   1.450 dòng  ✅ đã đếm        │
│   risk_rule_set · outbound_message · auto_prompt_rule (v1.2)   │
└───────────────────────────┬────────────────────────────────────┘
                            │
                 ┌──────────▼───────────┐
                 │ ④ API — FastAPI      │
                 │   JWT · RBAC · Cache │
                 │   Excel · PDF        │
                 └──────────┬───────────┘
                            │ JSON qua HTTP
                 ┌──────────▼───────────┐
                 │ ⑤ WEB — React        │
                 │   Chart.js · AntD    │
                 └──────────────────────┘
```

### 7.2 Vì sao phải tách kho phân tích riêng?

| Vấn đề khi truy vấn thẳng Moodle | Giải pháp của dự án |
|---|---|
| Phải JOIN 12 bảng, quét 6,4 triệu dòng log → mất **vài phút** | Tính trước, lưu sẵn vào bảng fact → mỗi câu SQL **dưới 10 ms** |
| Chạy truy vấn nặng làm chậm Moodle mà sinh viên đang dùng thật | ETL kết nối **read-only** có timeout, chạy lúc rảnh |
| Moodle không có khái niệm "học kỳ", "mức rủi ro" | ETL tự suy ra và lưu vào bảng fact |

### 7.3 Vòng đời một request

Ví dụ: giảng viên Bùi Đức Thắng mở trang Cảnh báo môn IT004.

```
① TRÌNH DUYỆT gửi
   GET /api/v1/teacher/courses/6/risk-students?level=RED
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
        │
        ▼
② BACKEND kiểm tra vé vào cửa
   ├─ security.py giải mã JWT → user_id=9, role=TEACHER
   │  └─ token hết hạn?  → trả 401
   └─ teacher.py: teacher_ids của môn 6 = {5, 9}, có chứa 9 không?
      └─ không có       → trả 403
        │
        ▼
③ REPOSITORY chạy SQL trên bảng fact
   SELECT student_code, student_name, risk_score, risk_level, ...
   FROM analytics.fact_student_risk_summary
   WHERE course_id = 6
     AND snapshot_date = '2026-11-06'
     AND risk_level = 'RED'
     AND teacher_ids @> ARRAY[9]     ← phân quyền lần 2, ngay trong SQL
   ORDER BY risk_score DESC;
        │
        ▼
④ BACKEND đóng gói JSON  { "total": 30, "items": [...] }
        │
        ▼
⑤ REACT QUERY nhận, cache lại, tự làm mới sau 60 giây
        │
        ▼
⑥ CHART.JS vẽ doughnut + bảng cảnh báo lên màn hình
```

### 7.4 Ba lớp bảo vệ độc lập

| Lớp | Ở đâu | Làm gì |
|---|---|---|
| **1. Giao diện** | [ProtectedRoute.jsx](frontend/src/routes/ProtectedRoute.jsx) | Ẩn/chặn trang không đúng vai trò |
| **2. API** | [security.py](backend/app/core/security.py) `require_role()` | Trả 401 nếu token sai/hết hạn, 403 nếu sai vai trò |
| **3. Dữ liệu** | [repositories/teacher.py](backend/app/repositories/teacher.py) | Mọi câu SQL kèm `teacher_ids @> ARRAY[:teacher_id]` |

Ba lớp độc lập nhau. Người dùng có sửa JavaScript trong trình duyệt để vượt lớp 1 thì lớp 2 và 3 vẫn chặn.

### 7.5 Luật chấm điểm "đèn giao thông"

Đây là nghiệp vụ cốt lõi, cài đặt ở [etl/transform/risk_rules.py](etl/transform/risk_rules.py):

| Tiêu chí | 🟢 0 điểm | 🟡 1 điểm | 🔴 2 điểm |
|---|---|---|---|
| **C1** Vắng học | < 15% | 15% – < 30% | ≥ 30% |
| **C2** Không tương tác | vào gần đây | khá lâu | rất lâu |
| **C3** Thiếu bài tập | 0 bài | ít bài | nhiều bài |

Tổng điểm 3 tiêu chí quyết định `risk_level` = RED / YELLOW / GREEN.
Luật này được kiểm thử với **≥ 20 ca biên**, yêu cầu 100% pass ([tests/etl/test_risk_rules.py](tests/etl/test_risk_rules.py)).

### 7.6 Lịch chạy ETL tự động

| Job | Lịch | Việc |
|---|---|---|
| `traffic` | mỗi **5 phút** | Cập nhật lưu lượng, chụp mẫu người online |
| `course_progress` | mỗi **1 giờ** | Cập nhật tiến độ môn trong ngày |
| `student_risk` | mỗi **2 giờ** (07h–21h) | Chấm lại điểm rủi ro, ghi đè snapshot hôm nay |
| `nightly` | **01:00** hằng đêm | Chốt số liệu ngày hôm qua tại 23:59:59 |
| `maintenance` | **CN 03:00** | Tỉa snapshot cũ hơn 180 ngày, `VACUUM ANALYZE` |

Mỗi job dùng `pg_try_advisory_lock` để không chạy chồng lên nhau, và ghi lại kết quả vào bảng `etl_run_log`.

---

## 8. Cách xem cơ sở dữ liệu

### 8.1 Hai cơ sở dữ liệu cần phân biệt

| | `moodle_src` | `lms_analytics` |
|---|---|---|
| Vai trò | **Nguồn** — mô phỏng Moodle thật | **Đích** — kho phân tích |
| Schema | `public` | `analytics` |
| Số bảng | 30 (`mdl_*`) | 14 |
| Dung lượng | 2,6 GB | 1,25 GB |
| Ai ghi vào | `mockdata/` | `etl/` |
| Ai đọc | `etl/` (chỉ đọc) | `backend/` |

### 8.2 Xem bằng psql (dòng lệnh)

`psql.exe` thường **chưa có trong PATH** sau khi cài PostgreSQL trên Windows:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d lms_analytics
```

Hoặc thêm vào PATH một lần cho tiện:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\18\bin", "User")
```

Lệnh cơ bản trong psql:

| Lệnh | Tác dụng |
|---|---|
| `\l` | Liệt kê tất cả CSDL |
| `\dt analytics.*` | Liệt kê bảng trong schema `analytics` |
| `\d analytics.fact_student_risk_summary` | Xem cấu trúc, khóa, index của bảng |
| `\x` | Bật hiển thị dọc (dễ đọc khi bảng nhiều cột) |
| `\q` | Thoát |

### 8.3 Xem bằng pgAdmin 4 (giao diện đồ họa)

pgAdmin đi kèm bộ cài PostgreSQL. Mở **Start → PostgreSQL 18 → pgAdmin 4**.

```
Servers
└── PostgreSQL 18                    ← nhập mật khẩu user postgres
    └── Databases
        ├── lms_analytics
        │   └── Schemas
        │       └── analytics        ← chú ý: KHÔNG phải "public"
        │           └── Tables (8)
        └── moodle_src
            └── Schemas
                └── public
                    └── Tables (26)
```

- Xem dữ liệu: chuột phải bảng → **View/Edit Data** → **First 100 Rows**
- Gõ SQL: menu **Tools** → **Query Tool**

> ⚠️ Nếu báo `password authentication failed`: kiểm tra xem có vô tình gõ cả dấu nháy `'` không. Trong file `.env`, dấu nháy chỉ là cú pháp bao chuỗi, **không thuộc mật khẩu**.

### 8.4 Xem sơ đồ quan hệ (ERD)

**Với `lms_analytics`** — pgAdmin vẽ được ngay:
chuột phải database → **ERD For Database** → **Auto-layout** → **Download image**.

Schema này có 5 khóa ngoại thật:

```
  etl_run_log (run_id)
       ▲  ▲  ▲  ▲
       │  │  │  └──── etl_online_snapshot.etl_run_id
       │  │  └─────── fact_server_traffic_hourly.etl_run_id
       │  └────────── fact_course_progress_daily.etl_run_id
       └───────────── fact_student_risk_summary.etl_run_id

  app_user (user_id) ◀── intervention_log.teacher_id
```

**Với `moodle_src`** — cần thêm một bước. CSDL này có **0 khóa ngoại**, vì Moodle thật cũng không dùng khóa ngoại ở tầng CSDL (nó kiểm soát quan hệ ở tầng code PHP để chạy được trên nhiều hệ CSDL). Công cụ ERD vì thế sẽ vẽ ra 26 hộp rời rạc.

Cách khắc phục: dùng **DBeaver** (tải ở dbeaver.io) và khai báo *virtual foreign key* — chỉ lưu trong metadata của DBeaver, không đụng gì tới CSDL:

1. Mở bảng → tab **Foreign Keys** → chuột phải → **Create New Virtual Foreign Key**
2. Khai các quan hệ chính:

| Bảng | Cột | → Bảng đích |
|---|---|---|
| `mdl_course` | `category` | `mdl_course_categories.id` |
| `mdl_enrol` | `courseid` | `mdl_course.id` |
| `mdl_user_enrolments` | `enrolid` / `userid` | `mdl_enrol.id` / `mdl_user.id` |
| `mdl_assign` | `course` | `mdl_course.id` |
| `mdl_assign_submission` | `assignment` / `userid` | `mdl_assign.id` / `mdl_user.id` |
| `mdl_attendance` | `course` | `mdl_course.id` |
| `mdl_attendance_sessions` | `attendanceid` | `mdl_attendance.id` |
| `mdl_attendance_log` | `sessionid` / `studentid` | `mdl_attendance_sessions.id` / `mdl_user.id` |
| `mdl_course_modules` | `course` / `module` / `section` | `mdl_course.id` / `mdl_modules.id` / `mdl_course_sections.id` |
| `mdl_logstore_standard_log` | `userid` / `courseid` | `mdl_user.id` / `mdl_course.id` |

3. Click đôi **Tables** → tab **ER Diagram** → sơ đồ hiện đầy đủ

> ℹ️ **Không công cụ nào vẽ được quan hệ giữa bảng Moodle và 3 bảng fact**, vì chúng nằm ở hai database khác nhau — PostgreSQL không cho tạo khóa ngoại xuyên database. Cầu nối duy nhất là mã ETL trong [etl/extract/sql/](etl/extract/sql/).

### 8.5 Vài câu SQL hữu ích

```sql
-- Dung lượng và số dòng từng bảng
SELECT relname AS bang, n_live_tup AS so_dong,
       pg_size_pretty(pg_total_relation_size(relid)) AS dung_luong
FROM pg_stat_user_tables WHERE schemaname = 'analytics'
ORDER BY n_live_tup DESC;

-- Phân bố đèn giao thông ngày mới nhất
SELECT risk_level, COUNT(*) FROM analytics.fact_student_risk_summary
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM analytics.fact_student_risk_summary)
GROUP BY risk_level;

-- Top 10 sinh viên nguy cơ cao nhất của một môn
SELECT student_code, student_name, risk_score, absence_rate,
       missing_assignments_count, risk_reasons
FROM analytics.fact_student_risk_summary
WHERE course_id = 6 AND snapshot_date = '2026-11-06' AND risk_level = 'RED'
ORDER BY risk_score DESC LIMIT 10;

-- Lịch sử chạy ETL gần đây
SELECT run_id, job_name, status, started_at, finished_at
FROM analytics.etl_run_log ORDER BY run_id DESC LIMIT 10;
```

### 8.6 Kiểm tra trạng thái migration

Không cần mở CSDL vẫn xem được cấu trúc đã dựng tới đâu:

```powershell
python -m database.migrate status --target analytics
python -m database.migrate status --target moodle
```

### 8.7 Grain của 3 bảng fact

| Bảng | PRIMARY KEY | Một dòng là gì |
|---|---|---|
| `fact_student_risk_summary` | `(course_id, user_id, snapshot_date)` | 1 sinh viên, trong 1 môn, tại 1 ngày chụp |
| `fact_course_progress_daily` | `(course_id, stat_date)` | 1 môn học, trong 1 ngày |
| `fact_server_traffic_hourly` | `(stat_hour)` | 1 giờ đồng hồ |

---

## 9. Cấu trúc dự án — tác dụng từng file

```
Do_an_chuyen_nganh/
├── common/       Tiện ích dùng chung mọi tầng
├── database/   ① Migration CSDL
├── mockdata/   ② Sinh dữ liệu giả lập
├── etl/        ③ Extract → Transform → Load
├── backend/    ④ REST API
├── frontend/   ⑤ Giao diện web
├── tests/        Kiểm thử pytest
├── perf/         Đo hiệu năng
├── scripts/      Lệnh tắt Windows
├── docker/       Dockerfile, nginx, bootstrap
├── docs/         Tài liệu nộp kèm
└── SPEC/         Kế hoạch và báo cáo tiến độ
```

### 9.1 Thư mục gốc

| File | Tác dụng |
|---|---|
| `.env.example` | Mẫu cấu hình có chú thích, sao chép thành `.env` rồi điền |
| `.gitignore` | Loại `.env`, `node_modules`, `dist`, `__pycache__` khỏi Git |
| `.dockerignore` | Loại các thư mục không cần khỏi build context Docker |
| `README.md` | Chính là file bạn đang đọc |
| `requirements.txt` | Thư viện Python, chia nhóm theo từng bước của dự án |
| `docker-compose.yml` | Định nghĩa 5 dịch vụ Docker |
| `Makefile` | Lệnh tắt cho Linux/macOS |
| `pytest.ini` | Cấu hình pytest |

### 9.2 `common/` — Tiện ích dùng chung

| File | Tác dụng |
|---|---|
| `settings.py` | **Quản lý thời gian toàn hệ thống.** Định nghĩa `AS_OF` thay cho `now()`, nhờ đó mock data, ETL, API và giao diện đều nhìn cùng một mốc thời gian |

### 9.3 `database/` — ① Tầng cơ sở dữ liệu

| File | Tác dụng |
|---|---|
| `config.py` | Đọc `.env`, trả về cấu hình kết nối. Thiếu biến nào báo lỗi rõ tên biến đó. Dùng chung bởi ETL và Backend |
| `migrate.py` | Trình chạy migration tự viết: quét `V***__*.sql`, áp dụng tăng dần, ghi checksum vào `schema_migrations` |

**`migrations/analytics/` — dựng kho phân tích**

| File | Tác dụng |
|---|---|
| `V001__schema_domains_support_tables.sql` | Tạo schema `analytics`, bảng `app_user`, `etl_run_log`, `etl_watermark` |
| `V002__fact_student_risk_summary.sql` | **BẢNG FACT 1** — cảnh báo sinh viên, 38 cột |
| `V003__fact_course_progress_daily.sql` | **BẢNG FACT 2** — tiến độ môn theo ngày |
| `V004__fact_server_traffic_hourly.sql` | **BẢNG FACT 3** — lưu lượng theo giờ |
| `V005__intervention_log_and_views.sql` | Bảng nhật ký can thiệp + view `v_student_risk_latest` |
| `V006__online_snapshot_attendance_status_rule.sql` | Bảng mẫu người online 5 phút + ràng buộc trạng thái điểm danh |
| `V007__nullable_rates_without_data.sql` | Sửa lỗi nghiệp vụ: mẫu số bằng 0 thì lưu `NULL` ("chưa có dữ liệu") thay vì `0` |

**`migrations/moodle/` — dựng CSDL nguồn**

| File | Tác dụng |
|---|---|
| `V001__core_course_user_enrol.sql` | Bảng lõi: danh mục, khóa học, người dùng, ghi danh, vai trò, nhóm |
| `V002__logstore_sessions_lastaccess.sql` | Nhật ký sự kiện, phiên đăng nhập, lần truy cập gần nhất |
| `V003__course_modules_assign_completion.sql` | Cấu trúc nội dung môn, bài tập, theo dõi hoàn thành |
| `V004__mod_attendance.sql` | Plugin điểm danh `mod_attendance` |

> Cấu trúc các bảng này sao chép nguyên văn từ **Moodle 3.9 thật**. Khi có Moodle thật, chỉ cần đổi thông tin kết nối trong `.env` là ETL chạy được, không phải sửa mã.

### 9.4 `mockdata/` — ② Sinh dữ liệu giả lập

| File | Tác dụng |
|---|---|
| `config.py` | Tham số sinh dữ liệu: `RANDOM_SEED = 2026`, danh sách `FACULTIES` (5 khoa: bộ môn, môn và loại môn LT/TH/ĐA, số SV, giảng viên, tỷ lệ hồ sơ hành vi, hệ số truy cập), lớp Tiếng Anh dùng chung, tài khoản dịch vụ gửi tin, trọng số theo giờ và thứ |
| `db.py` | Kết nối `moodle_src`, dùng `COPY` ghi hàng loạt |
| `names.py` | Sinh họ tên tiếng Việt có tính tái lập |
| `seed_structure.py` | Dựng bộ khung: vai trò, cây Khoa→Bộ môn→Môn, 28 giảng viên, 3.000 SV (khoa ở `mdl_user.department`), ghi danh, bài tập và hoạt động điểm danh theo loại môn, tùy chọn nhận tin `mdl_user_preferences` |
| `generate_activity.py` | Sinh hành vi học tập: 6,4 triệu dòng log, 48.144 bài nộp, 180.786 lượt điểm danh (~7 phút) |
| `cleanup.py` | Xóa dữ liệu giả lập (`--activity` hoặc `--all`) |

### 9.5 `etl/` — ③ Tầng ETL

**File gốc**

| File | Tác dụng |
|---|---|
| `config.py` | Mọi ngưỡng nghiệp vụ tập trung ở đây: timezone, quy tắc học kỳ, ngưỡng rủi ro, lịch job |
| `db.py` | Hai engine SQLAlchemy. Engine Moodle **chỉ đọc** — read-only + `statement_timeout`, nên ETL không thể làm hỏng Moodle |
| `sqlfile.py` | Nạp file SQL tĩnh; cú pháp `{{ten}}` chèn đoạn SQL dùng chung từ `_ten.sql` |
| `scheduler.py` | Lập lịch bằng APScheduler, chạy như tiến trình nền |

**`extract/` — Bước E**

| File | Tác dụng |
|---|---|
| `course_data.py` | Trích bộ dữ liệu các môn đang diễn ra, chạy trong một transaction REPEATABLE READ |
| `sql/_student_enrol.sql` | CTE dùng chung: SV ghi danh hợp lệ. Viết dạng semi-join `EXISTS` để tránh timeout |
| `sql/courses.sql` | Môn đang diễn ra + tên khoa, bộ môn, danh sách giảng viên |
| `sql/enrolments.sql` | SV ghi danh + MSSV, họ tên, email |
| `sql/attendance.sql` | **Tiêu chí 1 — Điểm danh.** Không có bản ghi = coi như vắng |
| `sql/interaction.sql` | **Tiêu chí 2 — Tương tác.** Lần truy cập cuối lấy từ logstore để đúng theo `AS_OF` |
| `sql/assignments.sql` | **Tiêu chí 3 — Bài tập.** Xử lý cả bài nộp nhóm |
| `sql/completion.sql` | Hoàn thành hoạt động theo chương, chỉ tính hoạt động bắt buộc đã đến hạn |
| `sql/weekly_activity.sql` | Hoạt động theo tuần học, cho biểu đồ đường 15 tuần |
| `sql/submissions_day.sql` | Số bài nộp trong ngày theo môn |
| `sql/traffic_hourly.sql` | Lưu lượng theo giờ, tính lại toàn bộ để `COUNT(DISTINCT)` luôn đúng |
| `sql/online_sessions.sql` | Người online tại `AS_OF` từ `mdl_sessions` |
| `sql/online_logstore.sql` | Suy ra người online từ log theo khung 5 phút |
| `sql/max_log_id.sql` | `id` lớn nhất của logstore, dùng khóa chính nên rất nhanh |
| `sql/new_log_range.sql` | Khoảng thời gian của log mới trong khoảng watermark |

**`transform/` — Bước T** (thuần Python/pandas, không truy cập CSDL nên dễ test)

| File | Tác dụng |
|---|---|
| `risk_rules.py` | ⭐ **Luật chấm điểm đèn giao thông** — nghiệp vụ cốt lõi của đề tài |
| `student_risk.py` | Gộp chỉ số từng cặp (môn, SV), gọi `risk_rules` → dòng fact |
| `course_progress.py` | Gộp số liệu cả lớp → dòng fact |
| `traffic.py` | Gộp lưu lượng theo giờ, bổ sung 0 cho giờ không có sự kiện |
| `semester.py` | Suy ra năm học / học kỳ từ `startdate` của môn |

**`load/` — Bước L**

| File | Tác dụng |
|---|---|
| `upsert.py` | Nạp hàng loạt: `CREATE TEMP TABLE` → `COPY` → `INSERT ... ON CONFLICT DO UPDATE` |
| `sql/delete_stale_risk.sql` | Xóa SV không còn trong lần tính mới |
| `sql/mark_peak_hours.sql` | Đánh dấu giờ cao điểm khi requests > P90 của 28 ngày |
| `sql/merge_online_snapshot.sql` | Gộp mẫu online; mẫu chụp thật luôn ghi đè mẫu suy ra |
| `sql/aggregate_online.sql` | Tính lại peak/avg người online |
| `sql/risk_level_counts.sql` | Đếm phân bố đèn giao thông mỗi môn |
| `sql/prune_risk_snapshots.sql` | Snapshot cũ hơn 180 ngày chỉ giữ bản cuối mỗi tuần |

**`jobs/` — Các job định kỳ**

| File | Tác dụng |
|---|---|
| `runner.py` | Khung chạy chung: khóa chống chạy trùng → ghi log RUNNING → E/T/L → ghi SUCCESS/FAILED |
| `job_traffic.py` | Job mỗi 5 phút |
| `job_course_progress.py` | Job mỗi giờ |
| `job_student_risk.py` | Job mỗi 2 giờ (07h–21h) |
| `nightly.py` | Job 01:00 — chốt số liệu ngày hôm qua |
| `maintenance.py` | Job Chủ nhật 03:00 — dọn dẹp, tối ưu |
| `backfill.py` | Chạy thủ công — nạp lịch sử lần đầu |

### 9.6 `backend/` — ④ Tầng API

**Gốc và hạ tầng**

| File | Tác dụng |
|---|---|
| `app/main.py` | Điểm khởi động: tạo FastAPI app, gắn CORS, security header, đăng ký 5 router với tiền tố `/api/v1` |
| `app/cli.py` | Quản lý tài khoản: `sync-users`, `set-password`, `list-users`; sao lưu: `backup`, `list-backups`, `restore` |
| `app/core/config.py` | Đọc biến `BACKEND_*` từ `.env` + `AS_OF` |
| `app/core/db.py` | Connection pool (`pool_size=10`), dependency `get_conn` |
| `app/core/security.py` | ⭐ Băm bcrypt, ký/kiểm JWT HS256 (hạn 8 giờ), `require_role`, giới hạn đăng nhập sai |
| `app/core/cache.py` | Cache TTL 60 giây cho endpoint KPI |

**`routers/` — Nhận HTTP request**

| File | Tác dụng |
|---|---|
| `auth.py` | `POST /auth/login`, `GET /auth/me` |
| `common.py` | `/filters`, `/etl/status`, `/health` |
| `admin.py` | Tổng quan, drill-down Khoa→Môn→SV, lưu lượng. **Chỉ vai trò ADMIN** |
| `reports.py` | Data Preview + xuất Excel/PDF |
| `teacher.py` | Cảnh báo, modal, can thiệp, tiến độ. Kiểm tra GV thuộc `teacher_ids` của môn |
| `deps.py` | Dependency dùng chung: vai trò, học kỳ, thời điểm tham chiếu |
| `_export.py` | Tạo HTTP response tải file |

**`repositories/` — Truy vấn CSDL (SQL thuần)**

| File | Tác dụng |
|---|---|
| `admin.py` | Cây Khoa→Môn→SV và thẻ KPI |
| `teacher.py` | Cảnh báo và tiến độ, luôn kèm điều kiện phân quyền |
| `traffic.py` | Lưu lượng và người online |
| `reports.py` | Định nghĩa các loại báo cáo |
| `common.py` | Thời điểm cập nhật, bộ lọc, trạng thái ETL |
| `users.py` | Đọc/ghi bảng `app_user` |
| `_sql.py` | ⭐ Chống SQL injection: chỉ ghép đoạn SQL **tĩnh** từ danh sách cho phép; mọi giá trị người dùng đi qua tham số bind |

**`schemas/` — Kiểu dữ liệu Pydantic** (tự sinh tài liệu Swagger)

| File | Tác dụng |
|---|---|
| `auth.py` | `LoginIn`, `TokenOut`, `UserOut` |
| `admin.py` / `teacher.py` / `reports.py` | Schema các endpoint tương ứng |
| `common.py` | Phân trang, dấu thời gian, bộ lọc |

**`services/` — Nghiệp vụ không đụng CSDL**

| File | Tác dụng |
|---|---|
| `export_excel.py` | Xuất Excel bằng openpyxl chế độ write-only, ít bộ nhớ |
| `export_pdf.py` | Xuất PDF bằng ReportLab, A4 ngang, lặp tiêu đề mỗi trang |
| `formatting.py` | Định dạng số/ngày kiểu vi-VN |

### 9.7 `frontend/` — ⑤ Tầng giao diện

**Gốc**

| File | Tác dụng |
|---|---|
| `package.json` | Khai báo thư viện và script `dev` / `build` / `test` / `e2e` |
| `vite.config.js` | Cấu hình Vite + **proxy `/api` → `http://127.0.0.1:8000`** |
| `index.html` | HTML gốc, chứa `<div id="root">` |
| `playwright.config.js` | Cấu hình E2E chạy trên Chrome đã cài sẵn |

**`src/` — Mã nguồn**

| File | Tác dụng |
|---|---|
| `main.jsx` | Điểm khởi động React, gắn theme đạt tương phản WCAG AA |
| `App.jsx` | Bọc Provider (React Query, Ant Design tiếng Việt), định tuyến theo vai trò |
| `styles.css` | CSS toàn cục |
| `api/client.js` | axios + gắn JWT. **401 ở bất kỳ request nào → tự đăng xuất** |
| `api/hooks.js` | React Query hook cho từng endpoint, tự làm mới 60 giây |
| `auth/AuthContext.jsx` | Đăng nhập/đăng xuất, tự hết phiên theo hạn token |
| `routes/ProtectedRoute.jsx` | Chặn trang theo vai trò ở phía giao diện |
| `theme/tokens.js` | Màu đèn giao thông và màu chuỗi dữ liệu; màu **luôn đi kèm ký hiệu** |
| `utils/format.js` | Định dạng vi-VN; tỷ lệ `null` → "Chưa có dữ liệu", khác hẳn 0% |

**`src/charts/` — Biểu đồ**

| File | Tác dụng |
|---|---|
| `setup.js` | Đăng ký Chart.js một lần + thiết lập mặc định (lưới mảnh, chữ màu mực, đường 2px) |
| `TrafficDualAxisChart.jsx` | Biểu đồ 2 trục; hai đường **khác kiểu nét** để không đọc nhầm thang |
| `EnrollmentStackedBar.jsx` | Cột chồng theo khoa, nhấn để drill-down |
| `TrafficHeatmap.jsx` | Heatmap giờ × thứ, thang tuần tự một màu |
| `RiskDoughnut.jsx` | Biểu đồ vành khuyên, nhấn lát cắt để lọc |
| `StudentCharts.jsx` | Biểu đồ trong modal: so sánh SV vs lớp, hoạt động theo tuần |

**`src/components/`, `layouts/`, `pages/`**

| File | Tác dụng |
|---|---|
| `components/AppHeader.jsx` | Thanh tiêu đề chung |
| `components/TermFilterBar.jsx` | Bộ lọc Năm học / Học kỳ / Khoa |
| `components/HierarchyTable.jsx` | Bảng phân cấp drill-down có breadcrumb |
| `components/StudentDetailModal.jsx` | Cửa sổ chi tiết SV + 4 nút can thiệp |
| `components/common.jsx` | `RiskBadge`, `KpiCard`, `ChartCard` (có nút "Biểu đồ \| Bảng") |
| `layouts/AdminLayout.jsx` | Khung trang Admin |
| `layouts/TeacherLayout.jsx` | Khung trang Giảng viên, có ô chọn môn |
| `pages/LoginPage.jsx` | Trang đăng nhập |
| `pages/admin/AdminOverview.jsx` | Trang Tổng quan |
| `pages/admin/AdminTraffic.jsx` | Trang Lưu lượng |
| `pages/admin/AdminReports.jsx` | Trang Báo cáo |
| `pages/teacher/TeacherHome.jsx` | Tự mở môn đầu tiên |
| `pages/teacher/TeacherRisk.jsx` | Trang Cảnh báo |
| `pages/teacher/TeacherProgress.jsx` | Trang Tiến độ lớp |

**`e2e/` — Kiểm thử giao diện thật**

| File | Tác dụng |
|---|---|
| `tests/helpers.js` | Đăng nhập qua API để lấy token nhanh |
| `tests/admin.spec.js` | Luồng Admin: lọc → drill-down → Export Excel |
| `tests/teacher.spec.js` | Luồng GV: lọc ĐỎ → mở modal → gửi can thiệp |
| `tests/authz.spec.js` | Phân quyền: 403 khi xem môn người khác, 401 khi token hết hạn |
| `tests/a11y.spec.js` | Khả năng tiếp cận WCAG 2.1 A/AA bằng axe-core |
| `tests/responsive.spec.js` | Kiểm 4 độ rộng 1920 / 1366 / 768 / 390 px |
| `global-teardown.js` | Xóa can thiệp do E2E tạo (nội dung bắt đầu bằng `[e2e]`) |

### 9.8 `tests/` — Kiểm thử pytest

| File | Tác dụng |
|---|---|
| `backend/conftest.py` | Fixture: tài khoản test, client HTTP, kết nối CSDL |
| `backend/test_auth_api.py` | Xác thực, 401/403, giới hạn đăng nhập sai |
| `backend/test_admin_api.py` | API Admin — đối chiếu với truy vấn trực tiếp bảng fact |
| `backend/test_teacher_api.py` | API Giảng viên — phân quyền theo môn, modal, can thiệp |
| `backend/test_reports_api.py` | Data Preview và xuất Excel/PDF |
| `backend/test_security_api.py` | CORS, chống SQL injection, bcrypt, security header |
| `backend/test_security_unit.py` | Unit test không cần CSDL |
| `etl/test_risk_rules.py` | ⭐ Luật rủi ro, ≥20 ca biên, yêu cầu 100% pass |
| `etl/test_semester.py` | Quy tắc suy ra năm học / học kỳ |
| `etl/test_transforms.py` | Transform trên bộ dữ liệu nhỏ dựng tay |
| `database/test_analytics_schema.py` | Schema thật; mỗi test chạy trong transaction rồi rollback |
| `database/test_migrate_runner.py` | Unit test cho `migrate.py` |
| `integration/test_etl_pipeline.py` | Đối soát với Moodle, tính nhất quán, idempotency |
| `mockdata/test_mock_integrity.py` | Tính toàn vẹn dữ liệu giả lập |

### 9.9 `perf/`, `scripts/`, `docker/`, `docs/`, `SPEC/`

| File | Tác dụng |
|---|---|
| `perf/build_x10.py` | Dựng CSDL `lms_analytics_x10` — nhân 10 lần dữ liệu để đo |
| `perf/explain_queries.py` | `EXPLAIN (ANALYZE, BUFFERS)` các truy vấn chính |
| `perf/locustfile.py` | Test tải: 50 người đồng thời (40 GV, 10 Admin) |
| `perf/etl_bench.py` | Đo thời gian ETL trên ~2.000 SV |
| `perf/export_bench.py` | Đo xuất Excel 10.000 dòng, PDF 500 dòng |
| `perf/results/` | Kết quả đã đo, dùng làm minh chứng trong báo cáo |
| `scripts/lms.ps1` | ⭐ Lệnh tắt Windows cho mọi thao tác |
| `scripts/e2e_cleanup.py` | Dọn dữ liệu rác do E2E tạo |
| `docker/python.Dockerfile` | Image Python dùng chung cho `init`, `etl`, `backend` |
| `docker/frontend.Dockerfile` | Image build React |
| `docker/bootstrap.sh` | Script chạy một lần trong container `init` |
| `docker/nginx.conf` | Nginx phục vụ bản build + proxy `/api` |
| `docs/TAI_LIEU_HE_THONG.md` | **Tài liệu tổng hợp nộp kèm đồ án** |
| `docs/KET_QUA_KIEM_THU.md` | Kết quả kiểm thử và đo hiệu năng |
| `docs/images/` | Ảnh màn hình dùng trong tài liệu |
| `SPEC/KE_HOACH_TRIEN_KHAI.md` | Bản kế hoạch gốc — mọi file mã nguồn đều trích dẫn số mục của nó |
| `SPEC/BAO_CAO_TIEN_DO.md` | Tiến độ và các thay đổi so với kế hoạch, kèm lý do |

---

## 10. Kiểm thử

| Loại | Lệnh | Tiền điều kiện |
|---|---|---|
| CSDL, ETL, mock, tích hợp, API, gửi tin, sao lưu | `python -m pytest -q` | Đã chạy `etl-backfill`, `users` |
| Frontend (đơn vị) | `cd frontend; npm test` | — |
| E2E, phân quyền, responsive, WCAG | `cd frontend; npx playwright test` | API + web + `moodle-stub` đang chạy, đặt `LMS_DEMO_PASSWORD` (tùy chọn `E2E_TEACHER`, `E2E_JWT_SECRET`); dọn dữ liệu thử tự động sau khi chạy |
| Hiệu năng | `.\scripts\lms.ps1 bench` | Xem thêm [perf/README.md](perf/README.md) |

Kết quả đã đo được ghi ở [docs/KET_QUA_KIEM_THU.md](docs/KET_QUA_KIEM_THU.md). Tóm tắt v1.2 (dữ liệu 5 khoa): mọi kiểm thử
pytest, vitest, 57 E2E đều đạt; 94 câu SQL của Dashboard chậm nhất 8,9 ms; 50 người dùng đồng thời: p95 28 ms, p99 50 ms, 0 lỗi.

---

## 11. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Thiếu biến môi trường: ANALYTICS_DB_...` | Chưa tạo `.env` | `Copy-Item .env.example .env` rồi điền (mục 3.2) |
| `password authentication failed` | Sai mật khẩu, hoặc gõ cả dấu nháy | Mật khẩu **không bao gồm** dấu nháy trong file `.env` |
| `psql: command not found` | psql chưa có trong PATH | Dùng đường dẫn đầy đủ (mục 8.2) |
| Đăng nhập báo sai mật khẩu | Chưa chạy `lms.ps1 users` | Chạy lại bước 5 của mục 3.3 |
| Trang trắng, không có dữ liệu | Chưa chạy `etl-backfill` | Chạy lại bước 4 của mục 3.3 |
| Số liệu khác tài liệu | `LMS_AS_OF` sai | Đặt đúng `2026-11-06T10:30:00+07:00` rồi chạy lại từ `seed` |
| Đổi mật khẩu xong vẫn không vào được | Đổi nhầm CSDL | Bản local (cổng 5173) và Docker (cổng 8080) dùng **hai CSDL riêng** |
| `npm run dev` báo thiếu module | Chưa `npm install` | `cd frontend; npm install` |
| Biểu đồ trống nhưng bảng có số | Trình duyệt chặn canvas | Thử trình duyệt khác, hoặc bấm nút "Bảng" |
| Gửi tin nhắn Moodle báo "Moodle lỗi máy chủ" / không kết nối được | Chưa chạy máy chủ Moodle mô phỏng | `.\scripts\lms.ps1 moodle-stub` (cổng 8091); kiểm tra ở Hệ thống › Kênh gửi tin |
| Không thấy email đã gửi | Chế độ mặc định ghi file, không gửi ra ngoài | Mở thư mục `var/mail_outbox/` (file `.eml`) |

---

## 12. Tài liệu chi tiết hơn

| Muốn biết | Đọc |
|---|---|
| Kiến trúc, thiết kế CSDL, minh chứng trực quan hóa | [docs/TAI_LIEU_HE_THONG.md](docs/TAI_LIEU_HE_THONG.md) |
| Kết quả kiểm thử và đo hiệu năng | [docs/KET_QUA_KIEM_THU.md](docs/KET_QUA_KIEM_THU.md) |
| Kế hoạch gốc của đồ án | [SPEC/KE_HOACH_TRIEN_KHAI.md](SPEC/KE_HOACH_TRIEN_KHAI.md) |
| Tiến độ và thay đổi so với kế hoạch | [SPEC/BAO_CAO_TIEN_DO.md](SPEC/BAO_CAO_TIEN_DO.md) |
| Chi tiết tầng ETL | [etl/README.md](etl/README.md) |
| Danh sách endpoint API | [backend/README.md](backend/README.md) hoặc chạy backend rồi mở `http://localhost:8000/api/docs` |
| Chi tiết tầng giao diện | [frontend/README.md](frontend/README.md) |
| Cách sinh dữ liệu giả lập | [mockdata/README.md](mockdata/README.md) |
| Cách đo hiệu năng | [perf/README.md](perf/README.md) |

---

## Giấy phép và ghi chú

Đồ án học tập, không dùng cho mục đích thương mại.

Dữ liệu trong hệ thống là **dữ liệu giả lập** sinh bằng `mockdata/`, không phải dữ liệu sinh viên thật. Họ tên, MSSV, email đều do chương trình sinh ngẫu nhiên với seed cố định.
