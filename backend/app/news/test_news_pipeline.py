
import httpx

from backend.app.news.news_fetcher import (
    fetch_supply_chain_news,
)
from backend.app.news.news_ner import (
    analyze_news_article,
    extract_news_entities,
)

API_BASE_URL = "http://127.0.0.1:8000"


def get_graph_entities():
    url = f"{API_BASE_URL}/api/entities"

    with httpx.Client(timeout=20) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return (
            data.get("entities")
            or data.get("nodes")
            or []
        )

    raise ValueError(
        "Unexpected response from /api/entities"
    )


def main():
    print("=" * 60)
    print("ATMOGRAPH NEWS INGESTION TEST")
    print("=" * 60)

    print("\n[1] Testing spaCy NER")

    sample_text = (
        "A major strike at Mumbai Port in India "
        "has disrupted international shipping."
    )

    entities = extract_news_entities(sample_text)

    print("Extracted entities:", entities)

    print("\n[2] Loading supply-chain entities")

    graph_entities = get_graph_entities()

    print(
        "Loaded graph entities:",
        len(graph_entities),
    )

    if not graph_entities:
        raise RuntimeError(
            "No entities returned from /api/entities"
        )

    print("\n[3] Fetching live news")

    articles = fetch_supply_chain_news(
        limit_per_feed=5
    )

    print(
        "Fetched articles:",
        len(articles),
    )

    print("\n[4] Analyzing news articles")

    for article in articles[:10]:
        result = analyze_news_article(
            article,
            graph_entities,
        )

        print("\n" + "-" * 60)
        print("Title:", result["title"])
        print(
            "Disruption:",
            result["disruption_type"],
        )
        print(
            "Named entities:",
            result["named_entities"],
        )
        print(
            "Matched graph entity:",
            result["matched_entity"],
        )
        print(
            "Confidence:",
            result["match_confidence"],
        )
        print(
            "Requires confirmation:",
            result["requires_confirmation"],
        )


if __name__ == "__main__":
    main()
