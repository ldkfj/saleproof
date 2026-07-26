import React, { useState } from "react";
import type { Observation } from "../lib/contracts";
import { centsToPrice } from "../lib/format";

export const PriceChart: React.FC<{ observations: Observation[] }> = ({ observations }) => {
  const [activeObs, setActiveObs] = useState<Observation | null>(null);

  if (!observations || observations.length === 0) {
    return (
      <div
        style={{
          height: 200,
          background: "var(--bg-elevated)",
          borderRadius: "var(--radius-md)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
          fontFamily: "var(--font-mono)",
          fontSize: 13,
        }}
      >
        No price observations recorded yet for this product.
      </div>
    );
  }

  const width = 600;
  const height = 220;
  const padding = 40;

  const validObs = observations.filter((o) => o.ok);
  const prices = validObs.length > 0 ? validObs.map((o) => o.price_cents) : [1000];
  const minPrice = Math.min(...prices) * 0.9;
  const maxPrice = Math.max(...prices) * 1.1 || minPrice * 1.2;

  const currency = observations[0]?.currency || "USD";

  const getX = (index: number) => {
    if (observations.length <= 1) return padding + (width - 2 * padding) / 2;
    return padding + (index / (observations.length - 1)) * (width - 2 * padding);
  };

  const getY = (priceCents: number) => {
    if (maxPrice === minPrice) return height / 2;
    return height - padding - ((priceCents - minPrice) / (maxPrice - minPrice)) * (height - 2 * padding);
  };

  const points = observations
    .map((o, idx) => `${getX(idx)},${getY(o.ok ? o.price_cents : minPrice)}`)
    .join(" ");

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", overflow: "visible" }}
        role="img"
        aria-label={`Price history chart for product with ${observations.length} observations`}
      >
        <title>On-chain Price History Chart ({currency})</title>

        {[0, 0.5, 1].map((ratio, idx) => {
          const val = minPrice + ratio * (maxPrice - minPrice);
          const yPos = getY(val);
          return (
            <g key={idx}>
              <line
                x1={padding}
                y1={yPos}
                x2={width - padding}
                y2={yPos}
                stroke="var(--border-color)"
                strokeDasharray="4 4"
              />
              <text
                x={padding - 8}
                y={yPos + 4}
                fill="var(--text-muted)"
                fontSize="10"
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                {centsToPrice(val, currency)}
              </text>
            </g>
          );
        })}

        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="var(--border-color)"
        />

        {observations.length > 1 && (
          <polyline
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
          />
        )}

        {observations.map((o, idx) => {
          const cx = getX(idx);
          const cy = getY(o.ok ? o.price_cents : minPrice);

          return (
            <g key={idx}>
              <circle
                cx={cx}
                cy={cy}
                r={o.ok ? "5" : "4"}
                fill={o.ok ? "#818cf8" : "#4b5563"}
                stroke={o.ok ? "#4f46e5" : "#1f2937"}
                strokeWidth="2"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setActiveObs(o)}
                tabIndex={0}
                aria-label={`Observation ${idx + 1}: ${
                  o.ok ? centsToPrice(o.price_cents, o.currency) : "Dead URL (ok=false)"
                }`}
              />
              <text
                x={cx}
                y={height - padding + 16}
                fill="var(--text-subtle)"
                fontSize="9"
                fontFamily="var(--font-mono)"
                textAnchor="middle"
              >
                #{idx + 1}
              </text>
            </g>
          );
        })}
      </svg>

      {activeObs && (
        <div
          style={{
            marginTop: 8,
            padding: "8px 12px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <strong>Observation Status:</strong>{" "}
            <span style={{ color: activeObs.ok ? "#34d399" : "#f87171" }}>
              {activeObs.ok ? "OK" : "Dead Page / Unreadable"}
            </span>{" "}
            | Price: <strong>{centsToPrice(activeObs.price_cents, activeObs.currency)}</strong>
          </div>
          <div style={{ color: "var(--text-muted)" }}>
            Watcher: {activeObs.watcher.slice(0, 6)}...{activeObs.watcher.slice(-4)}
          </div>
        </div>
      )}
    </div>
  );
};
