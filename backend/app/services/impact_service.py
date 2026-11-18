
from backend.app.database.neo4j_connection import (
    get_driver,
    NEO4J_DATABASE,
)


def save_impact_snapshot(
    incident_id,
    prediction,
):
    """
    Persist predicted impact for a confirmed incident.

    Predictions remain incident-specific and
    are not treated as verified real-world states.
    """

    results = prediction.get("results", [])

    if not results:
        raise ValueError(
            "Prediction contains no results"
        )

    valid_statuses = {
        "NORMAL",
        "AFFECTED",
        "DISRUPTED",
    }

    rows = []

    for item in results:
        status = item.get("predicted_status")
        node_id = item.get("node_id")

        if (
            not node_id
            or status not in valid_statuses
        ):
            raise ValueError(
                "Invalid prediction result"
            )

        rows.append({
            "node_id": node_id,
            "status": status,
        })

    driver = get_driver()

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        incident = session.run(
            """
            MATCH (i:Incident {
                incident_id: $incident_id
            })
            WHERE i.status = 'CONFIRMED'
              AND EXISTS {
                MATCH (i)-[:AFFECTS]->(:Entity)
              }
            RETURN i.incident_id AS id
            """,
            incident_id=incident_id,
        ).single()

        if incident is None:
            raise ValueError(
                "Incident must be confirmed "
                "before saving impact"
            )

        # Delete only previous impact predictions
        # for this incident, not the supply-chain graph.
        session.run(
            """
            MATCH (i:Incident {
                incident_id: $incident_id
            })-[r:PREDICTED_IMPACT]->()
            DELETE r
            """,
            incident_id=incident_id,
        ).consume()

        record = session.run(
            """
            MATCH (i:Incident {
                incident_id: $incident_id
            })

            UNWIND $rows AS row

            MATCH (e:Entity {
                node_id: row.node_id
            })

            MERGE (i)-[r:PREDICTED_IMPACT]->(e)

            SET r.predicted_status = row.status,
                r.model_name = 'GraphSAGE',
                r.data_origin = 'SYNTHETIC_SIMULATION',
                r.updated_at = datetime()

            RETURN count(r) AS saved
            """,
            incident_id=incident_id,
            rows=rows,
        ).single()

        return {
            "incident_id": incident_id,
            "saved": record["saved"],
            "model_name": "GraphSAGE",
            "data_origin": "SYNTHETIC_SIMULATION",
        }


def get_impact_snapshot(incident_id):
    driver = get_driver()

    query = """
    MATCH (i:Incident {
        incident_id: $incident_id
    })

    OPTIONAL MATCH
        (i)-[r:PREDICTED_IMPACT]->(e:Entity)

    RETURN
        i.incident_id AS incident_id,
        i.status AS incident_status,
        collect(
            CASE
                WHEN r IS NULL THEN null
                ELSE {
                    node_id: e.node_id,
                    node_name: e.node_name,
                    predicted_status:
                        r.predicted_status
                }
            END
        ) AS results
    """

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        record = session.run(
            query,
            incident_id=incident_id,
        ).single()

    if record is None:
        raise ValueError(
            "Incident not found"
        )

    return dict(record)
