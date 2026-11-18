
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.prediction_service import (
    load_prediction_resources,
    predict_disruption,
)


router = APIRouter(prefix="/api", tags=["AtmoGraph"])

ROOT_DIR = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT_DIR / "ml" / "saved_model"


class PredictionRequest(BaseModel):
    disrupted_node: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )


@router.get("/entities")
def get_entities():
    resources = load_prediction_resources()

    nodes = resources["nodes"]

    return {
        "total": len(nodes),
        "entities": nodes.to_dict(orient="records"),
    }


@router.post("/predict")
def predict(request: PredictionRequest):
    try:
        return predict_disruption(request.disrupted_node)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/model/metrics")
def get_model_metrics():
    results = {}

    files = {
        "random_forest": "baseline_metrics.json",
        "graphsage": "gnn_metrics.json",
    }

    for model_name, filename in files.items():
        path = MODEL_DIR / filename

        if not path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Metrics file unavailable: {filename}",
            )

        with open(path, encoding="utf-8") as file:
            results[model_name] = json.load(file)

    return results
