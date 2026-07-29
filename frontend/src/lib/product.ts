import type { WriteRequest } from "./tx";

const SNAPSHOT_REFRESH_ATTEMPTS = 8;
const SNAPSHOT_REFRESH_DELAY_MS = 3_000;

export function buildAddProductRequest(
  address: `0x${string}`,
  rawUrl: string,
): WriteRequest {
  const url = rawUrl.trim();
  if (!url) throw new Error("Enter a product URL.");
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    throw new Error("Product URL must start with http:// or https://.");
  }
  if (url.length > 500) throw new Error("Product URL is too long.");
  return {
    address,
    functionName: "add_product",
    args: [url],
  };
}

export async function refreshUntilObservationCount(
  loadObservationCount: () => Promise<number | null>,
  minimumObservationCount: number,
  pause: (milliseconds: number) => Promise<void> = (milliseconds) =>
    new Promise((resolve) => window.setTimeout(resolve, milliseconds)),
): Promise<boolean> {
  for (let attempt = 1; attempt <= SNAPSHOT_REFRESH_ATTEMPTS; attempt += 1) {
    const observationCount = await loadObservationCount();
    if (
      observationCount !== null &&
      observationCount >= minimumObservationCount
    ) {
      return true;
    }
    if (attempt < SNAPSHOT_REFRESH_ATTEMPTS) {
      await pause(SNAPSHOT_REFRESH_DELAY_MS);
    }
  }
  return false;
}
