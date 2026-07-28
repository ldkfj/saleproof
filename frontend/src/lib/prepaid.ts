import { FinalizedTransactionError } from "./tx";
import type { WriteRequest } from "./tx";

export type PrepaidStage =
  | "checking"
  | "deposit_submitting"
  | "deposit_pending"
  | "credit_ready"
  | "operation_submitting"
  | "operation_pending";

export interface PrepaidFlowRecord {
  version: 1;
  wallet: `0x${string}`;
  requiredWei: string;
  operation: WriteRequest;
  stage: PrepaidStage;
  hash?: `0x${string}`;
  startedAt: number;
}

interface PrepaidFlowHooks {
  readCredit: () => Promise<bigint>;
  submit: (
    request: WriteRequest,
    onHash: (hash: `0x${string}`) => void,
  ) => Promise<void>;
  wait: (hash: `0x${string}`) => Promise<void>;
  save: (record: PrepaidFlowRecord | null) => void;
  onRecord: (record: PrepaidFlowRecord) => void;
}

export class PrepaidOperationError extends Error {
  constructor(error: unknown) {
    const original = error instanceof Error ? error.message : String(error);
    super(
      `${original} Any credit deposited for this action remains withdrawable from MerchantBond.`,
      { cause: error },
    );
    this.name = "PrepaidOperationError";
  }
}

export class InterruptedPrepaidFlowError extends Error {
  constructor(stage: "deposit" | "operation", error?: unknown) {
    const original =
      error === undefined
        ? ""
        : `${error instanceof Error ? error.message : String(error)} `;
    super(
      `${original}${stage === "deposit" ? "Deposit" : "Action"} submission was interrupted before its transaction hash was saved. ` +
        "The app will not submit it again automatically. Check the wallet or Explorer before retrying.",
      error === undefined ? undefined : { cause: error },
    );
    this.name = "InterruptedPrepaidFlowError";
  }
}

export class PendingPrepaidFlowError extends Error {
  constructor(error: unknown) {
    const original = error instanceof Error ? error.message : String(error);
    super(
      `${original} The transaction outcome is still unknown; its saved hash was retained. ` +
        "Check Explorer or click the action again to resume waiting. Do not submit another transaction.",
      { cause: error },
    );
    this.name = "PendingPrepaidFlowError";
  }
}

export class FailedDepositCustodyError extends Error {
  constructor(error: unknown) {
    const original = error instanceof Error ? error.message : String(error);
    super(
      `${original} Deposit execution finalized with an error, but the native transfer may still have occurred while prepaid credit rolled back. ` +
        "That value may not be withdrawable. The saved deposit hash was retained; do not submit another deposit for this action.",
      { cause: error },
    );
    this.name = "FailedDepositCustodyError";
  }
}

export class UnconfirmedDepositCreditError extends Error {
  constructor() {
    super(
      "Deposit finalized successfully, but finalized withdrawable credit is still below the required amount. " +
        "The saved deposit hash was retained; do not submit another deposit for this action.",
    );
    this.name = "UnconfirmedDepositCreditError";
  }
}

export function creditDeficit(requiredWei: bigint, availableWei: bigint): bigint {
  if (requiredWei < 0n || availableWei < 0n) {
    throw new Error("Credit amounts cannot be negative.");
  }
  return requiredWei > availableWei ? requiredWei - availableWei : 0n;
}

export function createPrepaidFlow(
  wallet: `0x${string}`,
  requiredWei: bigint,
  operation: WriteRequest,
): PrepaidFlowRecord {
  if (requiredWei <= 0n) {
    throw new Error("The prepaid amount must be greater than zero.");
  }
  if ((operation.value ?? 0n) !== 0n) {
    throw new Error("The prepaid operation itself must be nonpayable.");
  }
  return {
    version: 1,
    wallet,
    requiredWei: requiredWei.toString(),
    operation: { ...operation, value: undefined },
    stage: "checking",
    startedAt: Date.now(),
  };
}

function jsonReplacer(_key: string, value: unknown): unknown {
  return typeof value === "bigint" ? { __saleproof_bigint__: value.toString() } : value;
}

function jsonReviver(_key: string, value: unknown): unknown {
  if (
    typeof value === "object" &&
    value !== null &&
    "__saleproof_bigint__" in value &&
    typeof (value as { __saleproof_bigint__: unknown }).__saleproof_bigint__ === "string"
  ) {
    const encoded = (value as { __saleproof_bigint__: string }).__saleproof_bigint__;
    if (/^\d+$/.test(encoded)) return BigInt(encoded);
  }
  return value;
}

export function serializePrepaidFlow(record: PrepaidFlowRecord): string {
  return JSON.stringify(record, jsonReplacer);
}

export function deserializePrepaidFlow(
  raw: string,
  expectedWallet: `0x${string}`,
  expectedOperationAddress: `0x${string}`,
): PrepaidFlowRecord | null {
  try {
    const parsed = JSON.parse(raw, jsonReviver) as Partial<PrepaidFlowRecord>;
    const stages: PrepaidStage[] = [
      "checking",
      "deposit_submitting",
      "deposit_pending",
      "credit_ready",
      "operation_submitting",
      "operation_pending",
    ];
    if (
      parsed.version !== 1 ||
      typeof parsed.wallet !== "string" ||
      parsed.wallet.toLowerCase() !== expectedWallet.toLowerCase() ||
      typeof parsed.requiredWei !== "string" ||
      !/^[1-9]\d*$/.test(parsed.requiredWei) ||
      !parsed.operation ||
      typeof parsed.operation.address !== "string" ||
      !/^0x[a-fA-F0-9]{40}$/.test(parsed.operation.address) ||
      parsed.operation.address.toLowerCase() !==
        expectedOperationAddress.toLowerCase() ||
      typeof parsed.operation.functionName !== "string" ||
      !stages.includes(parsed.stage as PrepaidStage) ||
      typeof parsed.startedAt !== "number" ||
      !Number.isFinite(parsed.startedAt)
    ) {
      return null;
    }
    if (
      (parsed.stage === "deposit_pending" || parsed.stage === "operation_pending") &&
      !parsed.hash?.match(/^0x[a-fA-F0-9]{64}$/)
    ) {
      return null;
    }
    if ((parsed.operation.value ?? 0n) !== 0n) return null;
    return parsed as PrepaidFlowRecord;
  } catch {
    return null;
  }
}

export async function runPrepaidFlow(
  initial: PrepaidFlowRecord,
  depositAddress: `0x${string}`,
  hooks: PrepaidFlowHooks,
): Promise<void> {
  let record = initial;
  const requiredWei = BigInt(record.requiredWei);
  if (record.operation.address.toLowerCase() !== depositAddress.toLowerCase()) {
    throw new Error("Saved prepaid action targets a different MerchantBond contract.");
  }

  const update = (
    stage: PrepaidStage,
    hash?: `0x${string}`,
  ): PrepaidFlowRecord => {
    record = { ...record, stage, hash };
    hooks.save(record);
    hooks.onRecord(record);
    return record;
  };

  hooks.onRecord(record);

  // Every start and resume re-reads finalized credit before deciding what to do.
  let availableWei = await hooks.readCredit();

  if (record.stage === "deposit_submitting") {
    if (creditDeficit(requiredWei, availableWei) > 0n) {
      throw new InterruptedPrepaidFlowError("deposit");
    }
    update("credit_ready");
  } else if (record.stage === "deposit_pending") {
    try {
      await hooks.wait(record.hash!);
    } catch (error) {
      if (error instanceof FinalizedTransactionError) {
        throw new FailedDepositCustodyError(error);
      }
      throw new PendingPrepaidFlowError(error);
    }
    availableWei = await hooks.readCredit();
    if (creditDeficit(requiredWei, availableWei) > 0n) {
      throw new UnconfirmedDepositCreditError();
    }
    update("credit_ready");
  } else if (record.stage === "operation_submitting") {
    throw new InterruptedPrepaidFlowError("operation");
  } else if (record.stage === "operation_pending") {
    try {
      await hooks.wait(record.hash!);
      hooks.save(null);
      return;
    } catch (error) {
      if (error instanceof FinalizedTransactionError) {
        hooks.save(null);
        throw new PrepaidOperationError(error);
      }
      throw new PendingPrepaidFlowError(error);
    }
  }

  let deficit = creditDeficit(requiredWei, availableWei);
  if (deficit > 0n) {
    update("deposit_submitting");
    let depositHashSaved = false;
    try {
      await hooks.submit(
        {
          address: depositAddress,
          functionName: "deposit",
          args: [],
          value: deficit,
        },
        (hash) => {
          depositHashSaved = true;
          update("deposit_pending", hash);
        },
      );
    } catch (error) {
      if (!depositHashSaved) {
        throw new InterruptedPrepaidFlowError("deposit", error);
      }
      if (error instanceof FinalizedTransactionError) {
        throw new FailedDepositCustodyError(error);
      }
      throw new PendingPrepaidFlowError(error);
    }
    availableWei = await hooks.readCredit();
    deficit = creditDeficit(requiredWei, availableWei);
    if (deficit > 0n) {
      throw new UnconfirmedDepositCreditError();
    }
    update("credit_ready");
  }

  update("operation_submitting");
  let operationHashSaved = false;
  try {
    await hooks.submit(record.operation, (hash) => {
      operationHashSaved = true;
      update("operation_pending", hash);
    });
    hooks.save(null);
  } catch (error) {
    if (!operationHashSaved) {
      throw new InterruptedPrepaidFlowError("operation", error);
    }
    if (error instanceof FinalizedTransactionError) {
      hooks.save(null);
      throw new PrepaidOperationError(error);
    }
    throw new PendingPrepaidFlowError(error);
  }
}
