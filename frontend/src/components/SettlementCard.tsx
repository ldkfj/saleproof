import React from "react";
import type { Claim, Merchant } from "../lib/contracts";
import { weiToGen } from "../lib/format";

export const SettlementCard: React.FC<{ claim: Claim; merchant?: Merchant | null }> = ({
  claim,
  merchant,
}) => {
  const depositWei = claim.deposit_wei;
  const bondWei = merchant ? merchant.bond_wei : 0n;

  let buyerPayout = 0n;
  let merchantPayout = 0n;
  let poolPayout = 0n;
  let bondSlash = 0n;
  let strikeIssued = false;

  if (claim.verdict === "GENUINE") {
    merchantPayout = depositWei / 2n;
    poolPayout = depositWei - merchantPayout;
  } else if (claim.verdict === "INFLATED_REFERENCE") {
    bondSlash = (bondWei * 500n) / 10000n; // 5%
    buyerPayout = depositWei + bondSlash;
    strikeIssued = true;
  } else if (claim.verdict === "DECEPTIVE") {
    bondSlash = (bondWei * 1000n) / 10000n; // 10%
    buyerPayout = depositWei + bondSlash;
    strikeIssued = true;
  } else if (claim.verdict === "INSUFFICIENT_EVIDENCE") {
    buyerPayout = depositWei;
  }

  return (
    <div className="card" style={{ background: "var(--bg-elevated)", border: "1px solid #374151" }}>
      <div className="card-header">
        <h3 className="card-title">
          <span>⚖️</span> Settlement Breakdown
        </h3>
        <span className={`badge state-${claim.state}`}>{claim.state}</span>
      </div>

      <div className="grid-2" style={{ gap: 12, marginBottom: 16 }}>
        <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Buyer Return / Compensation
          </div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: "#34d399" }}>
            {weiToGen(buyerPayout)}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-subtle)" }}>
            Deposit ({weiToGen(depositWei)}) {bondSlash > 0n ? `+ Slash (${weiToGen(bondSlash)})` : ""}
          </div>
        </div>

        <div style={{ background: "var(--bg-surface)", padding: 12, borderRadius: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Merchant Bond Impact
          </div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: bondSlash > 0n ? "#f87171" : "var(--text-main)" }}>
            {bondSlash > 0n ? `-${weiToGen(bondSlash)}` : "No Slash"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-subtle)" }}>
            Strike Penalty: {strikeIssued ? "⚠️ +1 Strike" : "None"}
          </div>
        </div>
      </div>

      {poolPayout > 0n && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
          Protocol Pool Fee: <strong className="mono">{weiToGen(poolPayout)}</strong>
        </div>
      )}

      {merchantPayout > 0n && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
          Merchant Deposit Share: <strong className="mono">{weiToGen(merchantPayout)}</strong>
        </div>
      )}

      <div
        style={{
          fontSize: 11,
          fontStyle: "italic",
          color: "var(--text-subtle)",
          borderTop: "1px stroke var(--border-color)",
          paddingTop: 8,
          marginTop: 8,
        }}
      >
        * Figures derived from contract settlement rules.
      </div>
    </div>
  );
};
