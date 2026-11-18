# Phase 35 — Infotact final acceptance runbook

This is the companion to [INFOTACT_REQUIREMENTS_MATRIX.md](INFOTACT_REQUIREMENTS_MATRIX.md) and [TEST_PLAN.md](TEST_PLAN.md).

The user-supplied Infotact Project 2 specification requires: correctly ingested NLP news, Neo4j graph logic, multi-hop GNN regression, live WebSocket prediction overlays, a 30/60/90-day slider, and a performant React graph showing thousands of interconnected entities.

## Before you start

- Use a LOCAL development Neo4j database; back up persistent data.
- Keep the FastAPI service, trained model checkpoints and processed 25-node synthetic dataset available.
- The separate 5,000-node benchmark database graph is optional for the browser performance trial.
- Do not use real news incidents as writable test fixtures.
- Make sure both clients use `http://127.0.0.1:5173` (the WebSocket development origin allowlist).
- Run `git status` and check out this PR's branch.

## 1. Dependency-free acceptance unit tests

From the project root:

```powershell
python -m unittest discover -s tests -p "test_snapshot_contract_unit.py" -v
```

Expected: 11 unit tests for the validated GraphSAGE classification, delay and forecast snapshot contract, including rejection of wrong sources, nonfinite/negative delays, duplicate IDs, and missing horizons.

## 2. Existing read-only API tests

Start FastAPI, then in another terminal:

```powershell
python tests\test_system_smoke.py
python tests\test_integration.py
```

These require an initialized development Neo4j graph and model checkpoints. Do not confuse these with the independent CI unit tests.

## 3. Two-client WebSocket acceptance

Existing synthetic fixture (created by a previous local test):

- `ATMOGRAPH_PHASE32_TEST_PORT001`
- linked to `PORT_001`
- incident status `CONFIRMED`
- linked Entity has `data_origin = 'SYNTHETIC'`

First, verify the read-only preflight:

```powershell
python tests\acceptance_realtime_history.py
```

This validates the confirmed incident, associated node, GraphSAGE classification, regression and 30/60/90-day forecast without creating a snapshot.

To explicitly create **one new** synthetic test snapshot and verify that two independent WebSocket clients receive the *same* validated prediction event:

```powershell
python tests\acceptance_realtime_history.py --write
```

The test additionally retrieves the persisted snapshot and `GET /api/impact-states/incidents/ATMOGRAPH_PHASE32_TEST_PORT001`, requiring exactly 25 incident-scoped risk states and a unique `PORT_001` disruption source. It will not invent or auto-confirm an incident. Each `--write` invocation adds a new snapshot; run it intentionally and sparingly.

## 4. Browser checks

1. Open two independent browser tabs at `http://127.0.0.1:5173`.
2. Both should display an active WebSocket connection.
3. Confirm a NEW pending synthetic test incident in tab A or rerun the explicit-write acceptance script above. Confirmations only apply to pending events, so reuse of an already confirmed record may not trigger an additional `incident.confirmed` event.
4. Tab B should receive `impact.prediction.updated` and show a colored graph prediction + estimated delays.
5. Select the 30-, 60-, and 90-day forecast positions using the new slider; verify all corresponding summaries update.
6. Inspect the saved snapshot in the incident history panel after a hard refresh.

**Important:** The script proves WebSocket payload delivery at the transport level; it does not automatically prove React rendering in a real browser. The browser test must be recorded separately.

## 5. Large-graph acceptance

1. Confirm the separate 5,000-node graph is present and has 12,000 benchmark edges. If not, follow [SETUP.md](SETUP.md) to safely generate/import it.
2. Open Graph Explorer and select `Benchmark` source.
3. Enable the opt-in **Review benchmark (1,200 nodes)** rendering mode.
4. Try larger-depth selections, different roots and downstream/both directions to reach the maximum populated neighborhood. Use the loaded-node counter as the source of truth.
5. Open browser DevTools → Performance and Memory; record zoom/pan interaction latency, long tasks, FPS, and memory.
6. If the connected 4-hop neighborhood stays well below 1,000 nodes, do **not** claim the mid-review 1,000+ node rendering requirement was demonstrated. The rendering mode's cap is a capacity control, not proof of observed node count.

## 6. Final evidence

Save the following artifacts locally under `reports/testing`: unit test transcript, API smoke and integration test output, acceptance script output (with test snapshot ID), Neo4j risk-state count query, two-tab dashboard screenshots, 30/60/90-day slider screenshots, benchmark JSON, and browser performance profile.

Do not upload confidential Infotact HR documents, credentials, private news full text or third-party copyrighted datasets.

## Current evidence status

The author's historical local measurements were 11/11 smoke, 10/10 integration, 25-node/42-edge synthetic prediction graph, 5,000-node/12,000-edge Neo4j benchmark, and one prior persisted test snapshot. The new acceptance script and browser profile have **not** been run locally yet.
