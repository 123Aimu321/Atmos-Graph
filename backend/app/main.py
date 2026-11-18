
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes.graph import router as graph_router
from backend.app.routes.prediction import router
from backend.app.routes.event_analysis import (
    router as event_analysis_router,
)
from backend.app.routes.ripple import router as ripple_router
from backend.app.routes.risk import router as risk_router
from backend.app.routes.reports import router as reports_router
from backend.app.routes.incidents import (
    router as incidents_router,
)
from backend.app.routes.impacts import (
    router as impacts_router,
)
from backend.app.routes.delay import router as delay_router
from backend.app.routes.forecast import router as forecast_router
from backend.app.routes.realtime import (
    router as realtime_router,
)
from backend.app.routes.impact_states import router as impact_states_router
from backend.app.routes.history import (
    router as history_router,
)
from backend.app.routes.explorer import (
    router as explorer_router,
)


app = FastAPI(
    title="AtmoGraph API",
    description=(
        "Supply-chain disruption simulation and "
        "GraphSAGE prediction API"
    ),
    version="1.0.0",
)

# Local React/Vite development origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)
app.include_router(graph_router)
app.include_router(event_analysis_router)
app.include_router(ripple_router)
app.include_router(risk_router)
app.include_router(reports_router)
app.include_router(incidents_router)
app.include_router(impacts_router)
app.include_router(delay_router)
app.include_router(forecast_router)
app.include_router(realtime_router)
app.include_router(history_router)
app.include_router(impact_states_router)
app.include_router(explorer_router)

@app.get("/")
def home():
    return {
        "project": "AtmoGraph",
        "status": "running",
        "message": "Supply-chain prediction API is active",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AtmoGraph Backend",
    }
