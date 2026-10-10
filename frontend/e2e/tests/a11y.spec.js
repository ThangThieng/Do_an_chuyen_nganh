/**
 * Khả năng tiếp cận (SPEC 6.3): axe-core với bộ quy tắc WCAG 2.1 A/AA (gồm tương phản màu).
 * Không chấp nhận vi phạm mức "serious" hoặc "critical". Nội dung vẽ trên canvas không được axe kiểm tra –
 * biểu đồ có role="img" + aria-label và nút xem dạng bảng.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { ADMIN, TEACHER, login, requirePassword, waitForCharts } from "./helpers.js";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function audit(page, testInfo, name) {
  // Chờ hiệu ứng chuyển màu của Ant Design (0,2–0,3 s, vd nút vừa chuyển từ vô hiệu sang bấm được) kết thúc rồi mới đo
  await page.waitForTimeout(400);
  const result = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  await testInfo.attach(`axe-${name}.json`, { body: JSON.stringify(result.violations, null, 2), contentType: "application/json" });
  const blocking = result.violations.filter((v) => ["serious", "critical"].includes(v.impact));
  const summary = blocking.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} phần tử – ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
  expect(summary, `Vi phạm WCAG trên ${name}`).toEqual([]);
}

test("trang đăng nhập", async ({ page }, testInfo) => {
  await page.goto("/login");
  await audit(page, testInfo, "login");
});

test("Admin – tổng quan", async ({ page }, testInfo) => {
  requirePassword(test);
  await login(page, ADMIN);
  await waitForCharts(page, 3);
  await audit(page, testInfo, "admin-overview");
});

test("Giảng viên – cảnh báo và Modal chi tiết", async ({ page }, testInfo) => {
  requirePassword(test);
  await login(page, TEACHER);
  await expect(page.getByText("Bảng cảnh báo sinh viên", { exact: true })).toBeVisible();
  await waitForCharts(page, 1);
  await audit(page, testInfo, "teacher-risk");
  await page.locator(".ant-card", { hasText: "Bảng cảnh báo sinh viên" }).locator("tbody tr.ant-table-row").first().click();
  await expect(page.getByRole("dialog").getByText("So sánh với trung bình lớp")).toBeVisible();
  await page.waitForTimeout(600);
  await audit(page, testInfo, "teacher-modal");
  await page.getByRole("dialog").getByRole("button", { name: "Gửi tin nhắn Moodle" }).click();
  await expect(page.locator(".ant-drawer-open textarea")).toBeVisible();
  await audit(page, testInfo, "teacher-composer");
});

// ----------------------------------------------------------------------------- các trang mới của v1.2
test("Admin – trang Khoa, trang Môn học, Kênh gửi tin", async ({ page }, testInfo) => {
  requirePassword(test);
  await login(page, ADMIN);
  await page.locator(".ant-card", { hasText: "So sánh giữa các Khoa" }).locator("tbody tr.ant-table-row").first().click();
  await expect(page.getByText("So sánh các môn trong khoa", { exact: true })).toBeVisible();
  await waitForCharts(page, 4);
  await audit(page, testInfo, "admin-faculty");
  await page.locator(".ant-card", { hasText: "Bảng môn học của khoa" }).locator("tbody tr.ant-table-row").first().click();
  await expect(page.getByText(/luật cảnh báo: /)).toBeVisible();
  await waitForCharts(page, 2);
  await audit(page, testInfo, "admin-course");
  await page.getByRole("button", { name: /Nguồn & cách tính/ }).first().click();
  await expect(page.locator(".ant-drawer-open").getByText(/mdl_/).first()).toBeVisible();
  await audit(page, testInfo, "metric-drawer");
  await page.goto("/admin/channels");
  await expect(page.getByText("Cấu hình hiện hành (đã che bí mật)")).toBeVisible();
  await audit(page, testInfo, "admin-channels");
});

test("Giảng viên – Thiết lập cảnh báo và Can thiệp", async ({ page }, testInfo) => {
  requirePassword(test);
  await login(page, TEACHER);
  await page.getByRole("link", { name: "Thiết lập cảnh báo" }).click();
  await expect(page.getByText(/sinh viên đổi mức|Không ai đổi mức/).first()).toBeVisible();
  await audit(page, testInfo, "teacher-rules");
  await page.getByRole("link", { name: "Can thiệp" }).click();
  await expect(page.locator("tbody tr.ant-table-row").first()).toBeVisible();
  await audit(page, testInfo, "teacher-interventions");
  for (const tab of ["Đã gửi", "Nhắc tự động", "Mẫu tin nhắn"]) {
    await page.getByRole("tab", { name: tab }).click();
    await page.waitForLoadState("networkidle");
    await audit(page, testInfo, `teacher-interventions-${tab}`);
  }
});
