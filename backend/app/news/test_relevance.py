
from backend.app.news.news_relevance import (
    score_news_article,
)


TEST_ARTICLES = [
    {
        "title": (
            "Port workers strike causes "
            "cargo shipping delays"
        ),
        "summary": (
            "A port strike has disrupted "
            "container freight operations."
        ),
    },
    {
        "title": (
            "Shipping delays guide: "
            "how to prepare for holidays"
        ),
        "summary": (
            "Advice for customers about "
            "delivery delays."
        ),
    },
    {
        "title": (
            "New smartphone launched"
        ),
        "summary": (
            "The latest smartphone includes "
            "new camera technology."
        ),
    },
    {
        "title": (
            "Mumbai Port closure disrupts "
            "cargo shipments"
        ),
        "summary": (
            "Operations at Mumbai Port "
            "remain delayed."
        ),
    },
]


GRAPH_ENTITIES = [
    {
        "node_id": "PORT_001",
        "node_name": "Mumbai Port",
        "node_type": "PORT",
    },
]


def main():
    for article in TEST_ARTICLES:
        result = score_news_article(
            article,
            GRAPH_ENTITIES,
        )

        print(
            "\nTitle:",
            article["title"],
        )

        print(
            "Score:",
            result["relevance_score"],
        )

        print(
            "Relevant:",
            result["is_relevant"],
        )

        print(
            "Disruption:",
            result["disruption_type"],
        )

        print(
            "Entity matches:",
            result["entity_matches"],
        )


if __name__ == "__main__":
    main()
