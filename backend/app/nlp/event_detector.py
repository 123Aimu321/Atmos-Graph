
import re
from difflib import SequenceMatcher

DISRUPTION_KEYWORDS = {
    "FLOOD": [
        "flood", "flooding", "heavy rainfall",
        "monsoon", "waterlogging"
    ],
    "STRIKE": [
        "strike", "labor protest",
        "workers protest", "walkout"
    ],
    "PORT_CLOSURE": [
        "port closure", "port shutdown",
        "port closed", "terminal shutdown"
    ],
    "TRANSPORT_DELAY": [
        "shipment delay", "shipping delay",
        "transport delay", "traffic disruption",
        "logistics delay"
    ],
    "FIRE": [
        "fire", "warehouse fire",
        "factory fire", "blaze"
    ],
    "EARTHQUAKE": [
        "earthquake", "seismic activity",
        "tremor"
    ],
}


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def detect_disruption_type(text: str) -> str:
    normalized = normalize(text)

    for disruption_type, keywords in DISRUPTION_KEYWORDS.items():
        for keyword in keywords:
            if normalize(keyword) in normalized:
                return disruption_type

    return "OTHER"


def detect_entity(text: str, entities: list[dict]):
    normalized_text = normalize(text)

    # Prefer an exact entity-name match.
    for entity in entities:
        name = entity.get("node_name") or entity.get("label")

        if name and normalize(name) in normalized_text:
            return entity, 1.0

    # Fuzzy matching is a fallback, not proof of identity.
    best_entity = None
    best_score = 0.0

    for entity in entities:
        name = entity.get("node_name") or entity.get("label")

        if not name:
            continue

        score = SequenceMatcher(
            None,
            normalize(name),
            normalized_text
        ).ratio()

        if score > best_score:
            best_score = score
            best_entity = entity

    if best_score >= 0.65:
        return best_entity, round(best_score, 3)

    return None, 0.0


def analyze_event(text: str, entities: list[dict]):
    entity, confidence = detect_entity(text, entities)

    return {
        "event_text": text,
        "disruption_type": detect_disruption_type(text),
        "matched_entity": entity,
        "match_confidence": confidence,
        "requires_confirmation": confidence < 1.0,
    }
