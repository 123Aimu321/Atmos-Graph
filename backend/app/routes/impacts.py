
from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import BaseModel

from backend.app.services.impact_service import (
    save_impact_snapshot,
    get_impact_snapshot,
)

router = APIRouter(
    prefix="/api/impacts",
    tags=["Impact Snapshots"],
)


class ImpactSnapshotRequest(BaseModel):
    prediction: dict


@router.post("/{incident_id}")
def save_impact(
    incident_id: str,
    request: ImpactSnapshotRequest,
):
    try:
        return save_impact_snapshot(
            incident_id,
            request.prediction,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Impact save failed: {exc}",
        )


@router.get("/{incident_id}")
def get_impact(incident_id: str):
    try:
        return get_impact_snapshot(
            incident_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Impact load failed: {exc}",
        )
