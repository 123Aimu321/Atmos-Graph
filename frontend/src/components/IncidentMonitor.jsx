
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Filter,
  Newspaper,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import "./IncidentMonitor.css";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const STATUS_OPTIONS = [
  { value: "PENDING", label: "Pending" },
  { value: "CONFIRMED", label: "Confirmed" },
  { value: "REJECTED", label: "Rejected" },
  { value: "ALL", label: "All incidents" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "relevance", label: "Highest relevance" },
  { value: "lowest", label: "Lowest relevance" },
];

async function apiRequest(path, options = {}) {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    }
  );

  const raw = await response.text();

  let data = {};

  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error(
        `Invalid server response (${response.status})`
      );
    }
  }

  if (!response.ok) {
    const detail = data?.detail;

    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status})`
    );
  }

  return data;
}

function toTimestamp(value) {
  if (!value) return 0;

  // Neo4j datetime fields generally reach the
  // frontend as ISO 8601 strings.
  const valueToParse =
    typeof value === "string"
      ? value
      : value?.toString?.() || "";

  const timestamp = Date.parse(valueToParse);

  return Number.isFinite(timestamp)
    ? timestamp
    : 0;
}

function formatDate(value) {
  const timestamp = toTimestamp(value);

  if (!timestamp) {
    return "Date unavailable";
  }

  return new Date(timestamp).toLocaleString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}

function getIncidentTimestamp(incident) {
  return (
    toTimestamp(incident.created_at) ||
    toTimestamp(incident.published) ||
    toTimestamp(incident.updated_at) ||
    0
  );
}

function getRelevance(incident) {
  const value = Number(incident.relevance_score);

  if (
    incident.relevance_score == null ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  return Math.max(0, Math.min(100, value));
}

function StatusBadge({ status }) {
  const normalized = String(
    status || "PENDING"
  ).toUpperCase();

  return (
    <span
      className={`im-status im-status-${normalized.toLowerCase()}`}
    >
      {normalized === "CONFIRMED" ? (
        <CheckCircle2 size={13} />
      ) : normalized === "REJECTED" ? (
        <XCircle size={13} />
      ) : (
        <Clock3 size={13} />
      )}

      {normalized}
    </span>
  );
}

function RelevanceScore({ score }) {
  if (score == null) {
    return (
      <span className="im-score im-score-unknown">
        Not scored
      </span>
    );
  }

  const level =
    score >= 80
      ? "high"
      : score >= 55
        ? "medium"
        : "low";

  return (
    <span className={`im-score im-score-${level}`}>
      Relevance {score}/100
    </span>
  );
}

function IncidentCard({
  incident,
  entities,
  selectedEntity,
  onEntityChange,
  onConfirm,
  onReject,
  busy,
}) {
  const incidentId = incident.incident_id;

  const status = String(
    incident.status || "PENDING"
  ).toUpperCase();

  const isPending = status === "PENDING";

  const score = getRelevance(incident);

  const suggestion =
    incident.exact_match_entity_id ||
    incident.suggested_entity_id ||
    incident.matched_entity?.node_id ||
    "";

  const suggestedEntity = entities.find(
    (item) => item.node_id === suggestion
  );

  const matchMethod =
    incident.entity_match_method ||
    (suggestion ? "LEGACY_SUGGESTION" : "NONE");

  const evidence = Array.isArray(
    incident.relevance_reasons
  )
    ? incident.relevance_reasons
    : [];

  const isUnverifiedSuggestion =
    suggestion && matchMethod !== "EXACT_NAME";

  const sourceUrl = String(
    incident.source_url || ""
  );

  const hasSafeLink = /^https?:\/\//i.test(
    sourceUrl
  );

  const displayDate =
    incident.published ||
    incident.created_at;

  return (
    <article className="im-card">
      <div className="im-card-heading">
        <div className="im-card-title-group">
          <h3>
            {incident.title ||
              "Untitled disruption incident"}
          </h3>

          <div className="im-tags">
            <StatusBadge status={status} />

            <RelevanceScore score={score} />

            <span className="im-tag">
              {incident.disruption_type ||
                "UNKNOWN"}
            </span>

            {matchMethod === "EXACT_NAME" && (
              <span className="im-match-tag">
                Exact-name match
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="im-metadata">
        <span>
          <Clock3 size={13} />
          {formatDate(displayDate)}
        </span>

        {hasSafeLink && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Read original article
            <ExternalLink size={13} />
          </a>
        )}
      </div>

      {evidence.length > 0 && (
        <details className="im-evidence">
          <summary>
            Why this article was selected
          </summary>

          <ul>
            {evidence.map((reason, index) => (
              <li key={`${incidentId}-${index}`}>
                {reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="im-entity-information">
        <span className="im-subtitle">
          Suggested graph entity
        </span>

        {suggestion ? (
          <strong>
            {suggestedEntity?.node_name ||
              suggestion}
            {" "}
            ({suggestion})
          </strong>
        ) : (
          <span className="im-muted">
            No reliable entity suggestion
          </span>
        )}

        {isUnverifiedSuggestion && (
          <p className="im-muted">
            This is a legacy or unverified
            suggestion. Review it manually.
          </p>
        )}

        {incident.confirmed_entity_id && (
          <p className="im-confirmed-entity">
            Confirmed entity:{" "}
            <strong>
              {incident.confirmed_entity_id}
            </strong>
          </p>
        )}
      </div>

      {isPending && (
        <div className="im-review-area">
          <label
            htmlFor={`im-entity-${incidentId}`}
          >
            Select entity to confirm
          </label>

          <select
            id={`im-entity-${incidentId}`}
            value={selectedEntity || ""}
            onChange={(event) =>
              onEntityChange(
                incidentId,
                event.target.value
              )
            }
            disabled={busy}
          >
            <option value="">
              Choose an entity...
            </option>

            {entities.map((entity) => (
              <option
                key={entity.node_id}
                value={entity.node_id}
              >
                {entity.node_name} (
                {entity.node_id})
              </option>
            ))}
          </select>

          <p className="im-review-warning">
            <AlertTriangle size={14} />
            Check the article and entity
            carefully. Your supply-chain graph
            contains synthetic entities.
          </p>

          <div className="im-actions">
            <button
              type="button"
              className="im-confirm-button"
              disabled={
                busy ||
                !selectedEntity
              }
              onClick={() =>
                onConfirm(
                  incident,
                  selectedEntity
                )
              }
            >
              <ShieldCheck size={15} />

              {busy
                ? "Processing..."
                : "Confirm incident"}
            </button>

            <button
              type="button"
              className="im-reject-button"
              disabled={busy}
              onClick={() =>
                onReject(incident)
              }
            >
              <XCircle size={15} />
              Reject
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

export default function IncidentMonitor({
  onConfirmed,
  refreshToken = 0,
}) {
  const [statusFilter, setStatusFilter] =
    useState("PENDING");

  const [sortBy, setSortBy] =
    useState("relevance");

  const [searchText, setSearchText] =
    useState("");

  const [incidents, setIncidents] =
    useState([]);

  const [entities, setEntities] =
    useState([]);

  const [
    selectedEntities,
    setSelectedEntities,
  ] = useState({});

  const [loading, setLoading] =
    useState(true);

  const [ingesting, setIngesting] =
    useState(false);

  const [busyIncidentId, setBusyIncidentId] =
    useState(null);

  const [error, setError] =
    useState("");

  const [notice, setNotice] =
    useState("");

  const requestVersion = useRef(0);

  // Refetch incidents when status changes or
  // when App.jsx receives a WebSocket event.
  const loadData = useCallback(async () => {
    const version = ++requestVersion.current;

    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        limit: "200",
      });

      if (statusFilter !== "ALL") {
        params.set("status", statusFilter);
      }

      const [incidentData, graphData] =
        await Promise.all([
          apiRequest(
            `/api/incidents?${params.toString()}`
          ),
          apiRequest("/api/graph"),
        ]);

      if (version !== requestVersion.current) {
        return;
      }

      const nextIncidents =
        incidentData?.incidents || [];

      const graphEntities = (
        graphData?.nodes || []
      )
        .filter(
          (node) =>
            node?.id &&
            node?.type
        )
        .map((node) => ({
          node_id: node.id,
          node_name:
            node.label || node.id,
          node_type: node.type,
        }))
        .sort((a, b) =>
          a.node_name.localeCompare(
            b.node_name
          )
        );

      setIncidents(nextIncidents);
      setEntities(graphEntities);

      // Preserve a user's manual selection.
      // For newly loaded incidents, preselect
      // only an explicitly matched entity.
      setSelectedEntities((current) => {
        const updated = { ...current };

        for (const incident of nextIncidents) {
          const id = incident.incident_id;

          if (
            Object.prototype.hasOwnProperty.call(
              updated,
              id
            )
          ) {
            continue;
          }

          const exactSuggestion =
            incident.entity_match_method ===
            "EXACT_NAME"
              ? incident.exact_match_entity_id
              : null;

          if (
            exactSuggestion &&
            graphEntities.some(
              (entity) =>
                entity.node_id ===
                exactSuggestion
            )
          ) {
            updated[id] =
              exactSuggestion;
          }
        }

        return updated;
      });

    } catch (err) {
      if (version === requestVersion.current) {
        setError(
          err.message ||
          "Failed to load incidents."
        );
      }
    } finally {
      if (version === requestVersion.current) {
        setLoading(false);
      }
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();

    return () => {
      requestVersion.current += 1;
    };
  }, [loadData, refreshToken]);

  const displayedIncidents = useMemo(() => {
    const query = searchText
      .trim()
      .toLowerCase();

    const filtered = incidents.filter(
      (incident) => {
        if (!query) return true;

        return [
          incident.title,
          incident.disruption_type,
          incident.incident_id,
          incident.suggested_entity_id,
          incident.exact_match_entity_id,
        ]
          .filter(Boolean)
          .some((value) =>
            String(value)
              .toLowerCase()
              .includes(query)
          );
      }
    );

    return [...filtered].sort((a, b) => {
      if (sortBy === "newest") {
        return (
          getIncidentTimestamp(b) -
          getIncidentTimestamp(a)
        );
      }

      if (sortBy === "oldest") {
        return (
          getIncidentTimestamp(a) -
          getIncidentTimestamp(b)
        );
      }

      const scoreA =
        getRelevance(a) ?? -1;

      const scoreB =
        getRelevance(b) ?? -1;

      if (sortBy === "lowest") {
        // Keep unscored legacy records last.
        if (scoreA < 0) return 1;
        if (scoreB < 0) return -1;

        return scoreA - scoreB;
      }

      if (scoreA !== scoreB) {
        return scoreB - scoreA;
      }

      return (
        getIncidentTimestamp(b) -
        getIncidentTimestamp(a)
      );
    });
  }, [
    incidents,
    searchText,
    sortBy,
  ]);

  async function handleIngest() {
    if (ingesting) return;

    setIngesting(true);
    setError("");
    setNotice("");

    try {
      const result = await apiRequest(
        "/api/incidents/ingest",
        {
          method: "POST",
        }
      );

      setNotice(
        `Checked ${result.fetched ?? 0} articles; ` +
        `${result.saved_or_updated ?? 0} saved or updated; ` +
        `${result.skipped ?? 0} skipped.`
      );

      await loadData();
    } catch (err) {
      setError(
        err.message ||
        "News ingestion failed."
      );
    } finally {
      setIngesting(false);
    }
  }

  function handleEntityChange(
    incidentId,
    nodeId
  ) {
    setSelectedEntities((current) => ({
      ...current,
      [incidentId]: nodeId,
    }));
  }

  async function handleConfirm(
    incident,
    nodeId
  ) {
    if (!incident?.incident_id || !nodeId) {
      return;
    }

    const entity = entities.find(
      (item) => item.node_id === nodeId
    );

    const message =
      `Confirm incident:\n\n` +
      `${incident.title}\n\n` +
      `Selected entity: ` +
      `${entity?.node_name || nodeId}\n\n` +
      `This manually links the article ` +
      `to a synthetic supply-chain entity. ` +
      `Continue?`;

    if (!window.confirm(message)) {
      return;
    }

    setBusyIncidentId(
      incident.incident_id
    );

    setError("");
    setNotice("");

    try {
      const result = await apiRequest(
        `/api/incidents/${encodeURIComponent(
          incident.incident_id
        )}/confirm`,
        {
          method: "POST",
          body: JSON.stringify({
            node_id: nodeId,
          }),
        }
      );

      setNotice(
        "Incident confirmed successfully."
      );

      await loadData();

      // The parent dashboard can now run its
      // GraphSAGE simulation for this entity.
      if (typeof onConfirmed === "function") {
        try {
          await onConfirmed(
            nodeId,
            result.incident || incident
          );
        } catch (err) {
          setError(
            "Incident confirmed, but dashboard " +
            `simulation failed: ${err.message}`
          );
        }
      }

    } catch (err) {
      setError(
        err.message ||
        "Failed to confirm incident."
      );
    } finally {
      setBusyIncidentId(null);
    }
  }

  async function handleReject(incident) {
    if (!incident?.incident_id) {
      return;
    }

    if (
      !window.confirm(
        `Reject this incident?\n\n` +
        `${incident.title}`
      )
    ) {
      return;
    }

    setBusyIncidentId(
      incident.incident_id
    );

    setError("");
    setNotice("");

    try {
      await apiRequest(
        `/api/incidents/${encodeURIComponent(
          incident.incident_id
        )}/reject`,
        {
          method: "POST",
        }
      );

      setNotice(
        "Incident rejected successfully."
      );

      await loadData();
    } catch (err) {
      setError(
        err.message ||
        "Failed to reject incident."
      );
    } finally {
      setBusyIncidentId(null);
    }
  }

  return (
    <div className="im-panel">
      <div className="im-header">
        <div>
          <h2>
            <Newspaper size={21} />
            Live Incident Intelligence
          </h2>

          <p>
            Review relevant supply-chain news,
            verify graph entities, and manage
            incident confirmations.
          </p>
        </div>

        <div className="im-header-actions">
          <button
            type="button"
            className="im-button-secondary"
            disabled={loading || ingesting}
            onClick={loadData}
          >
            <RefreshCw size={15} />
            Refresh
          </button>

          <button
            type="button"
            className="im-button-primary"
            disabled={ingesting}
            onClick={handleIngest}
          >
            <Newspaper size={15} />
            {ingesting
              ? "Checking news..."
              : "Fetch News"}
          </button>
        </div>
      </div>

      <div className="im-toolbar">
        <div className="im-field">
          <label htmlFor="im-filter">
            <Filter size={14} />
            Status
          </label>

          <select
            id="im-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value
              )
            }
          >
            {STATUS_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="im-field">
          <label htmlFor="im-sort">
            Sort by
          </label>

          <select
            id="im-sort"
            value={sortBy}
            onChange={(event) =>
              setSortBy(
                event.target.value
              )
            }
          >
            {SORT_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="im-field im-search-field">
          <label htmlFor="im-search">
            Search incidents
          </label>

          <input
            id="im-search"
            value={searchText}
            onChange={(event) =>
              setSearchText(
                event.target.value
              )
            }
            placeholder="Search title, entity or type"
          />
        </div>
      </div>

      {error && (
        <div className="im-alert im-error">
          <AlertTriangle size={17} />
          <span>{error}</span>
        </div>
      )}

      {notice && (
        <div className="im-alert im-success">
          <CheckCircle2 size={17} />
          <span>{notice}</span>
        </div>
      )}

      <div className="im-list-heading">
        <strong>
          {displayedIncidents.length} incidents
        </strong>

        <span>
          {loading
            ? "Refreshing..."
            : "Stored in Neo4j"}
        </span>
      </div>

      {loading && incidents.length === 0 ? (
        <p className="im-empty">
          Loading incidents...
        </p>
      ) : displayedIncidents.length === 0 ? (
        <div className="im-empty">
          No incidents match your current
          filters. You can change the status
          filter or fetch new articles.
        </div>
      ) : (
        <div className="im-list">
          {displayedIncidents.map(
            (incident) => (
              <IncidentCard
                key={incident.incident_id}
                incident={incident}
                entities={entities}
                selectedEntity={
                  selectedEntities[
                    incident.incident_id
                  ] || ""
                }
                onEntityChange={
                  handleEntityChange
                }
                onConfirm={handleConfirm}
                onReject={handleReject}
                busy={
                  busyIncidentId ===
                  incident.incident_id
                }
              />
            )
          )}
        </div>
      )}

      <p className="im-disclaimer">
        Relevance scores are rule-based screening
        indicators, not probabilities. A news
        article should not be treated as affecting
        a synthetic graph entity without
        independent human verification.
      </p>
    </div>
  );
}
