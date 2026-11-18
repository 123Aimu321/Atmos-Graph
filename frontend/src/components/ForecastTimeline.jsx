
import { useMemo, useState } from "react";
import {
  CalendarDays,
  TrendingDown,
  AlertTriangle,
} from "lucide-react";

import "./ForecastTimeline.css";


const HORIZONS = [30, 60, 90];


export default function ForecastTimeline({
  forecast,
  loading = false,
  error = "",
}) {
  const [selectedHorizon, setSelectedHorizon] =
    useState(30);

  const snapshots = forecast?.horizons || [];

  const selectedSnapshot = snapshots.find(
    (item) =>
      item.horizon_days === selectedHorizon
  );

  const rankedEntities = useMemo(() => {
    return (
      selectedSnapshot?.entities || []
    )
      .filter(
        (item) =>
          item.is_downstream &&
          item.exposed_by_horizon
      )
      .sort(
        (a, b) =>
          b.residual_delay_days -
          a.residual_delay_days
      );
  }, [selectedSnapshot]);

  const maximum = Math.max(
    0,
    ...rankedEntities.map(
      (item) => item.residual_delay_days
    )
  );

  return (
    <div className="forecast-panel">
      <div className="forecast-header">
        <div>
          <h2>
            <CalendarDays size={20} />
            30 / 60 / 90-Day Forecast Scenarios
          </h2>

          <p>
            Explore modeled downstream exposure
            and remaining delays over time.
          </p>
        </div>
      </div>

      {loading && (
        <p className="forecast-muted">
          Calculating forecast scenarios...
        </p>
      )}

      {error && !loading && (
        <p className="forecast-error">
          <AlertTriangle size={16} />
          {error}
        </p>
      )}

      {!forecast && !loading && !error && (
        <p className="forecast-muted">
          Run a disruption simulation to view
          30, 60, and 90-day projections.
        </p>
      )}

      {forecast && !loading && (
        <>
          <div className="forecast-tabs">
            {HORIZONS.map((horizon) => (
              <button
                key={horizon}
                type="button"
                className={
                  selectedHorizon === horizon
                    ? "forecast-tab active"
                    : "forecast-tab"
                }
                onClick={() =>
                  setSelectedHorizon(horizon)
                }
              >
                {horizon} Days
              </button>
            ))}
          </div>

          <div className="forecast-overview">
            {snapshots.map((snapshot) => {
              const summary = snapshot.summary;

              return (
                <button
                  type="button"
                  key={snapshot.horizon_days}
                  className={[
                    "forecast-overview-card",
                    selectedHorizon ===
                    snapshot.horizon_days
                      ? "selected"
                      : "",
                  ].join(" ")}
                  onClick={() =>
                    setSelectedHorizon(
                      snapshot.horizon_days
                    )
                  }
                >
                  <span>
                    Day {snapshot.horizon_days}
                  </span>

                  <strong>
                    {Number(
                      summary
                        .mean_residual_delay_days
                    ).toFixed(2)}{" "}
                    days
                  </strong>

                  <small>
                    Average remaining delay
                  </small>
                </button>
              );
            })}
          </div>

          {selectedSnapshot && (
            <>
              <div className="forecast-summary">
                <div>
                  <span>Exposed downstream</span>
                  <strong>
                    {
                      selectedSnapshot.summary
                        .exposed_downstream_entities
                    }
                  </strong>
                </div>

                <div>
                  <span>Maximum remaining delay</span>
                  <strong>
                    {Number(
                      selectedSnapshot.summary
                        .max_residual_delay_days
                    ).toFixed(2)}{" "}
                    days
                  </strong>
                </div>

                <div>
                  <span>Recovery assumption</span>
                  <strong>
                    {forecast.recovery_half_life_days}{" "}
                    days
                  </strong>
                </div>
              </div>

              <div className="forecast-ranking-title">
                <h3>
                  <TrendingDown size={17} />
                  Remaining Delays — Day{" "}
                  {selectedHorizon}
                </h3>
              </div>

              <div className="forecast-entity-list">
                {rankedEntities.length === 0 ? (
                  <p className="forecast-muted">
                    No downstream entities are
                    modeled as exposed by this
                    horizon.
                  </p>
                ) : (
                  rankedEntities.map((item) => {
                    const value = Number(
                      item.residual_delay_days
                    );

                    const width =
                      maximum > 0
                        ? (value / maximum) * 100
                        : 0;

                    return (
                      <div
                        key={item.node_id}
                        className="forecast-entity"
                      >
                        <div className="forecast-entity-label">
                          <span>{item.node_id}</span>
                          <strong>
                            {value.toFixed(2)} days
                          </strong>
                        </div>

                        <div className="forecast-track">
                          <div
                            className="forecast-fill"
                            style={{
                              width: `${width}%`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}

          <p className="forecast-disclaimer">
            {forecast.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}
