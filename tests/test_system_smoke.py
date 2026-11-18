
import argparse
import sys
import time

import httpx


DEFAULT_URL = "http://127.0.0.1:8000"

PASSED = []
FAILED = []
WARNINGS = []


def check(name, function):
    start = time.perf_counter()

    try:
        details = function()
        elapsed = (
            time.perf_counter() - start
        ) * 1000

        PASSED.append(name)

        print(
            f"[PASS] {name} "
            f"({elapsed:.1f} ms)"
        )

        if details:
            print(f"       {details}")

    except Exception as exc:
        FAILED.append((name, str(exc)))

        print(f"[FAIL] {name}")
        print(f"       {exc}")


def assert_condition(condition, message):
    if not condition:
        raise AssertionError(message)


def get_json(client, path):
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def test_openapi(client):
    schema = get_json(
        client, "/openapi.json"
    )

    assert_condition(
        isinstance(schema.get("paths"), dict),
        "OpenAPI paths unavailable",
    )

    return (
        f"{len(schema['paths'])} "
        "documented paths"
    )


def test_graph(client):
    data = get_json(
        client, "/api/graph"
    )

    nodes = data.get("nodes")
    edges = data.get("edges")

    assert_condition(
        isinstance(nodes, list),
        "Graph nodes must be a list",
    )

    assert_condition(
        isinstance(edges, list),
        "Graph edges must be a list",
    )

    assert_condition(
        len(nodes) > 0,
        "Supply-chain graph is empty",
    )

    return (
        f"{len(nodes)} nodes, "
        f"{len(edges)} edges"
    )


def test_model_metrics(client):
    data = get_json(
        client, "/api/model/metrics"
    )

    assert_condition(
        isinstance(data, dict),
        "Model metrics must be an object",
    )

    return "GraphSAGE metrics available"


def test_delay_metrics(client):
    data = get_json(
        client, "/api/delay/metrics"
    )

    assert_condition(
        isinstance(data, dict),
        "Delay metrics must be an object",
    )

    return "Delay regression metrics available"


def test_incidents(client):
    data = get_json(
        client,
        "/api/incidents?limit=10"
    )

    assert_condition(
        isinstance(data.get("incidents"), list),
        "Incident list unavailable",
    )

    return (
        f"{len(data['incidents'])} "
        "incidents returned"
    )


def test_explorer_search(client):
    data = get_json(
        client,
        "/api/explorer/entities"
        "?q=BENCH_&origin=BENCHMARK"
        "&limit=10"
    )

    entities = data.get("entities")

    assert_condition(
        isinstance(entities, list),
        "Invalid search response",
    )

    assert_condition(
        len(entities) > 0,
        "Benchmark entities not found",
    )

    assert_condition(
        all(
            item.get("node_id", "").startswith(
                "BENCH_"
            )
            for item in entities
        ),
        "Search returned non-benchmark nodes",
    )

    return (
        f"{len(entities)} "
        "benchmark entities returned"
    )


def test_explorer_neighborhood(client):
    data = get_json(
        client,
        "/api/explorer/neighborhood/"
        "BENCH_000001"
        "?depth=4"
        "&max_nodes=300"
        "&max_relationships=1000"
        "&direction=downstream"
    )

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    summary = data.get("summary", {})

    ids = {
        node.get("id")
        for node in nodes
    }

    assert_condition(
        "BENCH_000001" in ids,
        "Source node missing",
    )

    assert_condition(
        len(nodes) <= 300,
        "Node limit exceeded",
    )

    assert_condition(
        len(edges) <= 1000,
        "Edge limit exceeded",
    )

    assert_condition(
        len(ids) == len(nodes),
        "Duplicate nodes found",
    )

    assert_condition(
        all(
            edge.get("source") in ids
            and edge.get("target") in ids
            for edge in edges
        ),
        "Edge references a missing node",
    )

    return (
        f"{summary.get('total_nodes')} nodes, "
        f"{summary.get('total_edges')} edges, "
        f"truncated={summary.get('truncated')}"
    )


def test_history_routes(client):
    schema = get_json(
        client, "/openapi.json"
    )

    paths = schema.get("paths", {})

    expected = [
        "/api/history/incidents/"
        "{incident_id}/snapshots",
        "/api/history/snapshots/"
        "{snapshot_id}",
    ]

    missing = [
        path
        for path in expected
        if path not in paths
    ]

    assert_condition(
        not missing,
        f"Missing routes: {missing}",
    )

    return "History API registered"


def test_forecast_route(client):
    schema = get_json(
        client, "/openapi.json"
    )

    paths = schema.get("paths", {})

    assert_condition(
        "/api/forecast/predict" in paths,
        "Forecast route missing",
    )

    return "30/60/90 forecast API registered"


def test_prediction_route(client):
    schema = get_json(
        client, "/openapi.json"
    )

    paths = schema.get("paths", {})

    assert_condition(
        "/api/predict" in paths,
        "Prediction route missing",
    )

    return "GraphSAGE prediction API registered"


def test_news_route(client):
    schema = get_json(
        client, "/openapi.json"
    )

    paths = schema.get("paths", {})

    assert_condition(
        "/api/incidents/ingest" in paths,
        "News ingestion route missing",
    )

    return "News ingestion API registered"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base-url",
        default=DEFAULT_URL,
    )

    args = parser.parse_args()

    print("=" * 55)
    print("ATMOGRAPH — SYSTEM SMOKE TEST")
    print("=" * 55)

    with httpx.Client(
        base_url=args.base_url,
        timeout=30,
        trust_env=False,
    ) as client:

        tests = [
            ("OpenAPI", test_openapi),
            ("Supply-chain graph", test_graph),
            (
                "GraphSAGE metrics",
                test_model_metrics,
            ),
            (
                "Delay regression metrics",
                test_delay_metrics,
            ),
            (
                "Incident retrieval",
                test_incidents,
            ),
            (
                "Benchmark entity search",
                test_explorer_search,
            ),
            (
                "Bounded graph neighborhood",
                test_explorer_neighborhood,
            ),
            (
                "History API registration",
                test_history_routes,
            ),
            (
                "Forecast API registration",
                test_forecast_route,
            ),
            (
                "Prediction API registration",
                test_prediction_route,
            ),
            (
                "News ingestion registration",
                test_news_route,
            ),
        ]

        for name, function in tests:
            check(
                name,
                lambda fn=function: fn(client),
            )

    print("\n" + "=" * 55)
    print("TEST SUMMARY")
    print("=" * 55)

    print(f"Passed: {len(PASSED)}")
    print(f"Failed: {len(FAILED)}")

    if FAILED:
        print("\nFailures:")

        for name, message in FAILED:
            print(f"- {name}: {message}")

        sys.exit(1)

    print(
        "\nAll basic system checks passed."
    )


if __name__ == "__main__":
    main()
