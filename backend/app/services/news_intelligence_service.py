
import os

from backend.app.database.neo4j_connection import (
    get_driver,
)


def _database_name():
    return os.getenv("NEO4J_DATABASE", "neo4j")


def save_news_intelligence(
    incident_id,
    relevance,
    article,
):
    """
    Persist scoring evidence on an existing
    Incident node.

    Does not change PENDING/CONFIRMED/REJECTED
    status or the confirmed graph entity.
    """
    if not incident_id:
        raise ValueError("incident_id is required")

    matches = relevance.get("entity_matches") or []

    distinct_matches = {
        item["node_id"]: item
        for item in matches
        if item.get("node_id")
    }

    suggested = (
        next(iter(distinct_matches.values()))
        if len(distinct_matches) == 1
        else None
    )

    query = """
    MATCH (i:Incident {incident_id: $incident_id})
    SET
        i.relevance_score = $score,
        i.relevance_method = $method,
        i.relevance_reasons = $reasons,
        i.supply_chain_terms = $supply_terms,
        i.disruption_terms = $disruption_terms,
        i.entity_match_method = $match_method,
        i.exact_match_entity_id = $matched_node,
        i.article_published_raw = $published,
        i.intelligence_updated_at = datetime()
    RETURN i.incident_id AS incident_id
    """

    params = {
        "incident_id": incident_id,
        "score": int(relevance["relevance_score"]),
        "method": relevance.get(
            "scoring_method", "RULE_BASED_V1"
        ),
        "reasons": relevance.get("reasons", []),
        "supply_terms": relevance.get(
            "supply_chain_terms", []
        ),
        "disruption_terms": relevance.get(
            "disruption_terms", []
        ),
        "match_method": (
            "EXACT_NAME"
            if suggested
            else "NONE"
        ),
        "matched_node": (
            suggested["node_id"]
            if suggested
            else None
        ),
        "published": str(
            article.get("published") or ""
        ),
    }

    driver = get_driver()

    with driver.session(
        database=_database_name()
    ) as session:
        record = session.execute_write(
            lambda tx: tx.run(
                query, **params
            ).single()
        )

    if not record:
        raise ValueError(
            f"Incident {incident_id} not found"
        )

    return {
        "incident_id": incident_id,
        "relevance_score": params["score"],
        "relevance_method": params["method"],
        "relevance_reasons": params["reasons"],
        "entity_match_method": params["match_method"],
        "exact_match_entity_id": params["matched_node"],
    }


def enrich_incidents(incidents):
    """
    Attach stored relevance metadata to results
    from the existing list_incidents service.

    Historical incidents with no intelligence
    metadata receive null fields.
    """
    if not incidents:
        return incidents

    ids = [
        item.get("incident_id")
        for item in incidents
        if item.get("incident_id")
    ]

    if not ids:
        return incidents

    query = """
    MATCH (i:Incident)
    WHERE i.incident_id IN $ids
    RETURN
        i.incident_id AS incident_id,
        i.relevance_score AS relevance_score,
        i.relevance_method AS relevance_method,
        i.relevance_reasons AS relevance_reasons,
        i.supply_chain_terms AS supply_chain_terms,
        i.disruption_terms AS disruption_terms,
        i.entity_match_method AS entity_match_method,
        i.exact_match_entity_id AS exact_match_entity_id,
        i.intelligence_updated_at AS intelligence_updated_at
    """

    driver = get_driver()

    with driver.session(
        database=_database_name()
    ) as session:
        records = session.execute_read(
            lambda tx: [
                dict(record)
                for record in tx.run(query, ids=ids)
            ]
        )

    metadata = {
        record["incident_id"]: record
        for record in records
    }

    enriched = []

    for incident in incidents:
        data = metadata.get(
            incident.get("incident_id"),
            {},
        )

        enriched.append({
            **incident,
            "relevance_score": data.get(
                "relevance_score"
            ),
            "relevance_method": data.get(
                "relevance_method"
            ),
            "relevance_reasons": (
                data.get("relevance_reasons") or []
            ),
            "supply_chain_terms": (
                data.get("supply_chain_terms") or []
            ),
            "disruption_terms": (
                data.get("disruption_terms") or []
            ),
            "entity_match_method": data.get(
                "entity_match_method"
            ),
            "exact_match_entity_id": data.get(
                "exact_match_entity_id"
            ),
            "intelligence_updated_at": (
                str(data["intelligence_updated_at"])
                if data.get("intelligence_updated_at")
                else None
            ),
        })

    return enriched
    