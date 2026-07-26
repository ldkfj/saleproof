import React from "react";

const STATES = ["OPEN", "JUDGED", "APPEALED", "FINAL", "SETTLED"];
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";

export const StateStepper: React.FC<{ currentState: string; appellant?: string }> = ({
  currentState,
  appellant,
}) => {
  const appealed =
    currentState === "APPEALED" ||
    Boolean(appellant && appellant.toLowerCase() !== ZERO_ADDRESS);
  const visibleStates = appealed ? STATES : STATES.filter((state) => state !== "APPEALED");
  const currentIndex = visibleStates.indexOf(currentState);

  return (
    <div className="stepper" aria-label="Claim State Machine Progress">
      {visibleStates.map((state, idx) => {
        const isCompleted = idx < currentIndex;
        const isActive = idx === currentIndex;

        return (
          <div
            key={state}
            className={`step-item ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
          >
            <div className="step-circle">{isCompleted ? "✓" : idx + 1}</div>
            <span className="step-label">{state}</span>
          </div>
        );
      })}
    </div>
  );
};
