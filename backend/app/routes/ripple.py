
from fastapi import APIRouter, HTTPException

from backend.app.services.ripple_service import (
    analyze_ripple,
)

router = APIRouter(prefix="/api", tags=["Ripple Analysis"])


@router.get("/ripple/{node_id}")
def get_ripple_analysis(node_id: str):
    try:
        return analyze_ripple(node_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Ripple analysis is unavailable.",
        )
