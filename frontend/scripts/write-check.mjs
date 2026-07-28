// Opt-in corrected-release write evidence. It verifies the configured chain
// first, then submits one real Studionet snapshot through the rendered UI.
import { execFileSync } from "child_process";
import { chromium } from "playwright";
import { createAccount } from "genlayer-js";
import fs from "fs";
import path from "path";

if (process.env.SALEPROOF_RUN_STUDIONET_WRITE_EVIDENCE !== "1") {
  throw new Error("Opt in with SALEPROOF_RUN_STUDIONET_WRITE_EVIDENCE=1.");
}
if ((process.env.VITE_GL_NETWORK ?? "studionet") !== "studionet") {
  throw new Error("The reviewed release write check is Studionet-only.");
}

const LEDGER_ADDRESS = process.env.VITE_LEDGER_ADDRESS;
const BOND_ADDRESS = process.env.VITE_BOND_ADDRESS;
for (const [name, value] of Object.entries({
  VITE_LEDGER_ADDRESS: LEDGER_ADDRESS,
  VITE_BOND_ADDRESS: BOND_ADDRESS,
})) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(value ?? "")) {
    throw new Error(`${name} must be an explicit 20-byte address.`);
  }
}

const PRODUCT_ID = Number(process.env.SALEPROOF_WRITE_PRODUCT_ID ?? "1");
if (!Number.isSafeInteger(PRODUCT_ID) || PRODUCT_ID < 1) {
  throw new Error("SALEPROOF_WRITE_PRODUCT_ID must be a positive integer.");
}

execFileSync(process.execPath, ["scripts/verify-live.mjs"], {
  cwd: process.cwd(),
  env: process.env,
  stdio: "inherit",
});

const BASE = process.env.PREVIEW_URL ?? "http://localhost:4173";
const OUT = path.resolve("../docs/screenshots/current");
const CHECKPOINT = path.resolve("scripts/.write-check-checkpoint.json");
fs.mkdirSync(OUT, { recursive: true });

function observationCount(text) {
  const match = text.match(/Snapshots Recorded\s+(\d+)\s+Observations/i);
  if (!match) {
    throw new Error("Could not read the product observation count from the UI.");
  }
  return Number(match[1]);
}

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
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

try {
  await page.goto(`${BASE}/product/${PRODUCT_ID}`, { waitUntil: "networkidle" });
  await assertBundleAddresses(page);
  await page
    .getByText(`Product #${PRODUCT_ID} Evidence Log`)
    .waitFor({ timeout: 45_000 });
  const checkpoint = fs.existsSync(CHECKPOINT)
    ? JSON.parse(fs.readFileSync(CHECKPOINT, "utf8"))
    : null;
  const before = checkpoint?.before ?? observationCount(await page.innerText("body"));

  await page.getByRole("button", { name: "Dev wallet — Studionet only" }).click();
  await page
    .getByText("Dev wallet — Studionet only", { exact: true })
    .first()
    .waitFor();

  let burnerAddress = checkpoint?.burnerAddress;
  let txHash = checkpoint?.hash;

  if (checkpoint) {
    await page.evaluate(
      ({ hash, startedAt, productId }) => {
        sessionStorage.setItem(
          `saleproof.tx.snapshot:${productId}`,
          JSON.stringify({ hash, startedAt }),
        );
      },
      { ...checkpoint, productId: PRODUCT_ID },
    );
    await page.getByRole("button", { name: "Disconnect" }).click();
    await page.getByRole("button", { name: "Dev wallet — Studionet only" }).click();
  } else {
    const privateKey = await page.evaluate(() =>
      localStorage.getItem("saleproof.studionet.burner-private-key"),
    );
    if (!privateKey) {
      throw new Error("Burner private key was not persisted.");
    }
    burnerAddress = createAccount(privateKey).address;

    await page.getByRole("button", { name: "Fund 1 GEN" }).click();
    await page
      .getByRole("button", { name: "Fund 1 GEN" })
      .waitFor({ state: "visible" });

    const snapshotButton = page.getByRole("button", { name: "Trigger snapshot" });
    await snapshotButton.waitFor({ state: "visible" });
    if (await snapshotButton.isDisabled()) {
      throw new Error(`Trigger snapshot is disabled: ${await page.innerText("body")}`);
    }
    await snapshotButton.click();

    const txLink = page.getByRole("link", { name: /Transaction: 0x/i });
    await txLink.waitFor({ timeout: 60_000 });
    const txText = await txLink.innerText();
    txHash = txText.match(/0x[a-fA-F0-9]{64}/)?.[0];
    if (!txHash) {
      throw new Error(`Transaction hash missing from pending UI: ${txText}`);
    }

    fs.writeFileSync(
      CHECKPOINT,
      JSON.stringify({
        hash: txHash,
        before,
        burnerAddress,
        startedAt: Date.now(),
        productId: PRODUCT_ID,
      }),
    );
    await page
      .getByText(/Validators are fetching the product page and voting/i)
      .waitFor();
    await page.screenshot({
      path: path.join(OUT, "06-write-pending.png"),
      fullPage: true,
    });
  }

  await page
    .getByText("FINALIZED · SUCCESS", { exact: true })
    .waitFor({ timeout: 600_000 });
  await page.waitForFunction(
    (previous) => {
      const match = document.body.innerText.match(
        /Snapshots Recorded\s+(\d+)\s+Observations/i,
      );
      return match ? Number(match[1]) === previous + 1 : false;
    },
    before,
    { timeout: 60_000 },
  );

  const after = observationCount(await page.innerText("body"));
  await page.screenshot({
    path: path.join(OUT, "07-write-final.png"),
    fullPage: true,
  });
  if (fs.existsSync(CHECKPOINT)) {
    fs.unlinkSync(CHECKPOINT);
  }

  console.log("SaleProof corrected Studionet write verification");
  console.log(`Ledger: ${LEDGER_ADDRESS}`);
  console.log(`MerchantBond: ${BOND_ADDRESS}`);
  console.log(`Product: ${PRODUCT_ID}`);
  console.log(`Burner wallet: ${burnerAddress}`);
  console.log(`Snapshot transaction: ${txHash}`);
  console.log("Pending UI: transaction hash + validator consensus message");
  console.log("Final UI: FINALIZED · SUCCESS");
  console.log(`Observation count: ${before} -> ${after} without page reload`);
  console.log("WRITE CHECK: PASS");
} finally {
  await browser.close();
}
