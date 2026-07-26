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
          VITE_LEDGER_ADDRESS=0x26aA8E0af993665e02A14408f75221e1951926C1
          <br />
          VITE_BOND_ADDRESS=0xDa121e6fF503eC2F13101df37Cf05aD38E93544F
        </div>
      </div>
    </div>
  );
};
