import React, { useEffect, useState } from "react";
import type { WriteRequest } from "../lib/tx";
import {
  EXPLORER_TX_URL,
  FinalizedTransactionError,
  submitAndFinalize,
} from "../lib/tx";
import { useWallet } from "../lib/wallet";

type TxPhase = "idle" | "submitting" | "pending" | "success" | "error";

interface TxActionProps {
  label: string;
  request: () => WriteRequest;
  onSuccess: () => Promise<void> | void;
  disabled?: boolean;
  disabledReason?: string;
  consensus?: boolean;
  className?: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof FinalizedTransactionError) return error.message;
  return error instanceof Error ? error.message : String(error);
}

export const TxAction: React.FC<TxActionProps> = ({
  label,
  request,
  onSuccess,
  disabled = false,
  disabledReason,
  consensus = false,
  className = "btn-primary",
}) => {
  const { client, address, refreshBalance } = useWallet();
  const [phase, setPhase] = useState<TxPhase>("idle");
  const [hash, setHash] = useState<`0x${string}` | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (phase !== "pending") return;
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [phase, startedAt]);

  const pending = phase === "submitting" || phase === "pending";
  const reason = !address ? "Connect a wallet first." : disabledReason;

  const run = async () => {
    if (!client || !address || disabled || pending) return;
    setPhase("submitting");
    setHash(null);
    setError(null);
    setElapsed(0);
    setStartedAt(Date.now());
    try {
      await submitAndFinalize(client, request(), (nextHash) => {
        setHash(nextHash);
        setPhase("pending");
      });
      setPhase("success");
      await Promise.all([onSuccess(), refreshBalance()]);
    } catch (nextError) {
      setError(errorMessage(nextError));
      setPhase("error");
    }
  };

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <button
        type="button"
        className={className}
        onClick={() => void run()}
        disabled={!address || disabled || pending}
        title={reason}
      >
        {phase === "submitting" ? "Submitting…" : phase === "pending" ? "Pending…" : label}
      </button>

      {hash && (
        <a
          href={`${EXPLORER_TX_URL}/${hash}`}
          target="_blank"
          rel="noreferrer"
          className="mono"
          style={{ fontSize: 11 }}
        >
          Transaction: {hash}
        </a>
      )}

      {phase === "pending" && (
        <div role="status" style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {consensus
            ? `Validators are fetching the product page and voting… ${elapsed}s elapsed`
            : `Transaction pending finalization… ${elapsed}s elapsed`}
        </div>
      )}

      {phase === "success" && (
        <div role="status" style={{ fontSize: 12, color: "#34d399" }}>
          FINALIZED · SUCCESS
        </div>
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
