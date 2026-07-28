import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useProtocolData } from "../lib/store";
import { bondContract } from "../lib/contracts";
import type { Merchant } from "../lib/contracts";
import { TableSkeleton } from "../components/Skeleton";
import { TxAction } from "../components/TxAction";
import { PrepaidTxAction } from "../components/PrepaidTxAction";
import { ActiveBadge, StateBadge, VerdictBadge } from "../components/Badge";
import { centsToPrice, shortAddr, timeAgo, weiToGen } from "../lib/format";
import { BOND_ADDRESS, GL_NETWORK_LABEL } from "../lib/chain";
import { genToWei } from "../lib/tx";
import { useWallet } from "../lib/wallet";

export const Overview: React.FC = () => {
  const { loading, error, products, observationsMap, sales, claims, config, refresh } =
    useProtocolData();
  const { address } = useWallet();
  const [walletMerchant, setWalletMerchant] = useState<Merchant | null>(null);
  const [withdrawable, setWithdrawable] = useState(0n);
  const [merchantName, setMerchantName] = useState("");
  const [bondInput, setBondInput] = useState("");
  const [topUpInput, setTopUpInput] = useState("0.1");

  const loadWalletState = useCallback(async () => {
    if (!address) {
      setWalletMerchant(null);
      setWithdrawable(0n);
      return;
    }
    const [merchant, pendingWithdrawal] = await Promise.all([
      bondContract.getMerchant(address).catch(() => null),
      bondContract.getWithdrawable(address).catch(() => ({ amount_wei: 0n })),
    ]);
    setWalletMerchant(merchant);
    setWithdrawable(pendingWithdrawal.amount_wei);
  }, [address]);

  useEffect(() => {
    void loadWalletState();
  }, [loadWalletState, sales, claims]);

  useEffect(() => {
    if (config && !bondInput) {
      setBondInput(weiToGen(config.min_bond_wei).replace(" GEN", ""));
    }
  }, [bondInput, config]);

  const refreshAfterWrite = async () => {
    await refresh();
    await loadWalletState();
  };

  if (error) {
    return (
      <div className="error-state">
        <div className="error-icon">⚠️</div>
        <h2 className="error-title">Unable to Load Protocol Data</h2>
        <p className="error-desc">{error}</p>
        <button onClick={() => refresh()} className="btn-primary">
          Retry Connection
        </button>
      </div>
    );
  }

  const getProductHost = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  };

  const getLatestObsPrice = (productId: number) => {
    const obs = observationsMap[productId] || [];
    const valid = obs.filter((o) => o.ok);
    if (valid.length === 0) return "No data";
    const last = valid[valid.length - 1];
    return centsToPrice(last.price_cents, last.currency);
  };

  const merchantSales = address
    ? sales.filter((sale) => sale.merchant.toLowerCase() === address.toLowerCase())
    : [];
  const openClaim = claims.some((claim) => {
    const sale = sales.find((candidate) => candidate.id === claim.sale_id);
    return (
      claim.state !== "SETTLED" &&
      Boolean(address) &&
      sale?.merchant.toLowerCase() === address?.toLowerCase()
    );
  });
  const activeSale = merchantSales.some(
    (sale) => sale.active && Math.floor(Date.now() / 1000) <= sale.ends_at,
  );
  const withdrawBondReason = openClaim
    ? "Open claims must be settled before withdrawing the bond."
    : activeSale
      ? "Active sales must end or be canceled before withdrawing the bond."
      : undefined;
  const registerBanned =
    Boolean(walletMerchant && config && walletMerchant.strikes >= config.strike_limit);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Protocol Dashboard</h1>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
          Real-time on-chain verification log, registered product evidence, and buyer dispute claims on{" "}
          {GL_NETWORK_LABEL}.
        </p>
      </div>

      {address && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Connected Wallet Actions</h2>
            <span className="mono" style={{ fontSize: 12 }}>
              {shortAddr(address)}
            </span>
          </div>

          {!walletMerchant || !walletMerchant.active ? (
            <div className="grid-3">
              <label>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Merchant name</span>
                <input
                  className="search-input"
                  value={merchantName}
                  maxLength={100}
                  onChange={(event) => setMerchantName(event.target.value)}
                  placeholder="Demo Shop"
                />
              </label>
              <label>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Bond in GEN (minimum {config ? weiToGen(config.min_bond_wei) : "loading…"})
                </span>
                <input
                  className="search-input"
                  value={bondInput}
                  inputMode="decimal"
                  onChange={(event) => setBondInput(event.target.value)}
                />
              </label>
              <PrepaidTxAction
                label={walletMerchant ? "Reactivate Merchant" : "Register Merchant"}
                requiredCredit={() => genToWei(bondInput)}
                persistenceKey="register-merchant"
                request={() => ({
                  address: BOND_ADDRESS as `0x${string}`,
                  functionName: "register_merchant",
                  args: [merchantName.trim(), genToWei(bondInput)],
                })}
                onSuccess={refreshAfterWrite}
                disabled={
                  registerBanned ||
                  !merchantName.trim() ||
                  !config ||
                  (() => {
                    try {
                      return genToWei(bondInput) < config.min_bond_wei;
                    } catch {
                      return true;
                    }
                  })()
                }
                disabledReason={
                  registerBanned
                    ? "This merchant reached the strike limit and is permanently banned."
                    : "Enter a name and at least the configured minimum bond."
                }
              />
            </div>
          ) : (
            <div className="grid-3">
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Active merchant
                </div>
                <strong>{walletMerchant.name}</strong>
                <div className="mono">{weiToGen(walletMerchant.bond_wei)}</div>
              </div>
              <label>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Top up bond (GEN)
                </span>
                <input
                  className="search-input"
                  value={topUpInput}
                  inputMode="decimal"
                  onChange={(event) => setTopUpInput(event.target.value)}
                />
              </label>
              <PrepaidTxAction
                label="Top Up Bond"
                requiredCredit={() => genToWei(topUpInput)}
                persistenceKey="top-up-bond"
                request={() => ({
                  address: BOND_ADDRESS as `0x${string}`,
                  functionName: "top_up_bond",
                  args: [genToWei(topUpInput)],
                })}
                onSuccess={refreshAfterWrite}
                disabled={(() => {
                  try {
                    return genToWei(topUpInput) === 0n;
                  } catch {
                    return true;
                  }
                })()}
                disabledReason="Enter a positive GEN amount."
              />
            </div>
          )}

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
              marginTop: 16,
              paddingTop: 16,
              borderTop: "1px solid var(--border-color)",
            }}
          >
            <TxAction
              label={`Withdraw ${weiToGen(withdrawable)}`}
              request={() => ({
                address: BOND_ADDRESS as `0x${string}`,
                functionName: "withdraw",
              })}
              onSuccess={refreshAfterWrite}
              disabled={withdrawable === 0n}
              disabledReason="No withdrawable balance is available."
              className="btn-search"
            />
            {walletMerchant?.active && (
              <TxAction
                label="Withdraw Merchant Bond"
                request={() => ({
                  address: BOND_ADDRESS as `0x${string}`,
                  functionName: "withdraw_bond",
                })}
                onSuccess={refreshAfterWrite}
                disabled={Boolean(withdrawBondReason)}
                disabledReason={withdrawBondReason}
                className="btn-search"
              />
            )}
          </div>
        </div>
      )}

      {/* Section 1: Registered Products */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>📦</span> Registered Products ({products.length})
          </h2>
        </div>

        {loading ? (
          <TableSkeleton rows={3} />
        ) : products.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Products Registered</div>
            <p className="empty-desc">Merchants register product URLs to track historical page evidence.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Host / URL</th>
                  <th>Merchant</th>
                  <th>Observations</th>
                  <th>Latest Price</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const obsCount = (observationsMap[p.id] || []).length;
                  const latestPrice = getLatestObsPrice(p.id);

                  return (
                    <tr key={p.id}>
                      <td className="mono">#{p.id}</td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{getProductHost(p.url)}</div>
                        <div className="mono" style={{ fontSize: 11, color: "var(--text-subtle)" }}>
                          {p.url.length > 40 ? p.url.slice(0, 40) + "..." : p.url}
                        </div>
                      </td>
                      <td className="mono">
                        <Link to={`/merchant/${p.merchant}`}>{shortAddr(p.merchant)}</Link>
                      </td>
                      <td className="mono">{obsCount} snapshots</td>
                      <td className="mono" style={{ fontWeight: 600, color: "#34d399" }}>
                        {latestPrice}
                      </td>
                      <td>
                        <ActiveBadge active={p.active} />
                      </td>
                      <td>
                        <Link to={`/product/${p.id}`} className="btn-search">
                          View Chart →
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

      {/* Section 2: Advertised Sales */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>🏷️</span> Active & Past Sales ({sales.length})
          </h2>
        </div>

        {loading ? (
          <TableSkeleton rows={2} />
        ) : sales.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Sales Announced</div>
            <p className="empty-desc">Merchants announce sales with claimed reference prices and discount basis points.</p>
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
                        {centsToPrice(s.claimed_ref_price_cents, "GBP")}
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

      {/* Section 3: Buyer Claims */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>⚖️</span> Dispute Claims ({claims.length})
          </h2>
        </div>

        {loading ? (
          <TableSkeleton rows={2} />
        ) : claims.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Claims Filed</div>
            <p className="empty-desc">Buyers file dispute claims when a sale advertises a deceptive reference price.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Sale ID</th>
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
                    <td>
                      <Link to={`/sale/${c.sale_id}`} className="mono">
                        Sale #{c.sale_id}
                      </Link>
                    </td>
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
                        View Verdict →
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
