
from datetime import datetime, timezone

from backend.app.news.news_relevance import (
    score_news_article,
)
from backend.app.services.incident_service import (
    save_incident,
    list_incidents,
)
from backend.app.services.news_intelligence_service import (
    save_news_intelligence,
    enrich_incidents,
)


def main():
    article = {
        "title": (
            "TEST ONLY: Mumbai Port strike "
            "causes cargo shipping delays"
        ),
        "summary": (
            "Simulated port workers strike "
            "disrupts container freight."
        ),
        "url": (
            "https://example.com/"
            "atmograph-intelligence-test"
        ),
        "published": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    entities = [{
        "node_id": "PORT_001",
        "node_name": "Mumbai Port",
        "node_type": "PORT",
    }]

    relevance = score_news_article(
        article,
        entities,
    )

    print(
        "Relevance score:",
        relevance["relevance_score"],
    )

    analysis = {
        "disruption_type": (
            relevance["disruption_type"]
        ),
        "matched_entity": (
            relevance["entity_matches"][0]
            if len(relevance["entity_matches"]) == 1
            else None
        ),
        "match_confidence": 1.0,
        "requires_confirmation": True,
    }

    incident = save_incident(
        article,
        analysis,
    )

    intelligence = save_news_intelligence(
        incident["incident_id"],
        relevance,
        article,
    )

    print("Saved:", intelligence)

    stored = enrich_incidents(
        list_incidents(limit=200)
    )

    matching = [
        item
        for item in stored
        if item["incident_id"]
        == incident["incident_id"]
    ]

    assert matching, "Incident not found"

    assert matching[0]["relevance_score"] == (
        relevance["relevance_score"]
    )

    print(
        "Persistence verified:",
        matching[0]["incident_id"],
    )


if __name__ == "__main__":
    main()
