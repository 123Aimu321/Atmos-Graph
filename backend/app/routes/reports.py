
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from io import BytesIO

from backend.app.services.report_service import (
    build_impact_report,
)

router = APIRouter(prefix="/api", tags=["Reports"])


class ReportRequest(BaseModel):
    prediction: dict[str, Any]
    ripple: dict[str, Any]
    risk: dict[str, Any]
    event_text: str | None = None
    analysis: dict[str, Any] | None = None


@router.post("/reports/impact")
def generate_impact_report(request: ReportRequest):
    try:
        pdf_bytes = build_impact_report(
            prediction=request.prediction,
            ripple=request.ripple,
            risk=request.risk,
            event_text=request.event_text,
            analysis=request.analysis,
        )

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    'attachment; filename="AtmoGraph_Impact_Report.pdf"'
            },
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate impact report",
        ) from exc
