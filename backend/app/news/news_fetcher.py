
import feedparser
import httpx

from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse
import re


NEWS_FEEDS = {
    "supply_chain": (
        "https://news.google.com/rss/search?"
        "q=supply+chain+disruption&hl=en-US&gl=US&ceid=US:en"
    ),
    "port_disruption": (
        "https://news.google.com/rss/search?"
        "q=port+strike+shipping+disruption"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "logistics": (
        "https://news.google.com/rss/search?"
        "q=logistics+transport+delay"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
}


def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(feed_name, url, limit=10):
    parsed_url = urlparse(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "news.google.com"
    ):
        raise ValueError("Unsupported news feed URL")

    with httpx.Client(
        timeout=20,
        follow_redirects=False,
        headers={
            "User-Agent": "AtmoGraph/1.0 News Research"
        },
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    parsed = feedparser.parse(response.content)

    if parsed.bozo and not parsed.entries:
        raise ValueError(
            f"Could not parse feed: {feed_name}"
        )

    articles = []

    for entry in parsed.entries[:limit]:
        published = entry.get("published", "")

        articles.append(
            {
                "title": clean_html(
                    entry.get("title", "")
                ),
                "summary": clean_html(
                    entry.get("summary", "")
                ),
                "url": entry.get("link", ""),
                "published": published,
                "feed": feed_name,
                "fetched_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )

    return articles


def fetch_supply_chain_news(limit_per_feed=10):
    all_articles = []
    seen = set()

    for name, url in NEWS_FEEDS.items():
        try:
            articles = fetch_feed(
                name,
                url,
                limit_per_feed,
            )

            for article in articles:
                key = (
                    article["url"]
                    or article["title"].lower()
                )

                if key not in seen:
                    seen.add(key)
                    all_articles.append(article)

        except (httpx.HTTPError, ValueError) as exc:
            print(
                f"[WARNING] Feed {name} failed: {exc}"
            )

    return all_articles


if __name__ == "__main__":
    news = fetch_supply_chain_news(5)

    print(f"Fetched {len(news)} articles")

    for article in news[:5]:
        print(
            f"\n{article['title']}\n"
            f"{article['url']}"
        )
