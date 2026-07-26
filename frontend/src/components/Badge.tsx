import React from "react";

export const ActiveBadge: React.FC<{ active: boolean }> = ({ active }) => {
  return (
    <span className={`badge ${active ? "badge-active" : "badge-inactive"}`}>
      {active ? "● ACTIVE" : "○ INACTIVE"}
    </span>
  );
};

export const StateBadge: React.FC<{ state: string }> = ({ state }) => {
  return <span className={`badge state-${state}`}>{state}</span>;
};

export const VerdictBadge: React.FC<{ verdict: string }> = ({ verdict }) => {
  if (!verdict) {
    return <span className="badge badge-inactive">UNJUDGED</span>;
  }

  let icon = "❓";
  let label = verdict;

  switch (verdict) {
    case "GENUINE":
      icon = "✓";
      label = "GENUINE";
      break;
    case "INFLATED_REFERENCE":
      icon = "⚠️";
      label = "INFLATED REF";
      break;
    case "DECEPTIVE":
      icon = "✖";
      label = "DECEPTIVE";
      break;
    case "INSUFFICIENT_EVIDENCE":
      icon = "ℹ";
      label = "INSUFFICIENT EVIDENCE";
      break;
  }

  return (
    <span className={`badge verdict-${verdict}`}>
      <span>{icon}</span> {label}
    </span>
  );
};

export const StrikePips: React.FC<{ strikes: number; limit?: number }> = ({
  strikes,
  limit = 3,
}) => {
  const pips = [];
  for (let i = 0; i < limit; i++) {
    pips.push(<span key={i} className={`pip ${i < strikes ? "filled" : ""}`} />);
  }

  return (
    <div className="strike-pips" title={`${strikes} / ${limit} strikes`}>
      {pips}
      <span className="mono" style={{ fontSize: 11, marginLeft: 4, color: "var(--text-muted)" }}>
        ({strikes}/{limit})
      </span>
    </div>
  );
};
