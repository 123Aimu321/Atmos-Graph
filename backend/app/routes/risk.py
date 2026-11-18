
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.risk_service import calculate_risk

router = APIRouter(prefix="/api", tags=["Risk Assessment"])


class RiskRequest(BaseModel):
    prediction: dict[str, Any]
    ripple: dict[str, Any]
    disruption_type: str = Field(default="OTHER")


@router.post("/risk-assessment")
def assess_risk(request: RiskRequest):
    try:
        return calculate_risk(
            prediction=request.prediction,
            ripple=request.ripple,
            disruption_type=request.disruption_type,
        )
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
