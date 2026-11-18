
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.delay_service import (
    predict_delay,
    get_delay_metrics,
)


router = APIRouter(
    prefix="/api/delay",
    tags=["Delay Regression"],
)


class DelayPredictionRequest(BaseModel):
    disrupted_node: str = Field(min_length=1)

    initial_delay_days: float = Field(
        default=14.0,
        ge=1,
        le=90,
    )

    decay: float = Field(
        default=0.75,
        ge=0.5,
        le=0.95,
    )


@router.post("/predict")
def predict_delay_endpoint(
    request: DelayPredictionRequest,
):
    try:
        return predict_delay(
            disrupted_node=request.disrupted_node,
            initial_delay_days=request.initial_delay_days,
            decay=request.decay,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@router.get("/metrics")
def delay_metrics_endpoint():
    try:
        return get_delay_metrics()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
