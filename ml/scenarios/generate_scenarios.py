
from pathlib import Path
from collections import defaultdict, deque
import pandas as pd
import random

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "datasets" / "processed"
OUTPUT_DIR = DATA_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

NODES_FILE = DATA_DIR / "synthetic_supply_chain_nodes.csv"
EDGES_FILE = DATA_DIR / "synthetic_supply_chain_edges.csv"

nodes_df = pd.read_csv(NODES_FILE)
edges_df = pd.read_csv(EDGES_FILE)

# Build directed supply-chain graph
graph = defaultdict(list)

for _, edge in edges_df.iterrows():
    graph[edge["source_id"]].append(edge["target_id"])

node_lookup = nodes_df.set_index("node_id").to_dict("index")


def find_downstream_nodes(start_node):
    """Return all reachable downstream entities."""
    visited = set()
    queue = deque([start_node])

    while queue:
        current = queue.popleft()

        for neighbor in graph[current]:
            if neighbor not in visited and neighbor != start_node:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


def calculate_disruption_impact(disrupted_node):
    """
    Simulate a complete outage of one entity.

    This is a simple reachability-based scenario model.
    It does not represent a calibrated real-world probability.
    """
    affected_nodes = find_downstream_nodes(disrupted_node)

    results = []

    for node_id, details in node_lookup.items():
        if node_id == disrupted_node:
            status = "DISRUPTED"
            impact_score = 1.0
        elif node_id in affected_nodes:
            status = "AFFECTED"
            impact_score = 0.75
        else:
            status = "NORMAL"
            impact_score = 0.0

        results.append({
            "node_id": node_id,
            "node_type": details["node_type"],
            "node_name": details["node_name"],
            "region": details["region"],
            "disrupted_node": disrupted_node,
            "disruption_type": node_lookup[disrupted_node]["node_type"],
            "status": status,
            "impact_score": impact_score,
            "data_origin": "SYNTHETIC_SIMULATION"
        })

    return results


# Create scenarios for every synthetic entity
all_results = []
scenario_summary = []

for node_id, details in node_lookup.items():
    scenario_results = calculate_disruption_impact(node_id)

    for result in scenario_results:
        result["scenario_id"] = f"SCN_{node_id}"
        all_results.append(result)

    affected_count = sum(
        result["status"] == "AFFECTED"
        for result in scenario_results
    )

    scenario_summary.append({
        "scenario_id": f"SCN_{node_id}",
        "disrupted_node": node_id,
        "disrupted_entity": details["node_name"],
        "disruption_type": details["node_type"],
        "affected_entities": affected_count,
        "total_entities": len(node_lookup),
        "affected_ratio": round(
            affected_count / max(len(node_lookup) - 1, 1), 4
        ),
        "data_origin": "SYNTHETIC_SIMULATION"
    })


results_df = pd.DataFrame(all_results)
summary_df = pd.DataFrame(scenario_summary)

results_path = OUTPUT_DIR / "disruption_scenario_labels.csv"
summary_path = OUTPUT_DIR / "disruption_scenario_summary.csv"

results_df.to_csv(results_path, index=False)
summary_df.to_csv(summary_path, index=False)

print("Disruption scenarios generated successfully.")
print(f"Total scenarios: {len(summary_df)}")
print(f"Total scenario-node records: {len(results_df)}")
print(f"Scenario labels: {results_path}")
print(f"Scenario summary: {summary_path}")

print("\nDisruption scenarios by entity type:")
print(summary_df.groupby("disruption_type").size().to_string())

print("\nTop 5 scenarios by affected entities:")
print(
    summary_df.sort_values(
        "affected_entities", ascending=False
    ).head(5).to_string(index=False)
)
