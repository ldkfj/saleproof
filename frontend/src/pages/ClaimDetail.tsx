import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { bondContract } from "../lib/contracts";
import type { Claim, Merchant } from "../lib/contracts";
import { StateStepper } from "../components/StateStepper";
import { VerdictBadge } from "../components/Badge";
import { SettlementCard } from "../components/SettlementCard";
import { CardSkeleton } from "../components/Skeleton";
import { shortAddr, timeAgo, weiToGen } from "../lib/format";

export const ClaimDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const claimId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);

  useEffect(() => {
    if (!claimId || isNaN(claimId)) {
      setError("Invalid Claim ID.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    bondContract
      .getClaim(claimId)
      .then(async (c) => {
        setClaim(c);

        const s = await bondContract.getSale(c.sale_id).catch(() => null);

        if (s) {
          const m = await bondContract.getMerchant(s.merchant).catch(() => null);
          setMerchant(m);
        }
      })
      .catch((err) => {
        console.error("Error fetching claim detail:", err);
        setError("Claim not found (ERR_NO_CLAIM).");
      })
      .finally(() => setLoading(false));
  }, [claimId]);

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

        <StateStepper currentState={claim.state} />
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
