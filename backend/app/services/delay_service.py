
import json
from functools import lru_cache

import torch

from ml.gnn.delay_regression import (
    MODEL_FILE,
    METRICS_FILE,
    DelayGraphSAGE,
    load_network,
    make_features,
)


@lru_cache(maxsize=1)
def load_delay_resources():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            "Delay regression model not found. "
            "Run: python -m ml.gnn.delay_regression --train"
        )

    network = load_network()

    checkpoint = torch.load(
        MODEL_FILE,
        map_location="cpu",
        weights_only=True,
    )

    if checkpoint["node_ids"] != network["ids"]:
        raise ValueError(
            "Graph node order differs from training. "
            "Retrain the delay model."
        )

    if checkpoint["regions"] != network["regions"]:
        raise ValueError(
            "Graph regions differ from training. "
            "Retrain the delay model."
        )

    model = DelayGraphSAGE(
        input_dim=checkpoint["input_dim"],
        hidden_dim=checkpoint["hidden_dim"],
        layers=checkpoint["layers"],
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    return model, network


def predict_delay(
    disrupted_node,
    initial_delay_days=14.0,
    decay=0.75,
):
    model, network = load_delay_resources()

    if disrupted_node not in network["id_to_index"]:
        raise ValueError(
            f"Unknown synthetic entity: {disrupted_node}"
        )

    if not 1 <= initial_delay_days <= 90:
        raise ValueError(
            "initial_delay_days must be between 1 and 90"
        )

    if not 0.5 <= decay <= 0.95:
        raise ValueError(
            "decay must be between 0.5 and 0.95"
        )

    source_index = network["id_to_index"][
        disrupted_node
    ]

    features = make_features(
        network,
        source_index,
        initial_delay_days,
        decay,
    )

    with torch.no_grad():
        predictions = model(
            features,
            network["edge_index"],
        ).numpy()

    # Identify nodes actually reachable through
    # directed supply-chain edges.
    reachable = {source_index}
    frontier = [source_index]

    while frontier:
        current = frontier.pop()

        for target, _ in network["adjacency"][current]:
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)

    results = []

    for index, node_id in enumerate(network["ids"]):
        is_reachable = index in reachable

        # Enforce the graph's reachability constraint.
        # The model may produce small positive outputs
        # for unreachable nodes due to Softplus.
        estimated = (
            max(0.0, float(predictions[index]))
            if is_reachable
            else 0.0
        )

        results.append({
            "node_id": node_id,
            "predicted_delay_days": round(
                estimated, 2
            ),
            "is_downstream": (
                is_reachable
                and index != source_index
            ),
            "is_disruption_source": (
                index == source_index
            ),
        })

    downstream = [
        item for item in results
        if item["is_downstream"]
    ]

    return {
        "disrupted_node": disrupted_node,
        "initial_delay_days": initial_delay_days,
        "decay": decay,
        "model": "GraphSAGE Regression",
        "data_origin": "SYNTHETIC_SIMULATION",
        "summary": {
            "downstream_entities": len(downstream),
            "max_predicted_delay_days": round(
                max(
                    (
                        item["predicted_delay_days"]
                        for item in downstream
                    ),
                    default=0.0,
                ),
                2,
            ),
            "mean_predicted_delay_days": round(
                sum(
                    item["predicted_delay_days"]
                    for item in downstream
                ) / max(len(downstream), 1),
                2,
            ),
        },
        "results": results,
        "disclaimer": (
            "Experimental delay estimates trained "
            "on synthetic propagation targets."
        ),
    }


def get_delay_metrics():
    if not METRICS_FILE.exists():
        raise FileNotFoundError(
            "Delay metrics unavailable. Train the model."
        )

    return json.loads(
        METRICS_FILE.read_text(
            encoding="utf-8"
        )
    )
