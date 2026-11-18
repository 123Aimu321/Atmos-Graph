
from pathlib import Path
import json
import random

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from torch import nn
from torch_geometric.nn import SAGEConv

# -----------------------------------
# Configuration
# -----------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "datasets" / "processed"
MODEL_DIR = ROOT_DIR / "ml" / "saved_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EPOCHS = 300
LEARNING_RATE = 0.01

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Using device:", device)

# -----------------------------------
# Load data
# -----------------------------------

nodes = pd.read_csv(
    DATA_DIR / "synthetic_supply_chain_nodes.csv"
)
edges = pd.read_csv(
    DATA_DIR / "synthetic_supply_chain_edges.csv"
)
dataset = pd.read_csv(
    DATA_DIR / "gnn_training_dataset.csv"
)

node_ids = nodes["node_id"].tolist()
node_to_idx = {
    node_id: i for i, node_id in enumerate(node_ids)
}

class_names = ["NORMAL", "AFFECTED", "DISRUPTED"]
class_to_idx = {
    name: i for i, name in enumerate(class_names)
}

# -----------------------------------
# Build directed graph
# -----------------------------------

# For edge A -> B, PyG passes information from A to B.
# This allows disruption information to travel downstream.

edge_pairs = []

for _, row in edges.iterrows():
    source = node_to_idx[row["source_id"]]
    target = node_to_idx[row["target_id"]]
    edge_pairs.append([source, target])

edge_index = torch.tensor(
    edge_pairs,
    dtype=torch.long
).t().contiguous().to(device)

# -----------------------------------
# Build static node features
# -----------------------------------

in_degree = {node_id: 0 for node_id in node_ids}
out_degree = {node_id: 0 for node_id in node_ids}

for _, row in edges.iterrows():
    out_degree[row["source_id"]] += 1
    in_degree[row["target_id"]] += 1

node_features = nodes[["node_type", "region"]].copy()

node_features["in_degree"] = [
    in_degree[n] for n in node_ids
]
node_features["out_degree"] = [
    out_degree[n] for n in node_ids
]

# Match the baseline's structural information.
node_features["total_degree"] = (
    node_features["in_degree"] +
    node_features["out_degree"]
)

node_features = pd.get_dummies(
    node_features,
    columns=["node_type", "region"],
    dtype=float
)

# Normalize numeric degree features.
for column in [
    "in_degree",
    "out_degree",
    "total_degree"
]:
    maximum = max(node_features[column].max(), 1)
    node_features[column] /= maximum

static_x = torch.tensor(
    node_features.to_numpy(dtype=np.float32),
    dtype=torch.float32
)

# -----------------------------------
# Scenario-specific graph samples
# -----------------------------------

samples = {}

for scenario_id, group in dataset.groupby("scenario_id"):
    group = group.set_index("node_id").loc[node_ids]

    disrupted_node = group["disrupted_node"].iloc[0]

    source_flag = torch.tensor(
        [
            [1.0 if n == disrupted_node else 0.0]
            for n in node_ids
        ],
        dtype=torch.float32
    )

    disruption_type = group["disruption_type"].iloc[0]

    disruption_types = [
        "SUPPLIER",
        "MANUFACTURER",
        "PORT",
        "WAREHOUSE",
        "RETAILER"
    ]

    type_vector = [
        1.0 if disruption_type == t else 0.0
        for t in disruption_types
    ]

    scenario_type_features = torch.tensor(
        [type_vector] * len(node_ids),
        dtype=torch.float32
    )

    x = torch.cat(
        [
            static_x,
            source_flag,
            scenario_type_features
        ],
        dim=1
    ).to(device)

    y = torch.tensor(
        [
            class_to_idx[status]
            for status in group["status"]
        ],
        dtype=torch.long
    ).to(device)

    samples[scenario_id] = (x, y)

# -----------------------------------
# Use same split as Random Forest
# -----------------------------------

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=SEED
)

train_idx, test_idx = next(
    splitter.split(
        dataset,
        groups=dataset["scenario_id"]
    )
)

train_scenarios = sorted(
    dataset.iloc[train_idx]["scenario_id"].unique()
)
test_scenarios = sorted(
    dataset.iloc[test_idx]["scenario_id"].unique()
)

print("Training scenarios:", len(train_scenarios))
print("Testing scenarios:", len(test_scenarios))

# -----------------------------------
# GraphSAGE model
# -----------------------------------

class SupplyChainGNN(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super().__init__()

        self.conv1 = SAGEConv(input_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.conv3 = SAGEConv(hidden_dim, hidden_dim)
        self.conv4 = SAGEConv(hidden_dim, hidden_dim)

        self.classifier = nn.Linear(
            hidden_dim,
            len(class_names)
        )

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = F.relu(self.conv3(x, edge_index))
        x = F.relu(self.conv4(x, edge_index))

        return self.classifier(x)


model = SupplyChainGNN(
    input_dim=static_x.shape[1] + 1 + 5
).to(device)

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)

# -----------------------------------
# Training
# -----------------------------------

print("\nTraining GraphSAGE model...")

for epoch in range(1, EPOCHS + 1):
    model.train()
    optimizer.zero_grad()

    losses = []

    for scenario_id in train_scenarios:
        x, y = samples[scenario_id]

        logits = model(x, edge_index)
        loss = F.cross_entropy(logits, y)

        losses.append(loss)

    total_loss = torch.stack(losses).mean()

    total_loss.backward()
    optimizer.step()

    if epoch == 1 or epoch % 25 == 0:
        print(
            f"Epoch {epoch:03d}/{EPOCHS} "
            f"| Loss: {total_loss.item():.4f}"
        )

# -----------------------------------
# Evaluation
# -----------------------------------

model.eval()

all_true = []
all_pred = []
prediction_rows = []

with torch.no_grad():
    for scenario_id in test_scenarios:
        x, y = samples[scenario_id]

        logits = model(x, edge_index)
        predictions = logits.argmax(dim=1)

        true_values = y.cpu().tolist()
        predicted_values = predictions.cpu().tolist()

        all_true.extend(true_values)
        all_pred.extend(predicted_values)

        for node_id, true_idx, pred_idx in zip(
            node_ids,
            true_values,
            predicted_values
        ):
            prediction_rows.append({
                "scenario_id": scenario_id,
                "node_id": node_id,
                "status": class_names[true_idx],
                "predicted_status": class_names[pred_idx],
                "correct": true_idx == pred_idx
            })

accuracy = accuracy_score(all_true, all_pred)
macro_f1 = f1_score(
    all_true,
    all_pred,
    labels=[0, 1, 2],
    average="macro",
    zero_division=0
)
weighted_f1 = f1_score(
    all_true,
    all_pred,
    labels=[0, 1, 2],
    average="weighted",
    zero_division=0
)

matrix = confusion_matrix(
    all_true,
    all_pred,
    labels=[0, 1, 2]
)

print("\n=== GraphSAGE Results ===")
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1-score: {macro_f1:.4f}")
print(f"Weighted F1-score: {weighted_f1:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        all_true,
        all_pred,
        labels=[0, 1, 2],
        target_names=class_names,
        zero_division=0
    )
)

print("\nConfusion Matrix:")
print(
    pd.DataFrame(
        matrix,
        index=[f"Actual_{x}" for x in class_names],
        columns=[f"Predicted_{x}" for x in class_names]
    ).to_string()
)

# -----------------------------------
# Save model and metrics
# -----------------------------------

model_path = MODEL_DIR / "graphsage_model.pt"

torch.save({
    "model_state_dict": model.state_dict(),
    "input_dim": static_x.shape[1] + 1 + 5,
    "hidden_dim": 64,
    "node_ids": node_ids,
    "feature_columns": node_features.columns.tolist(),
    "class_names": class_names
}, model_path)

metrics = {
    "model": "GraphSAGE",
    "accuracy": float(accuracy),
    "macro_f1": float(macro_f1),
    "weighted_f1": float(weighted_f1),
    "training_scenarios": list(train_scenarios),
    "testing_scenarios": list(test_scenarios),
    "confusion_matrix": matrix.tolist(),
    "data_origin": "SYNTHETIC_SIMULATION"
}

metrics_path = MODEL_DIR / "gnn_metrics.json"

with open(metrics_path, "w", encoding="utf-8") as file:
    json.dump(metrics, file, indent=4)

predictions_path = MODEL_DIR / "gnn_predictions.csv"

pd.DataFrame(prediction_rows).to_csv(
    predictions_path,
    index=False
)

print("\nModel saved:", model_path)
print("Metrics saved:", metrics_path)
print("Predictions saved:", predictions_path)
print("\nGNN training completed successfully!")
