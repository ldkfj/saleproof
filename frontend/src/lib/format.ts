/**
 * Format utilities for SaleProof protocol values.
 */

const CURRENCY_SYMBOLS: Record<string, string> = {
  GBP: "£",
  USD: "$",
  EUR: "€",
  JPY: "¥",
  VND: "₫",
};

/**
 * Converts wei (bigint/string/number) to a GEN formatted string with up to 4 decimals using pure BigInt math.
 * Avoids any parseFloat / number precision loss.
 */
export function weiToGen(wei: bigint | string | number): string {
  const w = BigInt(wei);
  const negative = w < 0n;
  const absW = negative ? -w : w;
  const scale = 10n ** 18n;
  const integerPart = absW / scale;
  const remainder = absW % scale;

  if (remainder === 0n) {
    return `${negative ? "-" : ""}${integerPart.toString()} GEN`;
  }

  const fractionScale = 10n ** 14n; // 10^18 / 10^4
  let fraction = (remainder / fractionScale).toString().padStart(4, "0");
  fraction = fraction.replace(/0+$/, "");

  return `${negative ? "-" : ""}${integerPart.toString()}.${fraction} GEN`;
}

/**
 * Formats price in cents to currency string (e.g. 5177 cents in GBP -> "£51.77").
 */
export function centsToPrice(cents: number | bigint, currency: string = "USD"): string {
  const c = Number(cents);
  const symbol = CURRENCY_SYMBOLS[currency.toUpperCase()] || `${currency} `;
  const formatted = (c / 100).toFixed(2);
  return `${symbol}${formatted}`;
}

/**
 * Truncates Ethereum / GenLayer hex address (e.g. 0x7885...2339).
 */
export function shortAddr(addr: string): string {
  if (!addr) return "";
  if (addr.length <= 10) return addr;
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

/**
 * Relative or absolute time formatting for Unix epoch timestamps in seconds.
 */
export function timeAgo(timestampSec: number | bigint): string {
  const nowSec = Math.floor(Date.now() / 1000);
  const diff = nowSec - Number(timestampSec);

  if (diff < 0) {
    const futureDiff = -diff;
    if (futureDiff < 60) return `in ${futureDiff}s`;
    if (futureDiff < 3600) return `in ${Math.floor(futureDiff / 60)}m`;
    if (futureDiff < 86400) return `in ${Math.floor(futureDiff / 3600)}h`;
    return `in ${Math.floor(futureDiff / 86400)}d`;
  }

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  const date = new Date(Number(timestampSec) * 1000);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Custom JSON replacer function to convert BigInt values to string representations.
 */
export function jsonReplacer(_key: string, value: any): any {
  if (typeof value === "bigint") {
    return value.toString();
  }
  return value;
}
