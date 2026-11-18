
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from neo4j.exceptions import (
    Neo4jError,
    ServiceUnavailable,
)

from backend.app.services.graph_service import (
    fetch_supply_chain_graph,
)


router = APIRouter(
    prefix="/api",
    tags=["Graph"],
)

ROOT_DIR = Path(__file__).resolve().parents[3]

PROCESSED_DIR = ROOT_DIR / "datasets" / "processed"

SCENARIOS_FILE = (
    PROCESSED_DIR
    / "disruption_scenario_summary.csv"
)

SYNTHETIC_NODES_FILE = (
    PROCESSED_DIR
    / "synthetic_supply_chain_nodes.csv"
)


def load_graph_entities():
    """
    Load the 25 synthetic supply-chain entities.

    Used by the news NLP pipeline for entity matching.
    """

    if not SYNTHETIC_NODES_FILE.exists():
        raise FileNotFoundError(
            "Synthetic supply-chain dataset not found: "
            f"{SYNTHETIC_NODES_FILE}"
        )

    df = pd.read_csv(SYNTHETIC_NODES_FILE)

    required_columns = {
        "node_id",
        "node_name",
        "node_type",
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing columns in synthetic nodes CSV: "
            f"{sorted(missing_columns)}"
        )

    df = df.fillna("")

    entities = []

    for row in df.to_dict(orient="records"):
        entities.append(
            {
                "node_id": str(row["node_id"]),
                "node_name": str(row["node_name"]),
                "node_type": str(row["node_type"]),
            }
        )

    return entities


@router.get("/graph")
def get_supply_chain_graph():
    """
    Fetch the supply-chain graph from Neo4j.
    """

    try:
        return fetch_supply_chain_graph()

    except (
        ServiceUnavailable,
        Neo4jError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Neo4j graph database is unavailable: "
                f"{exc}"
            ),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load supply-chain graph: "
                f"{exc}"
            ),
        )


@router.get("/scenarios")
def get_scenarios():
    """
    Return the generated disruption scenarios.
    """

    if not SCENARIOS_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Scenario dataset is unavailable."
            ),
        )

    try:
        df = pd.read_csv(SCENARIOS_FILE)

        df = df.where(
            pd.notnull(df),
            None,
        )

        return {
            "total": len(df),
            "scenarios": df.to_dict(
                orient="records"
            ),
            "data_origin": (
                "SYNTHETIC_SIMULATION"
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load scenarios: "
                f"{exc}"
            ),
        )
