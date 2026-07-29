import { describe, expect, it, vi } from "vitest";
import {
  buildAddProductRequest,
  refreshUntilObservationCount,
} from "./product";

const BOND = "0x1111111111111111111111111111111111111111";

describe("buildAddProductRequest", () => {
  it("builds a nonpayable add_product request for a valid URL", () => {
    const request = buildAddProductRequest(
      BOND,
      "  https://merchant.example/product  ",
    );

    expect(request).toEqual({
      address: BOND,
      functionName: "add_product",
      args: ["https://merchant.example/product"],
    });
    expect(request).not.toHaveProperty("value");
  });

  it("rejects an invalid URL before submission", () => {
    expect(() => buildAddProductRequest(BOND, "merchant.example/product")).toThrow(
      "http:// or https://",
    );
  });

  it("retries stale finalized reads until the appended observation is visible", async () => {
    const loadObservationCount = vi
      .fn<() => Promise<number | null>>()
      .mockResolvedValueOnce(4)
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce(5);
    const pause = vi.fn(async () => undefined);

    await expect(
      refreshUntilObservationCount(loadObservationCount, 5, pause),
    ).resolves.toBe(true);
    expect(loadObservationCount).toHaveBeenCalledTimes(3);
    expect(pause).toHaveBeenCalledTimes(2);
    expect(pause).toHaveBeenCalledWith(3_000);
  });

  it("stops after a bounded number of stale reads", async () => {
    const loadObservationCount = vi.fn(async () => 4);
    const pause = vi.fn(async () => undefined);

    await expect(
      refreshUntilObservationCount(loadObservationCount, 5, pause),
    ).resolves.toBe(false);
    expect(loadObservationCount).toHaveBeenCalledTimes(8);
    expect(pause).toHaveBeenCalledTimes(7);
  });
});
