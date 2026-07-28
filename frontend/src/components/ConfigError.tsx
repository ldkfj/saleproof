import React from "react";

export const ConfigError: React.FC = () => {
  return (
    <div className="app-container" style={{ justifyContent: "center", alignItems: "center" }}>
      <div className="error-state" style={{ maxWidth: 540 }}>
        <div className="error-icon">⚠️</div>
        <h2 className="error-title">Environment Configuration Error</h2>
        <p className="error-desc">
          Missing valid contract addresses in <code>frontend/.env</code>. Both{" "}
          <code>VITE_LEDGER_ADDRESS</code> and <code>VITE_BOND_ADDRESS</code> must be configured
          with valid 0x-prefixed hex contract addresses.
        </p>
        <div
          style={{
            background: "var(--bg-elevated)",
            padding: 12,
            borderRadius: 6,
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            textAlign: "left",
            margin: "16px 0",
          }}
        >
          VITE_GL_NETWORK=studionet
          <br />
          VITE_LEDGER_ADDRESS=&lt;corrected deployment address&gt;
          <br />
          VITE_BOND_ADDRESS=&lt;corrected deployment address&gt;
        </div>
      </div>
    </div>
  );
};
