import { describe, expect, it } from "vitest";
import { STUDIONET_FAUCET_AMOUNT_WEI } from "./wallet";

describe("Studionet burner funding", () => {
  it("requests exactly one GEN in wei", () => {
    expect(BigInt(STUDIONET_FAUCET_AMOUNT_WEI)).toBe(10n ** 18n);
  });
});
