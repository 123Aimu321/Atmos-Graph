
import argparse
import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "datasets" / "benchmark"

TYPES = [
    "SUPPLIER",
    "MANUFACTURER",
    "PORT",
    "WAREHOUSE",
    "RETAILER",
]

REGIONS = [
    "India",
    "Europe",
    "North America",
    "East Asia",
    "Southeast Asia",
]

RELATIONSHIPS = [
    "SUPPLIES",
    "SHIPS_THROUGH",
    "DISTRIBUTES_TO",
    "DELIVERS_TO",
]


def generate_network(
    node_count=2000,
    seed=42,
    edges_per_node=3,
):
    if node_count < 25:
        raise ValueError(
            "node_count must be at least 25"
        )

    if edges_per_node < 1:
        raise ValueError(
            "edges_per_node must be positive"
        )

    rng = random.Random(seed)

    groups = {node_type: [] for node_type in TYPES}

    nodes = []

    # Assign every node to one of five stages.
    for index in range(node_count):
        node_type = TYPES[index % len(TYPES)]

        node_id = f"BENCH_{index + 1:06d}"

        region = rng.choice(REGIONS)

        node = {
            "node_id": node_id,
            "node_name": (
                f"Benchmark {node_type.title()} "
                f"{index + 1:06d}"
            ),
            "node_type": node_type,
            "region": region,
            "data_origin": "BENCHMARK",
        }

        nodes.append(node)
        groups[node_type].append(node_id)

    edges = []
    edge_number = 0

    # Connect each stage to the next.
    #
    # The result is a directed layered graph.
    # RETAILER nodes do not have outgoing edges.
    for stage_index in range(len(TYPES) - 1):
        source_type = TYPES[stage_index]
        target_type = TYPES[stage_index + 1]

        targets = groups[target_type]

        for source_id in groups[source_type]:
            selected_targets = rng.sample(
                targets,
                k=min(edges_per_node, len(targets)),
            )

            for target_id in selected_targets:
                edge_number += 1

                edges.append({
                    "edge_id": (
                        f"BENCH_EDGE_{edge_number:08d}"
                    ),
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship": (
                        RELATIONSHIPS[stage_index]
                    ),
                    "transport_days": rng.randint(
                        1, 14
                    ),
                    "data_origin": "BENCHMARK",
                })

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes_file = OUTPUT / "benchmark_nodes.csv"
    edges_file = OUTPUT / "benchmark_edges.csv"

    with nodes_file.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "node_id",
                "node_name",
                "node_type",
                "region",
                "data_origin",
            ],
        )
        writer.writeheader()
        writer.writerows(nodes)

    with edges_file.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "edge_id",
                "source_id",
                "target_id",
                "relationship",
                "transport_days",
                "data_origin",
            ],
        )
        writer.writeheader()
        writer.writerows(edges)

    print("Benchmark network generated")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Nodes CSV: {nodes_file}")
    print(f"Edges CSV: {edges_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--nodes",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "--edges-per-node",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    generate_network(
        node_count=args.nodes,
        seed=args.seed,
        edges_per_node=args.edges_per_node,
    )
