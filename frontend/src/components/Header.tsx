import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useProtocolData } from "../lib/store";
import { useWallet } from "../lib/wallet";
import { shortAddr, weiToGen } from "../lib/format";

export const Header: React.FC = () => {
  const { secondsAgo, refresh, loading } = useProtocolData();
  const {
    address,
    balance,
    providerKind,
    connecting,
    funding,
    error: walletError,
    connectInjected,
    connectBurner,
    disconnect,
    fundBurner,
  } = useWallet();
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;

    if (q.startsWith("0x") && q.length === 42) {
      navigate(`/merchant/${q}`);
    } else if (!isNaN(Number(q))) {
      navigate(`/product/${q}`);
    } else {
      navigate(`/merchant/${q}`);
    }
  };

  return (
    <header className="app-header">
      <div className="header-brand">
        <Link to="/" className="brand-title">
          <span>🛡️ SALEPROOF</span>
          <span className="brand-tag">Studionet</span>
        </Link>
      </div>

      <nav className="header-nav" aria-label="Main Navigation">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} end>
          Overview
        </NavLink>
      </nav>

      <div className="header-actions">
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {address ? (
            <>
              <div
                className="status-indicator"
                title={providerKind === "burner" ? "Dev wallet — Studionet only" : "Injected EIP-1193 wallet"}
              >
                <span>{providerKind === "burner" ? "Dev wallet — Studionet only" : "Wallet"}</span>
                <strong className="mono">{shortAddr(address)}</strong>
                <span className="mono">{balance === null ? "…" : weiToGen(balance)}</span>
              </div>
              {providerKind === "burner" && (
                <button className="btn-search" onClick={() => void fundBurner()} disabled={funding}>
                  {funding ? "Funding…" : "Fund 1 GEN"}
                </button>
              )}
              <button className="btn-search" onClick={disconnect}>
                Disconnect
              </button>
            </>
          ) : (
            <>
              <button
                className="btn-search"
                onClick={() => void connectInjected()}
                disabled={connecting}
              >
                Connect MetaMask
              </button>
              <button
                className="btn-search"
                onClick={() => void connectBurner()}
                disabled={connecting}
              >
                Dev wallet — Studionet only
              </button>
            </>
          )}
          {walletError && (
            <span style={{ color: "#f87171", fontSize: 11 }} title={walletError}>
              Wallet error
            </span>
          )}
        </div>

        <form onSubmit={handleSearch} className="search-box" aria-label="Search form">
          <input
            type="text"
            className="search-input"
            placeholder="Search address (0x...) or Product ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search merchant address or product ID"
          />
          <button type="submit" className="btn-search" aria-label="Search">
            🔍
          </button>
        </form>

        <div className="status-indicator" title="Connected to GenLayer Studionet">
          <span className="status-dot" />
          <span>Updated {secondsAgo}s ago</span>
          <button
            onClick={() => refresh()}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              marginLeft: 4,
              color: "var(--text-muted)",
            }}
            title="Refresh data"
            disabled={loading}
          >
            {loading ? "⌛" : "🔄"}
          </button>
        </div>
      </div>
    </header>
  );
};
