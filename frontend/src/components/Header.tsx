import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useProtocolData } from "../lib/store";

export const Header: React.FC = () => {
  const { secondsAgo, refresh, loading } = useProtocolData();
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
