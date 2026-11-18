# backend/app/services/history_service.py

import json
import os
from uuid import uuid4

from backend.app.database.neo4j_connection import (
    get_driver,
)
from ml.gnn.delay_regression import load_network

from backend.app.services.snapshot_validation import (
    validate_snapshot,
    SnapshotValidationError,
)


def get_database():
    return os.getenv("NEO4J_DATABASE", "neo4j")


def encode_json(value):
    """
    Store structured model outputs as JSON text.
    Neo4j properties do not support nested maps.
    """
    if value is None:
        return None

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )

    if len(encoded.encode("utf-8")) > 2_000_000:
        raise ValueError(
            "Simulation payload exceeds 2 MB"
        )

    return encoded


def decode_json(value):
    return json.loads(value) if value else None


def get_confirmed_incident_source(incident_id):
    """
    Read the actual confirmed graph entity
    from Neo4j, not from the React payload.
    """
    query = """
    MATCH (i:Incident {incident_id: $incident_id})
          -[:AFFECTS]->(e:Entity)
    WHERE i.status = 'CONFIRMED'
      AND e.data_origin = 'SYNTHETIC'

    RETURN DISTINCT e.node_id AS node_id
    """

    driver = get_driver()

    with driver.session(
        database=get_database()
    ) as session:
        records = session.execute_read(
            lambda tx: [
                record["node_id"]
                for record in tx.run(
                    query,
                    incident_id=incident_id,
                )
            ]
        )

    if len(records) != 1:
        raise SnapshotValidationError(
            "Incident must be CONFIRMED and "
            "linked to exactly one synthetic entity"
        )

    return records[0]


def save_history_snapshot(
    incident_id,
    prediction,
    delay=None,
    forecast=None,
    ripple=None,
    risk=None,
):
    """
    Save a NEW snapshot for a CONFIRMED incident.

    Each execution creates a unique snapshot.
    Existing snapshots are never overwritten.
    """
    if not incident_id:
        raise ValueError("incident_id is required")

    if not isinstance(prediction, dict):
        raise ValueError(
            "prediction must be a JSON object"
        )

    if not isinstance(
        prediction.get("results"),
        list,
    ):
        raise ValueError(
            "prediction.results must be a list"
        )

    for name, value in {
        "delay": delay,
        "forecast": forecast,
        "ripple": ripple,
        "risk": risk,
    }.items():
        if value is not None and not isinstance(
            value, dict
        ):
            raise ValueError(
                f"{name} must be a JSON object"
            )

    # Confirm the incident's actual source in Neo4j.
    confirmed_source = get_confirmed_incident_source(
        incident_id
    )

    # Use the exact training network's entity IDs.
    network = load_network()
    allowed_node_ids = set(network["ids"])

    # Validate the complete simulation payload.
    validate_snapshot(
        source_node_id=confirmed_source,
        allowed_node_ids=allowed_node_ids,
        prediction=prediction,
        delay=delay,
        forecast=forecast,
    )

    snapshot_id = str(uuid4())

    params = {
        "incident_id": incident_id,
        "snapshot_id": snapshot_id,
        "source_node_id": confirmed_source,
        "prediction_json": encode_json(prediction),
        "delay_json": encode_json(delay),
        "forecast_json": encode_json(forecast),
        "ripple_json": encode_json(ripple),
        "risk_json": encode_json(risk),
        "model_name": "GraphSAGE",
        "data_origin": "SYNTHETIC_SIMULATION",
        "initial_delay_days": (
            delay.get("initial_delay_days")
            if delay
            else None
        ),
        "recovery_half_life_days": (
            forecast.get("recovery_half_life_days")
            if forecast
            else None
        ),
    }

    query = """
    MATCH (i:Incident {incident_id: $incident_id})
    WHERE i.status = 'CONFIRMED'
      AND EXISTS {
        MATCH (i)-[:AFFECTS]->
              (:Entity {
                  node_id: $source_node_id,
                  data_origin: 'SYNTHETIC'
              })
      }

    CREATE (s:ImpactSnapshot {
        snapshot_id: $snapshot_id,
        source_node_id: $source_node_id,
        created_at: datetime(),
        model_name: $model_name,
        data_origin: $data_origin,
        prediction_json: $prediction_json,
        delay_json: $delay_json,
        forecast_json: $forecast_json,
        ripple_json: $ripple_json,
        risk_json: $risk_json,
        initial_delay_days: $initial_delay_days,
        recovery_half_life_days: $recovery_half_life_days
    })

    CREATE (i)-[:HAS_SNAPSHOT]->(s)

    RETURN
        s.snapshot_id AS snapshot_id,
        toString(s.created_at) AS created_at,
        i.incident_id AS incident_id,
        s.model_name AS model_name,
        s.data_origin AS data_origin
    """

    driver = get_driver()

    with driver.session(
        database=get_database()
    ) as session:
        record = session.execute_write(
            lambda tx: tx.run(
                query,
                **params,
            ).single()
        )

    if record is None:
        raise ValueError(
            "Incident must exist, be CONFIRMED, "
            "and have an AFFECTS relationship"
        )

    return dict(record)


def list_history_snapshots(
    incident_id,
    limit=50,
):
    query = """
    MATCH (i:Incident {incident_id: $incident_id})
          -[:HAS_SNAPSHOT]->(s:ImpactSnapshot)

    RETURN
        s.snapshot_id AS snapshot_id,
        i.incident_id AS incident_id,
        i.title AS incident_title,
        toString(s.created_at) AS created_at,
        s.model_name AS model_name,
        s.data_origin AS data_origin,
        s.initial_delay_days AS initial_delay_days,
        s.recovery_half_life_days
            AS recovery_half_life_days

    ORDER BY s.created_at DESC
    LIMIT $limit
    """

    driver = get_driver()

    with driver.session(
        database=get_database()
    ) as session:
        records = session.execute_read(
            lambda tx: [
                dict(record)
                for record in tx.run(
                    query,
                    incident_id=incident_id,
                    limit=limit,
                )
            ]
        )

    return records


def get_history_snapshot(snapshot_id):
    query = """
    MATCH (i:Incident)-[:HAS_SNAPSHOT]->
          (s:ImpactSnapshot {
              snapshot_id: $snapshot_id
          })

    RETURN
        s.snapshot_id AS snapshot_id,
        i.incident_id AS incident_id,
        i.title AS incident_title,
        toString(s.created_at) AS created_at,
        s.model_name AS model_name,
        s.data_origin AS data_origin,
        s.initial_delay_days AS initial_delay_days,
        s.recovery_half_life_days
            AS recovery_half_life_days,
        s.prediction_json AS prediction_json,
        s.delay_json AS delay_json,
        s.forecast_json AS forecast_json,
        s.ripple_json AS ripple_json,
        s.risk_json AS risk_json
    LIMIT 1
    """

    driver = get_driver()

    with driver.session(
        database=get_database()
    ) as session:
        record = session.execute_read(
            lambda tx: tx.run(
                query,
                snapshot_id=snapshot_id,
            ).single()
        )

    if record is None:
        return None

    result = dict(record)

    for name in (
        "prediction",
        "delay",
        "forecast",
        "ripple",
        "risk",
    ):
        key = f"{name}_json"
        result[name] = decode_json(
            result.pop(key)
        )

    return result
