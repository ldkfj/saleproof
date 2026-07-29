import { describe, expect, it } from "vitest";
import type { Observation, Sale } from "./contracts";
import {
  buildAnnounceSaleArgs,
  getEligibleSaleEvidence,
  THIRTY_DAYS_S,
} from "./sale";

const ANNOUNCED_AT = 4_000_000;

function sale(overrides: Partial<Sale> = {}): Sale {
  return {
    id: 1,
    merchant: "0x1111111111111111111111111111111111111111",
    product_id: 1,
    claimed_ref_price_cents: 6_500,
    claimed_discount_bp: 2_000,
    currency: "GBP",
    announced_at: ANNOUNCED_AT,
    ends_at: ANNOUNCED_AT + 86_400,
    observation_count_at_announcement: 100,
    claim_id: 0,
    active: true,
    ...overrides,
  };
}

function observation(
  note: string,
  overrides: Partial<Observation> = {},
): Observation {
  return {
    price_cents: 5_177,
    currency: "GBP",
    observed_at: ANNOUNCED_AT - 60,
    watcher: "0x2222222222222222222222222222222222222222",
    ok: true,
    note,
    ...overrides,
  };
}

describe("sale contract alignment", () => {
  it("builds the exact five-argument announce_sale calldata", () => {
    expect(
      buildAnnounceSaleArgs({
        productId: 1,
        referencePrice: "65.00",
        discountPercent: "20",
        durationSeconds: 86_400,
        currency: "GBP",
      }),
    ).toEqual([1, 6_500, 2_000, 86_400, "GBP"]);
  });

  it("rejects unsupported currency and out-of-range inputs", () => {
    expect(() =>
      buildAnnounceSaleArgs({
        productId: 1,
        referencePrice: "65.00",
        discountPercent: "20",
        durationSeconds: 86_400,
        currency: "BTC",
      }),
    ).toThrow("supported currency");
    expect(() =>
      buildAnnounceSaleArgs({
        productId: 1,
        referencePrice: "65.00",
        discountPercent: "0.99",
        durationSeconds: 86_400,
        currency: "GBP",
      }),
    ).toThrow("between 1% and 95%");
  });

  it("uses only the frozen prefix, exact currency, valid window, and ok observations", () => {
    const observations = [
      observation("window-start", {
        observed_at: ANNOUNCED_AT - THIRTY_DAYS_S,
      }),
      observation("announcement", { observed_at: ANNOUNCED_AT }),
      observation("wrong-currency", { currency: "EUR" }),
      observation("too-old", {
        observed_at: ANNOUNCED_AT - THIRTY_DAYS_S - 1,
      }),
      observation("post-announcement", { observed_at: ANNOUNCED_AT + 1 }),
      observation("not-ok", { ok: false }),
      observation("zero-price", { price_cents: 0 }),
      observation("fractional-price", { price_cents: 51.77 }),
      observation("after-frozen-prefix", { price_cents: 1 }),
    ];

    const evidence = getEligibleSaleEvidence(
      observations,
      sale({ observation_count_at_announcement: 8 }),
    );

    expect(evidence.eligibleObservations.map((item) => item.note)).toEqual([
      "window-start",
      "announcement",
    ]);
    expect(evidence.lowestPriceCents).toBe(5_177);
  });

  it("computes the low from all eligible evidence while charting only the final 50", () => {
    const observations = Array.from({ length: 55 }, (_, index) =>
      observation(`eligible-${index}`, {
        price_cents: index === 0 ? 1_000 : 5_000 + index,
        observed_at: ANNOUNCED_AT - 55 + index,
      }),
    );

    const evidence = getEligibleSaleEvidence(
      observations,
      sale({ observation_count_at_announcement: observations.length }),
    );

    expect(evidence.eligibleObservations).toHaveLength(55);
    expect(evidence.chartObservations).toHaveLength(50);
    expect(evidence.chartObservations[0].note).toBe("eligible-5");
    expect(evidence.lowestPriceCents).toBe(1_000);
  });
});
