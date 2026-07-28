import { createClient, chains } from "genlayer-js";
import { TransactionHashVariant } from "genlayer-js/types";

const NETWORK = process.env.VITE_GL_NETWORK ?? "studionet";
const LEDGER_ADDRESS = process.env.VITE_LEDGER_ADDRESS;
const BOND_ADDRESS = process.env.VITE_BOND_ADDRESS;

if (NETWORK !== "studionet") {
  throw new Error("verify-live.mjs verifies the reviewed Studionet release only.");
}

function requireAddress(name, value) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(value ?? "")) {
    throw new Error(`${name} must be set to a real corrected Studionet address.`);
  }
  return value;
}

const ledgerAddress = requireAddress("VITE_LEDGER_ADDRESS", LEDGER_ADDRESS);
const bondAddress = requireAddress("VITE_BOND_ADDRESS", BOND_ADDRESS);
const client = createClient({ chain: chains.studionet });

function asBigInt(value) {
  return typeof value === "bigint" ? value : BigInt(value);
}

function weiToGen(wei) {
  const value = asBigInt(wei);
  const scale = 10n ** 18n;
  const whole = value / scale;
  const remainder = value % scale;

  if (remainder === 0n) return `${whole} GEN`;

  const fraction = remainder.toString().padStart(18, "0").replace(/0+$/, "");
  return `${whole}.${fraction} GEN`;
}

function centsToPrice(cents, currency) {
  const symbols = { GBP: "£", USD: "$", EUR: "€", JPY: "¥", VND: "₫" };
  const value = asBigInt(cents);
  const symbol = symbols[currency] ?? `${currency} `;
  return `${symbol}${value / 100n}.${(value % 100n).toString().padStart(2, "0")}`;
}

function settledSlash(verdict, bondAfter) {
  if (verdict === "INFLATED_REFERENCE") {
    const preBond = (bondAfter * 10000n) / 9500n;
    return preBond - bondAfter;
  }
  if (verdict === "DECEPTIVE") {
    const preBond = (bondAfter * 10000n) / 9000n;
    return preBond - bondAfter;
  }
  return 0n;
}

function expect(label, actual, expected) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, received ${actual}`);
  }
}

const readLedger = (functionName, args) =>
  client.readContract({
    address: ledgerAddress,
    functionName,
    args,
    transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
  });
const readBond = (functionName, args) =>
  client.readContract({
    address: bondAddress,
    functionName,
    args,
    transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
  });

const [ledgerConfig, bondConfig, product, observations, sale, claim] =
  await Promise.all([
    readLedger("get_config", []),
    readBond("get_config", []),
    readLedger("get_product", [1]),
    readLedger("get_observations", [1]),
    readBond("get_sale", [1]),
    readBond("get_claim", [1]),
  ]);

expect(
  "Bond ledger link",
  String(bondConfig.ledger).toLowerCase(),
  ledgerAddress.toLowerCase(),
);
const registrar = await readLedger("is_registrar", [bondAddress]);
expect("Bond registrar authorization", Boolean(registrar), true);

const merchant = await readBond("get_merchant", [sale.merchant]);
const latestObservation = observations.at(-1);

if (!latestObservation) {
  throw new Error("Product 1 has no observations");
}

const productUrl = String(product.url);
const latestPrice = centsToPrice(
  latestObservation.price_cents,
  String(latestObservation.currency),
);
const merchantName = String(merchant.name);
const merchantBond = weiToGen(merchant.bond_wei);
const merchantStrikes = Number(merchant.strikes);
const saleReference = centsToPrice(sale.claimed_ref_price_cents, "GBP");
const saleDiscount = Number(sale.claimed_discount_bp);
const claimState = String(claim.state);
const claimVerdict = String(claim.verdict);
const claimConfidence = Number(claim.confidence_bp);
const claimDeposit = asBigInt(claim.deposit_wei);
const slash = settledSlash(claimVerdict, asBigInt(merchant.bond_wei));
const buyerTotal = claimDeposit + slash;

if (!productUrl.includes("books.toscrape.com/catalogue/a-light-in-the-attic")) {
  throw new Error(`Product 1 URL did not match the verified demo product: ${productUrl}`);
}
expect("Latest price", latestPrice, "£51.77");
expect("Merchant name", merchantName, "Demo Shop");
expect("Merchant bond", merchantBond, "1.9 GEN");
expect("Merchant strikes", merchantStrikes, 1);
expect("Sale reference", saleReference, "£65.00");
expect("Sale discount", saleDiscount, 2000);
expect("Claim state", claimState, "SETTLED");
expect("Claim verdict", claimVerdict, "INFLATED_REFERENCE");
expect("Claim confidence", claimConfidence, 10000);
expect("Claim deposit", weiToGen(claimDeposit), "0.1 GEN");
expect("Settlement slash", weiToGen(slash), "0.1 GEN");
expect("Buyer total", weiToGen(buyerTotal), "0.2 GEN");

console.log("SaleProof corrected Studionet UI verification");
console.log(`Ledger: ${ledgerAddress}`);
console.log(`MerchantBond: ${bondAddress}`);
console.log(`Snapshot cooldown: ${Number(ledgerConfig.snapshot_cooldown_s)} s`);
console.log(`Product 1 URL: ${productUrl}`);
console.log(`Latest price: ${latestPrice}`);
console.log(`Merchant name: ${merchantName}`);
console.log(`Merchant bond: ${merchantBond}`);
console.log(`Merchant strikes: ${merchantStrikes}`);
console.log(`Sale 1 reference: ${saleReference}`);
console.log(`Sale 1 discount: ${saleDiscount} bp`);
console.log(`Claim 1 state: ${claimState}`);
console.log(`Claim 1 verdict: ${claimVerdict}`);
console.log(`Claim 1 confidence: ${claimConfidence} bp`);
console.log(`Claim 1 deposit: ${weiToGen(claimDeposit)}`);
console.log(
  `Settlement: deposit ${weiToGen(claimDeposit)} + slash ${weiToGen(slash)} = ${weiToGen(buyerTotal)} buyer total`,
);
console.log("Verification: PASS");
