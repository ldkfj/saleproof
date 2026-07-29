import { describe, expect, it, vi } from "vitest";

vi.mock("./chain", () => ({
  client: {},
  LEDGER_ADDRESS: "0x1111111111111111111111111111111111111111",
  BOND_ADDRESS: "0x2222222222222222222222222222222222222222",
}));

import { decodeObservation, decodeSale } from "./contracts";

describe("contract response decoding", () => {
  it("preserves the sale currency, frozen observation count, and claim id", () => {
    expect(
      decodeSale({
        id: 7n,
        merchant: "0x3333333333333333333333333333333333333333",
        product_id: 4n,
        claimed_ref_price_cents: 6_500n,
        claimed_discount_bp: 2_000n,
        currency: "GBP",
        announced_at: 1_710_000_000n,
        ends_at: 1_710_086_400n,
        observation_count_at_announcement: 73n,
        claim_id: 9n,
        active: true,
      }),
    ).toMatchObject({
      currency: "GBP",
      observation_count_at_announcement: 73,
      claim_id: 9,
    });
  });

  it("does not fabricate or coerce malformed observation fields", () => {
    const decoded = decodeObservation({
      price_cents: true,
      currency: null,
      observed_at: false,
      watcher: "0x4444444444444444444444444444444444444444",
      ok: 1,
      note: "",
    });

    expect(decoded).toMatchObject({
      currency: "",
      ok: false,
    });
    expect(Number.isNaN(decoded.price_cents)).toBe(true);
    expect(Number.isNaN(decoded.observed_at)).toBe(true);
  });
});
