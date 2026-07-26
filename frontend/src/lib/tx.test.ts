import { describe, expect, it } from "vitest";
import { genToWei, isExecutionSuccess, transactionFailure } from "./tx";

describe("transaction helpers", () => {
  it("converts GEN decimal strings to wei without floating point", () => {
    expect(genToWei("0.1")).toBe(100000000000000000n);
    expect(genToWei("1.000000000000000001")).toBe(1000000000000000001n);
  });

  it("rejects more than 18 decimal places", () => {
    expect(() => genToWei("0.0000000000000000001")).toThrow("at most 18");
  });

  it("accepts a successful leader even when another validator receipt is idle", () => {
    expect(
      isExecutionSuccess({
        consensus_data: {
          final: true,
          leader_receipt: [
            { execution_result: "SUCCESS" },
            { execution_result: "ERROR", result: { payload: "idle" } },
          ] as never,
        },
      }),
    ).toBe(true);
  });

  it("extracts a contract error code and human message", () => {
    const failure = transactionFailure({
      consensus_data: {
        final: true,
        leader_receipt: [
          {
            execution_result: "ERROR",
            result: { status: "contract_error", payload: "Exception: ERR_COOLDOWN" },
          },
        ] as never,
      },
    });
    expect(failure.code).toBe("ERR_COOLDOWN");
    expect(failure.message).toContain("cooldown");
  });
});
