"""Incident-scoped, read-only graph risk states."""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend.app.services.incident_risk_state_service import (
    get_latest_incident_risk_states,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/impact-states", tags=["Incident Risk States"]
)


@router.get("/incidents/{incident_id}")
async def read_incident_risk_states(incident_id: str):
    try:
        return await run_in_threadpool(
            get_latest_incident_risk_states,
            incident_id,
        )
    except Exception as exc:
        logger.exception("Could not retrieve incident risk states")
        raise HTTPException(
            status_code=503,
            detail="Incident risk states unavailable",
        ) from exc
