
import argparse
import json
import math
import statistics
import sys
import time

from pathlib import Path
from datetime import datetime, timezone

import httpx


ROOT = Path(__file__).resolve().parents[1]

REPORT_DIR = ROOT / "reports" / "testing"

SOURCE_NODE = "PORT_001"

INITIAL_DELAY_DAYS = 14
DECAY = 0.75
RECOVERY_HALF_LIFE_DAYS = 30

VALID_CLASSES = {
    "NORMAL",
    "AFFECTED",
    "DISRUPTED",
}


class IntegrationTestError(Exception):
    pass


def ensure(condition, message):
    if not condition:
        raise IntegrationTestError(message)


def request_json(
    client,
    method,
    path,
    payload=None,
):
    start = time.perf_counter()

    response = client.request(
        method,
        path,
        json=payload,
    )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    if not response.is_success:
        raise IntegrationTestError(
            f"{method} {path} returned "
            f"{response.status_code}: "
            f"{response.text[:800]}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise IntegrationTestError(
            f"{path} did not return valid JSON"
        ) from exc

    ensure(
        isinstance(data, dict),
        f"{path} must return a JSON object",
    )

    return data, round(elapsed_ms, 2)


def get_items(data, possible_keys):
    """
    Support alternate response key names.
    Return the first list found.
    """
    for key in possible_keys:
        value = data.get(key)

        if isinstance(value, list):
            return value

    return None


def get_node_id(item):
    return (
        item.get("node_id")
        or item.get("id")
    )


def get_class(item):
    return (
        item.get("predicted_status")
        or item.get("status")
        or item.get("prediction")
    )


def validate_graph(data):
    nodes = data.get("nodes")
    edges = data.get("edges")

    ensure(
        isinstance(nodes, list),
        "Graph nodes must be a list",
    )

    ensure(
        isinstance(edges, list),
        "Graph edges must be a list",
    )

    node_ids = {
        get_node_id(node)
        for node in nodes
        if isinstance(node, dict)
    }

    ensure(
        None not in node_ids,
        "Graph contains a node without an ID",
    )

    ensure(
        len(node_ids) == len(nodes),
        "Duplicate node IDs found",
    )

    ensure(
        SOURCE_NODE in node_ids,
        f"{SOURCE_NODE} missing from graph",
    )

    for edge in edges:
        ensure(
            edge.get("source") in node_ids
            and edge.get("target") in node_ids,
            "Graph contains an invalid edge",
        )

    return node_ids


def validate_prediction(data, node_ids):
    results = get_items(
        data,
        (
            "results",
            "predictions",
            "node_predictions",
        ),
    )

    ensure(
        results is not None,
        "Prediction response has no recognizable "
        "node-results array. Available keys: "
        f"{sorted(data)}",
    )

    ensure(
        len(results) > 0,
        "Prediction results are empty",
    )

    observed = set()
    classes = {}

    for item in results:
        ensure(
            isinstance(item, dict),
            "Prediction result must be an object",
        )

        node_id = get_node_id(item)
        predicted_class = get_class(item)

        ensure(
            node_id in node_ids,
            f"Unknown prediction node: {node_id}",
        )

        ensure(
            node_id not in observed,
            f"Duplicate prediction node: {node_id}",
        )

        ensure(
            predicted_class in VALID_CLASSES,
            f"Invalid predicted class for "
            f"{node_id}: {predicted_class}",
        )

        observed.add(node_id)
        classes[node_id] = predicted_class

    ensure(
        observed == node_ids,
        "Prediction does not cover the complete "
        "25-node synthetic network",
    )

    return {
        name: sum(
            value == name
            for value in classes.values()
        )
        for name in sorted(VALID_CLASSES)
    }


def find_numeric_delay(item):
    for key in (
        "predicted_delay_days",
        "delay_days",
        "estimated_delay_days",
    ):
        value = item.get(key)

        if isinstance(value, (int, float)):
            return float(value)

    return None


def validate_delay(data, node_ids):
    results = get_items(
        data,
        (
            "results",
            "predictions",
            "node_delays",
            "delays",
        ),
    )

    ensure(
        results is not None,
        "Delay response has no recognizable "
        "results array. Available keys: "
        f"{sorted(data)}",
    )

    ensure(
        len(results) > 0,
        "Delay prediction returned no entities",
    )

    seen = set()
    values = []

    for item in results:
        ensure(
            isinstance(item, dict),
            "Delay result must be an object",
        )

        node_id = get_node_id(item)

        ensure(
            node_id in node_ids,
            f"Unknown delay node: {node_id}",
        )

        ensure(
            node_id not in seen,
            f"Duplicate delay node: {node_id}",
        )

        seen.add(node_id)

        delay = find_numeric_delay(item)

        ensure(
            delay is not None,
            f"Missing numeric delay for {node_id}",
        )

        ensure(
            math.isfinite(delay) and delay >= 0,
            f"Invalid delay for {node_id}: {delay}",
        )

        values.append(delay)

    ensure(
        seen == node_ids,
        "Delay results do not cover "
        "the entire synthetic graph",
    )

    return {
        "entities": len(values),
        "mean_delay_days": round(
            statistics.mean(values), 3
        ),
        "max_delay_days": round(
            max(values), 3
        ),
    }


def validate_forecast(data):
    horizons = get_items(
        data,
        (
            "horizons",
            "forecasts",
            "scenarios",
        ),
    )

    ensure(
        horizons is not None,
        "Forecast response has no recognizable "
        "horizons array. Available keys: "
        f"{sorted(data)}",
    )

    observed = set()
    horizon_details = []

    for horizon in horizons:
        ensure(
            isinstance(horizon, dict),
            "Forecast horizon must be an object",
        )

        day = (
            horizon.get("horizon_days")
            or horizon.get("day")
            or horizon.get("days")
        )

        ensure(
            isinstance(day, int)
            and not isinstance(day, bool),
            "Forecast horizon day must be an integer",
        )

        ensure(
            day not in observed,
            f"Duplicate forecast horizon: {day}",
        )

        observed.add(day)

        horizon_details.append({
            "day": day,
            "summary": (
                horizon.get("summary") or {}
            ),
        })

    ensure(
        {30, 60, 90}.issubset(observed),
        "Forecast must include "
        "days 30, 60 and 90",
    )

    return horizon_details


def check_history_api(client):
    incidents, elapsed = request_json(
        client,
        "GET",
        "/api/incidents?status=CONFIRMED&limit=50",
    )

    items = incidents.get("incidents")

    ensure(
        isinstance(items, list),
        "Confirmed incidents must be a list",
    )

    if not items:
        return {
            "confirmed_incidents": 0,
            "message": (
                "No confirmed incidents; "
                "history listing skipped"
            ),
            "response_ms": elapsed,
        }

    incident_id = items[0].get("incident_id")

    ensure(
        incident_id,
        "Confirmed incident missing incident_id",
    )

    history, history_ms = request_json(
        client,
        "GET",
        (
            "/api/history/incidents/"
            f"{incident_id}/snapshots"
        ),
    )

    snapshots = history.get("snapshots")

    ensure(
        isinstance(snapshots, list),
        "History snapshots must be a list",
    )

    result = {
        "confirmed_incidents": len(items),
        "selected_incident": incident_id,
        "snapshots": len(snapshots),
        "response_ms": history_ms,
    }

    if snapshots:
        snapshot_id = snapshots[0].get(
            "snapshot_id"
        )

        ensure(
            snapshot_id,
            "Snapshot missing snapshot_id",
        )

        snapshot, detail_ms = request_json(
            client,
            "GET",
            f"/api/history/snapshots/{snapshot_id}",
        )

        ensure(
            snapshot.get("snapshot_id")
            == snapshot_id,
            "Snapshot ID mismatch",
        )

        result["retrieved_snapshot"] = snapshot_id
        result["detail_response_ms"] = detail_ms

    return result


def measure_warm_latency(
    client,
    path,
    repetitions=10,
):
    # First request warms the endpoint.
    response = client.get(path)
    response.raise_for_status()

    timings = []

    for _ in range(repetitions):
        start = time.perf_counter()

        response = client.get(path)
        response.raise_for_status()

        timings.append(
            (time.perf_counter() - start)
            * 1000
        )

    return {
        "mean_ms": round(
            statistics.mean(timings), 2
        ),
        "min_ms": round(
            min(timings), 2
        ),
        "max_ms": round(
            max(timings), 2
        ),
        "samples": repetitions,
    }


def run_test(name, fn, report):
    print(f"\n[TEST] {name}")

    try:
        result = fn()

        report["tests"][name] = {
            "status": "PASS",
            "result": result,
        }

        print(f"[PASS] {name}")

        if result is not None:
            print(
                json.dumps(
                    result,
                    indent=2,
                    default=str,
                )
            )

        return result

    except Exception as exc:
        report["tests"][name] = {
            "status": "FAIL",
            "error": str(exc),
        }

        print(f"[FAIL] {name}")
        print(f"       {exc}")

        return None


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )

    args = parser.parse_args()

    report = {
        "project": "AtmoGraph",
        "phase": 31,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "scenario": {
            "source_node": SOURCE_NODE,
            "initial_delay_days": (
                INITIAL_DELAY_DAYS
            ),
            "decay": DECAY,
            "recovery_half_life_days": (
                RECOVERY_HALF_LIFE_DAYS
            ),
        },
        "tests": {},
    }

    print("=" * 60)
    print("ATMOGRAPH — PHASE 31 INTEGRATION TEST")
    print("=" * 60)

    with httpx.Client(
        base_url=args.base_url,
        timeout=120,
        trust_env=False,
    ) as client:

        graph_data = run_test(
            "Supply-chain graph",
            lambda: request_json(
                client,
                "GET",
                "/api/graph",
            )[0],
            report,
        )

        node_ids = None

        if graph_data:
            node_ids = run_test(
                "Graph integrity",
                lambda: sorted(
                    validate_graph(graph_data)
                ),
                report,
            )

        if node_ids is not None:
            prediction_result = run_test(
                "GraphSAGE classification",
                lambda: request_json(
                    client,
                    "POST",
                    "/api/predict",
                    {
                        "disrupted_node": SOURCE_NODE,
                    },
                )[0],
                report,
            )

            if prediction_result:
                run_test(
                    "Prediction integrity",
                    lambda: validate_prediction(
                        prediction_result,
                        set(node_ids),
                    ),
                    report,
                )

            delay_result = run_test(
                "GraphSAGE delay regression",
                lambda: request_json(
                    client,
                    "POST",
                    "/api/delay/predict",
                    {
                        "disrupted_node": SOURCE_NODE,
                        "initial_delay_days": (
                            INITIAL_DELAY_DAYS
                        ),
                        "decay": DECAY,
                    },
                )[0],
                report,
            )

            if delay_result:
                run_test(
                    "Delay integrity",
                    lambda: validate_delay(
                        delay_result,
                        set(node_ids),
                    ),
                    report,
                )

        forecast_result = run_test(
            "Recovery forecast",
            lambda: request_json(
                client,
                "POST",
                "/api/forecast/predict",
                {
                    "disrupted_node": SOURCE_NODE,
                    "initial_delay_days": (
                        INITIAL_DELAY_DAYS
                    ),
                    "decay": DECAY,
                    "recovery_half_life_days": (
                        RECOVERY_HALF_LIFE_DAYS
                    ),
                },
            )[0],
            report,
        )

        if forecast_result:
            run_test(
                "Forecast horizon integrity",
                lambda: validate_forecast(
                    forecast_result
                ),
                report,
            )

        run_test(
            "Neo4j impact history",
            lambda: check_history_api(
                client
            ),
            report,
        )

        run_test(
            "Warm API latency",
            lambda: {
                "graph": measure_warm_latency(
                    client,
                    "/api/graph",
                ),
                "openapi": measure_warm_latency(
                    client,
                    "/openapi.json",
                ),
            },
            report,
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        REPORT_DIR /
        "phase31_integration_report.json"
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    statuses = [
        item["status"]
        for item in report["tests"].values()
    ]

    passed = statuses.count("PASS")
    failed = statuses.count("FAIL")

    print("\n" + "=" * 60)
    print("PHASE 31 SUMMARY")
    print("=" * 60)

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Report: {output_path}")

    if failed:
        sys.exit(1)

    print("\nAll executed integration checks passed.")


if __name__ == "__main__":
    main()
