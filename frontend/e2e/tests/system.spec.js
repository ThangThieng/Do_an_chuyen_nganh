/**
 * Nhánh Hệ thống / Danh mục / Trợ giúp / Tài khoản (bổ sung ở phiên bản 1.1).
 * Không đổi mật khẩu thật của tài khoản demo: chỉ kiểm tra các nhánh bị từ chối.
 */
import { expect, test } from "@playwright/test";
import { ADMIN, TEACHER, login, requirePassword } from "./helpers.js";

test.beforeEach(() => requirePassword(test));

async function openSystemItem(page, label) {
  await page.getByRole("button", { name: /Hệ thống/ }).click();
  await page.getByRole("menuitem", { name: label }).click();
}

test("Admin: menu Hệ thống mở được 4 màn hình quản trị", async ({ page }) => {
  await login(page, ADMIN);

  await openSystemItem(page, "Quản lý người dùng");
  await expect(page).toHaveURL(/\/admin\/users$/);
  await expect(page.getByRole("cell", { name: TEACHER, exact: true })).toBeVisible();
  await expect(page.getByText("Tài khoản của bạn")).toBeVisible();          // không tự khóa được chính mình

  await openSystemItem(page, "Nhật ký ETL");
  await expect(page).toHaveURL(/\/admin\/etl$/);
  await expect(page.locator(".ant-table-row").first()).toBeVisible();

  await openSystemItem(page, "Sao lưu & phục hồi");
  await expect(page).toHaveURL(/\/admin\/backups$/);
  await expect(page.getByText("Bản sao lưu chứa toàn bộ dữ liệu của CSDL phân tích")).toBeVisible();

  await openSystemItem(page, "Kênh gửi tin");
  await expect(page).toHaveURL(/\/admin\/channels$/);
  await expect(page.getByText("Cấu hình hiện hành (đã che bí mật)")).toBeVisible();
});

test("Admin: kiểm tra kết nối Moodle Web Service trên trang Kênh gửi tin", async ({ page }) => {
  await login(page, ADMIN);
  await page.goto("/admin/channels");
  await page.getByRole("button", { name: "Kiểm tra Moodle" }).click();
  await expect(page.getByText(/Kết nối được: .*Moodle/)).toBeVisible();
});

test("Admin: tạo, xem điều kiện phục hồi rồi xóa một bản sao lưu", async ({ page }) => {
  test.setTimeout(180_000);
  await login(page, ADMIN);
  await page.goto("/admin/backups");
  await page.getByRole("button", { name: "Tạo bản sao lưu" }).click();
  const created = page.locator(".ant-message").getByText(/Đã tạo lms_analytics_\d{8}_\d{6}/);
  await expect(created).toBeVisible({ timeout: 120_000 });
  const name = (await created.textContent()).match(/lms_analytics_\d{8}_\d{6}(_\d+)?\.zip/)[0];
  const row = page.locator(".ant-table-row", { hasText: name });
  await expect(row).toBeVisible();

  // Nút Phục hồi trong hộp thoại chỉ bật khi gõ đúng tên file
  await row.getByRole("button", { name: "Phục hồi" }).click();
  const dialog = page.getByRole("dialog", { name: "Phục hồi dữ liệu" });
  const confirm = dialog.getByRole("button", { name: "Phục hồi" });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel("Tên file xác nhận").fill(name.replace(".zip", ""));
  await expect(confirm).toBeDisabled();
  await dialog.getByRole("button", { name: "Hủy" }).click();

  await row.getByRole("button", { name: "Xóa" }).click();
  await page.locator(".ant-popconfirm").getByRole("button", { name: "Xóa" }).click();
  await expect(page.locator(".ant-table-row", { hasText: name })).toHaveCount(0);
});

test("Admin: danh mục môn học có giảng viên phụ trách và tìm kiếm được", async ({ page }) => {
  await login(page, ADMIN);
  await page.getByRole("link", { name: "Danh mục" }).click();
  await expect(page.getByText("58 môn", { exact: true })).toBeVisible();      // 5 khoa
  await expect(page.locator(".ant-table-row")).toHaveCount(20);                 // trang 1 / phân trang 20 dòng
  await page.getByLabel("Tìm môn học").fill("IT001");
  await expect(page.locator(".ant-table-row")).toHaveCount(1);
  await expect(page.locator(".ant-table-row").first().locator(".ant-tag").first()).toBeVisible();
});

test("Đổi mật khẩu: kiểm tra từng ô và báo sai mật khẩu hiện tại", async ({ page }) => {
  await login(page, TEACHER);
  await page.getByRole("button", { name: "Tài khoản" }).click();
  await page.getByRole("menuitem", { name: "Tài khoản & đổi mật khẩu" }).click();
  await expect(page).toHaveURL(/\/teacher\/account$/);

  await page.getByLabel("Mật khẩu mới", { exact: true }).fill("abcdefgh");
  await page.getByLabel("Nhập lại mật khẩu mới").click();                         // rời ô -> kiểm tra ngay
  await expect(page.getByText("Cần có cả chữ và số")).toBeVisible();

  await page.getByLabel("Mật khẩu hiện tại").fill("sai-mat-khau-1");
  await page.getByLabel("Mật khẩu mới", { exact: true }).fill("MatKhauMoi2026");
  await page.getByLabel("Nhập lại mật khẩu mới").fill("MatKhauKhac2026");
  await page.getByRole("button", { name: "Lưu mật khẩu mới" }).click();
  await expect(page.getByText("Hai lần nhập không khớp")).toBeVisible();

  await page.getByLabel("Nhập lại mật khẩu mới").fill("MatKhauMoi2026");
  await page.getByRole("button", { name: "Lưu mật khẩu mới" }).click();
  await expect(page.locator(".ant-message").getByText("Mật khẩu hiện tại không đúng")).toBeVisible();
});

test("Giảng viên: có Trợ giúp, không vào được màn hình quản trị", async ({ page }) => {
  await login(page, TEACHER);
  await page.getByRole("link", { name: "Trợ giúp" }).click();
  await expect(page.getByText("Hướng dẫn sử dụng – Giảng viên")).toBeVisible();
  await expect(page.getByText("Cách hệ thống xếp mức rủi ro")).toBeVisible();
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/teacher/);
});
