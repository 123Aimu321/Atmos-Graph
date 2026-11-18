
import { useMemo } from "react";
import {
  Clock3,
  TrendingUp,
  AlertTriangle,
  Truck,
} from "lucide-react";

import "./DelayImpact.css";

function DelayStat({ title, value, icon: Icon }) {
  return (
    <div className="delay-stat">
      <div className="delay-stat-heading">
        <span>{title}</span>
        <Icon size={18} />
      </div>

      <strong>{value}</strong>
    </div>
  );
}

export default function DelayImpact({
  delay,
  loading = false,
  error = "",
}) {
  const downstream = useMemo(() => {
    return (delay?.results || [])
      .filter((item) => item.is_downstream)
      .sort(
        (a, b) =>
          b.predicted_delay_days -
          a.predicted_delay_days
      );
  }, [delay]);

  const maximum = Math.max(
    0,
    ...downstream.map(
      (item) => item.predicted_delay_days
    )
  );

  if (loading) {
    return (
      <div className="delay-panel">
        <h2>Predicted Delivery Delays</h2>
        <p className="delay-muted">
          Running GraphSAGE delay regression...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="delay-panel">
        <h2>Predicted Delivery Delays</h2>
        <p className="delay-error">
          <AlertTriangle size={16} />
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="delay-panel">
      <div className="delay-panel-header">
        <div>
          <h2>
            <Clock3 size={20} />
            Predicted Delivery Delays
          </h2>

          <p>
            GraphSAGE regression estimates for
            downstream supply-chain entities.
          </p>
        </div>

        {delay && (
          <span className="delay-model-tag">
            GraphSAGE Regression
          </span>
        )}
      </div>

      {!delay ? (
        <p className="delay-muted">
          Select a disruption source and run
          a simulation to view estimated delays.
        </p>
      ) : (
        <>
          <div className="delay-stats-grid">
            <DelayStat
              title="Average Downstream Delay"
              value={`${Number(
                delay.summary
                  ?.mean_predicted_delay_days || 0
              ).toFixed(2)} days`}
              icon={Clock3}
            />

            <DelayStat
              title="Maximum Downstream Delay"
              value={`${Number(
                delay.summary
                  ?.max_predicted_delay_days || 0
              ).toFixed(2)} days`}
              icon={TrendingUp}
            />

            <DelayStat
              title="Downstream Entities"
              value={
                delay.summary
                  ?.downstream_entities ?? 0
              }
              icon={Truck}
            />
          </div>

          <div className="delay-chart-heading">
            <h3>Downstream Delay Ranking</h3>
            <span>Estimated days</span>
          </div>

          <div className="delay-bars">
            {downstream.length === 0 ? (
              <p className="delay-muted">
                No downstream entities found.
              </p>
            ) : (
              downstream.map((item) => {
                const value = Number(
                  item.predicted_delay_days || 0
                );

                const percentage =
                  maximum > 0
                    ? (value / maximum) * 100
                    : 0;

                return (
                  <div
                    className="delay-bar-row"
                    key={item.node_id}
                  >
                    <div className="delay-bar-label">
                      <strong>{item.node_id}</strong>
                      <span>
                        {value.toFixed(2)} days
                      </span>
                    </div>

                    <div className="delay-bar-track">
                      <div
                        className="delay-bar-fill"
                        style={{
                          width: `${percentage}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <p className="delay-disclaimer">
            Experimental predictions trained on
            synthetic delay-propagation targets.
            These are not verified real-world
            delivery forecasts.
          </p>
        </>
      )}
    </div>
  );
}
