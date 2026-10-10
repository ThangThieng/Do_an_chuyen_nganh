/**
 * Tìm phần tử làm trang bị cuộn ngang ở một độ rộng màn hình (công cụ chẩn đoán khi kiểm thử responsive báo lỗi).
 *   $env:LMS_DEMO_PASSWORD = "..."; node e2e/overflow_probe.mjs <user> <đường dẫn hoặc tên menu> [độ rộng]
 */
import { chromium } from "playwright-core";

const [user = "admin", target = "/admin", width = "390"] = process.argv.slice(2);
const BASE = process.env.PROBE_BASE_URL ?? "http://127.0.0.1:5173";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: Number(width), height: 844 } });
await page.goto(`${BASE}/login`);
await page.getByLabel("Tên đăng nhập").fill(user);
await page.getByLabel("Mật khẩu").fill(process.env.LMS_DEMO_PASSWORD ?? "");
await page.getByRole("button", { name: "Đăng nhập" }).click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"));
if (target.startsWith("/")) await page.goto(`${BASE}${target}`);
else await page.getByRole("link", { name: target }).click();
await page.waitForLoadState("networkidle");
await page.waitForTimeout(1500);
const report = await page.evaluate(() => {
  const vw = window.innerWidth;
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.right <= vw + 1) continue;
    // chỉ phần tử "lá" của vùng tràn: không có con nào cũng tràn
    if ([...el.children].some((c) => c.getBoundingClientRect().right > vw + 1)) continue;
    let p = el; let clipped = false;
    while ((p = p.parentElement)) {
      const o = getComputedStyle(p).overflowX;
      if (o === "auto" || o === "scroll" || o === "hidden") { clipped = true; break; }
    }
    if (!clipped) out.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")} right=${Math.round(r.right)} "${(el.textContent || "").trim().slice(0, 40)}"`);
  }
  return { overflow: document.documentElement.scrollWidth - vw, items: out.slice(0, 15) };
});
console.log(JSON.stringify(report, null, 2));
const hidden = await page.evaluate(() => [...document.querySelectorAll(".ant-card-head-title")].map((e) => ({
  text: e.textContent.trim().slice(0, 40), width: Math.round(e.getBoundingClientRect().width) })).filter((x) => x.width < 40));
console.log("tiêu đề thẻ bị ép:", JSON.stringify(hidden));
await browser.close();
