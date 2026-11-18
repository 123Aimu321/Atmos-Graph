
from pathlib import Path
from functools import lru_cache

import pandas as pd
import torch
import torch.nn.functional as F

from torch import nn
from torch_geometric.nn import SAGEConv


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "datasets" / "processed"
MODEL_PATH = ROOT_DIR / "ml" / "saved_model" / "graphsage_model.pt"

DEVICE = torch.device("cpu")

DISRUPTION_TYPES = [
    "SUPPLIER",
    "MANUFACTURER",
    "PORT",
    "WAREHOUSE",
    "RETAILER",
]


class SupplyChainGNN(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super().__init__()

        self.conv1 = SAGEConv(input_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.conv3 = SAGEConv(hidden_dim, hidden_dim)
        self.conv4 = SAGEConv(hidden_dim, hidden_dim)

        self.classifier = nn.Linear(hidden_dim, 3)

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = F.relu(self.conv3(x, edge_index))
        x = F.relu(self.conv4(x, edge_index))

        return self.classifier(x)


@lru_cache(maxsize=1)
def load_prediction_resources():
    # Only load model checkpoints produced by this project.
    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=True,
    )

    nodes = pd.read_csv(
        DATA_DIR / "synthetic_supply_chain_nodes.csv"
    )

    edges = pd.read_csv(
        DATA_DIR / "synthetic_supply_chain_edges.csv"
    )

    node_ids = nodes["node_id"].tolist()

    if node_ids != checkpoint["node_ids"]:
        raise ValueError(
            "Graph nodes differ from the training graph. "
            "Retrain the GNN before serving predictions."
        )

    node_to_idx = {
        node_id: index
        for index, node_id in enumerate(node_ids)
    }

    in_degree = {node_id: 0 for node_id in node_ids}
    out_degree = {node_id: 0 for node_id in node_ids}

    edge_pairs = []

    for _, edge in edges.iterrows():
        source = edge["source_id"]
        target = edge["target_id"]

        if source not in node_to_idx or target not in node_to_idx:
            raise ValueError("Graph contains unknown node IDs.")

        out_degree[source] += 1
        in_degree[target] += 1

        edge_pairs.append([
            node_to_idx[source],
            node_to_idx[target],
        ])

    edge_index = torch.tensor(
        edge_pairs,
        dtype=torch.long,
    ).t().contiguous()

    node_features = nodes[["node_type", "region"]].copy()

    node_features["in_degree"] = [
        in_degree[node_id] for node_id in node_ids
    ]

    node_features["out_degree"] = [
        out_degree[node_id] for node_id in node_ids
    ]

    node_features["total_degree"] = (
        node_features["in_degree"] +
        node_features["out_degree"]
    )

    node_features = pd.get_dummies(
        node_features,
        columns=["node_type", "region"],
        dtype=float,
    )

    for column in [
        "in_degree",
        "out_degree",
        "total_degree",
    ]:
        maximum = max(node_features[column].max(), 1)
        node_features[column] /= maximum

    expected_columns = checkpoint["feature_columns"]

    node_features = node_features.reindex(
        columns=expected_columns,
        fill_value=0,
    )

    static_x = torch.tensor(
        node_features.to_numpy(dtype="float32"),
        dtype=torch.float32,
    )

    model = SupplyChainGNN(
        input_dim=checkpoint["input_dim"],
        hidden_dim=checkpoint["hidden_dim"],
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(DEVICE)
    model.eval()

    return {
        "model": model,
        "nodes": nodes,
        "edges": edges,
        "node_ids": node_ids,
        "edge_index": edge_index,
        "static_x": static_x,
        "class_names": checkpoint["class_names"],
    }


def predict_disruption(disrupted_node_id):
    resources = load_prediction_resources()

    nodes = resources["nodes"]
    node_ids = resources["node_ids"]

    if disrupted_node_id not in node_ids:
        raise ValueError(
            f"Unknown disrupted entity: {disrupted_node_id}"
        )

    disrupted_row = nodes.loc[
        nodes["node_id"] == disrupted_node_id
    ].iloc[0]

    disruption_type = disrupted_row["node_type"]

    source_flag = torch.tensor(
        [
            [1.0 if node_id == disrupted_node_id else 0.0]
            for node_id in node_ids
        ],
        dtype=torch.float32,
    )

    type_vector = [
        1.0 if disruption_type == item else 0.0
        for item in DISRUPTION_TYPES
    ]

    type_features = torch.tensor(
        [type_vector] * len(node_ids),
        dtype=torch.float32,
    )

    x = torch.cat(
        [
            resources["static_x"],
            source_flag,
            type_features,
        ],
        dim=1,
    )

    with torch.no_grad():
        logits = resources["model"](
            x,
            resources["edge_index"],
        )

        probabilities = torch.softmax(logits, dim=1)
        predictions = probabilities.argmax(dim=1)

    class_names = resources["class_names"]

    results = []

    for index, node in nodes.iterrows():
        predicted_class = int(predictions[index].item())
        status = class_names[predicted_class]

        results.append({
            "node_id": node["node_id"],
            "node_name": node["node_name"],
            "node_type": node["node_type"],
            "region": node["region"],
            "predicted_status": status,
            "class_scores": {
                name: round(float(probabilities[index, j]), 4)
                for j, name in enumerate(class_names)
            },
        })

    return {
        "scenario_id": f"SCN_{disrupted_node_id}",
        "disrupted_node": disrupted_node_id,
        "disrupted_entity": disrupted_row["node_name"],
        "disruption_type": disruption_type,
        "model": "GraphSAGE",
        "data_origin": "SYNTHETIC_SIMULATION",
        "results": results,
        "summary": {
            "total_entities": len(results),
            "normal": sum(
                item["predicted_status"] == "NORMAL"
                for item in results
            ),
            "affected": sum(
                item["predicted_status"] == "AFFECTED"
                for item in results
            ),
            "disrupted": sum(
                item["predicted_status"] == "DISRUPTED"
                for item in results
            ),
        },
    }
