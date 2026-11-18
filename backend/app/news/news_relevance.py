
import re
from html import unescape

from backend.app.news.news_ner import (
    detect_disruption_type,
)


MIN_RELEVANCE_SCORE = 55


SUPPLY_CHAIN_TERMS = {
    "supply chain",
    "logistics",
    "shipment",
    "shipping",
    "freight",
    "cargo",
    "container",
    "warehouse",
    "port",
    "terminal",
    "vessel",
    "customs",
    "delivery",
    "distribution",
    "manufacturing",
    "rail freight",
    "trucking",
    "air cargo",
}


DISRUPTION_TERMS = {
    "strike",
    "walkout",
    "shutdown",
    "closure",
    "closed",
    "disruption",
    "disrupted",
    "delay",
    "delays",
    "congestion",
    "flood",
    "flooding",
    "earthquake",
    "wildfire",
    "blockade",
    "suspended",
    "ground stop",
    "cancelled",
    "canceled",
}


STRONG_EVENT_PHRASES = {
    "port strike",
    "port closure",
    "cargo delays",
    "shipping delays",
    "supply chain disruption",
    "freight disruption",
    "container backlog",
    "terminal shutdown",
    "logistics disruption",
    "shipment delays",
}


NON_EVENT_PHRASES = {
    "how to",
    "ultimate guide",
    "beginner's guide",
    "shipping guide",
    "shipping tips",
    "everything you need to know",
    "explained:",
    "what is",
    "holiday schedule",
    "shipping calendar",
    "forecast guide",
}


def clean_text(value):
    """Normalize article text and remove HTML."""
    text = unescape(str(value or ""))

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().casefold()


def contains_phrase(text, phrase):
    """
    Match a full phrase, respecting word
    boundaries to avoid partial-word matches.
    """
    escaped = re.escape(phrase)

    return bool(
        re.search(
            rf"(?<!\w){escaped}(?!\w)",
            text,
        )
    )


def find_terms(text, terms):
    return sorted(
        term
        for term in terms
        if contains_phrase(text, term)
    )


def find_explicit_entity_matches(
    article,
    entities,
):
    """
    Only match explicitly mentioned names.

    Do not infer that a real article belongs
    to a synthetic entity merely because it
    mentions the same country or category.
    """
    text = clean_text(
        " ".join([
            str(article.get("title") or ""),
            str(article.get("summary") or ""),
        ])
    )

    matches = []

    for entity in entities or []:
        node_id = entity.get("node_id")
        name = entity.get("node_name")

        if not node_id or not name:
            continue

        normalized_name = clean_text(name)

        # Avoid short/generic names.
        if len(normalized_name) < 6:
            continue

        if not contains_phrase(
            text,
            normalized_name,
        ):
            continue

        matches.append({
            "node_id": node_id,
            "node_name": name,
            "node_type": entity.get(
                "node_type",
                "UNKNOWN",
            ),
            "match_method": "EXACT_NAME",
        })

    # A longer name is generally more specific.
    matches.sort(
        key=lambda item: len(
            item["node_name"]
        ),
        reverse=True,
    )

    return matches


def score_news_article(
    article,
    entities=None,
):
    title = clean_text(
        article.get("title")
    )

    summary = clean_text(
        article.get("summary")
    )

    text = f"{title} {summary}"

    supply_terms = find_terms(
        text,
        SUPPLY_CHAIN_TERMS,
    )

    disruption_terms = find_terms(
        text,
        DISRUPTION_TERMS,
    )

    title_supply_terms = find_terms(
        title,
        SUPPLY_CHAIN_TERMS,
    )

    title_disruption_terms = find_terms(
        title,
        DISRUPTION_TERMS,
    )

    strong_phrases = find_terms(
        text,
        STRONG_EVENT_PHRASES,
    )

    non_event_phrases = find_terms(
        title,
        NON_EVENT_PHRASES,
    )

    detected_type = (
        detect_disruption_type(text)
        or "OTHER"
    )

    entity_matches = (
        find_explicit_entity_matches(
            article,
            entities,
        )
    )

    score = 0
    reasons = []

    if supply_terms:
        score += 20
        reasons.append(
            "Supply-chain terminology detected"
        )

    if disruption_terms:
        score += 25
        reasons.append(
            "Disruption terminology detected"
        )

    if title_supply_terms:
        score += 15
        reasons.append(
            "Supply-chain subject in headline"
        )

    if title_disruption_terms:
        score += 15
        reasons.append(
            "Disruption mentioned in headline"
        )

    if strong_phrases:
        score += 15
        reasons.append(
            "Strong logistics disruption phrase"
        )

    if detected_type != "OTHER":
        score += 10
        reasons.append(
            f"Detected disruption type: {detected_type}"
        )

    if entity_matches:
        score += 5
        reasons.append(
            "Explicit graph entity name detected"
        )

    if non_event_phrases:
        score -= 60
        reasons.append(
            "Headline resembles an informational guide"
        )

    score = max(
        0,
        min(100, score),
    )

    # Require both supply-chain context and
    # evidence of disruption. One category
    # alone should not qualify an article.
    qualifies = (
        score >= MIN_RELEVANCE_SCORE
        and bool(supply_terms)
        and bool(disruption_terms)
        and detected_type != "OTHER"
        and not non_event_phrases
    )

    return {
        "relevance_score": score,
        "is_relevant": qualifies,
        "disruption_type": detected_type,
        "supply_chain_terms": supply_terms,
        "disruption_terms": disruption_terms,
        "strong_event_phrases": strong_phrases,
        "non_event_phrases": non_event_phrases,
        "entity_matches": entity_matches,
        "reasons": reasons,
        "scoring_method": "RULE_BASED_V1",
    }
