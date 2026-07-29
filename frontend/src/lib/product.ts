import type { WriteRequest } from "./tx";

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
