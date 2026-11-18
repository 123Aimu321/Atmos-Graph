
import logging

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from fastapi.concurrency import (
    run_in_threadpool,
)
from backend.app.realtime.manager import manager
from pydantic import BaseModel

from backend.app.services.history_service import (
    save_history_snapshot,
    list_history_snapshots,
    get_history_snapshot,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/history",
    tags=["Incident Impact History"],
)


class SaveHistoryRequest(BaseModel):
    prediction: dict
    delay: dict | None = None
    forecast: dict | None = None
    ripple: dict | None = None
    risk: dict | None = None



@router.post("/incidents/{incident_id}/snapshots")
async def save_snapshot(
    incident_id: str,
    request: SaveHistoryRequest,
):
    try:
        snapshot = await run_in_threadpool(
            save_history_snapshot,
            incident_id=incident_id,
            prediction=request.prediction,
            delay=request.delay,
            forecast=request.forecast,
            ripple=request.ripple,
            risk=request.risk,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Failed to save history snapshot"
        )

        raise HTTPException(
            status_code=503,
            detail="History storage unavailable",
        ) from exc

    # The database write has succeeded.
    # Notification failure must not cause the
    # API to report that storage failed.
    try:
        await manager.broadcast(
            "impact.snapshot.created",
            {
                "incident_id": incident_id,
                "snapshot_id": (
                    snapshot["snapshot_id"]
                ),
                "source_node_id": (
                    request.delay.get("disrupted_node")
                    if request.delay
                    else None
                ),
                "created_at": snapshot["created_at"],
                "data_origin": (
                    "SYNTHETIC_SIMULATION"
                ),
            },
        )

    except Exception:
        logger.exception(
            "Snapshot saved but WebSocket "
            "notification failed"
        )

    # Broadcast the confirmed, validated simulation so that
    # another connected dashboard can update its predictive
    # overlay without manually starting another model run.
    # This is an experimental SYNTHETIC_SIMULATION event.
    try:
        await manager.broadcast(
            "impact.prediction.updated",
            {
                "incident_id": incident_id,
                "snapshot_id": snapshot["snapshot_id"],
                "source_node_id": (
                    request.prediction.get("disrupted_node")
                ),
                "data_origin": "SYNTHETIC_SIMULATION",
                "prediction": request.prediction,
                "delay": request.delay,
                "forecast": request.forecast,
                "ripple": request.ripple,
                "risk": request.risk,
            },
        )
    except Exception:
        logger.exception(
            "Snapshot saved but predictive overlay "
            "broadcast failed"
        )

    return {
        "message": "Snapshot saved",
        "snapshot": snapshot,
    }



@router.get("/incidents/{incident_id}/snapshots")
async def list_snapshots(
    incident_id: str,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):
    try:
        snapshots = await run_in_threadpool(
            list_history_snapshots,
            incident_id,
            limit,
        )

        return {
            "incident_id": incident_id,
            "total": len(snapshots),
            "snapshots": snapshots,
        }

    except Exception as exc:
        logger.exception(
            "Failed to list history snapshots"
        )

        raise HTTPException(
            status_code=503,
            detail="History storage unavailable",
        ) from exc


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    try:
        snapshot = await run_in_threadpool(
            get_history_snapshot,
            snapshot_id,
        )

    except Exception as exc:
        logger.exception(
            "Failed to retrieve history snapshot"
        )

        raise HTTPException(
            status_code=503,
            detail="History storage unavailable",
        ) from exc

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Snapshot not found",
        )

    return snapshot
