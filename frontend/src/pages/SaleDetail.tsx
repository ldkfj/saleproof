import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { bondContract, ledgerContract } from "../lib/contracts";
import type { Sale, Observation, Merchant, Claim } from "../lib/contracts";
import { ActiveBadge, StrikePips, StateBadge, VerdictBadge } from "../components/Badge";
import { TxAction } from "../components/TxAction";
import { PrepaidTxAction } from "../components/PrepaidTxAction";
import { Sparkline } from "../components/Sparkline";
import { CardSkeleton } from "../components/Skeleton";
import { centsToPrice, shortAddr, timeAgo, weiToGen } from "../lib/format";
import { BOND_ADDRESS, GL_NETWORK_LABEL } from "../lib/chain";
import { useWallet } from "../lib/wallet";
import { useProtocolData } from "../lib/store";
import { getEligibleSaleEvidence } from "../lib/sale";

export const SaleDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const saleId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sale, setSale] = useState<Sale | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const { address } = useWallet();
  const { config, refresh } = useProtocolData();

  const loadSale = useCallback(async () => {
    if (!saleId || isNaN(saleId)) {
      setError("Invalid Sale ID.");
      setLoading(false);
      return;
    }

    setError(null);

    try {
      const nextSale = await bondContract.getSale(saleId);
      setSale(nextSale);

      const [nextObservations, nextMerchant, counts] = await Promise.all([
        ledgerContract.getObservations(nextSale.product_id).catch(() => []),
        bondContract.getMerchant(nextSale.merchant).catch(() => null),
        bondContract.getCounts().catch(() => ({ claim_count: 0 })),
      ]);

      setObservations(nextObservations);
      setMerchant(nextMerchant);

      const claimPromises: Promise<Claim | null>[] = [];
      for (let i = 1; i <= counts.claim_count; i++) {
        claimPromises.push(bondContract.getClaim(i).catch(() => null));
      }
      const allClaims = await Promise.all(claimPromises);
      setClaims(
        allClaims.filter(
          (candidate): candidate is Claim =>
            candidate !== null && candidate.sale_id === nextSale.id,
        ),
      );
    } catch (nextError) {
      console.error("Error fetching sale detail:", nextError);
      setError("Sale not found (ERR_NO_SALE).");
    } finally {
      setLoading(false);
    }
  }, [saleId]);

  useEffect(() => {
    void loadSale();
  }, [loadSale]);


  const refreshAfterWrite = async () => {
    await Promise.all([loadSale(), refresh()]);
  };

  if (loading) {
    return (
      <div>
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !sale) {
    return (
      <div className="error-state">
        <div className="error-icon">🏷️</div>
        <h2 className="error-title">Sale #{id} Not Found</h2>
        <p className="error-desc">
          No sale promotion exists with this ID on {GL_NETWORK_LABEL}.
        </p>
        <Link to="/" className="btn-primary">
          Back to Overview
        </Link>
      </div>
    );
  }

  const { eligibleObservations, chartObservations, lowestPriceCents } =
    getEligibleSaleEvidence(observations, sale);
  const thirtyDayLowCents = lowestPriceCents;
  const currency = sale.currency;
  const discountPct = (sale.claimed_discount_bp / 100).toFixed(1);

  const isRefPriceInflated =
    thirtyDayLowCents !== null && sale.claimed_ref_price_cents > thirtyDayLowCents;
  const isSaleMerchant =
    Boolean(address) && sale.merchant.toLowerCase() === address?.toLowerCase();
  const duplicateClaim =
    Boolean(address) &&
    claims.some((claim) => claim.buyer.toLowerCase() === address?.toLowerCase());
  const saleClosed = Math.floor(Date.now() / 1000) > sale.ends_at;
  const fileClaimReason = isSaleMerchant
    ? "Merchants cannot claim against their own sale."
    : !sale.active
      ? "This sale is inactive."
      : saleClosed
        ? "The sale claim window has closed."
        : duplicateClaim
          ? "This wallet already filed a claim for this sale."
          : !config
            ? "Protocol configuration is still loading."
            : undefined;

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
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>Sale Announcement #{sale.id}</h1>
            <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
              Announced {timeAgo(sale.announced_at)} | Ends {timeAgo(sale.ends_at)}
            </div>
          </div>
          <ActiveBadge active={sale.active} />
        </div>

        <div className="grid-3" style={{ marginBottom: 20 }}>
          <div style={{ background: "var(--bg-elevated)", padding: 14, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Claimed Reference Price
            </div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: "var(--text-main)" }}>
              {centsToPrice(sale.claimed_ref_price_cents, currency)}
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: 14, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Advertised Discount
            </div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: "#fbbf24" }}>
              -{discountPct}% ({sale.claimed_discount_bp} BP)
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: 14, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Eligible On-Chain 30-Day Low
            </div>
            <div
              className="mono"
              style={{
                fontSize: 20,
                fontWeight: 700,
                color: isRefPriceInflated ? "#f87171" : "#34d399",
              }}
            >
              {thirtyDayLowCents !== null ? centsToPrice(thirtyDayLowCents, currency) : "No History"}
            </div>
            {isRefPriceInflated && (
              <div style={{ fontSize: 11, color: "#f87171", marginTop: 2 }}>
                ⚠️ Claimed Ref Price &gt; Eligible Frozen Low
              </div>
            )}
          </div>
        </div>

        <div
          style={{
            background: "var(--bg-elevated)",
            padding: 16,
            borderRadius: 8,
            border: "1px solid var(--border-color)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>
              Price Evidence Sparkline vs Claimed Reference Price
            </span>
            <Sparkline
              observations={chartObservations}
              claimedRefPriceCents={sale.claimed_ref_price_cents}
            />
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Red dashed line indicates the merchant's claimed reference price. The purple sparkline shows the final {chartObservations.length} of {eligibleObservations.length} observations eligible under the sale's frozen prefix, exact {currency} currency, and inclusive 30-day announcement window.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Sale Actions</h2>
        </div>
        <div className="grid-2">
          <TxAction
            label="Cancel Sale"
            request={() => ({
              address: BOND_ADDRESS as `0x${string}`,
              functionName: "cancel_sale",
              args: [sale.id],
            })}
            onSuccess={refreshAfterWrite}
            disabled={!isSaleMerchant || !sale.active || claims.length > 0}
            disabledReason={
              !isSaleMerchant
                ? "Only the merchant who announced this sale may cancel it."
                : !sale.active
                  ? "This sale is already inactive."
                  : claims.length > 0
                    ? "A sale with claims cannot be canceled."
                    : undefined
            }
            className="btn-search"
          />
          <PrepaidTxAction
            label={`File Claim${config ? ` · ${weiToGen(config.claim_deposit_wei)}` : ""}`}
            requiredCredit={() => config?.claim_deposit_wei ?? 0n}
            persistenceKey={`file-claim-${sale.id}`}
            request={() => ({
              address: BOND_ADDRESS as `0x${string}`,
              functionName: "file_claim",
              args: [sale.id, config?.claim_deposit_wei ?? 0n],
            })}
            onSuccess={refreshAfterWrite}
            disabled={Boolean(fileClaimReason)}
            disabledReason={fileClaimReason}
          />
        </div>
      </div>

      {merchant && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <span>🏪</span> Merchant Staked Bond
            </h2>
            <ActiveBadge active={merchant.active} />
          </div>

          <div className="grid-3">
            <div>
              <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
                Merchant Name
              </span>
              <div style={{ fontWeight: 600, fontSize: 15 }}>{merchant.name}</div>
              <div className="mono" style={{ fontSize: 11, color: "var(--text-subtle)" }}>
                {shortAddr(merchant.addr)}
              </div>
            </div>

            <div>
              <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
                Staked Bond
              </span>
              <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: "#34d399" }}>
                {weiToGen(merchant.bond_wei)}
              </div>
            </div>

            <div>
              <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
                Strikes Accumulation
              </span>
              <StrikePips strikes={merchant.strikes} limit={3} />
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>⚖️</span> Claims Filed Against This Sale ({claims.length})
          </h2>
        </div>

        {claims.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Claims Filed Against This Sale</div>
            <p className="empty-desc">Buyers challenge sales when they believe the reference price was inflated.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Buyer</th>
                  <th>Deposit</th>
                  <th>State</th>
                  <th>Verdict</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((c) => (
                  <tr key={c.id}>
                    <td className="mono">#{c.id}</td>
                    <td className="mono">{shortAddr(c.buyer)}</td>
                    <td className="mono">{weiToGen(c.deposit_wei)}</td>
                    <td>
                      <StateBadge state={c.state} />
                    </td>
                    <td>
                      <VerdictBadge verdict={c.verdict} />
                    </td>
                    <td>
                      <Link to={`/claim/${c.id}`} className="btn-search">
                        Inspect Verdict →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
