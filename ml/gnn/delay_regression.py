
import argparse
import json
import random
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch_geometric.nn import SAGEConv


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets" / "processed"
MODELS = ROOT / "ml" / "models"

NODES_FILE = DATA / "synthetic_supply_chain_nodes.csv"
EDGES_FILE = DATA / "synthetic_supply_chain_edges.csv"

MODEL_FILE = MODELS / "delay_graphsage.pt"
METRICS_FILE = MODELS / "delay_metrics.json"

NODE_TYPES = [
    "SUPPLIER",
    "MANUFACTURER",
    "PORT",
    "WAREHOUSE",
    "RETAILER",
]

REGIONS = []
SEED = 42


def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_network():
    nodes = pd.read_csv(NODES_FILE).fillna("")
    edges = pd.read_csv(EDGES_FILE)

    required_nodes = {
        "node_id", "node_type", "region"
    }
    required_edges = {
        "source_id", "target_id", "transport_days"
    }

    if not required_nodes.issubset(nodes.columns):
        raise ValueError("Invalid nodes CSV columns")

    if not required_edges.issubset(edges.columns):
        raise ValueError("Invalid edges CSV columns")

    nodes = nodes.sort_values("node_id").reset_index(drop=True)
    nodes["node_id"] = nodes["node_id"].astype(str)

    if nodes["node_id"].duplicated().any():
        raise ValueError("Duplicate node IDs")

    ids = nodes["node_id"].tolist()
    id_to_index = {
        node_id: index
        for index, node_id in enumerate(ids)
    }

    regions = sorted(
        nodes["region"].astype(str).unique().tolist()
    )

    node_features = []

    for row in nodes.to_dict("records"):
        node_features.append(
            [
                float(row["node_type"] == node_type)
                for node_type in NODE_TYPES
            ]
            +
            [
                float(str(row["region"]) == region)
                for region in regions
            ]
        )

    sources = []
    targets = []
    adjacency = {
        index: [] for index in range(len(ids))
    }

    for edge in edges.to_dict("records"):
        source_id = str(edge["source_id"])
        target_id = str(edge["target_id"])

        if (
            source_id not in id_to_index
            or target_id not in id_to_index
        ):
            raise ValueError(
                f"Unknown edge: {source_id} -> {target_id}"
            )

        source = id_to_index[source_id]
        target = id_to_index[target_id]

        transport_days = float(edge["transport_days"])

        if (
            not np.isfinite(transport_days)
            or transport_days < 0
        ):
            raise ValueError("Invalid transport_days")

        sources.append(source)
        targets.append(target)

        adjacency[source].append(
            (target, transport_days)
        )

    if not sources:
        raise ValueError("Graph contains no edges")

    # Directed upstream-to-downstream propagation.
    # PyG message passing uses source -> target.
    edge_index = torch.tensor(
        [sources, targets],
        dtype=torch.long,
    )

    base_features = torch.tensor(
        node_features,
        dtype=torch.float32,
    )

    return {
        "ids": ids,
        "id_to_index": id_to_index,
        "regions": regions,
        "base_features": base_features,
        "edge_index": edge_index,
        "adjacency": adjacency,
        "node_count": len(ids),
    }


def propagate_delay(
    network,
    source_index,
    initial_delay,
    decay,
):
    """
    Synthetic propagation rule.

    At each downstream hop, delay is attenuated.
    The edge's transport duration contributes
    to attenuation.

    This is a simulation assumption, not a
    measured supply-chain delay mechanism.
    """
    count = network["node_count"]
    delays = np.zeros(count, dtype=np.float32)
    hops = np.full(count, -1, dtype=np.int32)

    delays[source_index] = initial_delay
    hops[source_index] = 0

    queue = deque([source_index])

    # The synthetic graph is layered. Iterative
    # relaxation also supports alternative paths.
    for _ in range(count):
        changed = False

        for source in range(count):
            if delays[source] <= 0:
                continue

            for target, travel_days in network[
                "adjacency"
            ][source]:
                candidate = (
                    delays[source]
                    * decay
                    * np.exp(-0.015 * travel_days)
                )

                if candidate > delays[target] + 1e-5:
                    delays[target] = candidate
                    changed = True

        if not changed:
            break

    # BFS hop counts are descriptive features.
    while queue:
        source = queue.popleft()

        for target, _ in network["adjacency"][source]:
            if hops[target] == -1:
                hops[target] = hops[source] + 1
                queue.append(target)

    return delays, hops


def make_features(
    network,
    source_index,
    initial_delay,
    decay,
):
    count = network["node_count"]

    disrupted = torch.zeros(
        (count, 1),
        dtype=torch.float32,
    )
    disrupted[source_index] = 1.0

    # Inputs describe the simulated event.
    # Do not include target delays or true
    # downstream hop counts as model features.
    severity = torch.full(
        (count, 1),
        initial_delay / 30.0,
        dtype=torch.float32,
    )

    decay_feature = torch.full(
        (count, 1),
        decay,
        dtype=torch.float32,
    )

    return torch.cat(
        [
            network["base_features"],
            disrupted,
            severity,
            decay_feature,
        ],
        dim=1,
    )


class DelayGraphSAGE(nn.Module):
    def __init__(
        self,
        input_dim,
        hidden_dim=64,
        layers=4,
    ):
        super().__init__()

        self.convs = nn.ModuleList()

        self.convs.append(
            SAGEConv(input_dim, hidden_dim)
        )

        for _ in range(layers - 1):
            self.convs.append(
                SAGEConv(hidden_dim, hidden_dim)
            )

        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Softplus(),
        )

    def forward(self, x, edge_index):
        for conv in self.convs:
            x = torch.relu(
                conv(x, edge_index)
            )

        return self.head(x).squeeze(-1)


def generate_scenarios(network, repetitions=12):
    scenarios = []

    for source_index in range(network["node_count"]):
        for repetition in range(repetitions):
            rng = np.random.default_rng(
                SEED + source_index * 1000 + repetition
            )

            initial_delay = float(
                rng.uniform(3.0, 30.0)
            )
            decay = float(
                rng.uniform(0.55, 0.90)
            )

            labels, _ = propagate_delay(
                network,
                source_index,
                initial_delay,
                decay,
            )

            features = make_features(
                network,
                source_index,
                initial_delay,
                decay,
            )

            scenarios.append({
                "source_index": source_index,
                "initial_delay": initial_delay,
                "decay": decay,
                "x": features,
                "y": torch.tensor(
                    labels,
                    dtype=torch.float32,
                ),
            })

    return scenarios


def evaluate(model, scenarios, edge_index):
    model.eval()

    predictions = []
    targets = []

    with torch.no_grad():
        for scenario in scenarios:
            predicted = model(
                scenario["x"],
                edge_index,
            )

            predictions.append(
                predicted.numpy()
            )
            targets.append(
                scenario["y"].numpy()
            )

    predictions = np.concatenate(predictions)
    targets = np.concatenate(targets)

    errors = predictions - targets

    return {
        "mae_days": float(
            np.mean(np.abs(errors))
        ),
        "rmse_days": float(
            np.sqrt(np.mean(errors ** 2))
        ),
        "samples": int(len(targets)),
    }


def train():
    set_seed()

    network = load_network()
    scenarios = generate_scenarios(network)

    # Split by disrupted source entity, rather
    # than randomly splitting individual nodes.
    # This tests generalization to unseen sources.
    source_ids = list(range(network["node_count"]))

    rng = random.Random(SEED)
    rng.shuffle(source_ids)

    test_count = max(
        1, round(len(source_ids) * 0.2)
    )
    val_count = max(
        1, round(len(source_ids) * 0.2)
    )

    test_sources = set(source_ids[:test_count])
    val_sources = set(
        source_ids[test_count:test_count + val_count]
    )

    train_scenarios = [
        s for s in scenarios
        if s["source_index"] not in (
            test_sources | val_sources
        )
    ]
    val_scenarios = [
        s for s in scenarios
        if s["source_index"] in val_sources
    ]
    test_scenarios = [
        s for s in scenarios
        if s["source_index"] in test_sources
    ]

    model = DelayGraphSAGE(
        input_dim=train_scenarios[0]["x"].shape[1]
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.003,
        weight_decay=1e-4,
    )

    best_loss = float("inf")
    best_state = None
    patience = 50
    wait = 0

    for epoch in range(1, 401):
        model.train()
        random.shuffle(train_scenarios)

        total_loss = 0.0

        for scenario in train_scenarios:
            optimizer.zero_grad()

            output = model(
                scenario["x"],
                network["edge_index"],
            )

            loss = nn.functional.smooth_l1_loss(
                output,
                scenario["y"],
            )

            loss.backward()
            optimizer.step()

            total_loss += float(loss.item())

        validation = evaluate(
            model,
            val_scenarios,
            network["edge_index"],
        )

        val_loss = validation["mae_days"]

        if val_loss < best_loss:
            best_loss = val_loss
            wait = 0

            best_state = {
                key: value.detach().clone()
                for key, value in model.state_dict().items()
            }
        else:
            wait += 1

        if epoch % 25 == 0:
            print(
                f"Epoch {epoch:03d} | "
                f"train loss "
                f"{total_loss / len(train_scenarios):.4f} | "
                f"val MAE {val_loss:.3f} days"
            )

        if wait >= patience:
            print("Early stopping")
            break

    model.load_state_dict(best_state)

    test_metrics = evaluate(
        model,
        test_scenarios,
        network["edge_index"],
    )

    MODELS.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": train_scenarios[0]["x"].shape[1],
            "hidden_dim": 64,
            "layers": 4,
            "node_ids": network["ids"],
            "regions": network["regions"],
            "node_types": NODE_TYPES,
            "seed": SEED,
        },
        MODEL_FILE,
    )

    metrics = {
        **test_metrics,
        "model": "GraphSAGE delay regression",
        "target": "synthetic propagated delay days",
        "training_scenarios": len(train_scenarios),
        "validation_scenarios": len(val_scenarios),
        "test_scenarios": len(test_scenarios),
        "test_source_nodes": sorted(
            network["ids"][index]
            for index in test_sources
        ),
        "validation_source_nodes": sorted(
            network["ids"][index]
            for index in val_sources
        ),
        "disclaimer": (
            "Targets are generated by a synthetic "
            "propagation formula, not observed delays."
        ),
    }

    METRICS_FILE.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("\nTEST RESULTS")
    print(json.dumps(metrics, indent=2))
    print(f"\nSaved model: {MODEL_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--train",
        action="store_true",
    )
    args = parser.parse_args()

    if args.train:
        train()
    else:
        print("Run with --train")
