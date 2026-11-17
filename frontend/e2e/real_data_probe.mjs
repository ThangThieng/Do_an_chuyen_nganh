/**
 * Kiểm tra giao diện trên môi trường DỮ LIỆU THẬT (chỉ đọc): đăng nhập, mở các màn hình chính, ghi nhận lỗi
 * JavaScript và phản hồi API >= 400, chụp ảnh từng màn hình.
 *
 *   $env:PROBE_PASSWORD = "<mật khẩu>"; $env:PROBE_TEACHER = "<username>"; $env:PROBE_COURSE = "<course_id>"
 *   node e2e/real_data_probe.mjs
 * Biến tùy chọn: PROBE_BASE_URL (mặc định http://localhost:4174), PROBE_OUT (thư mục ảnh, đặt NGOÀI repo vì có tên thật).
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { chromium } from "playwright-core";

const BASE = process.env.PROBE_BASE_URL ?? "http://localhost:4174";
const OUT = process.env.PROBE_OUT;
const PASSWORD = process.env.PROBE_PASSWORD;
const TEACHER = process.env.PROBE_TEACHER;
const COURSE = process.env.PROBE_COURSE;
if (!PASSWORD || !TEACHER || !COURSE || !OUT) {
  console.error("Cần PROBE_PASSWORD, PROBE_TEACHER, PROBE_COURSE, PROBE_OUT.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

const problems = [];
function watch(page, label) {
  page.on("pageerror", (e) => problems.push(`[${label}] lỗi JavaScript: ${e.message}`));
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 400) problems.push(`[${label}] ${r.status()} ${r.url().replace(BASE, "")}`);
  });
}

async function login(page, username) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Tên đăng nhập").fill(username);
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: /đăng nhập/i }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 15000 });
}

async function visit(page, label, route) {
  await page.goto(`${BASE}${route}`);
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => problems.push(`[${label}] chờ tải quá 30 giây`));
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(OUT, `${label}.png`), fullPage: true });
  console.log(`  ${label}: ${route}`);
}

const browser = await chromium.launch({ channel: process.env.PROBE_CHANNEL ?? "chrome" });
try {
  const admin = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(admin, "admin");
  await login(admin, "admin");
  for (const [label, route] of [["admin-tong-quan", "/admin"], ["admin-luu-luong", "/admin/traffic"],
    ["admin-bao-cao", "/admin/reports"], ["admin-danh-muc", "/admin/catalog"], ["admin-mon", `/admin/courses/${COURSE}`],
    ["admin-nguoi-dung", "/admin/users"], ["admin-etl", "/admin/etl"]]) {
    await visit(admin, label, route);
  }
  await admin.close();

  const teacher = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(teacher, "teacher");
  await login(teacher, TEACHER);
  for (const [label, route] of [["gv-trang-chu", "/teacher"], ["gv-canh-bao", `/teacher/courses/${COURSE}/risk`],
    ["gv-tien-do", `/teacher/courses/${COURSE}/progress`], ["gv-luat", `/teacher/courses/${COURSE}/rules`],
    ["gv-can-thiep", `/teacher/courses/${COURSE}/interventions`]]) {
    await visit(teacher, label, route);
  }
  // Cửa sổ chi tiết sinh viên: bấm dòng đầu tiên của bảng cảnh báo
  await teacher.goto(`${BASE}/teacher/courses/${COURSE}/risk`);
  await teacher.waitForLoadState("networkidle").catch(() => {});
  const row = teacher.locator(".ant-table-tbody tr.ant-table-row").first();
  if (await row.count()) {
    await row.click();
    await teacher.waitForTimeout(2500);
    await teacher.screenshot({ path: path.join(OUT, "gv-chi-tiet-sv.png"), fullPage: true });
    console.log("  gv-chi-tiet-sv");
  } else {
    problems.push("[teacher] bảng cảnh báo không có dòng nào");
  }
  await teacher.close();
} finally {
  await browser.close();
}
console.log(problems.length ? `\nVẤN ĐỀ (${problems.length}):\n${[...new Set(problems)].join("\n")}` : "\nKhông có lỗi JavaScript hay lỗi API.");
process.exit(problems.length ? 1 : 0);
