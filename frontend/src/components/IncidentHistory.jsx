
import {
  useEffect,
  useState,
} from "react";

import {
  Archive,
  CalendarClock,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";

import { api } from "../services/api";

import "./IncidentHistory.css";


function days(value) {
  return `${Number(value || 0).toFixed(2)} days`;
}


function formatDate(value) {
  if (!value) return "Unknown date";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}


export default function IncidentHistory({
  refreshToken = 0,
}) {
  const [incidents, setIncidents] =
    useState([]);

  const [incidentId, setIncidentId] =
    useState("");

  const [snapshots, setSnapshots] =
    useState([]);

  const [selectedSnapshot, setSelectedSnapshot] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  // Load confirmed incidents.
  useEffect(() => {
    let cancelled = false;

    async function loadIncidents() {
      try {
        const result = await api.getIncidents?.(
          "CONFIRMED"
        );

        // If api.getIncidents is unavailable,
        // retrieve incidents using the REST API.
        let data = result;

        if (!data) {
          const response = await fetch(
            "http://127.0.0.1:8000/api/incidents?status=CONFIRMED"
          );

          if (!response.ok) {
            throw new Error(
              "Could not load confirmed incidents"
            );
          }

          data = await response.json();
        }

        if (cancelled) return;

        const items =
          data?.incidents || [];

        setIncidents(items);

        setIncidentId((current) =>
          items.some(
            (item) =>
              item.incident_id === current
          )
            ? current
            : items[0]?.incident_id || ""
        );

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    loadIncidents();

    return () => {
      cancelled = true;
    };
  }, [refreshToken]);


  // Load snapshots for selected incident.
  useEffect(() => {
    let cancelled = false;

    async function loadSnapshots() {
      if (!incidentId) {
        setSnapshots([]);
        setSelectedSnapshot(null);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const result =
          await api.getHistory(incidentId);

        if (cancelled) return;

        setSnapshots(
          result?.snapshots || []
        );

        setSelectedSnapshot(null);

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSnapshots();

    return () => {
      cancelled = true;
    };
  }, [incidentId, refreshToken]);


  async function openSnapshot(snapshotId) {
    setLoading(true);
    setError("");

    try {
      const result =
        await api.getHistorySnapshot(
          snapshotId
        );

      setSelectedSnapshot(result);

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  const prediction =
    selectedSnapshot?.prediction;

  const delay =
    selectedSnapshot?.delay;

  const forecast =
    selectedSnapshot?.forecast;

  const predictionSummary =
    prediction?.summary || {};

  const delaySummary =
    delay?.summary || {};

  return (
    <section className="history-panel">
      <div className="history-heading">
        <div>
          <h2>
            <Archive size={20} />
            Incident Impact History
          </h2>

          <p>
            Review previously saved GraphSAGE
            simulations from Neo4j.
          </p>
        </div>

        <RefreshCw size={18} />
      </div>

      <div className="history-controls">
        <label htmlFor="history-incident">
          Confirmed incident
        </label>

        <select
          id="history-incident"
          value={incidentId}
          onChange={(event) =>
            setIncidentId(event.target.value)
          }
        >
          {incidents.length === 0 && (
            <option value="">
              No confirmed incidents
            </option>
          )}

          {incidents.map((incident) => (
            <option
              value={incident.incident_id}
              key={incident.incident_id}
            >
              {incident.title ||
                incident.incident_id}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="history-error">
          <AlertTriangle size={16} />
          {error}
        </p>
      )}

      {loading && (
        <p className="history-muted">
          Loading history...
        </p>
      )}

      {!loading &&
        incidentId &&
        snapshots.length === 0 && (
          <p className="history-muted">
            No saved simulation snapshots for
            this incident yet.
          </p>
        )}

      <div className="history-snapshot-list">
        {snapshots.map((snapshot) => (
          <button
            type="button"
            key={snapshot.snapshot_id}
            className={
              selectedSnapshot?.snapshot_id ===
              snapshot.snapshot_id
                ? "history-snapshot selected"
                : "history-snapshot"
            }
            onClick={() =>
              openSnapshot(
                snapshot.snapshot_id
              )
            }
          >
            <CalendarClock size={17} />

            <span>
              <strong>
                {formatDate(
                  snapshot.created_at
                )}
              </strong>

              <small>
                Initial disruption:{" "}
                {snapshot.initial_delay_days ??
                  "—"}{" "}
                days
              </small>
            </span>
          </button>
        ))}
      </div>

      {selectedSnapshot && (
        <div className="history-details">
          <h3>Saved Simulation Results</h3>

          <div className="history-stats">
            <div>
              <span>Affected entities</span>
              <strong>
                {predictionSummary.affected ?? 0}
              </strong>
            </div>

            <div>
              <span>Disrupted entities</span>
              <strong>
                {predictionSummary.disrupted ?? 0}
              </strong>
            </div>

            <div>
              <span>Average downstream delay</span>
              <strong>
                {days(
                  delaySummary
                    .mean_predicted_delay_days
                )}
              </strong>
            </div>

            <div>
              <span>Maximum downstream delay</span>
              <strong>
                {days(
                  delaySummary
                    .max_predicted_delay_days
                )}
              </strong>
            </div>
          </div>

          <h4>30 / 60 / 90-Day Scenarios</h4>

          {forecast?.horizons?.length ? (
            <div className="history-forecasts">
              {forecast.horizons.map(
                (horizon) => (
                  <div
                    key={horizon.horizon_days}
                  >
                    <span>
                      Day {horizon.horizon_days}
                    </span>

                    <strong>
                      {days(
                        horizon.summary
                          ?.mean_residual_delay_days
                      )}
                    </strong>

                    <small>
                      Average remaining delay
                    </small>
                  </div>
                )
              )}
            </div>
          ) : (
            <p className="history-muted">
              No forecast scenarios were
              stored with this snapshot.
            </p>
          )}

          <p className="history-disclaimer">
            Historical outputs represent
            synthetic simulation results
            recorded at the time shown.
            They are not verified real-world
            disruption outcomes.
          </p>
        </div>
      )}
    </section>
  );
}
    