import { describe, expect, it } from "vitest";
import {
  STUDIONET_FAUCET_AMOUNT_WEI,
  studionetFaucetRequest,
} from "./wallet";

describe("Studionet burner funding", () => {
  it("builds the exact RPC request for one GEN in wei", () => {
    const address = "0x1111111111111111111111111111111111111111";
    expect(studionetFaucetRequest(address)).toEqual({
      method: "sim_fundAccount",
      params: [address, 1_000_000_000_000_000_000],
    });
    expect(BigInt(STUDIONET_FAUCET_AMOUNT_WEI)).toBe(10n ** 18n);
  });
});
