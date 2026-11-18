
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


def parse_publication_date(value):
    """
    Accept RSS dates and ISO 8601 timestamps.
    Return an aware UTC datetime, or None.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()

        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            try:
                parsed = datetime.fromisoformat(
                    text.replace("Z", "+00:00")
                )
            except ValueError:
                return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def is_recent_article(
    article,
    max_age_days=14,
):
    """
    Reject undated, stale, or future-dated news.
    """
    published = parse_publication_date(
        article.get("published")
    )

    if published is None:
        return False

    now = datetime.now(timezone.utc)

    oldest_allowed = now - timedelta(
        days=max_age_days
    )

    return oldest_allowed <= published <= now


def article_identity(article):
    """
    Stable identity for monitor-level deduplication.
    Prefer the article URL, then the title.
    """
    import hashlib

    identifier = (
        article.get("url")
        or article.get("title")
        or ""
    ).strip()

    return hashlib.sha256(
        identifier.encode("utf-8")
    ).hexdigest()
