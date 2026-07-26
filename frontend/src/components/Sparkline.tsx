import React from "react";
import type { Observation } from "../lib/contracts";

export const Sparkline: React.FC<{
  observations: Observation[];
  claimedRefPriceCents?: number;
}> = ({ observations, claimedRefPriceCents }) => {
  const validObs = observations.filter((o) => o.ok);
  if (validObs.length === 0) {
    return <span className="mono" style={{ color: "var(--text-muted)", fontSize: 11 }}>No history</span>;
  }

  const prices = validObs.map((o) => o.price_cents);
  if (claimedRefPriceCents) prices.push(claimedRefPriceCents);

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const width = 100;
  const height = 24;

  const points = validObs
    .map((o, idx) => {
      const x = (idx / Math.max(validObs.length - 1, 1)) * width;
      const y = height - ((o.price_cents - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  const refY = claimedRefPriceCents
    ? height - ((claimedRefPriceCents - min) / range) * (height - 4) - 2
    : null;

  return (
    <svg width={width} height={height} style={{ overflow: "visible" }} role="img" aria-label="Price trend sparkline">
      <polyline
        fill="none"
        stroke="#818cf8"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
      {refY !== null && (
        <g>
          <title>Claimed Ref Price</title>
          <line
            x1={0}
            y1={refY}
            x2={width}
            y2={refY}
            stroke="#f87171"
            strokeDasharray="2 2"
            strokeWidth="1"
          />
        </g>
      )}
    </svg>
  );
};
