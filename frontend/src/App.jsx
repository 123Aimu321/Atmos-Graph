// frontend/src/App.jsx
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Download,
  GitBranch,
  Network,
  Play,
  RefreshCw,
  Route,
} from "lucide-react";

import { api } from "./services/api";

import SupplyChainGraph from "./components/SupplyChainGraph";
import GraphExplorer from "./components/GraphExplorer";
import RipplePathExplorer from "./components/RipplePathExplorer";
import RiskAssessment from "./components/RiskAssessment";
import IncidentMonitor from "./components/IncidentMonitor";
import DelayImpact from "./components/DelayImpact";
import ForecastTimeline from "./components/ForecastTimeline";
import "./App.css";
import useIncidentSocket from "./hooks/useIncidentSocket";
import IncidentHistory from "./components/IncidentHistory";


// =====================================================
// REUSABLE STAT CARD
// =====================================================

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}) {
  return (
    <div className="stat-card">
      <div className="stat-heading">
        <span>{title}</span>
        <Icon size={20} color={color} />
      </div>

      <div className="stat-value">
        {value}
      </div>
    </div>
  );
}


// =====================================================
// MAIN APPLICATION
// =====================================================

export default function App() {

  // -------------------------------------------------
  // DASHBOARD DATA
  // -------------------------------------------------

  const [graph, setGraph] = useState(null);

  const [scenarios, setScenarios] = useState([]);

  const [selectedNode, setSelectedNode] =
    useState("");

  const [prediction, setPrediction] =
    useState(null);

  const [metrics, setMetrics] =
    useState(null);

  const [incidentRefreshKey, setIncidentRefreshKey] =
    useState(0);

  const [historyRefreshToken, setHistoryRefreshToken] =
    useState(0);


  // -------------------------------------------------
  // DELAY REGRESSION
  // -------------------------------------------------

  const [delay, setDelay] =
    useState(null);

  const [delayLoading, setDelayLoading] =
    useState(false);

  const [delayError, setDelayError] =
    useState("");

  const [
    initialDelayDays,
    setInitialDelayDays,
  ] = useState(14);

  const [delayMetrics, setDelayMetrics] =
    useState(null);

  // Recovery scenario, based on GraphSAGE delay predictions.
  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState("");
  const [recoveryHalfLifeDays, setRecoveryHalfLifeDays] = useState(30);


  // -------------------------------------------------
  // NLP EVENT ANALYSIS
  // -------------------------------------------------

  const [eventText, setEventText] =
    useState("");

  const [eventAnalysis, setEventAnalysis] =
    useState(null);


  // -------------------------------------------------
  // RIPPLE EFFECT
  // -------------------------------------------------

  const [ripple, setRipple] =
    useState(null);

  const [
    highlightedPath,
    setHighlightedPath,
  ] = useState([]);


  // -------------------------------------------------
  // RISK ASSESSMENT
  // -------------------------------------------------

  const [risk, setRisk] =
    useState(null);


  // -------------------------------------------------
  // CONFIRMED NEWS INCIDENT
  // -------------------------------------------------

  const [
    activeIncident,
    setActiveIncident,
  ] = useState(null);


  // -------------------------------------------------
  // LOADING STATES
  // -------------------------------------------------

  const [loading, setLoading] =
    useState(true);

  const [predicting, setPredicting] =
    useState(false);

  const [analyzing, setAnalyzing] =
    useState(false);

  const [rippleLoading, setRippleLoading] =
    useState(false);

  const [riskLoading, setRiskLoading] =
    useState(false);

  const [
    downloadingReport,
    setDownloadingReport,
  ] = useState(false);

  const [error, setError] =
    useState("");


  // -------------------------------------------------
  // REQUEST MANAGEMENT
  // -------------------------------------------------

  // Each new simulation gets a unique request ID.
  // Older asynchronous responses are ignored.

  const requestId = useRef(0);

  const dashboardRequestId = useRef(0);

  // WebSocket messages announce incident changes. Neo4j is the source of truth.
  const handleLiveIncidentEvent = useCallback(
    (event) => {
      const incidentEvents = new Set([
        "incidents.ingested",
        "incident.confirmed",
        "incident.rejected",
      ]);

      if (incidentEvents.has(event.type)) {
        setIncidentRefreshKey(
          (current) => current + 1
        );
      }

      const historyEvents = new Set([
        "impact.snapshot.created",
        "incident.confirmed",
      ]);

      if (historyEvents.has(event.type)) {
        setHistoryRefreshToken(
          (current) => current + 1
        );
      }
    },
    []
  );

  const {
    status: socketStatus,
    lastEvent: lastSocketEvent,
  } = useIncidentSocket(handleLiveIncidentEvent);

  // Apply the latest CONFIRMED incident simulation in every
  // connected tab. WebSocket data originates from the validated
  // snapshot-saving route. Unconfirmed news only refreshes the
  // incident monitor; it does not trigger a prediction.
  useEffect(() => {
    if (
      lastSocketEvent?.type !== "impact.prediction.updated"
    ) {
      return;
    }

    const data = lastSocketEvent.data || {};
    if (
      data.data_origin !== "SYNTHETIC_SIMULATION" ||
      !data.prediction ||
      !data.source_node_id
    ) {
      return;
    }

    // Supersede any stale in-flight local computation so it
    // cannot overwrite the received confirmed scenario.
    requestId.current += 1;
    setPredicting(false);
    setSelectedNode(data.source_node_id);
    setPrediction(data.prediction);
    setDelay(data.delay || null);
    setForecast(data.forecast || null);
    setRipple(data.ripple || null);
    setRisk(data.risk || null);
    setActiveIncident({
      incident_id: data.incident_id,
      title: "Confirmed disruption (live update)",
      disruption_type: "OTHER",
    });
    setHistoryRefreshToken((value) => value + 1);
  }, [lastSocketEvent]);


  // =================================================
  // LOAD DASHBOARD
  // =================================================

  const loadDashboard = useCallback(async () => {

    const currentDashboardRequest =
      ++dashboardRequestId.current;

    setLoading(true);
    setError("");

    try {

      const [
        graphData,
        scenarioData,
        metricData,
      ] = await Promise.all([
        api.getGraph(),
        api.getScenarios(),
        api.getMetrics(),
      ]);

      if (
        currentDashboardRequest !==
        dashboardRequestId.current
      ) {
        return;
      }

      setGraph(graphData);

      setScenarios(
        Array.isArray(scenarioData)
          ? scenarioData
          : scenarioData?.scenarios || []
      );

      setMetrics(metricData);

      setSelectedNode((current) => {

        const nodes =
          graphData?.nodes || [];

        const exists = nodes.some(
          (node) => node.id === current
        );

        return exists
          ? current
          : nodes[0]?.id || "";
      });

    } catch (err) {

      if (
        currentDashboardRequest ===
        dashboardRequestId.current
      ) {
        setError(
          err.message ||
          "Failed to load dashboard data."
        );
      }

    } finally {

      if (
        currentDashboardRequest ===
        dashboardRequestId.current
      ) {
        setLoading(false);
      }
    }

  }, []);


  // =================================================
  // LOAD REGRESSION METRICS
  // =================================================

  const loadDelayMetrics = useCallback(
    async () => {

      try {

        const data =
          await api.getDelayMetrics();

        setDelayMetrics(data);

      } catch (err) {

        // Delay metrics are optional dashboard
        // information. Do not block graph loading.

        console.warn(
          "Delay metrics unavailable:",
          err
        );
      }

    },
    []
  );


  // =================================================
  // INITIAL DASHBOARD LOAD
  // =================================================

  useEffect(() => {

    loadDashboard();

    loadDelayMetrics();

    return () => {
      requestId.current += 1;
      dashboardRequestId.current += 1;
    };

  }, [
    loadDashboard,
    loadDelayMetrics,
  ]);


  // =================================================
  // RESET SIMULATION
  // =================================================

  function resetSimulation() {

    // Invalidate previous async requests.

    requestId.current += 1;

    setPrediction(null);

    setRipple(null);

    setRisk(null);

    setDelay(null);

    setHighlightedPath([]);

    setEventAnalysis(null);

    setActiveIncident(null);

    setPredicting(false);

    setAnalyzing(false);

    setRippleLoading(false);

    setRiskLoading(false);

    setDelayLoading(false);

    setDelayError("");
    setForecast(null);
    setForecastLoading(false);
    setForecastError("");
  }


  // =================================================
  // SELECT GRAPH NODE
  // =================================================

  function selectNode(nodeId) {

    if (!nodeId) {
      return;
    }

    setSelectedNode(nodeId);

    resetSimulation();

    setError("");
  }


  // =================================================
  // CHANGE INITIAL DISRUPTION DURATION
  // =================================================

  function handleInitialDelayChange(event) {

    const value =
      Number(event.target.value);

    setInitialDelayDays(value);

    resetSimulation();

    setError("");
  }


  // =================================================
  // GRAPH SAGE DELAY REGRESSION
  // =================================================

  async function loadDelay(
    nodeId,
    currentRequestId
  ) {

    if (!nodeId) {
      return null;
    }

    setDelayLoading(true);

    setDelayError("");

    try {

      const data =
        await api.predictDelay(
          nodeId,
          initialDelayDays,
          0.75
        );

      if (
        currentRequestId !==
        requestId.current
      ) {
        return null;
      }

      setDelay(data);

      return data;

    } catch (err) {

      if (
        currentRequestId ===
        requestId.current
      ) {

        setDelay(null);

        setDelayError(
          err.message ||
          "Delay regression failed."
        );
      }

      return null;

    } finally {

      if (
        currentRequestId ===
        requestId.current
      ) {
        setDelayLoading(false);
      }
    }
  }


  // =================================================
  // 30/60/90-DAY RECOVERY SCENARIOS
  // =================================================

  async function loadForecast(nodeId, currentRequestId) {
    if (!nodeId) return null;

    setForecastLoading(true);
    setForecastError("");

    try {
      const data = await api.predictForecast(
        nodeId,
        initialDelayDays,
        recoveryHalfLifeDays
      );

      if (currentRequestId !== requestId.current) return null;

      setForecast(data);
      return data;
    } catch (err) {
      if (currentRequestId === requestId.current) {
        setForecast(null);
        setForecastError(err.message || "Forecast calculation failed.");
      }
      return null;
    } finally {
      if (currentRequestId === requestId.current) {
        setForecastLoading(false);
      }
    }
  }


  // =================================================
  // RIPPLE EFFECT ANALYSIS
  // =================================================

  async function loadRipple(
    nodeId,
    currentRequestId
  ) {

    if (!nodeId) {
      return null;
    }

    setRippleLoading(true);

    try {

      const data =
        await api.getRipple(nodeId);

      if (
        currentRequestId !==
        requestId.current
      ) {
        return null;
      }

      setRipple(data);

      setHighlightedPath([]);

      return data;

    } catch (err) {

      if (
        currentRequestId ===
        requestId.current
      ) {

        setRipple(null);

        setError(
          `Ripple analysis failed: ${err.message}`
        );
      }

      return null;

    } finally {

      if (
        currentRequestId ===
        requestId.current
      ) {
        setRippleLoading(false);
      }
    }
  }


  // =================================================
  // RISK ASSESSMENT
  // =================================================

  async function loadRisk(
    predictionData,
    rippleData,
    disruptionType,
    currentRequestId
  ) {

    setRiskLoading(true);

    try {

      const data =
        await api.assessRisk(
          predictionData,
          rippleData,
          disruptionType
        );

      if (
        currentRequestId !==
        requestId.current
      ) {
        return null;
      }

      setRisk(data);

      return data;

    } catch (err) {

      if (
        currentRequestId ===
        requestId.current
      ) {

        setRisk(null);

        setError(
          `Risk assessment failed: ${err.message}`
        );
      }

      return null;

    } finally {

      if (
        currentRequestId ===
        requestId.current
      ) {
        setRiskLoading(false);
      }
    }
  }


  // =================================================
  // COMMON PREDICTION PIPELINE
  // =================================================

  async function executePrediction(
    nodeId,
    disruptionType = "OTHER",
    incident = null
  ) {

    if (!nodeId) {
      return;
    }

    const currentRequestId =
      ++requestId.current;

    setSelectedNode(nodeId);

    setPredicting(true);

    setError("");

    setPrediction(null);

    setRipple(null);

    setRisk(null);

    setDelay(null);

    setDelayError("");

    setHighlightedPath([]);

    setRippleLoading(false);

    setRiskLoading(false);

    setDelayLoading(false);
    setForecast(null);
    setForecastLoading(false);
    setForecastError("");

    setActiveIncident(incident);

    if (incident) {
      setEventAnalysis(null);
    }

    try {

      // -----------------------------------------
      // STEP 1: GRAPHSAGE CLASSIFICATION
      // -----------------------------------------

      const predictionData =
        await api.predict(nodeId);

      if (
        currentRequestId !==
        requestId.current
      ) {
        return;
      }

      setPrediction(predictionData);


      // -----------------------------------------
      // STEP 2: GRAPHSAGE DELAY REGRESSION
      // -----------------------------------------

      // Delay prediction runs independently.
      // A delay API error does not prevent
      // ripple and risk calculations.

      const delayData = await loadDelay(
        nodeId,
        currentRequestId
      );

      if (
        currentRequestId !==
        requestId.current
      ) {
        return;
      }


      // -----------------------------------------
      // STEP 3: TIME-DEPENDENT RECOVERY SCENARIOS
      // -----------------------------------------

      const forecastData = await loadForecast(
        nodeId,
        currentRequestId
      );

      if (currentRequestId !== requestId.current) return;


      // -----------------------------------------
      // STEP 4: SAVE CONFIRMED INCIDENT IMPACT
      // -----------------------------------------

      if (
        incident?.incident_id &&
        typeof api.saveImpact === "function"
      ) {

        try {

          await api.saveImpact(
            incident.incident_id,
            predictionData
          );

        } catch (err) {

          console.warn(
            "Incident impact persistence failed:",
            err
          );
        }

        if (
          currentRequestId !==
          requestId.current
        ) {
          return;
        }
      }


      // -----------------------------------------
      // STEP 5: DOWNSTREAM RIPPLE PATHS
      // -----------------------------------------

      const rippleData =
        await loadRipple(
          nodeId,
          currentRequestId
        );

      if (
        currentRequestId !==
        requestId.current ||
        !rippleData
      ) {
        return;
      }


      // -----------------------------------------
      // STEP 6: RISK ASSESSMENT
      // -----------------------------------------

      const riskData = await loadRisk(
        predictionData,
        rippleData,
        disruptionType,
        currentRequestId
      );

      if (currentRequestId !== requestId.current) {
        return;
      }

      // Save a historical snapshot only when the
      // simulation belongs to a confirmed incident.
      if (
        incident?.incident_id &&
        typeof api.saveHistory === "function"
      ) {
        try {
          await api.saveHistory(
            incident.incident_id,
            {
              prediction: predictionData,
              delay: delayData,
              forecast: forecastData,
              ripple: rippleData,
              risk: riskData,
            }
          );

          if (currentRequestId === requestId.current) {
            setHistoryRefreshToken(
              (current) => current + 1
            );
          }
        } catch (err) {
          console.error(
            "Unable to save impact history:",
            err
          );

          if (currentRequestId === requestId.current) {
            setError(
              `Impact history was not saved: ${err.message}`
            );
          }
        }
      }

    } catch (err) {

      if (
        currentRequestId ===
        requestId.current
      ) {

        setError(
          err.message ||
          "Prediction failed."
        );
      }

    } finally {

      if (
        currentRequestId ===
        requestId.current
      ) {
        setPredicting(false);
      }
    }
  }


  // =================================================
  // MANUAL DISRUPTION SIMULATION
  // =================================================

  async function runPrediction() {

    if (
      !selectedNode ||
      predicting ||
      analyzing ||
      loading
    ) {
      return;
    }

    setEventAnalysis(null);

    await executePrediction(
      selectedNode,
      "OTHER",
      null
    );
  }


  // =================================================
  // NLP EVENT ANALYSIS
  // =================================================

  async function handleAnalyzeEvent() {

    const text =
      eventText.trim();

    if (
      !text ||
      analyzing ||
      predicting ||
      loading
    ) {
      return;
    }

    const currentRequestId =
      ++requestId.current;

    setAnalyzing(true);

    setError("");

    setEventAnalysis(null);

    setActiveIncident(null);

    setPrediction(null);

    setRipple(null);

    setRisk(null);

    setDelay(null);

    setDelayError("");

    setHighlightedPath([]);

    setRippleLoading(false);

    setRiskLoading(false);

    setDelayLoading(false);
    setForecast(null);
    setForecastLoading(false);
    setForecastError("");

    try {

      const result =
        await api.analyzeEvent(text);

      if (
        currentRequestId !==
        requestId.current
      ) {
        return;
      }

      const analysis =
        result.analysis || {};

      setEventAnalysis(analysis);

      const matchedNode =
        analysis.matched_entity?.node_id ||
        analysis.matched_entity?.id;

      if (matchedNode) {
        setSelectedNode(matchedNode);
      }

      // Only run predictions automatically
      // when NLP entity confirmation is
      // not required.

      if (
        matchedNode &&
        result.prediction &&
        !analysis.requires_confirmation
      ) {

        setPrediction(
          result.prediction
        );


        // ---------------------------------------
        // DELAY REGRESSION
        // ---------------------------------------

        // Important: use matchedNode here.
        // The previous code incorrectly
        // referenced an undefined nodeId.

        await loadDelay(
          matchedNode,
          currentRequestId
        );

        if (
          currentRequestId !==
          requestId.current
        ) {
          return;
        }


        // ---------------------------------------
        // 30/60/90-DAY FORECAST SCENARIOS
        // ---------------------------------------

        await loadForecast(
          matchedNode,
          currentRequestId
        );

        if (currentRequestId !== requestId.current) return;


        // ---------------------------------------
        // RIPPLE PATHS
        // ---------------------------------------

        const rippleData =
          await loadRipple(
            matchedNode,
            currentRequestId
          );

        if (
          currentRequestId !==
          requestId.current
        ) {
          return;
        }


        // ---------------------------------------
        // RISK ASSESSMENT
        // ---------------------------------------

        if (rippleData) {

          await loadRisk(
            result.prediction,
            rippleData,
            analysis.disruption_type ||
              "OTHER",
            currentRequestId
          );
        }

      } else {

        setPrediction(null);

        setRipple(null);

        setRisk(null);

        setDelay(null);
        setForecast(null);

        setHighlightedPath([]);
      }

    } catch (err) {

      if (
        currentRequestId ===
        requestId.current
      ) {

        setError(
          err.message ||
          "Event analysis failed."
        );
      }

    } finally {

      if (
        currentRequestId ===
        requestId.current
      ) {
        setAnalyzing(false);
      }
    }
  }


  // =================================================
  // CONFIRMED NEWS INCIDENT
  // =================================================

  async function handleIncidentConfirmed(
    nodeId,
    incident
  ) {

    if (!nodeId) {
      return;
    }

    setEventText("");

    setEventAnalysis(null);

    await executePrediction(
      nodeId,
      incident?.disruption_type ||
        "OTHER",
      incident
    );
  }


  // =================================================
  // DOWNLOAD PDF IMPACT REPORT
  // =================================================

  async function handleDownloadReport() {

    if (
      !prediction ||
      !ripple ||
      !risk
    ) {

      setError(
        "Run a complete disruption analysis before downloading."
      );

      return;
    }

    setDownloadingReport(true);

    setError("");

    try {

      const blob =
        await api.downloadImpactReport({

          prediction,

          ripple,

          risk,

          event_text: activeIncident
            ? activeIncident.title
            : eventAnalysis
              ? eventText
              : null,

          analysis: activeIncident
            ? {
                disruption_type:
                  activeIncident.disruption_type,

                matched_entity: {
                  node_id: selectedNode,
                },

                source_url:
                  activeIncident.source_url,

                incident_id:
                  activeIncident.incident_id,

                requires_confirmation: false,
              }
            : eventAnalysis,
        });

      const url =
        URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;

      link.download =
        "AtmoGraph_Impact_Report.pdf";

      document.body.appendChild(link);

      link.click();

      link.remove();

      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 1000);

    } catch (err) {

      setError(
        err.message ||
        "Failed to generate PDF report."
      );

    } finally {

      setDownloadingReport(false);
    }
  }


  // =================================================
  // GRAPH PATH HIGHLIGHTING
  // =================================================

  function handleHighlightPath(path) {

    if (!Array.isArray(path)) {
      return;
    }

    setHighlightedPath(path);
  }


  function handleClearPath() {
    setHighlightedPath([]);
  }


  // =================================================
  // DERIVED DASHBOARD DATA
  // =================================================

  const summary =
    prediction?.summary || null;


  const affectedNodes = useMemo(() => {

    return (
      prediction?.results || []
    ).filter(
      (item) =>
        item.predicted_status ===
        "AFFECTED"
    );

  }, [prediction]);


  const selectedEntity = useMemo(() => {

    return graph?.nodes?.find(
      (node) =>
        node.id === selectedNode
    );

  }, [
    graph,
    selectedNode,
  ]);


  const totalEntities =
    graph?.summary?.total_nodes ??
    graph?.nodes?.length ??
    "—";


  const totalRelationships =
    graph?.summary?.total_edges ??
    graph?.edges?.length ??
    "—";


  const affectedCount =
    summary?.affected ??
    affectedNodes.length;


  const disruptedCount =
    summary?.disrupted ?? 0;


  const normalCount =
    summary?.normal ?? 0;


  const modelAccuracy =
    metrics?.graphsage?.accuracy;


  const delayMAE =
    delayMetrics?.mae_days;


  const delayRMSE =
    delayMetrics?.rmse_days;


  const isBusy =
    loading ||
    predicting ||
    analyzing;


  // =================================================
  // RENDER DASHBOARD
  // =================================================

  return (

    <div className="app-shell">

      {/* ========================================== */}
      {/* SIDEBAR */}
      {/* ========================================== */}

      <aside className="sidebar">

        {/* BRAND */}

        <div className="brand">

          <div className="brand-icon">
            <Network size={25} />
          </div>

          <div>
            <h2>AtmoGraph</h2>
            <p>Supply Chain Intelligence</p>
          </div>

        </div>


        {/* ======================================== */}
        {/* DISRUPTION SIMULATOR */}
        {/* ======================================== */}

        <div className="sidebar-section">

          <span className="section-label">
            DISRUPTION SIMULATOR
          </span>

          <label htmlFor="entity">
            Select supply-chain entity
          </label>

          <select
            id="entity"
            value={selectedNode}
            onChange={(event) =>
              selectNode(
                event.target.value
              )
            }
            disabled={loading}
          >

            {(graph?.nodes || []).map(
              (node) => (

                <option
                  key={node.id}
                  value={node.id}
                >
                  {node.label} ({node.type})
                </option>

              )
            )}

          </select>


          {selectedEntity && (

            <div className="entity-details">

              <strong>
                {selectedEntity.label}
              </strong>

              <span>
                {selectedEntity.type}
              </span>

              <span>
                {selectedEntity.region}
              </span>

            </div>

          )}


          {/* INITIAL DISRUPTION DURATION */}

          <div
            className="delay-control"
            style={{
              marginTop: 20,
              marginBottom: 20,
            }}
          >

            <label htmlFor="initial-delay">
              Initial disruption duration
            </label>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginTop: 12,
              }}
            >

              <input
                id="initial-delay"
                type="range"
                min="1"
                max="90"
                step="1"
                value={initialDelayDays}
                onChange={
                  handleInitialDelayChange
                }
                disabled={isBusy}
                style={{
                  flex: 1,
                  minWidth: 0,
                }}
              />

              <strong
                style={{
                  whiteSpace: "nowrap",
                  fontSize: 13,
                }}
              >
                {initialDelayDays} days
              </strong>

            </div>

            <p
              className="muted"
              style={{
                fontSize: 11,
                marginTop: 8,
              }}
            >
              Assumed duration of the initial
              disruption, not a forecast horizon.
            </p>

          </div>

          <div
            className="delay-control"
            style={{ marginBottom: 20 }}
          >
            <label htmlFor="recovery-half-life">
              Scenario recovery half-life
            </label>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginTop: 12,
              }}
            >
              <input
                id="recovery-half-life"
                type="range"
                min="1"
                max="180"
                step="1"
                value={recoveryHalfLifeDays}
                disabled={isBusy}
                onChange={(event) => {
                  setRecoveryHalfLifeDays(Number(event.target.value));
                  resetSimulation();
                  setError("");
                }}
                style={{ flex: 1, minWidth: 0 }}
              />
              <strong
                style={{
                  fontSize: 13,
                  whiteSpace: "nowrap",
                }}
              >
                {recoveryHalfLifeDays} days
              </strong>
            </div>
            <p
              className="muted"
              style={{ fontSize: 11, marginTop: 8 }}
            >
              Assumed time for residual delays to fall by half after exposure.
            </p>
          </div>

          <button
            className="primary-button"
            onClick={runPrediction}
            disabled={
              !selectedNode ||
              isBusy
            }
          >

            <Play size={17} />

            {predicting
              ? "Running prediction..."
              : "Simulate Disruption"}

          </button>

        </div>


        {/* ======================================== */}
        {/* NETWORK LEGEND */}
        {/* ======================================== */}

        <div className="sidebar-section">

          <span className="section-label">
            NETWORK LEGEND
          </span>

          <div className="legend-item">
            <span className="legend-dot normal" />
            Normal
          </div>

          <div className="legend-item">
            <span className="legend-dot affected" />
            Affected
          </div>

          <div className="legend-item">
            <span className="legend-dot disrupted" />
            Disrupted
          </div>

        </div>


        {/* ======================================== */}
        {/* MODEL INFORMATION */}
        {/* ======================================== */}

        <div className="sidebar-section">

          <span className="section-label">
            MODEL INFORMATION
          </span>

          <div className="model-info">
            <span>Classification model</span>
            <strong>GraphSAGE GNN</strong>
          </div>

          <div className="model-info">

            <span>
              Synthetic test accuracy
            </span>

            <strong>
              {modelAccuracy != null
                ? `${(
                    modelAccuracy * 100
                  ).toFixed(1)}%`
                : "—"}
            </strong>

          </div>


          <div className="model-info">
            <span>Delay prediction model</span>
            <strong>GraphSAGE Regression</strong>
          </div>


          <div className="model-info">

            <span>
              Synthetic delay MAE
            </span>

            <strong>
              {delayMAE != null
                ? `${Number(
                    delayMAE
                  ).toFixed(3)} days`
                : "—"}
            </strong>

          </div>


          <div className="model-info">

            <span>
              Synthetic delay RMSE
            </span>

            <strong>
              {delayRMSE != null
                ? `${Number(
                    delayRMSE
                  ).toFixed(3)} days`
                : "—"}
            </strong>

          </div>

        </div>

      </aside>


      {/* ========================================== */}
      {/* MAIN CONTENT */}
      {/* ========================================== */}

      <main className="main-content">


        {/* ======================================== */}
        {/* HEADER */}
        {/* ======================================== */}

        <header className="topbar">

          <div>

            <h1>
              Supply Chain Dashboard
            </h1>

            <p>
              Graph-based disruption propagation
              and delivery-delay analysis
            </p>

          </div>


          <div
            className="websocket-status"
            title={lastSocketEvent
              ? `Last event: ${lastSocketEvent.type}`
              : "Real-time incident connection"}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              border: "1px solid #26364d",
              borderRadius: 8,
              fontSize: 12,
              color: "#cbd5e1",
            }}
          >
            <span
              style={{
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: socketStatus === "connected"
                  ? "#22c55e"
                  : socketStatus === "connecting"
                    ? "#f59e0b"
                    : "#ef4444",
              }}
            />
            {socketStatus === "connected"
              ? "Live Connected"
              : socketStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
          </div>

          <button
            className="refresh-button"
            onClick={loadDashboard}
            disabled={loading}
          >

            <RefreshCw size={17} />

            {loading
              ? "Loading..."
              : "Refresh"}

          </button>

        </header>


        {/* ======================================== */}
        {/* SIMULATION DISCLAIMER */}
        {/* ======================================== */}

        <div className="simulation-notice">

          This dashboard uses a synthetic
          25-entity supply-chain network.
          GraphSAGE classification and delay
          regression results are experimental
          simulations, not validated
          real-world forecasts.

        </div>


        {/* ======================================== */}
        {/* ERROR MESSAGE */}
        {/* ======================================== */}

        {error && (

          <div className="error-message">

            <AlertTriangle size={18} />

            <span>
              {error}
            </span>

          </div>

        )}


        {/* ======================================== */}
        {/* NLP DISRUPTION ANALYZER */}
        {/* ======================================== */}

        <section className="nlp-panel">

          <div className="panel-heading">

            <div>

              <h2>

                <BrainCircuit
                  size={19}
                  style={{
                    display: "inline-block",
                    verticalAlign: "middle",
                    marginRight: 9,
                  }}
                />

                AI Disruption Analyzer

              </h2>

              <p>
                Describe a supply-chain incident
                to identify its source and
                estimate downstream impact.
              </p>

            </div>

          </div>


          <textarea
            className="event-input"
            value={eventText}
            onChange={(event) =>
              setEventText(
                event.target.value
              )
            }
            placeholder="Example: Heavy rainfall and flooding have disrupted operations at Mumbai Port."
            rows={4}
          />


          <button
            className="primary-button analyze-button"
            onClick={handleAnalyzeEvent}
            disabled={
              isBusy ||
              !eventText.trim()
            }
          >

            <BrainCircuit size={17} />

            {analyzing
              ? "Analyzing disruption..."
              : "Analyze Disruption"}

          </button>


          {eventAnalysis && (

            <div className="analysis-results">

              <div>

                <span>
                  Disruption Type
                </span>

                <strong>
                  {eventAnalysis.disruption_type ||
                    "UNKNOWN"}
                </strong>

              </div>


              <div>

                <span>
                  Detected Entity
                </span>

                <strong>
                  {eventAnalysis.matched_entity
                    ?.node_name ||
                    eventAnalysis.matched_entity
                      ?.label ||
                    "Not identified"}
                </strong>

              </div>


              <div>

                <span>
                  Match Confidence
                </span>

                <strong>
                  {(
                    (
                      eventAnalysis
                        .match_confidence || 0
                    ) * 100
                  ).toFixed(0)}
                  %
                </strong>

              </div>


              {eventAnalysis.requires_confirmation && (

                <p className="confirmation-warning">

                  Please verify the detected
                  entity. Automatic prediction
                  has been paused until the
                  entity is confirmed.

                </p>

              )}


              {!eventAnalysis.matched_entity && (

                <p className="confirmation-warning">

                  No matching supply-chain
                  entity was found. Select
                  an entity manually using
                  the disruption simulator.

                </p>

              )}

            </div>

          )}

        </section>


        {/* ======================================== */}
        {/* LIVE INCIDENT MONITOR */}
        {/* ======================================== */}

        <section
          className="incident-monitor-section"
          style={{
            marginTop: 24,
            marginBottom: 24,
          }}
        >

          <IncidentMonitor
            refreshToken={incidentRefreshKey}
            onConfirmed={handleIncidentConfirmed}
          />

        </section>


        {/* ======================================== */}
        {/* CONFIRMED INCIDENT CONTEXT */}
        {/* ======================================== */}

        {activeIncident && (

          <div
            className="simulation-notice"
            style={{
              marginBottom: 20,
            }}
          >

            <strong>
              Confirmed news incident:
            </strong>{" "}

            {activeIncident.title}

            <div
              style={{
                marginTop: 6,
              }}
            >

              Simulation source:{" "}

              <strong>
                {selectedEntity?.label ||
                  selectedNode}
              </strong>

              {" · "}

              Disruption type:{" "}

              <strong>
                {activeIncident.disruption_type}
              </strong>

            </div>

          </div>

        )}


        {/* ======================================== */}
        {/* STATISTICS */}
        {/* ======================================== */}

        <section className="stats-grid">

          <StatCard
            title="Total Entities"
            value={totalEntities}
            icon={Network}
            color="#38bdf8"
          />

          <StatCard
            title="Relationships"
            value={totalRelationships}
            icon={GitBranch}
            color="#a78bfa"
          />

          <StatCard
            title="Affected"
            value={
              prediction
                ? affectedCount
                : "—"
            }
            icon={AlertTriangle}
            color="#f59e0b"
          />

          <StatCard
            title="Disrupted"
            value={
              prediction
                ? disruptedCount
                : "—"
            }
            icon={Activity}
            color="#ef4444"
          />

        </section>


        {/* ======================================== */}
        {/* SUPPLY CHAIN GRAPH */}
        {/* ======================================== */}

        <section className="graph-panel">

          <div className="panel-heading">

            <div>

              <h2>
                Supply Chain Network
              </h2>

              <p>
                Click any entity to select
                a disruption source.
                Predicted delays are shown
                on affected graph nodes.
              </p>

            </div>

            <span className="panel-tag">
              {prediction
                ? "Simulation Active"
                : "Network Overview"}
            </span>

          </div>


          {loading ? (

            <div className="loading-state">
              Loading supply-chain graph...
            </div>

          ) : graph ? (

            <SupplyChainGraph
              graph={graph}
              predictions={
                prediction?.results
              }
              delay={delay}
              selectedNode={selectedNode}
              highlightedPath={
                highlightedPath
              }
              onSelectNode={selectNode}
            />

          ) : (

            <div className="loading-state">
              Graph unavailable.
            </div>

          )}

        </section>


        <section
          className="graph-explorer-section"
          style={{
            marginTop: 24,
            marginBottom: 24,
          }}
        >
          <GraphExplorer />
        </section>


        {/* ======================================== */}
        {/* RIPPLE PATH EXPLORER */}
        {/* ======================================== */}

        <section className="ripple-panel">

          {rippleLoading && (

            <div className="loading-state">

              <Route
                size={19}
                style={{
                  display: "inline-block",
                  verticalAlign: "middle",
                  marginRight: 8,
                }}
              />

              Calculating downstream
              disruption paths...

            </div>

          )}


          <RipplePathExplorer
            ripple={ripple}
            onHighlightPath={
              handleHighlightPath
            }
            onClearPath={
              handleClearPath
            }
          />

        </section>


        {/* ======================================== */}
        {/* GRAPHSAGE DELAY IMPACT */}
        {/* ======================================== */}

        <section
          className="delay-impact-section"
          style={{
            marginTop: 24,
            marginBottom: 24,
          }}
        >

          <DelayImpact
            delay={delay}
            loading={delayLoading}
            error={delayError}
          />

        </section>


        {/* ======================================== */}
        {/* DELAY MODEL INFORMATION */}
        {/* ======================================== */}

        {delay && (

          <div
            className="simulation-notice"
            style={{
              marginBottom: 24,
            }}
          >

            <Clock3
              size={16}
              style={{
                display: "inline-block",
                verticalAlign: "middle",
                marginRight: 8,
              }}
            />

            Initial simulated disruption:{" "}

            <strong>
              {delay.initial_delay_days} days
            </strong>

            {" · "}

            Downstream entities:{" "}

            <strong>
              {delay.summary
                ?.downstream_entities ?? 0}
            </strong>

            {" · "}

            Average estimated delay:{" "}

            <strong>
              {Number(
                delay.summary
                  ?.mean_predicted_delay_days || 0
              ).toFixed(2)}{" "}
              days
            </strong>

          </div>

        )}


        {/* ======================================== */}
        {/* 30 / 60 / 90-DAY FORECAST SCENARIOS */}
        {/* ======================================== */}

        <section
          className="forecast-timeline-section"
          style={{ marginTop: 24, marginBottom: 24 }}
        >
          <ForecastTimeline
            forecast={forecast}
            loading={forecastLoading}
            error={forecastError}
          />
        </section>

        <section
          className="incident-history-section"
          style={{
            marginTop: 24,
            marginBottom: 24,
          }}
        >
          <IncidentHistory
            refreshToken={historyRefreshToken}
          />
        </section>


        {/* ======================================== */}
        {/* RISK ASSESSMENT */}
        {/* ======================================== */}

        <section className="risk-panel">

          <RiskAssessment
            risk={risk}
            loading={riskLoading}
          />

        </section>


        {/* ======================================== */}
        {/* PDF IMPACT REPORT */}
        {/* ======================================== */}

        <section className="report-panel">

          <div>

            <h2>
              Disruption Impact Report
            </h2>

            <p>
              Download a PDF containing
              risk assessment, predicted
              impact, and downstream
              ripple paths.
            </p>

          </div>


          <button
            className="primary-button report-download-button"
            onClick={handleDownloadReport}
            disabled={
              !prediction ||
              !ripple ||
              !risk ||
              downloadingReport ||
              isBusy
            }
          >

            <Download size={18} />

            {downloadingReport
              ? "Generating PDF..."
              : "Download PDF Report"}

          </button>

        </section>


        {/* ======================================== */}
        {/* BOTTOM PANELS */}
        {/* ======================================== */}

        <section className="bottom-grid">


          {/* ====================================== */}
          {/* DISRUPTION IMPACT */}
          {/* ====================================== */}

          <div className="info-panel">

            <div className="panel-heading">

              <h2>
                Disruption Impact
              </h2>

            </div>


            {!prediction ? (

              <p className="empty-state">

                Select an entity and run
                a simulation to view the
                predicted impact.

              </p>

            ) : (

              <>

                <div className="impact-summary">

                  <CheckCircle2
                    color="#22c55e"
                    size={20}
                  />

                  <div>

                    <strong>
                      {prediction.disrupted_entity ||
                        selectedEntity?.label ||
                        selectedNode}
                    </strong>

                    <p>
                      {affectedCount} entities
                      predicted affected.
                    </p>

                  </div>

                </div>


                <div className="impact-counts">

                  <span>
                    Normal: {normalCount}
                  </span>

                  <span>
                    Affected: {affectedCount}
                  </span>

                  <span>
                    Disrupted: {disruptedCount}
                  </span>

                </div>


                <div className="affected-list">

                  {affectedNodes.length === 0 ? (

                    <p className="muted">
                      No affected entities predicted.
                    </p>

                  ) : (

                    affectedNodes.map(
                      (item) => (

                        <div
                          className="affected-item"
                          key={item.node_id}
                        >

                          <span>
                            {item.node_name ||
                              item.node_id}
                          </span>

                          <small>
                            {item.node_type}
                          </small>

                        </div>

                      )
                    )

                  )}

                </div>

              </>

            )}

          </div>


          {/* ====================================== */}
          {/* AVAILABLE SCENARIOS */}
          {/* ====================================== */}

          <div className="info-panel">

            <div className="panel-heading">

              <h2>
                Available Scenarios
              </h2>

            </div>


            <p className="muted">
              {scenarios.length} generated scenarios
            </p>


            <div className="scenario-list">

              {scenarios.slice(0, 10).map(
                (scenario, index) => (

                  <button
                    key={
                      scenario.scenario_id ||
                      index
                    }
                    className="scenario-item"
                    onClick={() =>
                      selectNode(
                        scenario.disrupted_node
                      )
                    }
                    disabled={
                      !scenario.disrupted_node ||
                      isBusy
                    }
                  >

                    <div>

                      <strong>
                        {scenario.disrupted_entity ||
                          scenario.disrupted_node}
                      </strong>

                      <small>
                        {scenario.disruption_type}
                      </small>

                    </div>

                    <span>
                      {scenario.affected_entities ??
                        "—"}{" "}
                      affected
                    </span>

                  </button>

                )
              )}

            </div>

          </div>

        </section>

      </main>

    </div>
  );
}
