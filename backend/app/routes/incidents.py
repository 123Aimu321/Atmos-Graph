
"""Incident ingestion, review, and real-time update endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.app.news.news_fetcher import fetch_supply_chain_news
from backend.app.news.news_ner import analyze_news_article
from backend.app.news.news_filters import (
    is_recent_article,
)
from backend.app.news.news_relevance import (
    score_news_article,
)
from backend.app.realtime.manager import manager
from backend.app.routes.graph import load_graph_entities
from backend.app.services.incident_service import (
    confirm_incident,
    list_incidents,
    reject_incident,
    save_incident,
)
from backend.app.services.news_intelligence_service import (
    save_news_intelligence,
    enrich_incidents,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
)

VALID_STATUSES = {"PENDING", "CONFIRMED", "REJECTED"}


class ConfirmIncidentRequest(BaseModel):
    node_id: str = Field(
        min_length=1,
        description="Synthetic supply-chain entity ID",
    )


def _ingest_news_sync() -> dict:
    """Perform blocking RSS/NLP/Neo4j work in a worker thread."""

    entities = load_graph_entities()

    if not entities:
        raise RuntimeError("No supply-chain entities available")

    articles = fetch_supply_chain_news(limit_per_feed=5)

    saved = []
    skipped = 0
    failed = []

    for article in articles:
        try:
            # Ignore old or undated news.
            if not is_recent_article(
                article,
                max_age_days=14,
            ):
                skipped += 1
                continue

            # Calculate article relevance.
            relevance = score_news_article(
                article,
                entities,
            )

            # Skip irrelevant articles.
            if not relevance["is_relevant"]:
                skipped += 1
                continue

            # Analyze disruption information.
            analysis = analyze_news_article(
                article,
                entities,
            )

            disruption_type = analysis.get(
                "disruption_type",
                "OTHER",
            )

            if disruption_type == "OTHER":
                skipped += 1
                continue

            # Save incident in Neo4j.
            incident = save_incident(
                article,
                analysis,
            )

            # Persist relevance metadata in Neo4j.
            intelligence = save_news_intelligence(
                incident_id=incident["incident_id"],
                relevance=relevance,
                article=article,
            )

            # Merge incident and intelligence information.
            response_incident = {
                **incident,
                **intelligence,
            }

            saved.append(response_incident)

        except Exception as exc:
            logger.exception(
                "Failed to process article: %s",
                article.get("title"),
            )

            failed.append({
                "title": article.get(
                    "title",
                    "Unknown article",
                ),
                "error": str(exc),
            })

    return {
        "message": "News ingestion completed",
        "fetched": len(articles),
        "saved_or_updated": len(saved),
        "skipped": skipped,
        "failed_count": len(failed),
        "failed": failed,
        "incidents": saved,
    }


async def _broadcast_safely(
    event_type: str,
    payload: dict,
) -> None:
    """A broken WebSocket must not turn a successful database write into HTTP 503."""

    try:
        await manager.broadcast(
            event_type,
            payload,
        )

    except Exception:
        logger.exception(
            "Could not broadcast WebSocket event %s",
            event_type,
        )


@router.post("/ingest")
async def ingest_news():
    """Ingest RSS incidents; they remain PENDING until reviewed."""

    try:
        result = await run_in_threadpool(
            _ingest_news_sync,
        )

    except Exception as exc:
        logger.exception("News ingestion failed")

        raise HTTPException(
            status_code=503,
            detail=f"News ingestion failed: {exc}",
        ) from exc

    if result["saved_or_updated"] > 0:
        await _broadcast_safely(
            "incidents.ingested",
            {
                "fetched": result["fetched"],
                "saved_or_updated": result["saved_or_updated"],
                "skipped": result["skipped"],
                "failed_count": result["failed_count"],
            },
        )

    return result


@router.get("")
async def get_incidents(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    status: str | None = None,
):
    """List Neo4j incidents, optionally filtered by status."""

    normalized_status = (
        status.strip().upper()
        if status is not None
        else None
    )

    if (
        normalized_status is not None
        and normalized_status not in VALID_STATUSES
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid incident status. "
                "Use PENDING, CONFIRMED, or REJECTED."
            ),
        )

    try:
        # Retrieve incidents from Neo4j.
        incidents = await run_in_threadpool(
            list_incidents,
            limit=limit,
            status=normalized_status,
        )

        # Enrich incidents with persistent relevance metadata.
        incidents = await run_in_threadpool(
            enrich_incidents,
            incidents,
        )

    except Exception as exc:
        logger.exception("Unable to load incidents")

        raise HTTPException(
            status_code=503,
            detail=f"Unable to load incidents: {exc}",
        ) from exc

    return {
        "total": len(incidents),
        "incidents": incidents,
    }


@router.post("/{incident_id}/confirm")
async def confirm(
    incident_id: str,
    request: ConfirmIncidentRequest,
):
    """Confirm a PENDING incident and link to a synthetic Entity."""

    try:
        result = await run_in_threadpool(
            confirm_incident,
            incident_id=incident_id,
            node_id=request.node_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Failed to confirm incident")

        raise HTTPException(
            status_code=503,
            detail=f"Failed to confirm incident: {exc}",
        ) from exc

    await _broadcast_safely(
        "incident.confirmed",
        {
            "incident_id": incident_id,
            "node_id": request.node_id,
            "status": "CONFIRMED",
        },
    )

    return {
        "message": "Incident confirmed successfully",
        "incident": result,
    }


@router.post("/{incident_id}/reject")
async def reject(incident_id: str):
    """Reject a PENDING incident."""

    try:
        result = await run_in_threadpool(
            reject_incident,
            incident_id=incident_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Failed to reject incident")

        raise HTTPException(
            status_code=503,
            detail=f"Failed to reject incident: {exc}",
        ) from exc

    await _broadcast_safely(
        "incident.rejected",
        {
            "incident_id": incident_id,
            "status": "REJECTED",
        },
    )

    return {
        "message": "Incident rejected successfully",
        "incident": result,
    }
