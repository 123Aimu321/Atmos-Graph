"""AtmoGraph local two-client WebSocket and Neo4j acceptance test.

Default mode is read-only. --write creates exactly one new synthetic
ImpactSnapshot (and related incident risk states) in the local database.

Requirements: running FastAPI/Neo4j, trained synthetic model checkpoints,
httpx, and websockets (installed by uvicorn[standard]).
"""
import argparse
import asyncio
import json
import sys
from urllib.parse import quote

import httpx
from websockets import connect


TEST_INCIDENT = "ATMOGRAPH_PHASE32_TEST_PORT001"
SOURCE_NODE = "PORT_001"
EXPECTED_COUNT = 25
VALID_STATUSES = {"NORMAL", "AFFECTED", "DISRUPTED"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


async def json_request(client, method, path, payload=None):
    response = await client.request(method, path, json=payload)
    if response.is_error:
        raise RuntimeError(
            f"{method} {path}: HTTP {response.status_code} "
            f"{response.text[:500]}"
        )
    return response.json()


async def preflight(client, incident_id, source):
    # Protect real-world news incidents from test writes.
    require(
        incident_id.startswith("ATMOGRAPH_") and "TEST" in incident_id,
        "Use a dedicated incident ID containing ATMOGRAPH_ and TEST.",
    )
    incidents = await json_request(
        client, "GET", "/api/incidents?status=CONFIRMED&limit=200"
    )
    records = incidents.get("incidents", [])
    matching = [
        item for item in records
        if item.get("incident_id") == incident_id
    ]
    require(
        len(matching) == 1,
        f"Confirmed synthetic test incident {incident_id!r} not found.",
    )
    incident = matching[0]
    linked = [
        entry.get("node_id") for entry in
        (incident.get("affected_entities") or [])
        if isinstance(entry, dict) and entry.get("node_id")
    ]
    require(
        linked == [source],
        f"Incident must link only to {source}; found {linked}.",
    )

    prediction = await json_request(
        client, "POST", "/api/predict",
        {"disrupted_node": source},
    )
    delay = await json_request(
        client, "POST", "/api/delay/predict",
        {
            "disrupted_node": source,
            "initial_delay_days": 14,
            "decay": 0.75,
        },
    )
    forecast = await json_request(
        client, "POST", "/api/forecast/predict",
        {
            "disrupted_node": source,
            "initial_delay_days": 14,
            "decay": 0.75,
            "recovery_half_life_days": 30,
        },
    )

    results = prediction.get("results", [])
    require(
        len(results) == EXPECTED_COUNT,
        f"Expected {EXPECTED_COUNT} prediction entities, got {len(results)}.",
    )
    source_results = [
        row for row in results
        if row.get("predicted_status") == "DISRUPTED"
    ]
    require(
        len(source_results) == 1 and
        source_results[0].get("node_id") == source,
        "GNN prediction has an unexpected DISRUPTED source.",
    )
    horizons = {
        row.get("horizon_days") for row in forecast.get("horizons", [])
    }
    require(horizons == {30, 60, 90}, "Missing recovery horizon.")
    return {
        "prediction": prediction,
        "delay": delay,
        "forecast": forecast,
    }


async def wait_for_prediction_event(websocket, timeout):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        require(remaining > 0, "Timed out waiting for prediction event.")
        message = await asyncio.wait_for(websocket.recv(), remaining)
        event = json.loads(message)
        if event.get("type") == "impact.prediction.updated":
            return event


async def live_acceptance(args, client, data):
    origin = "http://127.0.0.1:5173"

    async with (
        connect(args.ws_url, origin=origin) as socket_a,
        connect(args.ws_url, origin=origin) as socket_b,
    ):
        hello_a, hello_b = await asyncio.gather(
            asyncio.wait_for(socket_a.recv(), 10),
            asyncio.wait_for(socket_b.recv(), 10),
        )
        for hello in (hello_a, hello_b):
            require(
                json.loads(hello).get("type") == "connection.established",
                "One of the WebSocket clients was not accepted.",
            )
        print("[PASS] Two independent WebSocket clients connected")

        # The socket connections are open before the snapshot write.
        response = await json_request(
            client,
            "POST",
            "/api/history/incidents/"
            f"{quote(args.incident_id, safe='')}/snapshots",
            data,
        )
        snapshot_id = (response.get("snapshot") or {}).get("snapshot_id")
        require(snapshot_id, "Snapshot POST did not return snapshot_id.")
        print("[PASS] Saved new synthetic snapshot", snapshot_id)

        events = await asyncio.gather(
            wait_for_prediction_event(socket_a, args.event_timeout),
            wait_for_prediction_event(socket_b, args.event_timeout),
        )
        for event in events:
            payload = event.get("data") or {}
            require(
                payload.get("snapshot_id") == snapshot_id,
                "WebSocket payload references a different snapshot.",
            )
            require(
                payload.get("incident_id") == args.incident_id,
                "WebSocket incident ID mismatch.",
            )
            require(
                payload.get("source_node_id") == args.source_node,
                "WebSocket source node mismatch.",
            )
            require(
                payload.get("data_origin") == "SYNTHETIC_SIMULATION",
                "Unexpected WebSocket data origin.",
            )
            require(
                len((payload.get("prediction") or {}).get("results", []))
                == EXPECTED_COUNT,
                "Incomplete WebSocket prediction payload.",
            )
        print("[PASS] Both clients received the same validated prediction")

    saved = await json_request(
        client, "GET",
        f"/api/history/snapshots/{quote(snapshot_id, safe='')}",
    )
    require(
        saved.get("snapshot_id") == snapshot_id and
        saved.get("incident_id") == args.incident_id,
        "Snapshot was not retrieved correctly.",
    )
    for key in ("prediction", "delay", "forecast"):
        require(
            isinstance(saved.get(key), dict),
            f"Persisted snapshot lacks {key}.",
        )
    print("[PASS] Saved prediction, regression and forecast retrieved")

    risk = await json_request(
        client, "GET",
        "/api/impact-states/incidents/"
        f"{quote(args.incident_id, safe='')}",
    )
    states = risk.get("risk_states", [])
    require(
        risk.get("snapshot_id") == snapshot_id,
        "Risk-state API did not return the newly saved snapshot.",
    )
    require(
        len(states) == EXPECTED_COUNT,
        f"Expected {EXPECTED_COUNT} risk states, got {len(states)}.",
    )
    require(
        len({item.get("node_id") for item in states}) == EXPECTED_COUNT,
        "Duplicate risk-state node IDs.",
    )
    require(
        all(
            item.get("predicted_status") in VALID_STATUSES
            for item in states
        ),
        "Invalid risk state found.",
    )
    disrupted = [
        item.get("node_id") for item in states
        if item.get("predicted_status") == "DISRUPTED"
    ]
    require(
        disrupted == [args.source_node],
        f"Wrong disrupted source in Neo4j states: {disrupted}",
    )
    print("[PASS] 25 incident-scoped statuses persisted and retrieved")
    print("[PASS] Phase 35 two-client acceptance workflow")


async def run(args):
    async with httpx.AsyncClient(
        base_url=args.base_url,
        timeout=httpx.Timeout(120.0),
        trust_env=False,
    ) as client:
        data = await preflight(client, args.incident_id, args.source_node)
        print("[PASS] Confirmed synthetic incident and model API preflight")
        if not args.write:
            print(
                "[DRY RUN] Nothing written. Rerun with --write to "
                "verify two-client broadcasts and Neo4j persistence."
            )
            return
        await live_acceptance(args, client, data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--incident-id", default=TEST_INCIDENT,
        help="Dedicated confirmed synthetic TEST incident.",
    )
    parser.add_argument("--source-node", default=SOURCE_NODE)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8000/ws/incidents")
    parser.add_argument("--event-timeout", type=float, default=20.0)
    parser.add_argument(
        "--write", action="store_true",
        help="Explicitly create a new test snapshot; default is read-only.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except (RuntimeError, ValueError, OSError, httpx.HTTPError, TimeoutError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
