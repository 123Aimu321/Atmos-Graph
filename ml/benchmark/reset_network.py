
import argparse
import os

from backend.app.database.neo4j_connection import get_driver


def reset_benchmark():
    driver = get_driver()
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    with driver.session(database=database) as session:

        counts = session.run(
            """
            MATCH (n:Entity {
                data_origin: 'BENCHMARK'
            })
            WITH count(n) AS nodes
            OPTIONAL MATCH ()-[r:CONNECTED {
                data_origin: 'BENCHMARK'
            }]->()
            RETURN nodes, count(r) AS edges
            """
        ).single()

        print("Benchmark records before cleanup:")
        print(f"Nodes: {counts['nodes']}")
        print(f"Edges: {counts['edges']}")

        # Remove relationships that were created
        # by the benchmark importer.
        #
        # Do not delete relationships belonging to
        # DATACO or SYNTHETIC.
        session.run(
            """
            MATCH ()-[r:CONNECTED {
                data_origin: 'BENCHMARK'
            }]->()
            DELETE r
            """
        ).consume()

        # Delete only isolated benchmark entities.
        # A benchmark entity with other links is
        # intentionally retained for inspection.
        session.run(
            """
            MATCH (n:Entity {
                data_origin: 'BENCHMARK'
            })
            WHERE NOT (n)--()
            DELETE n
            """
        ).consume()

        remaining = session.run(
            """
            MATCH (n:Entity {
                data_origin: 'BENCHMARK'
            })
            RETURN count(n) AS nodes
            """
        ).single()

        print("Cleanup complete")
        print(
            "Remaining benchmark nodes:",
            remaining["nodes"],
        )

        if remaining["nodes"]:
            print(
                "Some benchmark nodes have "
                "non-benchmark relationships. "
                "They were preserved for safety."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicitly approve benchmark cleanup",
    )

    args = parser.parse_args()

    if not args.confirm:
        parser.error(
            "Use --confirm to remove BENCHMARK data"
        )

    reset_benchmark()
