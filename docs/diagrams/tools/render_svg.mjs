/**
 * Chụp từng <svg id="..."> trong một file HTML thành PNG (độ phân giải x2), dùng Chrome có sẵn qua playwright-core.
 *   node docs/diagrams/tools/render_svg.mjs docs/diagrams/tools/dfd.html docs/diagrams/png
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "../../../frontend/node_modules/playwright-core/index.mjs";

const [input, outDir] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ deviceScaleFactor: 2.5 });
await page.goto(pathToFileURL(path.resolve(input)).href);
const ids = await page.$$eval("svg[id]", (nodes) => nodes.map((n) => n.id));
for (const id of ids) {
  await page.locator(`#${id}`).screenshot({ path: path.join(outDir, `${id}.png`) });
  console.log(`✔ ${id}`);
}
await browser.close();
