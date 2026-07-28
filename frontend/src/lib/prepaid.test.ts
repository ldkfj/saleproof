import { describe, expect, it, vi } from "vitest";
import {
  createPrepaidFlow,
  creditDeficit,
  deserializePrepaidFlow,
  PrepaidOperationError,
  runPrepaidFlow,
  serializePrepaidFlow,
} from "./prepaid";
import type { PrepaidFlowRecord } from "./prepaid";
import { FinalizedTransactionError } from "./tx";
import type { WriteRequest } from "./tx";

const wallet = "0x1111111111111111111111111111111111111111";
const bond = "0x2222222222222222222222222222222222222222";
const operation: WriteRequest = {
  address: bond,
  functionName: "file_claim",
  args: [7, 100n],
};
const depositHash = `0x${"a".repeat(64)}` as `0x${string}`;
const operationHash = `0x${"b".repeat(64)}` as `0x${string}`;

describe("prepaid transaction flow", () => {
  it("computes only the missing finalized credit", () => {
    expect(creditDeficit(100n, 0n)).toBe(100n);
    expect(creditDeficit(100n, 40n)).toBe(60n);
    expect(creditDeficit(100n, 100n)).toBe(0n);
    expect(creditDeficit(100n, 140n)).toBe(0n);
  });

  it("persists bigint calldata and rejects a record for another wallet", () => {
    const record = createPrepaidFlow(wallet, 100n, operation);
    const encoded = serializePrepaidFlow(record);
    expect(deserializePrepaidFlow(encoded, wallet, bond)).toEqual(record);
    expect(
      deserializePrepaidFlow(
        encoded,
        "0x3333333333333333333333333333333333333333",
        bond,
      ),
    ).toBeNull();
    expect(
      deserializePrepaidFlow(
        encoded,
        wallet,
        "0x4444444444444444444444444444444444444444",
      ),
    ).toBeNull();
  });

  it("deposits only the deficit, waits for success, then submits the nonpayable action", async () => {
    let credit = 40n;
    const saved: Array<PrepaidFlowRecord | null> = [];
    const submitted: WriteRequest[] = [];
    await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
      readCredit: vi.fn(async () => credit),
      submit: vi.fn(async (request, onHash) => {
        submitted.push(request);
        if (request.functionName === "deposit") {
          onHash(depositHash);
          credit += request.value ?? 0n;
        } else {
          onHash(operationHash);
          credit -= 100n;
        }
      }),
      wait: vi.fn(),
      save: (record) => saved.push(record),
      onRecord: vi.fn(),
    });

    expect(submitted).toEqual([
      {
        address: bond,
        functionName: "deposit",
        args: [],
        value: 60n,
      },
      operation,
    ]);
    expect(saved.at(-1)).toBeNull();
  });

  it("resumes a finalized deposit by rereading credit and never deposits twice", async () => {
    const resumed: PrepaidFlowRecord = {
      ...createPrepaidFlow(wallet, 100n, operation),
      stage: "deposit_pending",
      hash: depositHash,
    };
    const submit = vi.fn(
      async (_request: WriteRequest, onHash: (hash: `0x${string}`) => void) => {
        onHash(operationHash);
      },
    );
    const readCredit = vi
      .fn<() => Promise<bigint>>()
      .mockResolvedValueOnce(40n)
      .mockResolvedValueOnce(100n);
    const wait = vi.fn(async () => undefined);

    await runPrepaidFlow(resumed, bond, {
      readCredit,
      submit,
      wait,
      save: vi.fn(),
      onRecord: vi.fn(),
    });

    expect(wait).toHaveBeenCalledWith(depositHash);
    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit.mock.calls[0]?.[0].functionName).toBe("file_claim");
  });

  it("does not blindly resubmit when reload interrupted deposit submission before hash", async () => {
    const interrupted: PrepaidFlowRecord = {
      ...createPrepaidFlow(wallet, 100n, operation),
      stage: "deposit_submitting",
    };
    const submit = vi.fn();
    await expect(
      runPrepaidFlow(interrupted, bond, {
        readCredit: vi.fn(async () => 40n),
        submit,
        wait: vi.fn(),
        save: vi.fn(),
        onRecord: vi.fn(),
      }),
    ).rejects.toThrow("will not submit it again automatically");
    expect(submit).not.toHaveBeenCalled();
  });

  it("preserves the phase-two ERR code and explains that credit remains withdrawable", async () => {
    const submit = vi.fn(
      async (_request: WriteRequest, onHash: (hash: `0x${string}`) => void) => {
        onHash(operationHash);
        throw new FinalizedTransactionError({
          code: "ERR_SALE_ALREADY_CLAIMED",
          message: "canonical claim exists",
          details: "Exception: ERR_SALE_ALREADY_CLAIMED",
        });
      },
    );

    await expect(
      runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 100n),
        submit,
        wait: vi.fn(),
        save: vi.fn(),
        onRecord: vi.fn(),
      }),
    ).rejects.toEqual(
      expect.objectContaining({
        name: PrepaidOperationError.name,
        message: expect.stringContaining("ERR_SALE_ALREADY_CLAIMED"),
      }),
    );

    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 100n),
        submit,
        wait: vi.fn(),
        save: vi.fn(),
        onRecord: vi.fn(),
      });
    } catch (error) {
      expect((error as Error).message).toContain("remains withdrawable");
    }
  });

  it("retains a post-hash unknown outcome for safe resume without claiming funds are free", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    const submit = vi.fn(
      async (_request: WriteRequest, onHash: (hash: `0x${string}`) => void) => {
        onHash(operationHash);
        throw new Error("RPC timeout");
      },
    );

    let caught: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 100n),
        submit,
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      caught = error as Error;
    }

    expect(caught?.message).toContain("saved hash was retained");
    expect(caught?.message).not.toContain("withdrawable");
    expect(saved.at(-1)).toEqual(
      expect.objectContaining({
        stage: "operation_pending",
        hash: operationHash,
      }),
    );
  });

  it("retains a timed-out deposit hash and never submits a second deposit on resume", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    let firstError: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 40n),
        submit: vi.fn(async (request, onHash) => {
          expect(request.functionName).toBe("deposit");
          onHash(depositHash);
          throw new Error("RPC timeout after hash");
        }),
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      firstError = error as Error;
    }

    const pendingDeposit = saved.at(-1);
    expect(firstError?.message).toContain("saved hash was retained");
    expect(firstError?.message).not.toContain("withdrawable");
    expect(pendingDeposit).toEqual(
      expect.objectContaining({
        stage: "deposit_pending",
        hash: depositHash,
      }),
    );

    const resumeSubmit = vi.fn();
    let resumeError: Error | null = null;
    try {
      await runPrepaidFlow(pendingDeposit!, bond, {
        readCredit: vi.fn(async () => 40n),
        submit: resumeSubmit,
        wait: vi.fn(async () => {
          throw new Error("RPC still unavailable");
        }),
        save: vi.fn(),
        onRecord: vi.fn(),
      });
    } catch (error) {
      resumeError = error as Error;
    }

    expect(resumeError?.message).toContain("saved hash was retained");
    expect(resumeSubmit).not.toHaveBeenCalled();
  });

  it("retains a no-hash deposit timeout and resume never submits blindly", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    let firstError: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 40n),
        submit: vi.fn(async () => {
          throw new Error("RPC timeout before deposit hash");
        }),
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      firstError = error as Error;
    }

    const interruptedDeposit = saved.at(-1);
    expect(firstError?.message).toContain("RPC timeout before deposit hash");
    expect(firstError?.message).toContain("will not submit it again automatically");
    expect(firstError?.message).not.toContain("withdrawable");
    expect(interruptedDeposit).toEqual(
      expect.objectContaining({ stage: "deposit_submitting", hash: undefined }),
    );

    const resumeSubmit = vi.fn();
    await expect(
      runPrepaidFlow(interruptedDeposit!, bond, {
        readCredit: vi.fn(async () => 40n),
        submit: resumeSubmit,
        wait: vi.fn(),
        save: vi.fn(),
        onRecord: vi.fn(),
      }),
    ).rejects.toThrow("will not submit it again automatically");
    expect(resumeSubmit).not.toHaveBeenCalled();
  });

  it("retains a no-hash operation timeout without a withdrawable claim or resubmit", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    let firstError: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 100n),
        submit: vi.fn(async () => {
          throw new Error("RPC timeout before operation hash");
        }),
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      firstError = error as Error;
    }

    const interruptedOperation = saved.at(-1);
    expect(firstError?.message).toContain("RPC timeout before operation hash");
    expect(firstError?.message).toContain("will not submit it again automatically");
    expect(firstError?.message).not.toContain("withdrawable");
    expect(interruptedOperation).toEqual(
      expect.objectContaining({ stage: "operation_submitting", hash: undefined }),
    );

    const resumeSubmit = vi.fn();
    let resumeError: Error | null = null;
    try {
      await runPrepaidFlow(interruptedOperation!, bond, {
        readCredit: vi.fn(async () => 100n),
        submit: resumeSubmit,
        wait: vi.fn(),
        save: vi.fn(),
        onRecord: vi.fn(),
      });
    } catch (error) {
      resumeError = error as Error;
    }
    expect(resumeError?.message).toContain("will not submit it again automatically");
    expect(resumeError?.message).not.toContain("withdrawable");
    expect(resumeSubmit).not.toHaveBeenCalled();
  });

  it("fails closed when a deposit finalizes with execution error and never redeposits", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    const finalizedFailure = new FinalizedTransactionError({
      code: "ERR_DEPOSIT_FAILED",
      message: "deposit execution failed",
      details: "Exception: ERR_DEPOSIT_FAILED",
    });
    let firstError: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 40n),
        submit: vi.fn(async (_request, onHash) => {
          onHash(depositHash);
          throw finalizedFailure;
        }),
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      firstError = error as Error;
    }

    const failedDeposit = saved.at(-1);
    expect(firstError?.message).toContain(
      "native transfer may still have occurred",
    );
    expect(firstError?.message).toContain("may not be withdrawable");
    expect(failedDeposit).toEqual(
      expect.objectContaining({
        stage: "deposit_pending",
        hash: depositHash,
      }),
    );

    const resumeSubmit = vi.fn();
    let resumeError: Error | null = null;
    try {
      await runPrepaidFlow(failedDeposit!, bond, {
        readCredit: vi.fn(async () => 40n),
        submit: resumeSubmit,
        wait: vi.fn(async () => {
          throw finalizedFailure;
        }),
        save: vi.fn(),
        onRecord: vi.fn(),
      });
    } catch (error) {
      resumeError = error as Error;
    }
    expect(resumeError?.message).toContain(
      "native transfer may still have occurred",
    );
    expect(resumeSubmit).not.toHaveBeenCalled();
  });

  it("keeps the deposit hash when success credit readback is short and never redeposits", async () => {
    const saved: Array<PrepaidFlowRecord | null> = [];
    let firstError: Error | null = null;
    try {
      await runPrepaidFlow(createPrepaidFlow(wallet, 100n, operation), bond, {
        readCredit: vi.fn(async () => 40n),
        submit: vi.fn(async (_request, onHash) => {
          onHash(depositHash);
        }),
        wait: vi.fn(),
        save: (record) => saved.push(record),
        onRecord: vi.fn(),
      });
    } catch (error) {
      firstError = error as Error;
    }

    const unconfirmedDeposit = saved.at(-1);
    expect(firstError?.message).toContain(
      "finalized withdrawable credit is still below",
    );
    expect(firstError?.message).toContain("do not submit another deposit");
    expect(unconfirmedDeposit).toEqual(
      expect.objectContaining({
        stage: "deposit_pending",
        hash: depositHash,
      }),
    );

    const resumeSubmit = vi.fn();
    let resumeError: Error | null = null;
    try {
      await runPrepaidFlow(unconfirmedDeposit!, bond, {
        readCredit: vi.fn(async () => 40n),
        submit: resumeSubmit,
        wait: vi.fn(async () => undefined),
        save: vi.fn(),
        onRecord: vi.fn(),
      });
    } catch (error) {
      resumeError = error as Error;
    }
    expect(resumeError?.message).toContain(
      "finalized withdrawable credit is still below",
    );
    expect(resumeSubmit).not.toHaveBeenCalled();
  });
});
