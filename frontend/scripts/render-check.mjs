// Headless render verification: asserts chain-truth strings in the DOM and
// captures screenshots into docs/screenshots/. Run: node scripts/render-check.mjs
import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE = process.env.PREVIEW_URL ?? "http://localhost:4173";
const OUT = path.resolve("../docs/screenshots");
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  {
    route: "/",
    file: "01-overview.png",
    expect: ["books.toscrape.com", "£51.77", "£65.00", "SETTLED", "INFLATED REF"],
  },
  {
    route: "/product/1",
    file: "02-product.png",
    expect: ["a-light-in-the-attic", "£51.77", "0x7885"],
    minObservations: 3,
  },
  {
    route: "/sale/1",
    file: "03-sale.png",
    expect: ["£65.00", "£51.77", "Demo Shop", "1.9"],
  },
  {
    route: "/claim/1",
    file: "04-claim.png",
    expect: [
      "INFLATED REF",
      "SETTLED",
      "The merchant claims a reference price of 6500 cents",
      "0.2",
    ],
  },
  {
    route: "/merchant/0x7885536194BbD6E1D0A6Ab991aB215CFa9542339",
    file: "05-merchant.png",
    expect: ["Demo Shop", "1.9", "ACTIVE"],
  },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
let failures = 0;

for (const p of PAGES) {
  process.stdout.write(`${p.route} ... `);
  await page.goto(BASE + p.route, { waitUntil: "networkidle" });
  // wait for live data (first expected string) up to 45 s
  try {
    await page.waitForFunction(
      (needle) => document.body.innerText.toLowerCase().includes(needle.toLowerCase()),
      p.expect[0],
      { timeout: 45000 },
    );
  } catch {
    /* fall through to assertion report */
  }
  const text = (await page.innerText("body")).toLowerCase();
  const missing = p.expect.filter((e) => !text.includes(e.toLowerCase()));
  if (p.minObservations) {
    const observationCount = Number(
      text.match(/snapshots recorded\s+(\d+)\s+observations/i)?.[1] ?? 0,
    );
    if (observationCount < p.minObservations) {
      missing.push(`at least ${p.minObservations} observations`);
    }
  }
  await page.screenshot({ path: path.join(OUT, p.file), fullPage: true });
  if (missing.length) {
    failures++;
    console.log(`FAIL — missing: ${missing.join(" | ")}`);
  } else {
    console.log("OK");
  }
}

await browser.close();
console.log(failures === 0 ? "RENDER CHECK: PASS" : `RENDER CHECK: ${failures} page(s) FAILED`);
process.exit(failures === 0 ? 0 : 1);
