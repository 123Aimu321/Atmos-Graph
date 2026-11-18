
import hashlib
from datetime import datetime, timezone

from backend.app.database.neo4j_connection import (
    get_driver,
    NEO4J_DATABASE,
)


def make_incident_id(article):
    """Generate a stable ID to prevent duplicate news records."""
    source = (
        article.get("url")
        or article.get("title")
        or ""
    ).strip()

    if not source:
        raise ValueError("Article must have a URL or title")

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:24]


def save_incident(article, analysis):
    """
    Save an NLP-analyzed article.

    New incidents start as PENDING.
    Existing confirmation decisions are preserved.
    """
    incident_id = make_incident_id(article)

    query = """
    MERGE (i:Incident {incident_id: $incident_id})
    ON CREATE SET
        i.created_at = datetime(),
        i.status = 'PENDING'

    SET i.title = $title,
        i.source_url = $source_url,
        i.published = $published,
        i.disruption_type = $disruption_type,
        i.match_confidence = $match_confidence,
        i.suggested_entity_id = $suggested_entity_id,
        i.requires_confirmation = $requires_confirmation,
        i.updated_at = datetime()

    RETURN i {
        .*,
        created_at: toString(i.created_at),
        updated_at: toString(i.updated_at),
        confirmed_at: toString(i.confirmed_at)
    } AS incident
    """

    matched = analysis.get("matched_entity") or {}

    parameters = {
        "incident_id": incident_id,
        "title": article.get("title", ""),
        "source_url": article.get("url", ""),
        "published": article.get("published", ""),
        "disruption_type": analysis.get(
            "disruption_type", "OTHER"
        ),
        "match_confidence": float(
            analysis.get("match_confidence") or 0
        ),
        "suggested_entity_id": (
            matched.get("node_id")
            or matched.get("id")
        ),
        "requires_confirmation": bool(
            analysis.get("requires_confirmation", True)
        ),
    }

    driver = get_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.run(query, **parameters).single()

    return record["incident"]


def list_incidents(limit=50, status=None):
    if not 1 <= limit <= 200:
        raise ValueError("Limit must be between 1 and 200")

    query = """
    MATCH (i:Incident)
    WHERE $status IS NULL OR i.status = $status

    OPTIONAL MATCH (i)-[:AFFECTS]->(e:Entity)

    WITH i, collect(
        CASE
            WHEN e IS NULL THEN null
            ELSE {
                node_id: e.node_id,
                node_name: e.node_name
            }
        END
    ) AS entities

    RETURN i {
        .*,
        created_at: toString(i.created_at),
        updated_at: toString(i.updated_at),
        confirmed_at: toString(i.confirmed_at),
        affected_entities: entities
    } AS incident

    ORDER BY i.created_at DESC
    LIMIT $limit
    """

    driver = get_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(
            query,
            status=status,
            limit=limit,
        )

        return [
            record["incident"]
            for record in records
        ]


def confirm_incident(incident_id, node_id):
    """
    Link an incident to a confirmed synthetic graph entity.

    This does not overwrite the entity's base properties
    or change its global risk state.
    """

    query = """
    MATCH (i:Incident {incident_id: $incident_id})
    MATCH (e:Entity {node_id: $node_id})
    WHERE e.data_origin = 'SYNTHETIC'
      AND i.status = 'PENDING'

    OPTIONAL MATCH (i)-[old:AFFECTS]->(:Entity)
    DELETE old

    MERGE (i)-[:AFFECTS]->(e)

    SET i.status = 'CONFIRMED',
        i.confirmed_entity_id = e.node_id,
        i.confirmed_at = datetime(),
        i.updated_at = datetime()

    RETURN i.incident_id AS incident_id,
           i.status AS status,
           i.disruption_type AS disruption_type,
           e.node_id AS node_id,
           e.node_name AS node_name,
           toString(i.confirmed_at) AS confirmed_at
    """

    driver = get_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.run(
            query,
            incident_id=incident_id,
            node_id=node_id,
        ).single()

    if record is None:
        raise ValueError(
            "Incident not pending, incident not found, "
            "or synthetic entity not found"
        )

    return dict(record)


def reject_incident(incident_id):
    query = """
    MATCH (i:Incident {incident_id: $incident_id})
    WHERE i.status = 'PENDING'

    SET i.status = 'REJECTED',
        i.updated_at = datetime()

    RETURN i.incident_id AS incident_id,
           i.status AS status
    """

    driver = get_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.run(
            query,
            incident_id=incident_id,
        ).single()

    if record is None:
        raise ValueError(
            "Incident not found or not pending"
        )

    return dict(record)
