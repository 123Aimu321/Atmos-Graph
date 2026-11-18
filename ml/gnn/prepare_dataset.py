
from pathlib import Path
from collections import defaultdict, deque
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "datasets" / "processed"

NODES_FILE = DATA_DIR / "synthetic_supply_chain_nodes.csv"
EDGES_FILE = DATA_DIR / "synthetic_supply_chain_edges.csv"
LABELS_FILE = DATA_DIR / "disruption_scenario_labels.csv"

nodes = pd.read_csv(NODES_FILE)
edges = pd.read_csv(EDGES_FILE)
labels = pd.read_csv(LABELS_FILE)

# Build graph adjacency structures
outgoing = defaultdict(list)
incoming = defaultdict(list)

for _, edge in edges.iterrows():
    source = edge["source_id"]
    target = edge["target_id"]

    outgoing[source].append(target)
    incoming[target].append(source)


def shortest_distances(start):
    """Calculate shortest directed distances from disrupted entity."""
    distances = {start: 0}
    queue = deque([start])

    while queue:
        current = queue.popleft()

        for neighbor in outgoing[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    return distances


# Static features for each entity
node_features = []

for _, node in nodes.iterrows():
    node_id = node["node_id"]

    node_features.append({
        "node_id": node_id,
        "node_type": node["node_type"],
        "region": node["region"],
        "in_degree": len(incoming[node_id]),
        "out_degree": len(outgoing[node_id]),
        "total_degree": (
            len(incoming[node_id]) + len(outgoing[node_id])
        )
    })

features_df = pd.DataFrame(node_features)

# Combine scenario labels with entity features
dataset = labels.merge(
    features_df,
    on=["node_id", "node_type", "region"],
    how="left"
)

# Calculate distance from disrupted entity in each scenario
distance_values = []

for scenario_id, group in dataset.groupby("scenario_id"):
    disrupted_node = group["disrupted_node"].iloc[0]
    distances = shortest_distances(disrupted_node)

    for _, row in group.iterrows():
        distance_values.append({
            "scenario_id": scenario_id,
            "node_id": row["node_id"],
            "distance_from_disruption": distances.get(
                row["node_id"], -1
            )
        })

distance_df = pd.DataFrame(distance_values)

dataset = dataset.merge(
    distance_df,
    on=["scenario_id", "node_id"],
    how="left"
)

# Add scenario information
dataset["is_disrupted_entity"] = (
    dataset["node_id"] == dataset["disrupted_node"]
).astype(int)

# Save the prepared dataset
output_path = DATA_DIR / "gnn_training_dataset.csv"
dataset.to_csv(output_path, index=False)

print("Machine-learning dataset prepared successfully.")
print(f"Total records: {len(dataset)}")
print(f"Unique entities: {dataset['node_id'].nunique()}")
print(f"Unique scenarios: {dataset['scenario_id'].nunique()}")
print(f"Missing feature values: {dataset.isnull().sum().sum()}")

print("\nFeature columns:")
print(dataset.columns.tolist())

print("\nClass distribution:")
print(dataset["status"].value_counts().to_string())

print(f"\nSaved to: {output_path}")
