import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { bondContract, ledgerContract } from "../lib/contracts";
import type { Sale, Observation, Merchant, Claim } from "../lib/contracts";
import { ActiveBadge, StrikePips, StateBadge, VerdictBadge } from "../components/Badge";
import { Sparkline } from "../components/Sparkline";
import { CardSkeleton } from "../components/Skeleton";
import { centsToPrice, shortAddr, timeAgo, weiToGen } from "../lib/format";

export const SaleDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const saleId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sale, setSale] = useState<Sale | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);

  useEffect(() => {
    if (!saleId || isNaN(saleId)) {
      setError("Invalid Sale ID.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    bondContract
      .getSale(saleId)
      .then(async (s) => {
        setSale(s);

        const [obs, m, counts] = await Promise.all([
          ledgerContract.getObservations(s.product_id).catch(() => []),
          bondContract.getMerchant(s.merchant).catch(() => null),
          bondContract.getCounts().catch(() => ({ claim_count: 0 })),
        ]);

        setObservations(obs);
        setMerchant(m);

        const claimPromises: Promise<Claim | null>[] = [];
        for (let i = 1; i <= counts.claim_count; i++) {
          claimPromises.push(bondContract.getClaim(i).catch(() => null));
        }
        const allClaims = await Promise.all(claimPromises);
        const saleClaims = allClaims.filter((c): c is Claim => c !== null && c.sale_id === s.id);
        setClaims(saleClaims);
      })
      .catch((err) => {
        console.error("Error fetching sale detail:", err);
        setError("Sale not found (ERR_NO_SALE).");
      })
      .finally(() => setLoading(false));
  }, [saleId]);

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
        <p className="error-desc">No sale promotion exists with this ID on Studionet.</p>
        <Link to="/" className="btn-primary">
          Back to Overview
        </Link>
      </div>
    );
  }

  const validObsPrices = observations.filter((o) => o.ok).map((o) => o.price_cents);
  const thirtyDayLowCents = validObsPrices.length > 0 ? Math.min(...validObsPrices) : null;
  const currency = observations[0]?.currency || "GBP";
  const discountPct = (sale.claimed_discount_bp / 100).toFixed(1);

  const isRefPriceInflated =
    thirtyDayLowCents !== null && sale.claimed_ref_price_cents > thirtyDayLowCents;

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
              On-Chain 30-Day Low
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
                ⚠️ Claimed Ref Price &gt; Observed Low
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
            <Sparkline observations={observations} claimedRefPriceCents={sale.claimed_ref_price_cents} />
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Red dashed line indicates the merchant's claimed reference price. The purple sparkline tracks actual on-chain snapshot evidence.
          </p>
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
