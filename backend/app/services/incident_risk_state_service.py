"""Read incident-scoped GraphSAGE risk states from Neo4j.

Risk states are SYNTHETIC_SIMULATION outputs. They are not verified
operational risk measurements or calibrated event probabilities.
"""
from backend.app.database.neo4j_connection import (
    get_driver,
    NEO4J_DATABASE,
)


def get_latest_incident_risk_states(incident_id: str):
    query = """
    MATCH (i:Incident {incident_id: $incident_id})
          -[:HAS_SNAPSHOT]->(s:ImpactSnapshot)
    WITH i, s ORDER BY s.created_at DESC
    LIMIT 1
    MATCH (s)-[:HAS_RISK_STATE]->(rs:IncidentRiskState)
          -[:FOR_ENTITY]->(e:Entity)
    WHERE e.data_origin = 'SYNTHETIC'
    RETURN
      i.incident_id AS incident_id,
      s.snapshot_id AS snapshot_id,
      toString(s.created_at) AS created_at,
      rs.node_id AS node_id,
      rs.predicted_status AS predicted_status,
      rs.predicted_delay_days AS predicted_delay_days,
      rs.is_disruption_source AS is_disruption_source
    ORDER BY node_id
    """
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        rows = session.execute_read(
            lambda tx: [
                dict(record)
                for record in tx.run(query, incident_id=incident_id)
            ]
        )
    return {
        "incident_id": incident_id,
        "snapshot_id": rows[0]["snapshot_id"] if rows else None,
        "data_origin": "SYNTHETIC_SIMULATION",
        "risk_states": [
            {
                "node_id": row["node_id"],
                "predicted_status": row["predicted_status"],
                "predicted_delay_days": row["predicted_delay_days"],
                "is_disruption_source": row["is_disruption_source"],
            }
            for row in rows
        ],
    }
