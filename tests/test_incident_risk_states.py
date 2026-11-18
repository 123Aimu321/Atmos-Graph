"""Read-only check for the new incident-scoped risk-state graph."""
import argparse
import sys

import httpx

VALID = {"NORMAL", "AFFECTED", "DISRUPTED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--source-node", default="PORT_001")
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000"
    )
    args = parser.parse_args()

    with httpx.Client(
        base_url=args.base_url, timeout=60, trust_env=False
    ) as client:
        response = client.get(
            f"/api/impact-states/incidents/{args.incident_id}"
        )
        response.raise_for_status()
        payload = response.json()

    states = payload.get("risk_states", [])
    assert len(states) == 25, (
        f"Expected 25 new risk states, found {len(states)}; "
        "save a NEW snapshot after applying this refactor."
    )

    ids = [item["node_id"] for item in states]
    assert len(set(ids)) == len(ids), "Duplicate entity IDs"
    assert all(
        item["predicted_status"] in VALID
        and item["predicted_delay_days"] >= 0
        for item in states
    ), "Invalid risk states"

    sources = [
        item["node_id"] for item in states
        if item.get("is_disruption_source")
    ]
    assert sources == [args.source_node], (
        f"Unexpected source nodes: {sources}"
    )

    print("[PASS] 25 incident risk states persisted")
    print("[PASS] Unique IDs, valid status and delay values")
    print("[PASS] Source entity:", sources[0])
    print("[PASS] Snapshot:", payload["snapshot_id"])


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print("[FAIL]", exc)
        sys.exit(1)
