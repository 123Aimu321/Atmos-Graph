
import {
  AlertTriangle,
  ShieldAlert,
  TrendingUp,
  GitBranch,
} from "lucide-react";

const RISK_COLORS = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

function getRecommendations(risk) {
  const recommendations = [];

  if (risk.reachable_downstream > 0) {
    recommendations.push(
      "Review alternative supply routes for downstream entities."
    );
  }

  if (risk.predicted_affected > 0) {
    recommendations.push(
      "Prioritize monitoring of affected warehouses and retailers."
    );
  }

  if (risk.event_severity === "HIGH" ||
      risk.event_severity === "CRITICAL") {
    recommendations.push(
      "Escalate the incident to the supply-chain operations team."
    );
  }

  if (risk.risk_level === "CRITICAL") {
    recommendations.push(
      "Evaluate contingency inventory and alternate suppliers."
    );
  }

  if (recommendations.length === 0) {
    recommendations.push(
      "Continue monitoring the supply-chain network."
    );
  }

  return recommendations;
}

export default function RiskAssessment({ risk, loading }) {
  if (loading) {
    return (
      <div className="risk-empty">
        Calculating risk assessment...
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="risk-empty">
        Run a disruption simulation to calculate
        the supply-chain risk score.
      </div>
    );
  }

  const color =
    RISK_COLORS[risk.risk_level] || "#64748b";

  const score = Math.max(
    0,
    Math.min(100, Number(risk.risk_score) || 0)
  );

  const components = risk.score_components || {};
  const recommendations = getRecommendations(risk);

  return (
    <div className="risk-assessment">
      <div className="risk-header">
        <div>
          <h2>Supply Chain Risk Assessment</h2>
          <p>Experimental weighted risk index</p>
        </div>

        <span
          className="risk-level-badge"
          style={{
            color,
            borderColor: color,
          }}
        >
          {risk.risk_level} RISK
        </span>
      </div>

      <div className="risk-score-section">
        <div
          className="risk-score-circle"
          style={{ borderColor: color }}
        >
          <strong>{score.toFixed(1)}</strong>
          <span>/ 100</span>
        </div>

        <div className="risk-score-details">
          <h3>Overall Risk Score</h3>

          <p>
            Disruption: {risk.disruption_type}
          </p>

          <p>
            Event severity: {risk.event_severity}
          </p>

          <div className="risk-progress-track">
            <div
              className="risk-progress-fill"
              style={{
                width: `${score}%`,
                backgroundColor: color,
              }}
            />
          </div>
        </div>
      </div>

      <div className="risk-breakdown">
        <div>
          <TrendingUp size={19} color="#38bdf8" />
          <span>Prediction Exposure</span>
          <strong>
            {components.prediction_exposure ?? 0}%
          </strong>
        </div>

        <div>
          <GitBranch size={19} color="#a78bfa" />
          <span>Graph Reachability</span>
          <strong>
            {components.graph_reachability ?? 0}%
          </strong>
        </div>

        <div>
          <AlertTriangle size={19} color="#f59e0b" />
          <span>Event Severity Weight</span>
          <strong>
            {components.event_severity_weight ?? 0}%
          </strong>
        </div>
      </div>

      <div className="risk-recommendations">
        <h3>
          <ShieldAlert size={19} />
          Suggested Mitigation Actions
        </h3>

        <ul>
          {recommendations.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </div>

      <p className="risk-disclaimer">
        {risk.disclaimer}
      </p>
    </div>
  );
}
