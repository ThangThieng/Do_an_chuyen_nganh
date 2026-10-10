/** Dựng lại thao tác soạn tin trong report_shots và in mọi phản hồi API >= 400 kèm nội dung (chẩn đoán). */
import { chromium } from "playwright-core";

const BASE = "http://127.0.0.1:5173";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
page.on("response", async (r) => {
  if (r.url().includes("/api/") && r.status() >= 400) {
    console.log(r.status(), r.request().method(), r.url(), "\n  gửi:", r.request().postData(), "\n  nhận:", await r.text());
  }
});
await page.goto(`${BASE}/login`);
await page.getByLabel("Tên đăng nhập").fill(process.argv[2] ?? "gv.nguyenthilan");
await page.getByLabel("Mật khẩu").fill(process.env.LMS_DEMO_PASSWORD ?? "");
await page.getByRole("button", { name: "Đăng nhập" }).click();
await page.waitForURL(/\/teacher\//);
await page.getByRole("link", { name: "Can thiệp" }).click();
await page.locator("tbody tr.ant-table-row").first().waitFor();
await page.locator("tbody .ant-checkbox-input").first().check();
await page.getByRole("button", { name: /Soạn tin cho 1 sinh viên/ }).click();
const composer = page.locator(".ant-drawer-open");
await composer.locator("textarea").waitFor();
await page.keyboard.press("Escape");                       // như ảnh mh15_soan_tin
await page.getByRole("tab", { name: "Nhắc tự động" }).click();
await page.waitForTimeout(800);
await page.getByRole("tab", { name: "Cần liên hệ" }).click();
await page.locator("tbody .ant-checkbox-input").first().check();
await page.getByRole("button", { name: /Soạn tin cho 1 sinh viên/ }).click();
await composer.locator("textarea").waitFor();
await page.waitForTimeout(800);
await composer.getByRole("checkbox", { name: "Email" }).click();
await page.waitForTimeout(2000);
console.log("xong");
await browser.close();
