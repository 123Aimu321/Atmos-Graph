
import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT / "datasets" / "benchmark"
)

DEFAULT_BASE_URL = (
    "http://127.0.0.1:8000"
)


TEST_CASES = [
    {
        "name": "entity_search",
        "path": (
            "/api/explorer/entities"
            "?q=BENCH_&limit=30"
        ),
    },
    {
        "name": "depth_1",
        "path": (
            "/api/explorer/neighborhood/"
            "BENCH_000001"
            "?depth=1&max_nodes=100"
            "&max_relationships=500"
        ),
    },
    {
        "name": "depth_2",
        "path": (
            "/api/explorer/neighborhood/"
            "BENCH_000001"
            "?depth=2&max_nodes=100"
            "&max_relationships=500"
        ),
    },
    {
        "name": "depth_3",
        "path": (
            "/api/explorer/neighborhood/"
            "BENCH_000001"
            "?depth=3&max_nodes=200"
            "&max_relationships=500"
        ),
    },
    {
        "name": "depth_4",
        "path": (
            "/api/explorer/neighborhood/"
            "BENCH_000001"
            "?depth=4&max_nodes=300"
            "&max_relationships=1000"
        ),
    },
]


def percentile(values, fraction):
    ordered = sorted(values)

    if not ordered:
        return 0.0

    index = int(
        (len(ordered) - 1) * fraction
    )

    return ordered[index]


def benchmark_case(
    client,
    base_url,
    test_case,
    repetitions,
):
    url = base_url.rstrip("/") + test_case["path"]

    # Warm up the endpoint before measuring.
    warmup = client.get(url)
    warmup.raise_for_status()

    timings = []
    result = None

    for _ in range(repetitions):
        start = time.perf_counter()

        response = client.get(url)

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        response.raise_for_status()

        result = response.json()

        timings.append(elapsed_ms)

    summary = result.get("summary") or {}

    return {
        "test": test_case["name"],
        "requests": repetitions,
        "mean_ms": round(
            statistics.mean(timings), 2
        ),
        "median_ms": round(
            statistics.median(timings), 2
        ),
        "p95_ms": round(
            percentile(timings, 0.95), 2
        ),
        "maximum_ms": round(
            max(timings), 2
        ),
        "returned_nodes": (
            summary.get("total_nodes")
            if summary
            else result.get("returned")
        ),
        "returned_edges": summary.get(
            "total_edges"
        ),
        "truncated": summary.get(
            "truncated"
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=20,
    )

    args = parser.parse_args()

    if args.repetitions < 1:
        parser.error(
            "repetitions must be positive"
        )

    results = []

    with httpx.Client(
        timeout=30,
        trust_env=False,
    ) as client:
        for test_case in TEST_CASES:
            print(
                f"Testing {test_case['name']}..."
            )

            result = benchmark_case(
                client,
                args.base_url,
                test_case,
                args.repetitions,
            )

            results.append(result)

            print(
                f"  Mean: {result['mean_ms']} ms"
            )

            print(
                f"  P95: {result['p95_ms']} ms"
            )

            print(
                f"  Nodes: "
                f"{result['returned_nodes']}"
            )

    report = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "base_url": args.base_url,
        "repetitions": args.repetitions,
        "results": results,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR / "api_benchmark.json"
    )

    output_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nBenchmark completed")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
