/**
 * Chụp toàn bộ màn hình phục vụ báo cáo (Chương 5): độ phân giải x2, dữ liệu demo tại LMS_AS_OF.
 * Không thay đổi dữ liệu: chỉ mở hộp thoại xác nhận, không bấm xác nhận; bản sao lưu tạo để chụp được xóa ngay.
 * Ngoại lệ có chủ đích: gửi MỘT tin minh họa (tiêu đề "[e2e] …", chế độ kiểm thử – file .eml / Moodle mô phỏng) để chụp
 * mã xác nhận và hộp tin sinh viên; chạy `python scripts/e2e_cleanup.py` sau khi chụp để xóa tin này.
 *
 *   $env:LMS_DEMO_PASSWORD = "<mật khẩu demo>"
 *   node e2e/report_shots.mjs          # ảnh lưu ở ../docs/images/report
 * Biến tùy chọn: SHOT_BASE_URL (mặc định http://localhost:5173), SHOT_OUT, SHOT_CHANNEL, SHOT_TEACHER.
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect } from "@playwright/test";
import { chromium } from "playwright-core";

const BASE = process.env.SHOT_BASE_URL ?? "http://localhost:5173";
const OUT = process.env.SHOT_OUT ?? "../docs/images/report";
const PASSWORD = process.env.LMS_DEMO_PASSWORD;
const ADMIN = "admin";
const TEACHER = process.env.SHOT_TEACHER ?? "gv.tranminhhung";
if (!PASSWORD) {
  console.error("Cần đặt biến LMS_DEMO_PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

const problems = [];
function watch(page, label) {
  page.on("pageerror", (e) => problems.push(`[${label}] lỗi JavaScript: ${e.message}`));
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 400 && !r.url().includes("/auth/login")) problems.push(`[${label}] API ${r.status()} ${r.url()}`);
  });
}
async function settle(page, ms = 900) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(ms);
}
async function shot(target, name, options = {}) {
  await target.screenshot({ path: path.join(OUT, `${name}.png`), ...options });
  console.log(`✔ ${name}`);
}
async function login(page, username, password = PASSWORD) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Tên đăng nhập").fill(username);
  await page.getByLabel("Mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
}
async function openSystem(page, label) {
  await page.getByRole("button", { name: /Hệ thống/ }).click();
  await page.getByRole("menuitem", { name: label }).click();
}

const browser = await chromium.launch({ channel: process.env.SHOT_CHANNEL ?? "chrome", headless: true });
const desktop = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: "vi-VN", timezoneId: "Asia/Ho_Chi_Minh" };
try {
  // ---------------------------------------------------------------- MH01 Đăng nhập
  {
    const context = await browser.newContext({ ...desktop, viewport: { width: 1280, height: 760 } });
    const page = await context.newPage();
    await page.goto(`${BASE}/login`);
    await page.getByLabel("Tên đăng nhập").waitFor();
    await shot(page, "mh01_dang_nhap");
    await login(page, ADMIN, "sai-mat-khau");
    await page.getByText("Sai tên đăng nhập hoặc mật khẩu").waitFor();
    await shot(page, "mh01_dang_nhap_loi");
    await context.close();
  }

  // ---------------------------------------------------------------- Quản trị viên
  {
    const context = await browser.newContext({ ...desktop, acceptDownloads: true });
    const page = await context.newPage();
    watch(page, "admin");
    await login(page, ADMIN);
    await page.waitForURL(/\/admin$/);
    await page.getByText("Tổng môn học").waitFor();
    await settle(page, 1200);
    await shot(page, "mh02_tong_quan", { fullPage: true });

    // Góp ý 3: Toàn trường › Khoa › Môn học (mỗi cấp một trang, URL riêng)
    await page.getByRole("row", { name: /Khoa Công nghệ Thông tin/ }).first().click();
    await page.getByText("So sánh các môn trong khoa").waitFor();
    await settle(page, 1200);
    await shot(page, "mh02_cap_khoa", { fullPage: true });
    await page.locator(".ant-card", { hasText: "Bảng môn học của khoa" }).locator("tbody tr.ant-table-row").first().click();
    await page.getByText(/luật cảnh báo: /).waitFor();
    await settle(page, 1200);
    await shot(page, "mh02_cap_mon_hoc", { fullPage: true });
    await page.getByRole("button", { name: /Nguồn & cách tính/ }).first().click();     // góp ý 4: minh bạch
    await page.locator(".ant-drawer-open").getByText(/mdl_/).first().waitFor();
    await settle(page);
    await shot(page.locator(".ant-drawer-open .ant-drawer-content"), "mh02_nguon_va_cach_tinh");
    await page.keyboard.press("Escape");

    await page.getByRole("link", { name: "Lưu lượng" }).click();
    await page.getByText("Top 10 giờ đông nhất").waitFor();
    await settle(page, 1200);
    await shot(page, "mh03_luu_luong", { fullPage: true });

    await page.getByRole("link", { name: "Báo cáo" }).click();
    await page.getByRole("button", { name: "Xem trước" }).click();
    await page.getByText(/dòng$/).first().waitFor();
    await settle(page);
    await shot(page, "mh04_bao_cao", { fullPage: true });

    await page.getByRole("link", { name: "Danh mục" }).click();
    await page.locator(".ant-table-row").first().waitFor();
    await settle(page);
    await shot(page, "mh05_danh_muc", { fullPage: true });

    await page.getByRole("button", { name: /Hệ thống/ }).click();
    await page.getByRole("menuitem", { name: "Quản lý người dùng" }).waitFor();
    await page.waitForTimeout(400);
    await shot(page, "menu_he_thong", { clip: { x: 0, y: 0, width: 1440, height: 260 } });
    await page.getByRole("menuitem", { name: "Quản lý người dùng" }).click();
    await page.getByRole("cell", { name: TEACHER, exact: true }).waitFor();
    await settle(page);
    await shot(page, "mh06_nguoi_dung", { fullPage: true });
    const row = page.locator(".ant-table-row", { hasText: TEACHER });
    await row.getByRole("button", { name: "Đặt lại mật khẩu" }).click();
    await page.locator(".ant-popconfirm").waitFor();
    await page.waitForTimeout(400);
    await shot(page, "mh06_xac_nhan_dat_lai");
    await page.locator(".ant-popconfirm").getByRole("button", { name: "Hủy" }).click();

    await openSystem(page, "Nhật ký ETL");
    await page.locator(".ant-table-row").first().waitFor();
    await settle(page);
    await shot(page, "mh07_nhat_ky_etl", { fullPage: true });

    await openSystem(page, "Sao lưu & phục hồi");
    await page.getByRole("button", { name: "Tạo bản sao lưu" }).click();
    const created = page.locator(".ant-message").getByText(/Đã tạo lms_analytics_/);
    await created.waitFor({ timeout: 120_000 });
    const name = (await created.textContent()).match(/lms_analytics_\d{8}_\d{6}(_\d+)?\.zip/)[0];
    await page.waitForTimeout(3500);                       // chờ thông báo tắt
    const backupRow = page.locator(".ant-table-row", { hasText: name });
    await backupRow.locator(".ant-table-row-expand-icon").click();
    await settle(page, 500);
    await shot(page, "mh08_sao_luu", { fullPage: true });
    await backupRow.getByRole("button", { name: "Phục hồi" }).click();
    const dialog = page.getByRole("dialog", { name: "Phục hồi dữ liệu" });
    await dialog.getByLabel("Tên file xác nhận").fill(name.slice(0, 20));
    await page.waitForTimeout(400);
    await shot(page, "mh08_xac_nhan_phuc_hoi");
    await dialog.getByRole("button", { name: "Hủy" }).click();
    await backupRow.getByRole("button", { name: "Xóa" }).click();
    await page.locator(".ant-popconfirm").getByRole("button", { name: "Xóa" }).click();
    await page.locator(".ant-table-row", { hasText: name }).waitFor({ state: "detached" });
    await page.locator(".ant-message-notice").first().waitFor({ state: "detached", timeout: 15_000 });   // chờ thông báo tắt

    await openSystem(page, "Kênh gửi tin");                                            // chức năng 2 – quản trị
    await page.getByRole("button", { name: "Kiểm tra Moodle" }).click();
    await page.getByText(/Kết nối được:/).waitFor();
    await settle(page);
    await shot(page, "mh16_kenh_gui_tin", { fullPage: true });

    await page.getByRole("link", { name: "Trợ giúp" }).click();
    await page.getByText("Giới thiệu hệ thống").waitFor();
    await settle(page);
    await shot(page, "mh13_tro_giup_quan_tri", { fullPage: true });

    await page.getByRole("button", { name: "Tài khoản", exact: true }).click();
    await page.getByRole("menuitem", { name: "Tài khoản & đổi mật khẩu" }).click();
    await page.getByLabel("Mật khẩu mới", { exact: true }).fill("abcdefgh");
    await page.getByLabel("Nhập lại mật khẩu mới").fill("abcdefgk");
    await page.getByRole("button", { name: "Lưu mật khẩu mới" }).click();
    await page.getByText("Hai lần nhập không khớp").waitFor();
    await page.waitForTimeout(400);
    await shot(page, "mh12_doi_mat_khau");
    await context.close();
  }

  // ---------------------------------------------------------------- Giảng viên
  {
    const context = await browser.newContext(desktop);
    const page = await context.newPage();
    watch(page, "teacher");
    await login(page, TEACHER);
    await page.waitForURL(/\/teacher\/courses\/\d+\/risk$/);
    await page.getByText("Bảng cảnh báo sinh viên").waitFor();
    await settle(page, 1200);
    await page.setViewportSize({ width: 1440, height: 1250 });     // đủ thấy thẻ, biểu đồ và các dòng đầu của bảng
    await settle(page, 600);
    await shot(page, "mh09_canh_bao");
    await page.setViewportSize({ width: 1440, height: 900 });

    await page.getByRole("button", { name: /Nguy cơ cao/ }).first().click();
    await settle(page);
    await page.setViewportSize({ width: 1440, height: 1800 });      // đủ cao để thấy trọn Modal kể cả các nút can thiệp
    await page.locator(".ant-card", { hasText: "Bảng cảnh báo sinh viên" }).locator("tbody tr.ant-table-row").first().click();
    await page.getByRole("dialog").getByText("So sánh với trung bình lớp").waitFor();
    await settle(page, 1200);
    await shot(page.locator(".ant-modal-content"), "mh10_chi_tiet_sinh_vien");
    await page.keyboard.press("Escape");
    await page.setViewportSize({ width: 1440, height: 900 });

    await page.getByRole("link", { name: "Tiến độ lớp" }).click();
    await page.getByText("Tiến độ theo chương / tuần").waitFor();
    await settle(page, 1200);
    await shot(page, "mh11_tien_do_lop", { fullPage: true });

    await page.getByRole("link", { name: "Thiết lập cảnh báo" }).click();          // chức năng 1
    await page.getByText("Tác động nếu áp dụng").waitFor();
    await page.getByText("Đồ án", { exact: true }).click();                          // chỉ xem trước, không lưu
    await page.getByText(/sinh viên đổi mức/).waitFor();
    await settle(page, 1200);
    await shot(page, "mh14_thiet_lap_canh_bao", { fullPage: true });

    await page.getByRole("link", { name: "Can thiệp" }).click();                     // chức năng 2
    await page.locator("tbody tr.ant-table-row").first().waitFor();
    await settle(page, 1200);
    await shot(page, "mh15_can_thiep_can_lien_he", { fullPage: true });
    await page.locator("tbody .ant-checkbox-input").first().check();
    await page.getByRole("button", { name: /Soạn tin cho 1 sinh viên/ }).click();
    await page.locator(".ant-drawer-open textarea").waitFor();
    await settle(page, 1200);
    await shot(page.locator(".ant-drawer-open .ant-drawer-content"), "mh15_soan_tin");
    await page.keyboard.press("Escape");
    await page.getByRole("tab", { name: "Nhắc tự động" }).click();
    await settle(page);
    await shot(page, "mh15_nhac_tu_dong", { fullPage: true });

    // Bằng chứng gửi (mức 3): gửi 1 tin minh họa qua Moodle mô phỏng -> mã xác nhận -> hộp tin của sinh viên
    await page.getByRole("tab", { name: "Cần liên hệ" }).click();
    await page.locator("tbody .ant-checkbox-input").first().check();
    await page.getByRole("button", { name: /Soạn tin cho 1 sinh viên/ }).click();
    const composer = page.locator(".ant-drawer-open");
    await composer.locator("textarea").waitFor();
    await settle(page, 800);                                                         // chờ ngăn trượt vào xong
    const email = composer.getByRole("checkbox", { name: "Email" });
    await email.click();
    await expect.poll(() => email.isChecked()).toBe(false);
    await composer.getByText(/Xem trước 1\/1/).waitFor();
    const subject = composer.locator("input.ant-input").first();
    await subject.fill(`[e2e] ${await subject.inputValue()}`);
    await composer.getByRole("button", { name: /^Gửi 1 tin$/ }).click();
    await composer.getByText(/Đã gửi 1 tin/).waitFor();
    await settle(page, 500);
    await shot(composer.locator(".ant-drawer-content"), "mh15_ket_qua_gui");
    await composer.locator(".ant-drawer-body").getByRole("button", { name: "Đóng" }).click();
    await page.getByRole("tab", { name: "Đã gửi" }).click();
    await page.locator(".ant-tabs-tabpane-active tbody tr.ant-table-row").first().click();
    const detail = page.locator(".ant-drawer-open");
    await detail.getByText("Mã xác nhận").first().waitFor();
    await settle(page, 500);
    await shot(page, "mh15_da_gui", { fullPage: true });
    const [inbox] = await Promise.all([
      context.waitForEvent("page"),
      detail.getByRole("link", { name: "Mở hộp tin trên Moodle mô phỏng" }).click(),
    ]);
    await inbox.setViewportSize({ width: 1100, height: 760 });
    await inbox.getByText("[e2e]").first().waitFor();
    await shot(inbox, "mh17_hop_tin_sinh_vien");
    await inbox.close();
    await page.keyboard.press("Escape");

    await page.getByRole("link", { name: "Trợ giúp" }).click();
    await page.getByText("Hướng dẫn sử dụng – Giảng viên").waitFor();
    await settle(page);
    await shot(page, "mh13_tro_giup_giang_vien", { fullPage: true });
    await context.close();
  }

  // ---------------------------------------------------------------- điện thoại
  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
    const page = await context.newPage();
    await login(page, TEACHER);
    await page.getByText("Bảng cảnh báo sinh viên").waitFor();
    await settle(page, 1200);
    await shot(page, "mh09_dien_thoai");
    await context.close();
  }
} finally {
  await browser.close();
}
if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log("Xong, không có lỗi JavaScript hay API.");
