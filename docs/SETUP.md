# AtmoGraph setup and reproducible local demonstration

> Development/research prototype. Python 3.11, Node.js 20+, Neo4j Desktop or a Neo4j server. Do not put passwords or proprietary/private datasets into public GitHub.

## Dependencies

PowerShell from the repository root:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    python -m spacy download en_core_web_sm

Frontend in another terminal:

    cd frontend
    npm ci
    npm run dev

## Neo4j environment

Copy `.env.example` to `.env` and set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`. The implementation reads `NEO4J_USERNAME` (not `NEO4J_USER`). Keep `.env` untracked.

## Rebuild the 25-node synthetic prediction network

The CSVs and trained `.pt` checkpoints are ignored by Git; a fresh clone therefore needs to recreate them.

Run these commands from the repository root, in order:

    python -m ml.preprocessing.generate_synthetic_network
    python -m ml.scenarios.generate_scenarios
    python -m ml.gnn.prepare_dataset
    python -m ml.preprocessing.import_graph
    python -m ml.gnn.train_gnn
    python -m ml.gnn.delay_regression --train

Import is intended for a **development** Neo4j database. Back it up and inspect the importer before using it against existing persistent data. Do not delete unrelated nodes or relationships.

## Start backend

    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

Open `http://127.0.0.1:8000/docs`. React dev server: `http://127.0.0.1:5173`.

## Optional news monitor

    python -m backend.app.news.auto_monitor --interval 900

The monitor requires access to Google News RSS. Detection and matching can be wrong; confirmation is human reviewed.

## Optional 5,000-node benchmark (separate from trained model)

    python -m ml.benchmark.generate_network --nodes 5000
    python -m ml.benchmark.import_network --batch-size 500
    python -m ml.benchmark.benchmark_api --repetitions 100

Use `ml.benchmark.reset_network` when intentionally changing benchmark sizes, after reviewing its deletion scope. 5,000-node database graph exploration is bounded to keep browser memory controlled.

## Verification

    python tests/test_system_smoke.py
    python tests/test_integration.py
    python tests/audit_impact_history.py

The first two require a running backend and a populated local graph.

After confirming a synthetic incident and saving one new snapshot, query:

    MATCH (i:Incident)-[:HAS_SNAPSHOT]->(s:ImpactSnapshot)-[:HAS_RISK_STATE]->(rs:IncidentRiskState)-[:FOR_ENTITY]->(e:Entity)
    RETURN i.incident_id, s.snapshot_id, count(DISTINCT e) AS entity_states
    ORDER BY entity_states DESC;

For newly saved snapshots, `entity_states` should equal 25.

## Deployment limitations

The included GitHub CI checks Python syntax and the frontend production build. It cannot prove that the GNN trains successfully, that a database is running, or that multi-client WebSockets work. Confirm these separately in an isolated test environment.
