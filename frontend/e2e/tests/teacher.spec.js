/** E2E Giảng viên (SPEC 6.3, v1.2): lọc ĐỎ → Modal → ghi chú / gửi email; thiết lập cảnh báo; trung tâm can thiệp; tiến độ lớp. */
import { expect, test } from "@playwright/test";
import { TEACHER, chooseOption, login, requirePassword, waitForCharts } from "./helpers.js";

test.beforeEach(async ({ page }) => {
  requirePassword(test);
  await login(page, TEACHER);
  await expect(page).toHaveURL(/\/teacher\/courses\/\d+\/risk$/);
});

test("lọc Nguy cơ cao → mở Modal → ghi nhận can thiệp → thấy trong lịch sử can thiệp", async ({ page }) => {
  await page.locator(".risk-card").filter({ hasText: "Nguy cơ cao" }).click();
  const table = page.locator(".ant-card", { has: page.getByText("Bảng cảnh báo sinh viên", { exact: true }) });
  await expect(table.locator("tbody tr.ant-table-row").first()).toBeVisible();
  for (const text of await table.locator("tbody .risk-badge").allInnerTexts()) expect(text).toContain("Nguy cơ cao");

  await table.locator("tbody tr.ant-table-row").first().click();
  const modal = page.getByRole("dialog").filter({ hasText: "So sánh với trung bình lớp" });
  await expect(modal.getByText(/Lý do:/)).toBeVisible();
  await expect(modal.getByText(/Điểm rủi ro \d+/)).toBeVisible();

  const note = `[e2e] Đã nhắc nhở trên lớp ${Date.now()}`;
  await modal.getByRole("button", { name: /Ghi chú/ }).click();
  const dialog = page.getByRole("dialog").filter({ hasText: "Nội dung" });
  await dialog.getByPlaceholder(/Đã nhắc nhở/).fill(note);
  await dialog.getByRole("button", { name: "Ghi nhận" }).click();
  await expect(page.getByText("Đã ghi nhận: Ghi chú")).toBeVisible();
  await expect(modal.getByText(note)).toBeVisible();
});

test("gửi email từ Modal: xem trước đã điền số liệu, chế độ kiểm thử, có mã xác nhận", async ({ page }) => {
  await page.locator(".risk-card").filter({ hasText: "Nguy cơ cao" }).click();
  const table = page.locator(".ant-card", { has: page.getByText("Bảng cảnh báo sinh viên", { exact: true }) });
  await table.locator("tbody tr.ant-table-row").first().click();
  await page.getByRole("dialog").getByRole("button", { name: "Gửi email" }).click();

  const drawer = page.locator(".ant-drawer-open");
  await expect(drawer.getByText(/Email: Chế độ kiểm thử|Email: Chế độ vận hành thật/)).toBeVisible();
  const body = drawer.locator("textarea");
  await expect(body).not.toHaveValue("");
  expect(await body.inputValue()).not.toMatch(/\{[a-z_]+\}/);
  const subject = drawer.locator("input.ant-input").first();
  await subject.fill(`[e2e] ${await subject.inputValue()}`);
  await drawer.getByRole("button", { name: /^Gửi 1 tin$/ }).click();
  await expect(drawer.getByText(/Đã gửi 1 tin · 0 chờ thử lại · 0 lỗi/)).toBeVisible();
  await expect(drawer.locator("code").first()).toContainText("@");          // Message-ID
});

test("thiết lập cảnh báo: giới hạn an toàn chặn lưu và báo lỗi ngay", async ({ page }) => {
  await page.getByRole("link", { name: "Thiết lập cảnh báo" }).click();
  const impact = page.locator(".ant-card", { has: page.getByText("Tác động nếu áp dụng", { exact: true }) });
  await expect(impact.getByText("Hiện tại")).toBeVisible();
  await page.getByLabel("Trọng số Vắng học").fill("90");
  await expect(impact.getByText("Chưa hợp lệ")).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu và áp dụng" })).toBeDisabled();
});

test("thiết lập cảnh báo: mẫu Đồ án → xem trước → lưu → trang Cảnh báo đổi theo → khôi phục mặc định", async ({ page }) => {
  const riskFootnote = page.getByText(/luật cảnh báo: /).first();
  const counts = async () => (await page.locator(".risk-card .kpi-value").allInnerTexts()).join("|");
  await expect(riskFootnote).toContainText("mặc định của trường");
  const before = await counts();

  await page.getByRole("link", { name: "Thiết lập cảnh báo" }).click();
  const impact = page.locator(".ant-card", { has: page.getByText("Tác động nếu áp dụng", { exact: true }) });
  await page.getByText("Đồ án", { exact: true }).click();
  await expect(impact.getByText(/\d+ sinh viên đổi mức/)).toBeVisible();
  const after = await impact.locator(".impact-row").nth(1).innerText();
  await page.getByPlaceholder(/Môn đồ án nộp báo cáo/).fill("[e2e] thử mẫu Đồ án");
  await page.getByRole("button", { name: "Lưu và áp dụng" }).click();
  await expect(page.getByText(/Đã lưu luật riêng v\d+/)).toBeVisible();
  await expect(page.getByText(/Luật đang áp dụng: riêng của môn/)).toBeVisible();

  await page.getByRole("link", { name: "Cảnh báo", exact: true }).click();
  await expect(riskFootnote).toContainText("riêng của môn");
  const red = after.match(/([\d.]+) đỏ/)[1];
  await expect(page.locator(".risk-card").filter({ hasText: "Nguy cơ cao" }).locator(".kpi-value")).toContainText(red);

  await page.getByRole("link", { name: "Thiết lập cảnh báo" }).click();
  await page.getByRole("button", { name: "Khôi phục mặc định" }).click();
  await page.locator(".ant-popconfirm").getByRole("button", { name: "Khôi phục" }).click();
  await expect(page.getByText("Đã khôi phục luật mặc định của trường")).toBeVisible();
  await page.getByRole("link", { name: "Cảnh báo", exact: true }).click();
  await expect(riskFootnote).toContainText("mặc định của trường");
  await expect.poll(counts).toBe(before);
});

test("can thiệp: gửi tin cho 3 sinh viên → mã xác nhận → xem trong hộp tin Moodle mô phỏng", async ({ page, context }) => {
  await page.getByRole("link", { name: "Can thiệp" }).click();
  await expect(page.getByRole("tab", { name: "Cần liên hệ" })).toBeVisible();
  await chooseOption(page, "Khoảng chưa liên hệ", "Hiện tất cả");
  const rows = page.locator("tbody tr.ant-table-row");
  await expect(rows.first()).toBeVisible();
  for (let i = 0; i < 3; i += 1) await rows.nth(i).locator(".ant-checkbox-input").check();
  await page.getByRole("button", { name: "Soạn tin cho 3 sinh viên đã chọn" }).click();

  const drawer = page.locator(".ant-drawer-open");
  await expect(drawer.getByText(/Tin nhắn Moodle: /)).toBeVisible();
  const subject = drawer.locator("input.ant-input").first();
  for (let i = 0; i < 3; i += 1) {
    await expect(drawer.getByText(`Xem trước ${i + 1}/3:`)).toBeVisible();
    await subject.fill(`[e2e] ${await subject.inputValue()}`);
    if (i < 2) await drawer.getByRole("button", { name: "Sau" }).click();
  }
  await drawer.getByRole("button", { name: /^Gửi 6 tin$/ }).click();
  await expect(drawer.getByText(/Đã gửi 6 tin · 0 chờ thử lại · 0 lỗi/)).toBeVisible();
  await drawer.locator(".ant-drawer-body").getByRole("button", { name: "Đóng" }).click();

  await page.getByRole("tab", { name: "Đã gửi" }).click();
  const sent = page.locator(".ant-tabs-tabpane-active tbody tr.ant-table-row", { hasText: "Tin nhắn Moodle" }).first();
  await sent.click();
  const detail = page.locator(".ant-drawer-open");
  await expect(detail.getByText(/Mã xác nhận/)).toBeVisible();
  const [inbox] = await Promise.all([
    context.waitForEvent("page"),
    detail.getByRole("link", { name: "Mở hộp tin trên Moodle mô phỏng" }).click(),
  ]);
  await expect(inbox.getByText(/\[e2e\]/).first()).toBeVisible();
  await inbox.close();
});

test("can thiệp: thêm quy tắc nhắc tự động và chạy thử (không gửi)", async ({ page }) => {
  await page.getByRole("link", { name: "Can thiệp" }).click();
  await page.getByRole("tab", { name: "Nhắc tự động" }).click();
  await page.getByRole("button", { name: "Thêm quy tắc" }).click();
  const modal = page.getByRole("dialog");
  await modal.getByLabel("Tên quy tắc").fill("[e2e] Nhắc khi không truy cập");
  await modal.getByRole("button", { name: "Lưu" }).click();
  await expect(page.getByText("Đã lưu quy tắc")).toBeVisible();
  const card = page.locator(".ant-card", { hasText: "[e2e] Nhắc khi không truy cập" }).first();
  await card.getByRole("button", { name: "Chạy thử (không gửi)" }).click();
  const dry = page.getByRole("dialog").filter({ hasText: "Chạy thử:" });
  await expect(dry.getByText(/sinh viên khớp điều kiện/)).toBeVisible();
  await dry.locator(".ant-modal-close").click();
  await expect(dry).toBeHidden();
  await page.getByRole("tab", { name: "Mẫu tin nhắn" }).click();
  await expect(page.getByText("Hệ thống").first()).toBeVisible();
});

test("tiến độ lớp: progress bar, tiến độ theo chương và chuyển tuần/ngày", async ({ page }) => {
  await page.getByRole("link", { name: "Tiến độ lớp" }).click();
  await waitForCharts(page, 2);
  await expect(page.getByText("Hoàn thành hoạt động bắt buộc")).toBeVisible();
  await expect(page.getByText("Tuần 1", { exact: true })).toBeVisible();
  await page.getByText("Theo ngày", { exact: true }).first().click();
  await expect(page.getByText("Số SV có truy cập trong mỗi ngày")).toBeVisible();
});

test("đổi môn trên thanh tiêu đề", async ({ page }) => {
  const select = page.locator(".app-header .ant-select");
  const before = page.url();
  await select.click();
  const options = page.locator(".ant-select-item-option");
  await expect(options).toHaveCount(2);
  const second = await options.nth(1).innerText();
  await options.nth(1).click();
  await expect(select).toContainText(second.split(" – ")[0]);
  await expect(page).not.toHaveURL(before);
  await expect(page).toHaveURL(/\/teacher\/courses\/\d+\/risk$/);
  await expect(page.getByText("Bảng cảnh báo sinh viên", { exact: true })).toBeVisible();
});
