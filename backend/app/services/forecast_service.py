
import heapq
import math

from backend.app.services.delay_service import (
    predict_delay,
)
from ml.gnn.delay_regression import load_network


HORIZONS = (30, 60, 90)


def calculate_arrival_days(network, source_id):
    """
    Minimum cumulative transport time along
    directed paths from the disrupted entity.

    This is a simplified exposure-time proxy.
    It is not an observed delivery schedule.
    """
    source = network["id_to_index"][source_id]
    distances = {source: 0.0}
    queue = [(0.0, source)]

    while queue:
        current_days, current = heapq.heappop(queue)

        if current_days > distances[current]:
            continue

        for target, transport_days in (
            network["adjacency"][current]
        ):
            candidate = current_days + transport_days

            if candidate < distances.get(
                target, math.inf
            ):
                distances[target] = candidate
                heapq.heappush(
                    queue, (candidate, target)
                )

    return distances


def forecast_disruption(
    disrupted_node,
    initial_delay_days=14.0,
    decay=0.75,
    recovery_half_life_days=30.0,
):
    if not 1 <= recovery_half_life_days <= 180:
        raise ValueError(
            "Recovery half-life must be 1–180 days"
        )

    network = load_network()

    # Reuse the trained GraphSAGE regression.
    delay_prediction = predict_delay(
        disrupted_node=disrupted_node,
        initial_delay_days=initial_delay_days,
        decay=decay,
    )

    arrival_days = calculate_arrival_days(
        network, disrupted_node
    )

    snapshots = []

    for horizon in HORIZONS:
        entities = []

        for item in delay_prediction["results"]:
            node_id = item["node_id"]
            index = network["id_to_index"][node_id]

            arrival = arrival_days.get(
                index, math.inf
            )

            exposed = (
                math.isfinite(arrival)
                and arrival <= horizon
            )

            base_delay = float(
                item["predicted_delay_days"]
            )

            # Recovery begins after the modeled
            # downstream exposure time.
            elapsed_recovery = max(
                0.0, horizon - arrival
            )

            recovery_factor = (
                0.5 ** (
                    elapsed_recovery
                    / recovery_half_life_days
                )
            )

            residual_delay = (
                base_delay * recovery_factor
                if exposed
                else 0.0
            )

            entities.append({
                "node_id": node_id,
                "is_downstream": item["is_downstream"],
                "is_disruption_source": (
                    item["is_disruption_source"]
                ),
                "estimated_exposure_day": (
                    round(arrival, 2)
                    if math.isfinite(arrival)
                    else None
                ),
                "exposed_by_horizon": exposed,
                "baseline_delay_days": round(
                    base_delay, 2
                ),
                "residual_delay_days": round(
                    residual_delay, 2
                ),
            })

        downstream = [
            entity
            for entity in entities
            if entity["is_downstream"]
        ]

        exposed_downstream = [
            entity
            for entity in downstream
            if entity["exposed_by_horizon"]
        ]

        total_residual = sum(
            entity["residual_delay_days"]
            for entity in exposed_downstream
        )

        snapshots.append({
            "horizon_days": horizon,
            "summary": {
                "exposed_downstream_entities": len(
                    exposed_downstream
                ),
                "total_downstream_entities": len(
                    downstream
                ),
                "mean_residual_delay_days": round(
                    total_residual
                    / max(len(exposed_downstream), 1),
                    2,
                ),
                "max_residual_delay_days": round(
                    max(
                        (
                            entity["residual_delay_days"]
                            for entity in exposed_downstream
                        ),
                        default=0.0,
                    ),
                    2,
                ),
            },
            "entities": entities,
        })

    return {
        "disrupted_node": disrupted_node,
        "initial_delay_days": initial_delay_days,
        "decay": decay,
        "recovery_half_life_days": (
            recovery_half_life_days
        ),
        "model": (
            "GraphSAGE regression + "
            "assumption-based recovery scenario"
        ),
        "data_origin": "SYNTHETIC_SIMULATION",
        "horizons": snapshots,
        "disclaimer": (
            "30/60/90-day scenarios are derived "
            "from synthetic delay predictions, "
            "transport-time exposure estimates, "
            "and assumed exponential recovery. "
            "They are not validated temporal forecasts."
        ),
    }
