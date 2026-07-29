import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { bondContract } from "../lib/contracts";
import type { Merchant, Sale } from "../lib/contracts";
import { ActiveBadge, StrikePips } from "../components/Badge";
import { CardSkeleton, TableSkeleton } from "../components/Skeleton";
import { centsToPrice, timeAgo, weiToGen } from "../lib/format";
import { GL_NETWORK_LABEL } from "../lib/chain";

export const MerchantDetail: React.FC = () => {
  const { addr } = useParams<{ addr: string }>();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);

  useEffect(() => {
    if (!addr || !addr.startsWith("0x")) {
      setError("Invalid Merchant Address format.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    bondContract
      .getMerchant(addr)
      .then(async (m) => {
        setMerchant(m);

        const counts = await bondContract.getCounts().catch(() => ({ sale_count: 0 }));
        const salePromises: Promise<Sale | null>[] = [];
        for (let i = 1; i <= counts.sale_count; i++) {
          salePromises.push(bondContract.getSale(i).catch(() => null));
        }

        const allSales = await Promise.all(salePromises);
        const merchantSales = allSales.filter(
          (s): s is Sale => s !== null && s.merchant.toLowerCase() === addr.toLowerCase()
        );
        setSales(merchantSales);
      })
      .catch((err) => {
        console.error("Error fetching merchant detail:", err);
        setError("Merchant profile not found (ERR_NO_MERCHANT).");
      })
      .finally(() => setLoading(false));
  }, [addr]);

  if (loading) {
    return (
      <div>
        <CardSkeleton />
        <TableSkeleton rows={2} />
      </div>
    );
  }

  if (error || !merchant) {
    return (
      <div className="error-state">
        <div className="error-icon">🏪</div>
        <h2 className="error-title">Merchant Not Registered</h2>
        <p className="error-desc">
          Address <code className="mono">{addr}</code> is not registered as a bonded merchant on{" "}
          {GL_NETWORK_LABEL}.
        </p>
        <Link to="/" className="btn-primary">
          Back to Overview
        </Link>
      </div>
    );
  }

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
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>Merchant Profile</h1>
            <div className="mono" style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
              {merchant.addr}
            </div>
          </div>
          <ActiveBadge active={merchant.active} />
        </div>

        <div className="grid-3">
          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Registered Name
            </span>
            <div style={{ fontWeight: 600, fontSize: 16 }}>{merchant.name || "Unnamed Merchant"}</div>
          </div>

          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Staked Bond Balance
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

        <div style={{ marginTop: 16, fontSize: 12, color: "var(--text-subtle)" }}>
          Joined protocol: {timeAgo(merchant.joined_at)}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>🏷️</span> Sales Announced by {merchant.name} ({sales.length})
          </h2>
        </div>

        {sales.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Sales Announced</div>
            <p className="empty-desc">This merchant has not announced any active product promotions yet.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sale ID</th>
                  <th>Product</th>
                  <th>Claimed Ref Price</th>
                  <th>Discount</th>
                  <th>Ends</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((s) => {
                  const discountPct = (s.claimed_discount_bp / 100).toFixed(1);
                  return (
                    <tr key={s.id}>
                      <td className="mono">#{s.id}</td>
                      <td>
                        <Link to={`/product/${s.product_id}`} className="mono">
                          Product #{s.product_id}
                        </Link>
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        {centsToPrice(s.claimed_ref_price_cents, s.currency)}
                      </td>
                      <td className="mono" style={{ color: "#fbbf24", fontWeight: 700 }}>
                        -{discountPct}% ({s.claimed_discount_bp} BP)
                      </td>
                      <td className="mono">{timeAgo(s.ends_at)}</td>
                      <td>
                        <ActiveBadge active={s.active} />
                      </td>
                      <td>
                        <Link to={`/sale/${s.id}`} className="btn-search">
                          Inspect Sale →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
