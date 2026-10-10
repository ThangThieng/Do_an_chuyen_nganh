/** Responsive (SPEC 6.3): 1920, 1366, 768, 390 px – biểu đồ co giãn trong khung, trang không cuộn ngang, bảng cuộn trong khung. */
import { expect, test } from "@playwright/test";
import { ADMIN, TEACHER, horizontalOverflow, login, requirePassword, waitForCharts } from "./helpers.js";

const WIDTHS = [1920, 1366, 768, 390];
// path: đi thẳng URL · nav: nhấn liên kết menu (trang theo môn đang chọn của giảng viên)
const PAGES = [
  { name: "admin-tong-quan", user: ADMIN, path: "/admin", charts: 5, ready: "Tổng môn học" },
  { name: "admin-khoa", user: ADMIN, path: "/admin/faculties/1", charts: 4, ready: "So sánh các môn trong khoa" },
  { name: "admin-mon-hoc", user: ADMIN, path: "/admin/courses/2", charts: 2, ready: "Bảng cảnh báo" },
  { name: "gv-canh-bao", user: TEACHER, path: "/teacher", charts: 2, ready: "Bảng cảnh báo sinh viên" },
  { name: "gv-tien-do", user: TEACHER, nav: "Tiến độ lớp", charts: 2, ready: "Tiến độ theo chương / tuần" },
  { name: "gv-thiet-lap-canh-bao", user: TEACHER, nav: "Thiết lập cảnh báo", charts: 0, ready: "Tác động nếu áp dụng" },
  { name: "gv-can-thiep", user: TEACHER, nav: "Can thiệp", charts: 0, ready: "Cần liên hệ" },
];

for (const width of WIDTHS) {
  for (const target of PAGES) {
    test(`${target.name} @ ${width}px`, async ({ page }, testInfo) => {
      requirePassword(test);
      await page.setViewportSize({ width, height: width < 500 ? 844 : 900 });
      await login(page, target.user);
      if (target.path) await page.goto(target.path);
      else await page.getByRole("link", { name: target.nav }).click();
      await expect(page.getByText(target.ready, { exact: true }).first()).toBeVisible();
      if (target.charts) await waitForCharts(page, target.charts);
      else await page.waitForLoadState("networkidle");

      expect(await horizontalOverflow(page), "trang không được cuộn ngang").toBeLessThanOrEqual(1);
      const canvases = await page.locator("canvas").evaluateAll((els) => els.map((c) => c.getBoundingClientRect().width));
      for (const w of canvases) {
        expect(w).toBeGreaterThan(0);
        expect(w).toBeLessThanOrEqual(width);
      }
      await expect(page.locator(".app-nav a").first()).toBeInViewport();
      await testInfo.attach(`${target.name}-${width}`, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
    });
  }
}
