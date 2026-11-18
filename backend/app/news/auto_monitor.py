
import argparse
import json
import logging
import signal
import time

from datetime import datetime, timezone
from pathlib import Path
from backend.app.news.news_relevance import (
    score_news_article,
)
import httpx

from backend.app.news.news_fetcher import (
    fetch_supply_chain_news,
)
from backend.app.news.news_ner import (
    detect_disruption_type,
)
from backend.app.news.news_filters import (
    article_identity,
    is_recent_article,
)


ROOT = Path(__file__).resolve().parents[3]

STATE_FILE = (
    ROOT / "datasets"
    / "processed"
    / "news_monitor_state.json"
)

DEFAULT_API_URL = (
    "http://127.0.0.1:8000"
    "/api/incidents/ingest"
)

LOGGER = logging.getLogger("atmograph.news_monitor")

STOP = False


def stop_monitor(signum, frame):
    global STOP

    STOP = True
    LOGGER.info(
        "Shutdown signal received: %s",
        signum,
    )


def read_state():
    if not STATE_FILE.exists():
        return {"seen_articles": {}}

    try:
        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            data.get("seen_articles"), dict
        ):
            raise ValueError("Invalid state format")

        return data

    except (OSError, ValueError, TypeError):
        LOGGER.warning(
            "State file is unavailable or invalid. "
            "Starting with an empty monitor state."
        )
        return {"seen_articles": {}}


def write_state(state):
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = STATE_FILE.with_suffix(
        ".json.tmp"
    )

    temporary.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary.replace(STATE_FILE)



def find_new_articles(articles, state):
    """
    Apply the same freshness and relevance
    screening used by the ingestion API.
    """
    seen = state["seen_articles"]
    new_articles = []

    for article in articles:
        if not is_recent_article(
            article,
            max_age_days=14,
        ):
            continue

        relevance = score_news_article(
            article
        )

        if not relevance["is_relevant"]:
            continue

        identity = article_identity(article)

        if identity in seen:
            continue

        new_articles.append(
            (identity, article)
        )

    return new_articles



def trigger_ingestion(api_url):
    """
    Call the existing FastAPI endpoint.

    FastAPI performs NLP, writes to Neo4j,
    and broadcasts WebSocket notifications.
    """
    with httpx.Client(
        timeout=120,
        trust_env=False,
    ) as client:
        response = client.post(api_url)
        response.raise_for_status()
        return response.json()


def monitor_once(api_url):
    LOGGER.info("Checking RSS news feeds")

    articles = fetch_supply_chain_news(
        limit_per_feed=5
    )

    state = read_state()

    new_articles = find_new_articles(
        articles,
        state,
    )

    LOGGER.info(
        "Fetched=%d, new relevant=%d",
        len(articles),
        len(new_articles),
    )

    if not new_articles:
        LOGGER.info(
            "No new qualifying articles"
        )
        return

    result = trigger_ingestion(api_url)

    LOGGER.info(
        "Ingestion finished: fetched=%s "
        "saved_or_updated=%s failed=%s",
        result.get("fetched"),
        result.get("saved_or_updated"),
        result.get("failed_count"),
    )

    # The HTTP endpoint processes the feed again.
    # Only commit the local seen state if the
    # ingestion completed without article failures.
    #
    # If any item fails, retrying may reprocess
    # already-persisted records. Neo4j MERGE
    # must remain the authoritative deduplicator.
    if result.get("failed_count", 0) > 0:
        LOGGER.warning(
            "Some articles failed. "
            "Retaining state for retry."
        )
        return

    now = datetime.now(
        timezone.utc
    ).isoformat()

    for identity, article in new_articles:
        state["seen_articles"][identity] = {
            "title": article.get("title"),
            "first_seen": now,
        }

    # Keep local state from growing forever.
    # Old entries can be rediscovered after
    # pruning, but the API's date filter and
    # Neo4j MERGE still provide protection.
    if len(state["seen_articles"]) > 5000:
        state["seen_articles"] = dict(
            list(
                state["seen_articles"].items()
            )[-5000:]
        )

    write_state(state)

    LOGGER.info(
        "Recorded %d newly seen articles",
        len(new_articles),
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "AtmoGraph automatic RSS news monitor"
        )
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Polling interval in seconds",
    )

    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
    )

    parser.add_argument(
        "--once",
        action="store_true",
    )

    args = parser.parse_args()

    if args.interval < 60:
        parser.error(
            "--interval must be at least 60 seconds"
        )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s "
            "| %(message)s"
        ),
    )

    signal.signal(
        signal.SIGINT,
        stop_monitor,
    )

    if hasattr(signal, "SIGTERM"):
        signal.signal(
            signal.SIGTERM,
            stop_monitor,
        )

    LOGGER.info(
        "AtmoGraph News Monitor started"
    )

    LOGGER.info(
        "Polling interval: %d seconds",
        args.interval,
    )

    while not STOP:
        try:
            monitor_once(args.api_url)

        except Exception:
            LOGGER.exception(
                "News monitoring cycle failed"
            )

        if args.once:
            break

        # Sleep in short increments so Ctrl+C
        # can stop the process promptly.
        for _ in range(args.interval):
            if STOP:
                break
            time.sleep(1)

    LOGGER.info(
        "AtmoGraph News Monitor stopped"
    )


if __name__ == "__main__":
    main()
