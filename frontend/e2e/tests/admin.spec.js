/** E2E Admin (SPEC 6.3, v1.2): toàn trường → khoa → môn → sinh viên; minh bạch nguồn dữ liệu; lưu lượng; báo cáo PDF. */
import { expect, test } from "@playwright/test";
import { ADMIN, chooseOption, login, requirePassword, waitForCharts } from "./helpers.js";

test.beforeEach(async ({ page }) => {
  requirePassword(test);
  await login(page, ADMIN);
  await expect(page).toHaveURL(/\/admin$/);
});

test("toàn trường: KPI, biểu đồ tròn + xu hướng, so sánh 5 khoa; xuất Excel", async ({ page }) => {
  await waitForCharts(page, 5);
  await chooseOption(page, "Học kỳ", "HK1");
  await expect(page.locator(".ant-select[aria-label='Học kỳ']")).toContainText("HK1");
  await expect(page.locator(".level-crumb [aria-current=page]")).toHaveText("Toàn trường");
  await expect(page.getByText("Xu hướng mức rủi ro theo thời gian")).toBeVisible();

  const compare = page.locator(".ant-card", { has: page.getByText("So sánh giữa các Khoa", { exact: true }) });
  await expect(compare.locator("canvas")).toHaveCount(3);
  await expect(compare.locator("tbody tr.ant-table-row")).toHaveCount(5);

  await page.getByRole("button", { name: "Xuất báo cáo" }).click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByText("Báo cáo quy mô & tương tác – Excel").click(),
  ]);
  expect(download.suggestedFilename()).toBe("bao_cao_enrollment_HK1_2026-2027.xlsx");
  expect(await download.path()).toBeTruthy();
});

test("drill-down Khoa → Môn → Sinh viên, quay lại bằng thanh cấp xem và nút Back", async ({ page }) => {
  const compare = page.locator(".ant-card", { has: page.getByText("So sánh giữa các Khoa", { exact: true }) });
  await compare.getByRole("row", { name: /Khoa Công nghệ Thông tin/ }).click();
  await expect(page).toHaveURL(/\/admin\/faculties\/\d+/);
  await expect(page.locator(".level-crumb [aria-current=page]")).toHaveText("Khoa Công nghệ Thông tin");
  await expect(page.getByText("So sánh các môn trong khoa", { exact: true })).toBeVisible();

  const courses = page.locator(".ant-card", { has: page.getByText("Bảng môn học của khoa", { exact: true }) });
  await courses.locator("tbody tr.ant-table-row").first().click();
  await expect(page).toHaveURL(/\/admin\/courses\/\d+/);
  await expect(page.getByText(/luật cảnh báo: /)).toBeVisible();
  await page.locator("tbody tr.ant-table-row").first().click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByText("So sánh với trung bình lớp")).toBeVisible();
  await expect(modal.getByRole("button", { name: "Gửi email" })).toHaveCount(0);   // quản trị chỉ xem
  await modal.getByRole("button", { name: "Đóng" }).first().click();

  // Cấp Sinh viên gắn với URL (?student=): F5 mở lại đúng cửa sổ, Back đóng cửa sổ về cấp Môn học
  await page.locator("tbody tr.ant-table-row").first().click();
  await expect(page).toHaveURL(/[?&]student=\d+/);
  await page.reload();
  await expect(page.getByRole("dialog").getByText("So sánh với trung bình lớp")).toBeVisible();
  await expect(page.locator(".level-crumb [aria-current=page]")).toHaveText("Sinh viên");
  await page.goBack();
  await expect(page).not.toHaveURL(/[?&]student=/);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/faculties\/\d+/);
  await page.locator(".level-crumb").getByRole("link", { name: "Toàn trường" }).click();
  await expect(page).toHaveURL(/\/admin(\?.*)?$/);
});

test("minh bạch: ngăn Nguồn & cách tính nêu bảng Moodle và luật 3 tiêu chí", async ({ page }) => {
  await page.getByRole("button", { name: /Nguồn & cách tính/ }).first().click();
  const drawer = page.locator(".ant-drawer-open");
  await expect(drawer.getByText(/mdl_/).first()).toBeVisible();
  await expect(drawer.getByText(/Vắng học/).first()).toBeVisible();
});

test("trang lưu lượng: biểu đồ 2 trục, heatmap và thẻ thời gian thực", async ({ page }) => {
  await page.getByRole("link", { name: "Lưu lượng" }).click();
  await waitForCharts(page, 2);
  await expect(page.getByText("Online hiện tại")).toBeVisible();
  await expect(page.getByText("Top 10 giờ đông nhất")).toBeVisible();
  await expect(page.locator("tbody tr.ant-table-row")).toHaveCount(10);
});

test("báo cáo cảnh báo: lọc mức Nguy cơ cao → xem trước → xuất PDF", async ({ page }) => {
  await page.getByRole("link", { name: "Báo cáo" }).click();
  await chooseOption(page, "Loại báo cáo", "Cảnh báo sinh viên nguy cơ");
  await chooseOption(page, "Mức rủi ro", "Nguy cơ cao");
  await page.getByRole("button", { name: "Xem trước" }).click();
  await expect(page.getByText("Báo cáo cảnh báo sinh viên nguy cơ")).toBeVisible();
  const badges = page.locator("tbody .risk-badge");
  await expect(badges.first()).toBeVisible();
  for (const text of await badges.allInnerTexts()) expect(text).toContain("Nguy cơ cao");

  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /Xuất PDF/ }).click()]);
  expect(download.suggestedFilename()).toMatch(/^bao_cao_risk_HK1_2026-2027\.pdf$/);
});
