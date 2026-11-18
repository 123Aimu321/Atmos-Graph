
# 🌍 AtmoGraph
### AI-Powered Supply Chain Disruption Prediction & Ripple Effect Analysis

AtmoGraph is an AI-powered supply chain disruption analysis platform that uses **Graph Neural Networks (GNNs), GraphSAGE, Natural Language Processing (NLP), Neo4j, and FastAPI** to analyze how disruptions can propagate across interconnected supply chain entities.

The platform provides interactive network visualization, disruption classification, estimated shipment delays, assumption-based recovery forecasts, real-time news monitoring, and historical incident tracking.

> **Project Status:** Research Prototype | AI/ML | Graph Neural Networks | Full-Stack Development

> **Important:** The primary prediction network and training labels are synthetic. Model outputs are experimental and should not be interpreted as validated real-world disruption forecasts.

---

## 📋 Infotact project specification

This implementation follows **Infotact Project 2 — AtmoGraph: Supply Chain Ripple Effect Predictor** (Week 1–4: Neo4j foundations, spaCy ingestion, GraphSAGE delay regression, React Flow risk overlays, WebSocket updates, and a 30/60/90-day slider).

- [Requirement-by-requirement implementation matrix](docs/INFOTACT_REQUIREMENTS_MATRIX.md)
- [Setup and model-training instructions](docs/SETUP.md)
- [Architecture and risk-state schema](docs/architecture.md)
- [API specification](docs/API_documentation.md)
- [Testing and final-review evidence plan](docs/TEST_PLAN.md)

**Important limits:** Predictions are trained on a **25-node synthetic graph**. The 5,000-node network is a **separate benchmark**; its optional 1,200-node browser mode still needs measured performance evidence. Live news is screened and **human-confirmed** before the system saves a simulated impact. The 30/60/90-day outputs describe recovery scenarios, **not validated predictions of actual three-month delays**.

To reproduce the excluded training datasets and model checkpoints, follow [SETUP.md](docs/SETUP.md) after cloning.

---

## 📌 Project Overview

Modern supply chains are highly interconnected. A disruption affecting a port, manufacturer, supplier, or warehouse can influence multiple downstream businesses.

AtmoGraph explores this problem through graph-based modeling and machine learning.

The system represents supply chain entities as nodes and their connections as directed relationships. GraphSAGE analyzes the network to classify potentially affected entities and estimate disruption-related delays.

The application also incorporates news monitoring to identify potentially relevant supply chain disruptions and allows users to review incidents before associating them with the network.

### 🎯 Project Objectives

- Model interconnected supply chains using graph structures.
- Identify potentially affected entities after a disruption.
- Classify supply chain nodes using GraphSAGE.
- Estimate disruption-related delays using GNN regression.
- Simulate recovery scenarios over 30, 60, and 90 days.
- Detect potential disruptions from news articles and text.
- Store incident information and prediction history in Neo4j.
- Visualize disruption propagation through an interactive dashboard.
- Explore large supply chain networks efficiently.

---

## 🚀 Key Features

### 1. Graph Neural Network-Based Disruption Prediction

AtmoGraph uses a GraphSAGE classification model to assign one of three disruption states to each entity:

- 🟢 **NORMAL** — No predicted disruption.
- 🟡 **AFFECTED** — Potential downstream impact.
- 🔴 **DISRUPTED** — Entity selected as the disruption source.

The primary synthetic prediction network contains **25 entities and 42 directed relationships**.

### 2. Supply Chain Ripple Effect Analysis

The platform visualizes how disruptions can propagate through interconnected entities, including:

- Suppliers
- Manufacturers
- Ports
- Warehouses
- Retailers

Users can explore downstream impact and network connectivity through interactive graph visualizations.

### 3. GraphSAGE Delay Regression

A separate GraphSAGE regression model estimates the potential number of delay days associated with a selected disruption scenario.

Users can adjust the initial disruption duration and propagation decay.

For a tested synthetic Mumbai Port scenario:

| Metric | Result |
|---|---:|
| Initial disruption | 14 days |
| Propagation decay | 0.75 |
| Downstream affected entities | 10 |
| Mean downstream delay | 8.10 days |
| Maximum downstream delay | 10.18 days |

These values are experimental predictions trained on synthetic targets.

### 4. Recovery Scenario Forecasting

AtmoGraph calculates residual delay scenarios for three time horizons:

- Day 30
- Day 60
- Day 90

The recovery model uses an assumed exponential half-life rather than a separately trained temporal forecasting model.

**Example scenario:**

| Horizon | Average remaining downstream delay |
|---|---:|
| 30 days | 4.40 days |
| 60 days | 2.20 days |
| 90 days | 1.10 days |

### 5. NLP-Based Disruption Detection

The NLP pipeline analyzes text and news articles to identify disruption categories such as:

- Port closures
- Labor strikes
- Flooding
- Earthquakes
- Fires
- Transportation delays

It combines spaCy-based NLP processing with rule-based detection.

### 6. Automated News Monitoring

AtmoGraph integrates Google News RSS feeds to monitor potentially relevant supply chain news.

Capabilities include:

- Automatic RSS polling
- Publication-date filtering
- Rule-based article relevance scoring
- Duplicate article detection
- Disruption classification
- Conservative entity-name matching
- Incident review and confirmation

The automated monitor can run at a configurable interval.

### 7. Real-Time WebSocket Notifications

FastAPI WebSockets support notifications for events such as:

- Incident ingestion
- Incident confirmation
- Incident rejection
- Saved impact snapshots

Connected dashboards can refresh relevant information without requiring a full browser reload.

### 8. Neo4j Incident Management

Neo4j stores supply chain entities, relationships, incidents, and simulation history.

The workflow allows users to:

- Review pending incidents.
- Confirm or reject incident reports.
- Associate confirmed incidents with supply chain entities.
- Store simulation results for later review.
- Retrieve historical impact snapshots.

### 9. Large-Scale Graph Exploration

A separate graph explorer supports bounded network exploration using React Flow.

It includes:

- Entity search
- Upstream and downstream navigation
- Configurable graph depth
- Progressive node expansion
- Node and edge limits
- Interactive zooming and panning

The explorer was benchmarked using a separate **5,000-node, 12,000-relationship synthetic network**.

The larger benchmark graph is not used by the trained 25-node GraphSAGE prediction model.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python, JavaScript |
| Frontend | React.js, Vite, CSS |
| Backend | FastAPI, Uvicorn |
| Machine Learning | PyTorch, PyTorch Geometric |
| Graph Neural Networks | GraphSAGE |
| NLP | spaCy, regular expressions |
| Graph Database | Neo4j |
| Visualization | React Flow |
| API Communication | REST API, WebSockets |
| News Integration | Google News RSS |
| Data Processing | Pandas, NumPy |
| Testing | Python, HTTPX |
| Development | VS Code, Git, GitHub |

---

## 🏗️ System Architecture

```text
                 ┌─────────────────────┐
                 │  Google News RSS    │
                 │  / User Text Input  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ NLP Event Detection │
                 │ Relevance Screening │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Incident Management │
                 │ Human Verification  │
                 └──────────┬──────────┘
                            │
                            ▼
┌────────────────────────────────────────────────┐
│                 FastAPI Backend                │
│                                                │
│  ┌───────────────────┐ ┌───────────────────┐   │
│  │ GraphSAGE         │ │ GraphSAGE         │   │
│  │ Classification    │ │ Delay Regression  │   │
│  └───────────────────┘ └───────────────────┘   │
│                                                │
│       Recovery Scenario Forecasting            │
│           Ripple Effect Analysis               │
│                                                │
└───────────────┬──────────────────┬─────────────┘
                │                  │
                ▼                  ▼
       ┌────────────────┐  ┌─────────────────┐
       │ Neo4j Database │  │ React Dashboard │
       │                │  │                 │
       │ Entities       │  │ Network Graph   │
       │ Relationships  │  │ Delay Estimates │
       │ Incidents      │  │ Forecasts       │
       │ Impact History │  │ Incident Review │
       └────────────────┘  └─────────────────┘
```

---

## 📂 Project Structure

```text
AtmoGraph/
│
├── backend/
│   └── app/
│       ├── database/
│       ├── news/
│       ├── nlp/
│       ├── realtime/
│       ├── routes/
│       ├── services/
│       └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
├── ml/
│   ├── benchmark/
│   ├── gnn/
│   ├── models/
│   └── scenarios/
│
├── datasets/
│   ├── raw/
│   ├── processed/
│   └── benchmark/
│
├── tests/
│   ├── test_system_smoke.py
│   ├── test_integration.py
│   ├── audit_impact_history.py
│   └── test_history_persistence.py
│
├── reports/
│   └── testing/
│
├── docs/
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation and Setup

### Prerequisites

Make sure the following are installed:

- Python 3.11
- Node.js and npm
- Neo4j Desktop
- Git
- VS Code or another code editor

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/AtmoGraph.git
cd AtmoGraph
```

Replace `YOUR_USERNAME` with your actual GitHub username or clone URL.

### 2. Create a Python Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Backend Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Neo4j

Start your local Neo4j database.

Create a `.env` file in the project root and configure the Neo4j connection using the environment variables expected by your backend.

Example:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
NEO4J_DATABASE=neo4j
```

Replace the password with your local credentials.

**Never upload `.env` or passwords to GitHub.**

The graph datasets and trained model checkpoints must also be prepared or restored before running prediction endpoints.

### 5. Start the Backend

From the project root:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

FastAPI documentation:

http://127.0.0.1:8000/docs

### 6. Start the Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the dashboard:

http://127.0.0.1:5173

### 7. Start Automatic News Monitoring (Optional)

From the project root:

```powershell
python -m backend.app.news.auto_monitor --interval 900
```

This checks RSS feeds every 15 minutes while the monitor process is running.

Run only one monitor instance in the local development setup.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/graph` | Retrieve the supply-chain graph |
| POST | `/api/predict` | GraphSAGE disruption classification |
| GET | `/api/model/metrics` | Classification model metrics |
| POST | `/api/delay/predict` | Estimate disruption delays |
| GET | `/api/delay/metrics` | Delay regression metrics |
| POST | `/api/forecast/predict` | Calculate recovery scenarios |
| POST | `/api/analyze-event` | NLP disruption analysis |
| POST | `/api/incidents/ingest` | Ingest news articles |
| GET | `/api/incidents` | List incidents |
| POST | `/api/incidents/{incident_id}/confirm` | Confirm an incident |
| POST | `/api/incidents/{incident_id}/reject` | Reject an incident |
| GET | `/api/explorer/entities` | Search graph entities |
| GET | `/api/explorer/neighborhood/{node_id}` | Retrieve bounded graph neighborhood |
| POST | `/api/history/incidents/{incident_id}/snapshots` | Save impact history |
| GET | `/api/history/incidents/{incident_id}/snapshots` | List incident snapshots |
| GET | `/api/history/snapshots/{snapshot_id}` | Retrieve a saved snapshot |
| WebSocket | `/ws/incidents` | Receive real-time event notifications |

The complete API schema is available through FastAPI Swagger UI.

---

## 🧠 Machine Learning Models

### GraphSAGE Classification

The classification model uses graph neural network message passing to learn from node information and graph connectivity.

**Output classes:**

```text
NORMAL
AFFECTED
DISRUPTED
```

For the tested synthetic `PORT_001` scenario:

| Class | Entities |
|---|---:|
| NORMAL | 14 |
| AFFECTED | 10 |
| DISRUPTED | 1 |
| Total | 25 |

The classification model achieved 100% accuracy on its held-out synthetic scenario evaluation.

This result reflects the simplicity and structure of the generated labels and does **not** demonstrate real-world classification accuracy.

### GraphSAGE Delay Regression

The delay regression model estimates node-level disruption delays.

Recorded synthetic test metrics:

| Metric | Value |
|---|---:|
| Mean Absolute Error (MAE) | 0.357 days |
| Root Mean Squared Error (RMSE) | 0.644 days |

These metrics are from synthetic propagation targets.

### Recovery Scenario Modeling

The forecast component combines estimated disruption delays with transport-time exposure assumptions and an exponential recovery half-life.

Recovery scenarios are calculated for 30, 60, and 90 days.

These outputs represent **assumption-based scenario projections**, not validated time-series predictions.

---

## 📊 Experimental Results

### Backend Testing

| Test Suite | Passed | Failed |
|---|---:|---:|
| System smoke tests | 11 | 0 |
| Integration tests | 10 | 0 |

### Neo4j Network Benchmark

A separate graph containing 5,000 benchmark nodes and 12,000 directed relationships was used to evaluate bounded graph queries.

| Operation | Mean latency | P95 latency |
|---|---:|---:|
| Entity search | 23.63 ms | 32.33 ms |
| 1-hop neighborhood | 17.12 ms | 19.82 ms |
| 2-hop neighborhood | 57.02 ms | 67.96 ms |
| 3-hop neighborhood | 104.36 ms | 126.76 ms |
| 4-hop neighborhood | 161.34 ms | 186.26 ms |

These measurements were collected locally using 100 HTTP requests per operation.

### Impact History Persistence

The history workflow was verified by saving a simulation snapshot for an explicitly labeled synthetic test incident.

The subsequent Neo4j audit reported:

- 8 confirmed incident records.
- 1 incident with saved impact history.
- 1 stored simulation snapshot.
- 0 history retrieval failures.

---

## 🧪 Running Tests

### System Smoke Tests

```powershell
python tests\test_system_smoke.py
```

### Model and API Integration Tests

```powershell
python tests\test_integration.py
```

### Impact History Audit

```powershell
python tests\audit_impact_history.py
```

### API Performance Benchmark

```powershell
python -m ml.benchmark.benchmark_api --repetitions 100
```

---

## 🔐 Security and Responsible Use

AtmoGraph is designed as a local research prototype.

Before production deployment, the platform would require:

- Authentication and authorization.
- Secure API and WebSocket access.
- Rate limiting and monitoring.
- Database backup and recovery procedures.
- Server-side verification of simulation data.
- Independent validation using real-world supply-chain outcomes.

Real-world news articles should not automatically be treated as evidence that a synthetic graph entity is disrupted.

Incident confirmation requires human verification.

---

## 🔮 Future Enhancements

- Real-world supply chain data integration.
- Temporal graph neural networks.
- Improved entity resolution using semantic embeddings.
- Probabilistic disruption forecasting.
- Automated model monitoring.
- Multi-user authentication and role-based access.
- Cloud deployment and CI/CD pipelines.
- Improved graph layout and performance.
- Supplier risk analysis and alternative route suggestions.
- Real-world validation against historical disruption outcomes.

---

## 👨‍💻 Developer

**Aiman Parker**

B.E. — Artificial Intelligence and Machine Learning

**GitHub:** [123Aimu321](https://github.com/123Aimu321)

**LinkedIn:** [Aiman Parker](https://www.linkedin.com/in/aiman-parker-539aa022b)

---

## 📄 License

No license is currently specified.

If you intend to make the project open source, add a suitable `LICENSE` file and verify that all included datasets and third-party resources can be redistributed.

---

## ⭐ Support

If you find this project useful, consider giving the repository a star.

**AtmoGraph — Exploring Supply Chain Resilience Through Graph AI.**
