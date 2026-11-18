# Infotact AtmoGraph — requirement traceability

Source: Infotact PROJECT.pdf, Project 2, pages 2–3. This file tracks the actual code against the assigned week-wise deliverables. Project outputs on the 25-node graph are synthetic experiments, not real-world forecasts.

| Milestone | Required output | Implementation and verification | Status |
| --- | --- | --- | --- |
| Week 1 backend | Neo4j graph, supply-chain nodes/edges, Cypher ingestion | `ml/preprocessing/import_graph.py`, `backend/app/database`, `/api/graph`; 25 nodes and 42 relationships in the tested local graph | Implemented locally |
| Week 1 frontend | Static/interactive React graph | `frontend/src/components/SupplyChainGraph.jsx` (React Flow) | Implemented |
| Week 2 backend | News text, spaCy NER, entity extraction and Neo4j risk state | `backend/app/news`, `backend/app/nlp`, manual incident confirmation; per-entity **simulated** statuses stored as `IncidentRiskState` on snapshot save | Implemented as reviewed, incident-scoped simulation; NOT automatic operational ground truth |
| Week 2 frontend | Graph zoom, pan, entity click | `SupplyChainGraph.jsx`, `GraphExplorer.jsx` | Implemented |
| Mid-review backend | Demonstrable extraction and Neo4j insertion | `/api/incidents/ingest` and review endpoints; demonstration still needs live feed + confirmed entity test | Partially demonstrated |
| Mid-review frontend | Render thousands of connected nodes without freezing | 5,000-node/12,000-edge **database** benchmark; bounded React Flow view defaults to 300 nodes, with opt-in 1,200-node virtualization mode; performance of 1,000+ rendered nodes has **not** been measured | Partially demonstrated |
| Week 3 backend | PyTorch Geometric GraphSAGE node regression and multi-hop propagation | `ml/gnn/delay_regression.py` and prediction APIs; synthetic MAE 0.357 days, RMSE 0.644 days in earlier evaluation | Implemented, synthetic only |
| Week 3 frontend | Highlight at-risk nodes | `SupplyChainGraph.jsx` and delay overlays | Implemented |
| Week 4 backend | WebSocket/FastAPI streams live predicted ripple effects | `/ws/incidents`; incident confirmation runs pipeline; `impact.prediction.updated` broadcasts validated saved simulation to other clients | Implemented in refactor; multi-client end-to-end test pending |
| Week 4 frontend | Timeline slider, 30/60/90-day states | `ForecastTimeline.jsx` has both discrete horizon buttons and a keyboard-accessible three-position range slider | Implemented; browser verification pending |
| Final review | Multi-hop GNN for disruption identified from unstructured news | News NLP + human confirmation + GNN classification/regression + history snapshot; not proven for real-world industrial outcomes | Research prototype |
| Final review | Enterprise-grade dashboard | React app, bounded graph explorer, API, WebSocket; no production authentication, roles, monitoring or real-data validation | Not production-ready |
| Common feature | Dockerized reproducibility | Optional Docker files; training data/checkpoints require preprocessing/retraining locally | Partial |
| Assignment deliverables | Source, documentation, report, PPT, evaluation, demo | Source and core testing done; report and presentation must be delivered separately | Pending report/PPT |

## Verified local results supplied by project author

* Smoke: 11/11 basic API tests passed.
* Integration: 10/10 checks passed, including prediction, regression, and 30/60/90 scenarios.
* Benchmark: 5,000 nodes / 12,000 relationships. Mean API search latency 23.63 ms and 4-hop neighborhood mean 161.34 ms (100 requests each).
* Impact history: one persisted snapshot linked to a synthetic test incident; no failures in the last audit.

## Important scientific boundary

The *30/60/90-day* screen shows how hypothetical residual delays recover over time under a chosen exponential half-life. It is **not** evidence that the system can predict a real three-month delay in North American electronics. The training graph has 25 synthetic entities; the 5,000-node benchmark is separate and is not a 5,000-node trained inference graph.

## Required final evidence

1. Show a published news article recognized by NLP, its entity suggestion, and an explicit human confirmation.
2. Show a WebSocket event and the newly colored prediction overlays in a second live browser tab.
3. Show incident-scoped statuses persisted and retrieved from Neo4j.
4. Capture the browser FPS/memory profile when navigating the 5,000-node *database* using the bounded graph explorer; if reviewers require 1,000+ simultaneous nodes, that requires an additional dedicated rendering proof.
5. Capture a tested clean-clone setup, model training, and reproduce a basic prediction.
6. Submit the final technical report, PPT, and demo in accordance with the assignment letter; do not publish confidential HR/assignment documents.
