
import argparse
import json
import sys

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    args = parser.parse_args()

    with httpx.Client(
        base_url=args.base_url,
        timeout=30,
        trust_env=False,
    ) as client:
        response = client.get(
            "/api/incidents",
            params={
                "status": "CONFIRMED",
                "limit": 200,
            },
        )
        response.raise_for_status()

        incidents = response.json().get(
            "incidents", []
        )

        print("\nATMOGRAPH — HISTORY AUDIT")
        print("=" * 55)
        print(
            "Confirmed incidents:",
            len(incidents),
        )

        total_snapshots = 0
        incidents_with_history = 0
        failed = 0

        for incident in incidents:
            incident_id = incident.get(
                "incident_id"
            )

            if not incident_id:
                failed += 1
                print("[FAIL] Missing incident ID")
                continue

            response = client.get(
                "/api/history/incidents/"
                f"{incident_id}/snapshots"
            )

            if not response.is_success:
                failed += 1
                print(
                    "[FAIL]",
                    incident_id,
                    response.status_code,
                )
                continue

            snapshots = response.json().get(
                "snapshots", []
            )

            count = len(snapshots)

            total_snapshots += count

            if count:
                incidents_with_history += 1

            print(
                f"[{'SAVED' if count else 'EMPTY'}] "
                f"{incident_id} — "
                f"{count} snapshot(s)"
            )

        print("\n" + "=" * 55)
        print(
            "Incidents with history:",
            incidents_with_history,
        )
        print(
            "Total snapshots:",
            total_snapshots,
        )
        print(
            "Request failures:",
            failed,
        )

        if failed:
            sys.exit(1)

        if not total_snapshots:
            print(
                "\nNo saved impact history found. "
                "Run a simulation for a "
                "confirmed synthetic test incident "
                "and save its results."
            )
        else:
            print(
                "\nHistory records are accessible."
            )


if __name__ == "__main__":
    main()
