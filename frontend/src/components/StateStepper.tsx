import React from "react";

const STATES = ["OPEN", "JUDGED", "APPEALED", "FINAL", "SETTLED"];

export const StateStepper: React.FC<{ currentState: string }> = ({ currentState }) => {
  const currentIndex = STATES.indexOf(currentState);

  return (
    <div className="stepper" aria-label="Claim State Machine Progress">
      {STATES.map((state, idx) => {
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
