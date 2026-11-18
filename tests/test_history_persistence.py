
import argparse
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Test AtmoGraph impact history "
            "using a confirmed synthetic incident"
        )
    )

    parser.add_argument(
        "--incident-id",
        required=True,
        help="ID of a synthetic test incident",
    )

    parser.add_argument(
        "--node-id",
        required=True,
        help="Entity confirmed for the incident",
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help="Explicitly create a test snapshot",
    )

    args = parser.parse_args()

    with httpx.Client(
        base_url=args.base_url,
        timeout=120,
        trust_env=False,
    ) as client:

        def post(path, payload):
            response = client.post(
                path,
                json=payload,
            )

            if not response.is_success:
                print(
                    f"\n[FAIL] {path}"
                )
                print(response.text[:1500])
                sys.exit(1)

            return response.json()

        prediction = post(
            "/api/predict",
            {
                "disrupted_node": args.node_id,
            },
        )

        delay = post(
            "/api/delay/predict",
            {
                "disrupted_node": args.node_id,
                "initial_delay_days": 14,
                "decay": 0.75,
            },
        )

        forecast = post(
            "/api/forecast/predict",
            {
                "disrupted_node": args.node_id,
                "initial_delay_days": 14,
                "decay": 0.75,
                "recovery_half_life_days": 30,
            },
        )

        print(
            "[PASS] Prediction API"
        )
        print(
            "[PASS] Delay regression API"
        )
        print(
            "[PASS] Forecast API"
        )

        if not args.write:
            print(
                "\nRead-only verification complete. "
                "No history was changed."
            )
            print(
                "To persist the result, rerun "
                "with --write."
            )
            return

        snapshot = post(
            "/api/history/incidents/"
            f"{args.incident_id}/snapshots",
            {
                "prediction": prediction,
                "delay": delay,
                "forecast": forecast,
            },
        )

        snapshot_id = snapshot.get(
            "snapshot", {}
        ).get("snapshot_id")

        if not snapshot_id:
            raise AssertionError(
                "Save response missing snapshot ID"
            )

        print(
            "[PASS] Snapshot saved:",
            snapshot_id,
        )

        response = client.get(
            f"/api/history/snapshots/{snapshot_id}"
        )
        response.raise_for_status()

        stored = response.json()

        assert (
            stored.get("snapshot_id")
            == snapshot_id
        ), "Retrieved snapshot ID mismatch"

        assert (
            stored.get("incident_id")
            == args.incident_id
        ), "Stored incident ID mismatch"

        assert isinstance(
            stored.get("prediction"), dict
        ), "Prediction missing from storage"

        assert isinstance(
            stored.get("delay"), dict
        ), "Delay missing from storage"

        assert isinstance(
            stored.get("forecast"), dict
        ), "Forecast missing from storage"

        print(
            "[PASS] Snapshot retrieved"
        )
        print(
            "[PASS] Incident association verified"
        )
        print(
            "[PASS] Prediction, delay and forecast "
            "payloads persisted"
        )

        print(
            "\nImpact history persistence test "
            "completed successfully."
        )


if __name__ == "__main__":
    main()
