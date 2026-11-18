
import re
from functools import lru_cache

import spacy

from backend.app.nlp.event_detector import analyze_event


DISRUPTION_PATTERNS = {
    "PORT_CLOSURE": [
        r"\bport closures?\b",
        r"\bport shutdowns?\b",
        r"\bports? (?:has been |was |is )?closed\b",
    ],
    "STRIKE": [
        r"\bstrikes?\b",
        r"\bwalkouts?\b",
        r"\blabou?r disputes?\b",
        r"\bwork stoppages?\b",
    ],
    "FLOOD": [
        r"\bfloods?\b",
        r"\bflooding\b",
        r"\bheavy rainfall\b",
    ],
    "EARTHQUAKE": [
        r"\bearthquakes?\b",
        r"\bseismic activity\b",
    ],
    "FIRE": [
        r"\bfires?\b",
        r"\bwildfires?\b",
    ],
    "TRANSPORT_DELAY": [
        r"\bshipping delays?\b",
        r"\bshipment delays?\b",
        r"\btransport delays?\b",
        r"\blogistics delays?\b",
        r"\bcargo delays?\b",
        r"\bground stops?\b",
    ],
}


def detect_disruption_type(text):
    normalized = (text or "").lower()

    for disruption_type, patterns in DISRUPTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return disruption_type

    return "OTHER"


@lru_cache(maxsize=1)
def load_nlp():
    return spacy.load("en_core_web_sm")



def extract_news_entities(text):
    doc = load_nlp()(text)

    entities = []
    seen = set()

    for ent in doc.ents:
        if ent.label_ not in {
            "GPE", "LOC", "ORG", "FAC"
        }:
            continue

        name = ent.text.strip()
        key = (name.casefold(), ent.label_)

        if key in seen:
            continue

        seen.add(key)

        entities.append({
            "text": name,
            "label": ent.label_,
        })

    return entities



def analyze_news_article(article, graph_entities):
    text = (
        f"{article.get('title') or ''}. "
        f"{article.get('summary') or ''}"
    )

    named_entities = extract_news_entities(text)

    disruption_type = detect_disruption_type(text)

    # Reuse the existing AtmoGraph graph matcher.
    graph_match = analyze_event(
        text,
        graph_entities,
    )

    matched_entity = graph_match.get(
        "matched_entity"
    )

    confidence = graph_match.get(
        "match_confidence",
        0,
    )

    requires_confirmation = graph_match.get(
        "requires_confirmation",
        True,
    )

    # Unknown event types require manual review.
    if disruption_type == "OTHER":
        requires_confirmation = True

    return {
        "title": article.get("title"),
        "url": article.get("url"),
        "published": article.get("published"),
        "disruption_type": disruption_type,
        "named_entities": named_entities,
        "matched_entity": matched_entity,
        "match_confidence": confidence,
        "requires_confirmation": requires_confirmation,
    }
