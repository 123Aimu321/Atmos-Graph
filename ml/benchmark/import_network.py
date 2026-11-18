
import argparse
import csv
import time
from pathlib import Path

from backend.app.database.neo4j_connection import (
    get_driver,
)

import os


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets" / "benchmark"

NODES_CSV = DATA / "benchmark_nodes.csv"
EDGES_CSV = DATA / "benchmark_edges.csv"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def batches(rows, size):
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def import_nodes(tx, rows):
    result = tx.run(
        """
        UNWIND $rows AS row

        MERGE (n:Entity {
            node_id: row.node_id
        })

        ON CREATE SET
            n.data_origin = 'BENCHMARK'

        WITH n, row
        WHERE n.data_origin = 'BENCHMARK'

        SET
            n.node_name = row.node_name,
            n.node_type = row.node_type,
            n.region = row.region

        RETURN count(n) AS processed
        """,
        rows=rows,
    )

    return result.single()["processed"]


def import_edges(tx, rows):
    result = tx.run(
        """
        UNWIND $rows AS row

        MATCH (a:Entity {
            node_id: row.source_id,
            data_origin: 'BENCHMARK'
        })

        MATCH (b:Entity {
            node_id: row.target_id,
            data_origin: 'BENCHMARK'
        })

        MERGE (a)-[r:CONNECTED {
            benchmark_edge_id: row.edge_id
        }]->(b)

        SET
            r.relationship = row.relationship,
            r.transport_days = toFloat(
                row.transport_days
            ),
            r.data_origin = 'BENCHMARK'

        RETURN count(r) AS processed
        """,
        rows=rows,
    )

    return result.single()["processed"]


def import_network(batch_size=500):
    if batch_size < 1:
        raise ValueError(
            "batch_size must be positive"
        )

    nodes = read_csv(NODES_CSV)
    edges = read_csv(EDGES_CSV)

    # Guard against unexpected IDs and origins.
    for node in nodes:
        if (
            not node["node_id"].startswith("BENCH_")
            or node["data_origin"] != "BENCHMARK"
        ):
            raise ValueError(
                "Invalid benchmark node"
            )

    for edge in edges:
        if (
            not edge["edge_id"].startswith(
                "BENCH_EDGE_"
            )
            or not edge["source_id"].startswith(
                "BENCH_"
            )
            or not edge["target_id"].startswith(
                "BENCH_"
            )
            or edge["data_origin"] != "BENCHMARK"
        ):
            raise ValueError(
                "Invalid benchmark edge"
            )

    driver = get_driver()
    database = os.getenv(
        "NEO4J_DATABASE", "neo4j"
    )

    start_time = time.perf_counter()

    with driver.session(
        database=database
    ) as session:
        session.run(
            """
            CREATE CONSTRAINT entity_node_id_unique
            IF NOT EXISTS
            FOR (n:Entity)
            REQUIRE n.node_id IS UNIQUE
            """
        ).consume()

        imported_nodes = 0

        for batch in batches(nodes, batch_size):
            imported_nodes += session.execute_write(
                import_nodes,
                batch,
            )

        imported_edges = 0

        for batch in batches(edges, batch_size):
            imported_edges += session.execute_write(
                import_edges,
                batch,
            )

        counts = session.execute_read(
            lambda tx: dict(
                tx.run(
                    """
                    MATCH (n:Entity {
                        data_origin: 'BENCHMARK'
                    })
                    WITH count(n) AS nodes
                    MATCH ()-[r:CONNECTED {
                        data_origin: 'BENCHMARK'
                    }]->()
                    RETURN
                        nodes,
                        count(r) AS edges
                    """
                ).single()
            )
        )

    elapsed = time.perf_counter() - start_time

    print("\nNeo4j benchmark import complete")
    print(f"Node rows processed: {imported_nodes}")
    print(f"Edge rows processed: {imported_edges}")
    print(f"Database nodes: {counts['nodes']}")
    print(f"Database edges: {counts['edges']}")
    print(f"Elapsed: {elapsed:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
    )

    args = parser.parse_args()

    import_network(
        batch_size=args.batch_size
    )
