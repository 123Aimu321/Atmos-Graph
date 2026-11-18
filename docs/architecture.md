# AtmoGraph — architecture

This architecture matches the **Project 2: AtmoGraph** specification from Infotact (Week 1–4).

## Network and data separation

* **25-node synthetic graph:** 42 directed edges, five entity types; GraphSAGE classification and regression training/evaluation.
* **5,000-node benchmark graph:** 12,000 edges; separate Neo4j-backed **query and visualization stress dataset**. It is not used to train the 25-node model.
* Raw DataCo records are a separate data source. Do not silently claim a direct ground-truth mapping between DataCo, news, and benchmark entities.

## News → prediction flow

    Google News RSS
      -> freshness/deduplication/relevance filters
      -> spaCy named-entity extraction + disruption patterns
      -> suggested entity, Neo4j :Incident (PENDING)
      -> HUMAN CONFIRMATION of one synthetic :Entity
      -> FastAPI prediction pipeline
          -> GraphSAGE node classification
          -> GraphSAGE node delay regression
          -> 30/60/90-day recovery scenarios (assumed half-life)
          -> graph reachability/ripple paths + heuristic risk
      -> validated :ImpactSnapshot
      -> per-entity :IncidentRiskState
      -> WebSocket event: impact.prediction.updated
      -> live React Flow overlay in connected dashboard tabs

## Graph database

    (:Entity {node_id, node_type, region, data_origin})
      -[:CONNECTED {transport_days}]->
    (:Entity)

    (:Incident {incident_id, status})
      -[:AFFECTS]->(:Entity)

    (:Incident)-[:HAS_SNAPSHOT]->(:ImpactSnapshot)
    (:ImpactSnapshot)-[:HAS_RISK_STATE]->(:IncidentRiskState)
    (:IncidentRiskState)-[:FOR_ENTITY]->(:Entity)

Entity `latest_simulated_*` properties represent the *most recently saved hypothetical scenario*, not ground truth about live operations. Historical states remain attached to their immutable snapshot. Incident confirmation is required before saving.

## Interfaces

* FastAPI REST routes for ingestion, confirmation, graph, prediction, delay, forecasts, history, graph explorer, and risk states.
* WebSocket `/ws/incidents` sends incident notifications and confirmed `impact.prediction.updated` payloads.
* React dashboard uses React Flow for colored risk overlays, node details, zoom/pan, and progressive bounded exploration.
* Timeline selector presents 30/60/90-day residual delays; not a learned temporal model.

## Evidence and limitations

Review `INFOTACT_REQUIREMENTS_MATRIX.md` and `TEST_PLAN.md` for milestone status, locally observed test results, and missing real-world verification. No claims of enterprise production readiness are made.
