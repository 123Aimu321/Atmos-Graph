
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.forecast_service import (
    forecast_disruption,
)


router = APIRouter(
    prefix="/api/forecast",
    tags=["Forecast Scenarios"],
)


class ForecastRequest(BaseModel):
    disrupted_node: str = Field(min_length=1)

    initial_delay_days: float = Field(
        default=14.0, ge=1, le=90
    )

    decay: float = Field(
        default=0.75, ge=0.5, le=0.95
    )

    recovery_half_life_days: float = Field(
        default=30.0, ge=1, le=180
    )


@router.post("/predict")
def forecast_endpoint(request: ForecastRequest):
    try:
        return forecast_disruption(
            disrupted_node=request.disrupted_node,
            initial_delay_days=request.initial_delay_days,
            decay=request.decay,
            recovery_half_life_days=(
                request.recovery_half_life_days
            ),
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
