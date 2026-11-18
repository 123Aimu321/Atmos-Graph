
import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database.neo4j_connection import (
    get_driver,
    NEO4J_DATABASE,
    verify_connection,
    close_connection
)

DATA_DIR = ROOT_DIR / "datasets" / "processed"

NODES_FILE = DATA_DIR / "nodes.csv"
EDGES_FILE = DATA_DIR / "edges.csv"

BATCH_SIZE = 1000


def clean_value(value):
    if pd.isna(value):
        return None

    # Convert pandas/numpy values into regular Python values
    if hasattr(value, "item"):
        value = value.item()

    return value


def prepare_records(df):
    records = []

    for row in df.to_dict(orient="records"):
        records.append({
            key: clean_value(value)
            for key, value in row.items()
        })

    return records


def create_constraints(session):
    session.run("""
        CREATE CONSTRAINT entity_node_id IF NOT EXISTS
        FOR (n:Entity)
        REQUIRE n.node_id IS UNIQUE
    """)

    print("Node uniqueness constraint created.")


def import_nodes(session, nodes_df):
    records = prepare_records(nodes_df)

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]

        session.run("""
            UNWIND $rows AS row
            MERGE (n:Entity {node_id: row.node_id})
            SET n += row
        """, rows=batch)

    print(f"Imported {len(records)} nodes.")


def import_edges(session, edges_df):
    records = prepare_records(edges_df)

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]

        result = session.run("""
            UNWIND $rows AS row
            MATCH (source:Entity {
                node_id: row.source_id
            })
            MATCH (target:Entity {
                node_id: row.target_id
            })
            MERGE (source)-[r:CONNECTED {
                relationship: row.relationship
            }]->(target)
            SET r += row
            RETURN count(r) AS processed
        """, rows=batch)

        result.consume()

    print(f"Processed {len(records)} relationships.")


def verify_graph(session):
    result = session.run("""
        MATCH (n:Entity)
        RETURN count(n) AS total_nodes
    """)

    print(
        "Neo4j total nodes:",
        result.single()["total_nodes"]
    )

    result = session.run("""
        MATCH (:Entity)-[r:CONNECTED]->(:Entity)
        RETURN count(r) AS total_edges
    """)

    print(
        "Neo4j total relationships:",
        result.single()["total_edges"]
    )

    result = session.run("""
        MATCH (n:Entity)
        WHERE NOT (n)-[:CONNECTED]-()
        RETURN count(n) AS isolated_nodes
    """)

    print(
        "Isolated nodes:",
        result.single()["isolated_nodes"]
    )


def main():
    if not NODES_FILE.exists():
        raise FileNotFoundError(NODES_FILE)

    if not EDGES_FILE.exists():
        raise FileNotFoundError(EDGES_FILE)

    nodes_df = pd.read_csv(NODES_FILE)
    edges_df = pd.read_csv(EDGES_FILE)

    SYNTHETIC_NODES_PATH = (
        ROOT_DIR / "datasets" / "processed" /
        "synthetic_supply_chain_nodes.csv"
    )

    SYNTHETIC_EDGES_PATH = (
        ROOT_DIR / "datasets" / "processed" /
        "synthetic_supply_chain_edges.csv"
    )

    synthetic_nodes_df = pd.read_csv(SYNTHETIC_NODES_PATH)
    synthetic_edges_df = pd.read_csv(SYNTHETIC_EDGES_PATH)

    nodes_df = pd.concat(
        [nodes_df, synthetic_nodes_df],
        ignore_index=True,
        sort=False
    )

    edges_df = pd.concat(
        [edges_df, synthetic_edges_df],
        ignore_index=True,
        sort=False
    )

    print(f"Combined nodes: {len(nodes_df)}")
    print(f"Combined edges: {len(edges_df)}")

    if nodes_df["node_id"].duplicated().any():
        raise ValueError("Duplicate node IDs found.")

    node_ids = set(nodes_df["node_id"])

    if not edges_df["source_id"].isin(node_ids).all():
        raise ValueError("Some source nodes are missing.")

    if not edges_df["target_id"].isin(node_ids).all():
        raise ValueError("Some target nodes are missing.")

    print("Nodes CSV:", len(nodes_df))
    print("Edges CSV:", len(edges_df))

    verify_connection()

    driver = get_driver()

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            create_constraints(session)
            import_nodes(session, nodes_df)
            import_edges(session, edges_df)
            verify_graph(session)

        print("\nAtmoGraph import completed successfully!")

    finally:
        close_connection()


if __name__ == "__main__":
    main()
