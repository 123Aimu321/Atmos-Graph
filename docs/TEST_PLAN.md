# AtmoGraph quality and acceptance test plan

## Already observed locally (before alignment refactor)

* 11/11 smoke checks passed; 25-node/42-edge synthetic graph available.
* 10/10 integration checks passed: prediction, regression, forecast, history GET, and local warm latency.
* 5,000-node/12,000-edge Neo4j benchmark: search mean 23.63 ms; 4-hop mean 161.34 ms (each 100 requests).
* One test incident was confirmed and had one saved historical snapshot.

These results were collected on the author's local system and **are not proof that the current refactor branch has passed**.

## Required checks on the new branch

1. **Static/build:** GitHub Actions Python compileall and `npm ci && npm run build` both pass.
2. **Data reproducibility:** Generate the synthetic nodes/edges, prepare scenarios, import to clean Neo4j, train both GraphSAGE models, and run `tests/test_system_smoke.py` and `tests/test_integration.py`.
3. **NLP:** Process a relevant example article and an irrelevant example; verify conservative entity matching, freshness rules, and no duplicate incidents.
4. **Risk state DB:** Confirm a synthetic test incident and save a full prediction snapshot. Query `GET /api/impact-states/incidents/{incident_id}`; expect exactly 25 status entries and one DISRUPTED source. Prior snapshots created before the refactor have no `IncidentRiskState` nodes.
5. **WebSocket end-to-end:** Open two local dashboard tabs. Confirm a test incident in tab A. Watch tab B receive `impact.prediction.updated` and redraw node status and delay overlay. Reload tab B and query history to confirm persistence. Confirming a PENDING incident is a privileged action in a real deployment; this research app has no login.
6. **Graph scalability:** Run the 5,000-node generator/import/benchmark and capture response times. Use DevTools Performance to record browser frame drops and memory while progressively exploring; standard mode shows at most 300 nodes/1,000 edges; opt-in review mode supports up to 1,200 nodes/5,000 edges using React Flow viewport virtualization. Confirm a browser profile at the larger budget; source changes alone do not prove absence of freezing.
7. **Timeline:** Select 30, 60 and 90 days; check nonnegative finite residual delays and correct recovery disclaimer.
8. **Failure cases:** DB unavailable, incorrect Neo4j password, invalid node ID, irrelevant news, rejected incident, missing model checkpoint, expired news item, disconnected WebSocket. Confirm informative error messages and no unintended graph mutations.

## Evidence to collect

Screenshots: incident matching/confirmation; two-tab live graph update; model result overlays; 30/60/90 recovery cards; Neo4j risk-state query; 5,000-node query benchmark; saved-history reload. Save log transcripts and performance measurements in local `reports/testing`, avoiding private credentials.

## Release criteria

The project remains a **research prototype** until the above workflow is confirmed, and stronger real-world evaluation, auth, access control, dataset provenance, and production monitoring are added.
