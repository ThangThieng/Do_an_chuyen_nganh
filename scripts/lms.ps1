<#
.SYNOPSIS
  Lệnh tắt cho dự án LMS Analytics trên Windows (SPEC 6.4 "Makefile/scripts").

.EXAMPLE
  .\scripts\lms.ps1 setup          # cài thư viện Python + npm, migrate 2 CSDL
  .\scripts\lms.ps1 ingest         # nạp CSV Moodle thật ($env:REAL_DATA_DIR = thư mục chứa Data_11-2026\ và NEW\NEW\)
  .\scripts\lms.ps1 etl-backfill   # tính lịch sử 3 bảng fact từ 13/09/2026
  .\scripts\lms.ps1 users          # tạo/cập nhật tài khoản (cần $env:BACKEND_SEED_PASSWORD)
  .\scripts\lms.ps1 api | web      # chạy API :8000 / frontend dev :5173
  .\scripts\lms.ps1 moodle-stub    # máy chủ Moodle 3.9 mô phỏng :8091 (kênh tin nhắn; hộp tin /stub/inbox)
  .\scripts\lms.ps1 etl            # ETL scheduler (tính rủi ro, nhắc tự động, gửi hàng đợi mỗi phút)
  .\scripts\lms.ps1 messaging-check # in cấu hình kênh gửi tin (đã che bí mật), thử kết nối SMTP và Moodle
  .\scripts\lms.ps1 test           # pytest + vitest
  .\scripts\lms.ps1 e2e            # Playwright (cần API + web đang chạy, $env:LMS_DEMO_PASSWORD)
  .\scripts\lms.ps1 bench          # hiệu năng: EXPLAIN các câu truy vấn của Dashboard (Locust: xem perf/README.md)
  .\scripts\lms.ps1 docker         # demo trọn gói bằng docker compose
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("setup", "ingest", "etl-backfill", "users", "api", "web", "moodle-stub", "etl", "messaging-check",
                 "test", "e2e", "bench", "docker")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step([string]$Title, [scriptblock]$Block) {
    Write-Host "==> $Title" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Thất bại: $Title (mã $LASTEXITCODE)" }
}

switch ($Command) {
    "setup" {
        Invoke-Step "Cài thư viện Python" { python -m pip install -r requirements.txt }
        Invoke-Step "Cài thư viện frontend" { Push-Location frontend; npm install; Pop-Location }
        Invoke-Step "Migrate CSDL phân tích" { python -m database.migrate up --target analytics }
        Invoke-Step "Migrate CSDL Moodle rút gọn" { python -m database.migrate up --target moodle }
    }
    "ingest" {
        if (-not $env:REAL_DATA_DIR) { throw "Đặt `$env:REAL_DATA_DIR = thư mục CSV Moodle thật (chứa Data_11-2026\ và NEW\NEW\)" }
        Invoke-Step "Nạp CSV Moodle thật" { python -m ingest.run --data-dir $env:REAL_DATA_DIR --batch 2026-11 }
    }
    "etl-backfill" { Invoke-Step "ETL backfill" { python -m etl.jobs.backfill --from 2026-09-13 } }
    "users" { Invoke-Step "Đồng bộ tài khoản" { python -m backend.app.cli sync-users } }
    "api" { python -m uvicorn backend.app.main:app --port 8000 }
    "web" { Push-Location frontend; npm run dev; Pop-Location }
    "moodle-stub" { python -m tools.moodle_ws_stub }
    "etl" { python -m etl.scheduler }
    "messaging-check" { Invoke-Step "Kiểm tra kênh gửi tin" { python -m backend.app.cli messaging-check } }
    "test" {
        Invoke-Step "pytest" { python -m pytest -q }
        Invoke-Step "vitest" { Push-Location frontend; npm test; Pop-Location }
    }
    "e2e" { Push-Location frontend; npx playwright test; Pop-Location }
    "bench" {
        Invoke-Step "EXPLAIN ANALYZE" { python -m perf.explain_queries --dataset x1 }
    }
    "docker" {
        if (-not (Test-Path docker\.env)) { throw "Chưa có docker/.env – sao chép từ docker/.env.example và điền giá trị" }
        Invoke-Step "docker compose up" { docker compose --env-file docker/.env up --build -d }
        Write-Host "Mở http://localhost:8080 (lần đầu chờ dịch vụ init nạp dữ liệu thật: docker compose logs -f init)"
    }
}
