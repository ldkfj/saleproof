import React from "react";

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th><div className="skeleton" style={{ height: 14, width: 60 }} /></th>
            <th><div className="skeleton" style={{ height: 14, width: 120 }} /></th>
            <th><div className="skeleton" style={{ height: 14, width: 80 }} /></th>
            <th><div className="skeleton" style={{ height: 14, width: 70 }} /></th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i}>
              <td><div className="skeleton" style={{ height: 16, width: 40 }} /></td>
              <td><div className="skeleton" style={{ height: 16, width: 180 }} /></td>
              <td><div className="skeleton" style={{ height: 16, width: 90 }} /></td>
              <td><div className="skeleton" style={{ height: 16, width: 60 }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="card">
      <div className="skeleton" style={{ height: 24, width: 200, marginBottom: 16 }} />
      <div className="skeleton" style={{ height: 16, width: "100%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 16, width: "80%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 16, width: "60%" }} />
    </div>
  );
};
