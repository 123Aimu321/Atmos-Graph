
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.nlp.event_detector import analyze_event
from backend.app.services.prediction_service import (
    predict_disruption,
)

router = APIRouter(prefix="/api", tags=["Event Analysis"])


class EventRequest(BaseModel):
    text: str = Field(min_length=5, max_length=2000)


@router.post("/analyze-event")
def analyze_disruption_event(request: EventRequest):
    # Import the same entities used by the existing API.
    from backend.app.routes.prediction import get_entities

    entity_response = get_entities()

    if isinstance(entity_response, dict):
        entities = entity_response.get("entities", [])
    else:
        entities = entity_response

    analysis = analyze_event(request.text, entities)

    matched = analysis["matched_entity"]

    if not matched:
        return {
            "analysis": analysis,
            "prediction": None,
            "message": (
                "No supply-chain entity was identified. "
                "Please select an entity manually."
            ),
        }

    if analysis["requires_confirmation"]:
        return {
            "analysis": analysis,
            "prediction": None,
            "message": (
                "Please confirm the matched entity "
                "before running the prediction."
            ),
        }

    node_id = matched.get("node_id") or matched.get("id")

    if not node_id:
        raise HTTPException(
            status_code=500,
            detail="Matched entity has no node ID",
        )

    prediction = predict_disruption(node_id)

    return {
        "analysis": analysis,
        "prediction": prediction,
        "message": "Event analyzed successfully.",
    }
