import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ledgerContract } from "../lib/contracts";
import type { Product, Observation } from "../lib/contracts";
import { PriceChart } from "../components/PriceChart";
import { ActiveBadge } from "../components/Badge";
import { CardSkeleton } from "../components/Skeleton";
import { centsToPrice, shortAddr, timeAgo } from "../lib/format";

export const ProductDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<Product | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);

  useEffect(() => {
    if (!productId || isNaN(productId)) {
      setError("Invalid Product ID.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      ledgerContract.getProduct(productId),
      ledgerContract.getObservations(productId),
    ])
      .then(([p, obs]) => {
        setProduct(p);
        setObservations(obs);
      })
      .catch((err) => {
        console.error("Error fetching product detail:", err);
        setError("Product not found (ERR_NO_PRODUCT).");
      })
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) {
    return (
      <div>
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="error-state">
        <div className="error-icon">🔍</div>
        <h2 className="error-title">Product #{id} Not Found</h2>
        <p className="error-desc">No registered product exists with this ID on Studionet.</p>
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
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>Product #{product.id} Evidence Log</h1>
            <div className="mono" style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
              {product.url}
            </div>
          </div>
          <ActiveBadge active={product.active} />
        </div>

        <div className="grid-3">
          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Merchant Address
            </span>
            <div className="mono" style={{ fontWeight: 600 }}>
              <Link to={`/merchant/${product.merchant}`}>{shortAddr(product.merchant)}</Link>
            </div>
          </div>

          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Registered On-Chain
            </span>
            <div className="mono" style={{ fontWeight: 600 }}>
              {timeAgo(product.registered_at)}
            </div>
          </div>

          <div>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Snapshots Recorded
            </span>
            <div className="mono" style={{ fontWeight: 600 }}>
              {observations.length} Observations
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>📈</span> Historical Price Trend (On-Chain Evidence)
          </h2>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            300s Cooldown Enforced
          </span>
        </div>

        <PriceChart observations={observations} />

        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "var(--bg-elevated)",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          ℹ️ <strong>Snapshot Rule:</strong> Anyone can trigger price snapshots for active products after a
          300-second cooldown. Failed page fetches (ok=false) are recorded as dead-page evidence.
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>📋</span> Full Observation History
          </h2>
        </div>

        {observations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Observations Triggered Yet</div>
            <p className="empty-desc">Watchers trigger snapshots to populate the on-chain evidence ledger.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Observed At</th>
                  <th>Observed Price</th>
                  <th>Status</th>
                  <th>Watcher Address</th>
                  <th>Note / Title</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((o, idx) => (
                  <tr key={idx} className={!o.ok ? "muted" : ""}>
                    <td className="mono">#{idx + 1}</td>
                    <td className="mono">{timeAgo(o.observed_at)}</td>
                    <td className="mono" style={{ fontWeight: 600, color: o.ok ? "#34d399" : "#f87171" }}>
                      {o.ok ? centsToPrice(o.price_cents, o.currency) : "UNREADABLE"}
                    </td>
                    <td>
                      <span className={`badge ${o.ok ? "badge-active" : "badge-inactive"}`}>
                        {o.ok ? "OK" : "DEAD PAGE"}
                      </span>
                    </td>
                    <td className="mono">{shortAddr(o.watcher)}</td>
                    <td style={{ fontSize: 12, color: "var(--text-muted)" }}>{o.note || "—"}</td>
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
