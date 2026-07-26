import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { bondContract } from "../lib/contracts";
import type { Claim, Merchant, Sale } from "../lib/contracts";
import { StateStepper } from "../components/StateStepper";
import { VerdictBadge } from "../components/Badge";
import { SettlementCard } from "../components/SettlementCard";
import { TxAction } from "../components/TxAction";
import { CardSkeleton } from "../components/Skeleton";
import { shortAddr, timeAgo, weiToGen } from "../lib/format";
import { BOND_ADDRESS } from "../lib/chain";
import { useWallet } from "../lib/wallet";
import { useProtocolData } from "../lib/store";

export const ClaimDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const claimId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [sale, setSale] = useState<Sale | null>(null);
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  const { address } = useWallet();
  const { config, refresh } = useProtocolData();

  const loadClaim = useCallback(async () => {
    if (!claimId || isNaN(claimId)) {
      setError("Invalid Claim ID.");
      setLoading(false);
      return;
    }

    setError(null);

    try {
      const nextClaim = await bondContract.getClaim(claimId);
      setClaim(nextClaim);

      const nextSale = await bondContract.getSale(nextClaim.sale_id).catch(() => null);
      setSale(nextSale);
      if (nextSale) {
        const nextMerchant = await bondContract.getMerchant(nextSale.merchant).catch(() => null);
        setMerchant(nextMerchant);
      }
    } catch (nextError) {
      console.error("Error fetching claim detail:", nextError);
      setError("Claim not found (ERR_NO_CLAIM).");
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    void loadClaim();
  }, [loadClaim]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <div>
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="error-state">
        <div className="error-icon">⚖️</div>
        <h2 className="error-title">Claim #{id} Not Found</h2>
        <p className="error-desc">No dispute claim exists with this ID on Studionet.</p>
        <Link to="/" className="btn-primary">
          Back to Overview
        </Link>
      </div>
    );
  }

  const confidencePct = (claim.confidence_bp / 100).toFixed(0);
  const appealDeadline =
    claim.judged_at > 0 && config ? claim.judged_at + config.appeal_window_s : 0;
  const appealRemaining = Math.max(0, appealDeadline - now);
  const appealWindowOpen = Boolean(appealDeadline && now <= appealDeadline);
  const isMerchantAppellant =
    Boolean(address && sale) &&
    sale?.merchant.toLowerCase() === address?.toLowerCase() &&
    ["INFLATED_REFERENCE", "DECEPTIVE"].includes(claim.verdict);
  const isBuyerAppellant =
    Boolean(address) &&
    claim.buyer.toLowerCase() === address?.toLowerCase() &&
    ["GENUINE", "INSUFFICIENT_EVIDENCE"].includes(claim.verdict);
  const mayAppeal = isMerchantAppellant || isBuyerAppellant;
  const refreshAfterWrite = async () => {
    await Promise.all([loadClaim(), refresh()]);
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/" style={{ fontSize: 13 }}>
          ← Back to Dashboard
        </Link>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>Dispute Claim #{claim.id}</h1>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
              Created {timeAgo(claim.created_at)}
              {claim.judged_at > 0 ? ` | Judged ${timeAgo(claim.judged_at)}` : ""}
            </div>
          </div>
          <Link to={`/sale/${claim.sale_id}`} className="mono" style={{ fontSize: 13 }}>
            Associated Sale #{claim.sale_id} →
          </Link>
        </div>

        <StateStepper currentState={claim.state} appellant={claim.appellant} />
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Claim Actions</h2>
        </div>
        <div className="grid-2">
          {claim.state === "OPEN" && (
            <TxAction
              label="Judge Claim"
              request={() => ({
                address: BOND_ADDRESS as `0x${string}`,
                functionName: "judge_claim",
                args: [claim.id],
              })}
              onSuccess={refreshAfterWrite}
              consensus
            />
          )}

          {claim.state === "JUDGED" && (
            <>
              <TxAction
                label={`Appeal · ${
                  config ? weiToGen(config.appeal_bond_wei) : "loading…"
                } · ${appealRemaining}s left`}
                request={() => ({
                  address: BOND_ADDRESS as `0x${string}`,
                  functionName: "appeal",
                  args: [claim.id],
                  value: config?.appeal_bond_wei ?? 0n,
                })}
                onSuccess={refreshAfterWrite}
                disabled={!config || !appealWindowOpen || !mayAppeal}
                disabledReason={
                  !appealWindowOpen
                    ? "The appeal window has closed."
                    : !mayAppeal
                      ? "Only the losing party may appeal: merchant for inflated/deceptive, buyer for genuine/insufficient evidence."
                      : !config
                        ? "Protocol configuration is still loading."
                        : undefined
                }
              />
              <TxAction
                label={
                  appealWindowOpen
                    ? `Finalize Unappealed · available in ${appealRemaining}s`
                    : "Finalize Unappealed"
                }
                request={() => ({
                  address: BOND_ADDRESS as `0x${string}`,
                  functionName: "finalize_unappealed",
                  args: [claim.id],
                })}
                onSuccess={refreshAfterWrite}
                disabled={appealWindowOpen}
                disabledReason={
                  appealWindowOpen
                    ? `Appeal window remains open for ${appealRemaining}s.`
                    : undefined
                }
                className="btn-search"
              />
            </>
          )}

          {claim.state === "APPEALED" && (
            <TxAction
              label="Judge Appeal"
              request={() => ({
                address: BOND_ADDRESS as `0x${string}`,
                functionName: "judge_appeal",
                args: [claim.id],
              })}
              onSuccess={refreshAfterWrite}
              consensus
            />
          )}

          {claim.state === "FINAL" && (
            <TxAction
              label="Settle Claim"
              request={() => ({
                address: BOND_ADDRESS as `0x${string}`,
                functionName: "settle",
                args: [claim.id],
              })}
              onSuccess={refreshAfterWrite}
            />
          )}
        </div>
      </div>

      <div className="card" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-color)" }}>
        <div className="card-header">
          <h2 className="card-title">
            <span>🤖</span> AI Consensus Verdict Showcase
          </h2>
          <VerdictBadge verdict={claim.verdict} />
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div style={{ background: "var(--bg-elevated)", padding: 14, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Consensus Verdict
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
              <VerdictBadge verdict={claim.verdict} />
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: 14, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Validator Confidence
            </div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: "#818cf8", marginTop: 4 }}>
              {confidencePct}% ({claim.confidence_bp} BP)
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
            On-Chain AI Reasoning Statement
          </div>
          <blockquote className={`reasoning-block ${!isReasoningExpanded && claim.reasoning.length > 180 ? "clamped" : ""}`}>
            "{claim.reasoning || "Pending judgment."}"
          </blockquote>

          {claim.reasoning.length > 180 && (
            <button
              className="btn-toggle-expand"
              onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
            >
              {isReasoningExpanded ? "▲ Show less" : "▼ Read full reasoning"}
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>📄</span> Claim Parameters
          </h2>
        </div>

        <div className="grid-3">
          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Buyer Address (Claimant)
            </span>
            <div className="mono" style={{ fontWeight: 600 }}>
              {shortAddr(claim.buyer)}
            </div>
          </div>

          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Anti-Spam Deposit
            </span>
            <div className="mono" style={{ fontWeight: 600, color: "#34d399" }}>
              {weiToGen(claim.deposit_wei)}
            </div>
          </div>

          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Appeal Bond
            </span>
            <div className="mono" style={{ fontWeight: 600 }}>
              {claim.appeal_bond_wei > 0n ? weiToGen(claim.appeal_bond_wei) : "None"}
            </div>
          </div>
        </div>
      </div>

      <SettlementCard claim={claim} merchant={merchant} />
    </div>
  );
};
