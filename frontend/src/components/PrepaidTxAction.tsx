import React, { useCallback, useEffect, useRef, useState } from "react";
import { BOND_ADDRESS, GL_NETWORK } from "../lib/chain";
import { bondContract } from "../lib/contracts";
import {
  createPrepaidFlow,
  deserializePrepaidFlow,
  PrepaidOperationError,
  runPrepaidFlow,
  serializePrepaidFlow,
} from "../lib/prepaid";
import type { PrepaidFlowRecord, PrepaidStage } from "../lib/prepaid";
import {
  explorerTxUrl,
  FinalizedTransactionError,
  submitAndFinalize,
  waitForFinalizedSuccess,
} from "../lib/tx";
import type { WriteRequest } from "../lib/tx";
import { useWallet } from "../lib/wallet";

type UiPhase = "idle" | PrepaidStage | "success" | "error";

interface PrepaidTxActionProps {
  label: string;
  requiredCredit: () => bigint;
  request: () => WriteRequest;
  persistenceKey: string;
  onSuccess: () => Promise<void> | void;
  disabled?: boolean;
  disabledReason?: string;
  className?: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof FinalizedTransactionError) return error.message;
  return error instanceof Error ? error.message : String(error);
}

function phaseLabel(phase: UiPhase, label: string): string {
  if (phase === "checking") return "Checking credit…";
  if (phase === "deposit_submitting") return "Depositing…";
  if (phase === "deposit_pending") return "Deposit pending…";
  if (phase === "credit_ready") return "Credit ready…";
  if (phase === "operation_submitting") return "Submitting…";
  if (phase === "operation_pending") return "Pending…";
  return label;
}

export const PrepaidTxAction: React.FC<PrepaidTxActionProps> = ({
  label,
  requiredCredit,
  request,
  persistenceKey,
  onSuccess,
  disabled = false,
  disabledReason,
  className = "btn-primary",
}) => {
  const { client, address, refreshBalance } = useWallet();
  const [phase, setPhase] = useState<UiPhase>("idle");
  const [hash, setHash] = useState<`0x${string}` | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const running = useRef(false);
  const resumedStorageKey = useRef<string | null>(null);
  const storageKey = address
    ? `saleproof.prepaid.${GL_NETWORK}.${BOND_ADDRESS.toLowerCase()}.${persistenceKey}.${address.toLowerCase()}`
    : null;

  const persist = useCallback(
    (record: PrepaidFlowRecord | null) => {
      if (!storageKey) return;
      if (record) {
        sessionStorage.setItem(storageKey, serializePrepaidFlow(record));
      } else {
        sessionStorage.removeItem(storageKey);
      }
    },
    [storageKey],
  );

  const execute = useCallback(
    async (record: PrepaidFlowRecord) => {
      if (!client || !address || !storageKey || running.current) return;
      running.current = true;
      setError(null);
      setElapsed(0);
      try {
        await runPrepaidFlow(record, BOND_ADDRESS as `0x${string}`, {
          readCredit: async () => (await bondContract.getWithdrawable(address)).amount_wei,
          submit: async (nextRequest, onHash) => {
            await submitAndFinalize(client, nextRequest, onHash);
          },
          wait: async (nextHash) => {
            await waitForFinalizedSuccess(client, nextHash);
          },
          save: persist,
          onRecord: (nextRecord) => {
            setPhase(nextRecord.stage);
            setHash(nextRecord.hash ?? null);
            setStartedAt(nextRecord.startedAt);
          },
        });
      } catch (nextError) {
        if (nextError instanceof PrepaidOperationError) {
          await Promise.allSettled([
            Promise.resolve().then(() => onSuccess()),
            Promise.resolve().then(() => refreshBalance()),
          ]);
        }
        setError(errorMessage(nextError));
        setPhase("error");
        running.current = false;
        return;
      }

      setPhase("success");
      setHash(null);
      const refreshResults = await Promise.allSettled([
        Promise.resolve().then(() => onSuccess()),
        Promise.resolve().then(() => refreshBalance()),
      ]);
      const refreshFailure = refreshResults.find(
        (result): result is PromiseRejectedResult => result.status === "rejected",
      );
      if (refreshFailure) {
        setError(
          `The action finalized successfully, but the UI refresh failed: ${errorMessage(refreshFailure.reason)}`,
        );
      }
      running.current = false;
    },
    [address, client, onSuccess, persist, refreshBalance, storageKey],
  );

  useEffect(() => {
    const pending =
      phase === "checking" ||
      phase === "deposit_submitting" ||
      phase === "deposit_pending" ||
      phase === "credit_ready" ||
      phase === "operation_submitting" ||
      phase === "operation_pending";
    if (!pending) return;
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [phase, startedAt]);

  useEffect(() => {
    if (!address || !storageKey || resumedStorageKey.current === storageKey) return;
    resumedStorageKey.current = storageKey;
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) return;
    const stored = deserializePrepaidFlow(
      raw,
      address,
      BOND_ADDRESS as `0x${string}`,
    );
    if (!stored) {
      sessionStorage.removeItem(storageKey);
      return;
    }
    void execute(stored);
  }, [address, execute, storageKey]);

  const run = async () => {
    if (!client || !address || !storageKey || disabled || running.current) return;
    setHash(null);
    setError(null);
    setStartedAt(Date.now());
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (raw) {
        const stored = deserializePrepaidFlow(
          raw,
          address,
          BOND_ADDRESS as `0x${string}`,
        );
        if (stored) {
          await execute(stored);
          return;
        }
        sessionStorage.removeItem(storageKey);
      }
      const record = createPrepaidFlow(address, requiredCredit(), request());
      persist(record);
      await execute(record);
    } catch (nextError) {
      setError(errorMessage(nextError));
      setPhase("error");
    }
  };

  const pending =
    phase === "checking" ||
    phase === "deposit_submitting" ||
    phase === "deposit_pending" ||
    phase === "credit_ready" ||
    phase === "operation_submitting" ||
    phase === "operation_pending";
  const reason = !address ? "Connect a wallet first." : disabledReason;

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <button
        type="button"
        className={className}
        onClick={() => void run()}
        disabled={!address || disabled || pending}
        title={reason}
      >
        {phaseLabel(phase, label)}
      </button>

      {hash && (
        <a
          href={explorerTxUrl(hash)}
          target="_blank"
          rel="noreferrer"
          className="mono"
          style={{ fontSize: 11 }}
        >
          Transaction: {hash}
        </a>
      )}

      {pending && (
        <div role="status" style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {phase === "deposit_pending"
            ? `Deposit pending finalization… ${elapsed}s elapsed`
            : phase === "operation_pending"
              ? `Action pending finalization… ${elapsed}s elapsed`
              : "Preparing prepaid credit and action…"}
        </div>
      )}

      {phase === "success" && (
        <>
          <div role="status" style={{ fontSize: 12, color: "#34d399" }}>
            FINALIZED · SUCCESS
          </div>
          {error && (
            <div role="alert" style={{ fontSize: 12, color: "#fbbf24" }}>
              {error}
            </div>
          )}
        </>
      )}

      {phase === "error" && error && (
        <div role="alert" style={{ fontSize: 12, color: "#f87171" }}>
          {error}
        </div>
      )}

      {!address && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{reason}</div>}
      {address && disabled && disabledReason && (
        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{disabledReason}</div>
      )}
    </div>
  );
};
