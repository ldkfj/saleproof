// Opt-in corrected-release render evidence. It verifies chain truth first,
// proves the preview bundle contains the same addresses, then captures DOM evidence.
import { execFileSync } from "child_process";
import { chromium } from "playwright";
import fs from "fs";
import path from "path";

if (process.env.SALEPROOF_RUN_LIVE_RENDER_EVIDENCE !== "1") {
  throw new Error("Opt in with SALEPROOF_RUN_LIVE_RENDER_EVIDENCE=1.");
}
if ((process.env.VITE_GL_NETWORK ?? "studionet") !== "studionet") {
  throw new Error("The reviewed release render check is Studionet-only.");
}

const LEDGER_ADDRESS = process.env.VITE_LEDGER_ADDRESS;
const BOND_ADDRESS = process.env.VITE_BOND_ADDRESS;
const MERCHANT_ADDRESS = process.env.SALEPROOF_EVIDENCE_MERCHANT_ADDRESS;
for (const [name, value] of Object.entries({
  VITE_LEDGER_ADDRESS: LEDGER_ADDRESS,
  VITE_BOND_ADDRESS: BOND_ADDRESS,
  SALEPROOF_EVIDENCE_MERCHANT_ADDRESS: MERCHANT_ADDRESS,
})) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(value ?? "")) {
    throw new Error(`${name} must be an explicit 20-byte address.`);
  }
}

execFileSync(process.execPath, ["scripts/verify-live.mjs"], {
  cwd: process.cwd(),
  env: process.env,
  stdio: "inherit",
});

const BASE = process.env.PREVIEW_URL ?? "http://localhost:4173";
const OUT = path.resolve("../docs/screenshots/current");
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  {
    route: "/",
    file: "01-overview.png",
    expect: ["Studionet", "books.toscrape.com", "£51.77", "£65.00", "SETTLED", "INFLATED REF"],
  },
  {
    route: "/product/1",
    file: "02-product.png",
    expect: ["Studionet", "a-light-in-the-attic", "£51.77", "60s Cooldown Enforced"],
    minObservations: 3,
  },
  {
    route: "/sale/1",
    file: "03-sale.png",
    expect: ["Studionet", "£65.00", "£51.77", "Demo Shop", "1.9"],
  },
  {
    route: "/claim/1",
    file: "04-claim.png",
    expect: [
      "Studionet",
      "INFLATED REF",
      "SETTLED",
      "The merchant claims a reference price of 6500 cents",
      "0.2",
    ],
  },
  {
    route: `/merchant/${MERCHANT_ADDRESS}`,
    file: "05-merchant.png",
    expect: ["Studionet", "Demo Shop", "1.9", "ACTIVE"],
  },
];

async function assertBundleAddresses(page) {
  const scriptUrls = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((entry) => entry.name)
      .filter((name) => /\.js(?:\?|$)/.test(name)),
  );
  const source = (
    await Promise.all(
      scriptUrls.map(async (url) => {
        const response = await fetch(url);
        return response.ok ? response.text() : "";
      }),
    )
  )
    .join("\n")
    .toLowerCase();
  for (const address of [LEDGER_ADDRESS, BOND_ADDRESS]) {
    if (!source.includes(address.toLowerCase())) {
      throw new Error(`Preview bundle does not contain configured address ${address}.`);
    }
  }
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
let failures = 0;

try {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await assertBundleAddresses(page);

  for (const evidencePage of PAGES) {
    process.stdout.write(`${evidencePage.route} ... `);
    await page.goto(BASE + evidencePage.route, { waitUntil: "networkidle" });
    try {
      await page.waitForFunction(
        (needle) =>
          document.body.innerText.toLowerCase().includes(needle.toLowerCase()),
        evidencePage.expect[0],
        { timeout: 45_000 },
      );
    } catch {
      // The complete assertion report below names every missing string.
    }
    const text = (await page.innerText("body")).toLowerCase();
    const missing = evidencePage.expect.filter(
      (expected) => !text.includes(expected.toLowerCase()),
    );
    if (evidencePage.minObservations) {
      const observationCount = Number(
        text.match(/snapshots recorded\s+(\d+)\s+observations/i)?.[1] ?? 0,
      );
      if (observationCount < evidencePage.minObservations) {
        missing.push(`at least ${evidencePage.minObservations} observations`);
      }
    }
    await page.screenshot({
      path: path.join(OUT, evidencePage.file),
      fullPage: true,
    });
    if (missing.length) {
      failures += 1;
      console.log(`FAIL — missing: ${missing.join(" | ")}`);
    } else {
      console.log("OK");
    }
  }
} finally {
  await browser.close();
}

console.log(`Verified preview ledger: ${LEDGER_ADDRESS}`);
console.log(`Verified preview MerchantBond: ${BOND_ADDRESS}`);
console.log(
  failures === 0 ? "RENDER CHECK: PASS" : `RENDER CHECK: ${failures} page(s) FAILED`,
);
process.exit(failures === 0 ? 0 : 1);
