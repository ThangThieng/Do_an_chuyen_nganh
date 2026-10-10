/**
 * In chi tiết vi phạm WCAG (màu, tỷ lệ tương phản, phần tử) cho một trang – công cụ chẩn đoán khi a11y.spec báo lỗi.
 *   node e2e/axe_probe.mjs <user> <đường dẫn hoặc tên menu> [tên tab]
 */
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright-core";

const [user = "admin", target = "/admin", tab] = process.argv.slice(2);
const BASE = process.env.PROBE_BASE_URL ?? "http://127.0.0.1:5173";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: 1366, height: 800 } });
const page = await context.newPage();
await page.goto(`${BASE}/login`);
await page.getByLabel("Tên đăng nhập").fill(user);
await page.getByLabel("Mật khẩu").fill(process.env.LMS_DEMO_PASSWORD ?? "");
await page.getByRole("button", { name: "Đăng nhập" }).click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"));
if (target.startsWith("/")) await page.goto(`${BASE}${target}`);
else await page.getByRole("link", { name: target, exact: true }).click();
if (tab) await page.getByRole("tab", { name: tab }).click();
await page.waitForLoadState("networkidle");
await page.waitForTimeout(1200);
const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
for (const v of result.violations.filter((x) => ["serious", "critical"].includes(x.impact))) {
  console.log(`== ${v.id} (${v.impact})`);
  for (const n of v.nodes.slice(0, 4)) console.log(`   ${n.target.join(" ")}\n   ${n.failureSummary.replace(/\n/g, " | ")}`);
}
console.log("xong");
await browser.close();
