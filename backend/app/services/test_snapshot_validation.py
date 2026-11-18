
from ml.gnn.delay_regression import load_network

from backend.app.services.snapshot_validation import (
    validate_snapshot,
    SnapshotValidationError,
)


def main():
    network = load_network()

    node_ids = network["ids"]
    source = "PORT_001"

    # Build a structurally valid synthetic
    # test payload using the actual graph IDs.
    prediction = {
        "disrupted_node": source,
        "results": [
            {
                "node_id": node_id,
                "predicted_status": (
                    "DISRUPTED"
                    if node_id == source
                    else "NORMAL"
                ),
            }
            for node_id in node_ids
        ],
        "summary": {
            "normal": len(node_ids) - 1,
            "affected": 0,
            "disrupted": 1,
        },
    }

    validate_snapshot(
        source_node_id=source,
        allowed_node_ids=set(node_ids),
        prediction=prediction,
    )

    print("PASS: Valid prediction accepted")

    # Try saving PORT_001 results against
    # a different confirmed source.
    try:
        validate_snapshot(
            source_node_id="PORT_002",
            allowed_node_ids=set(node_ids),
            prediction=prediction,
        )

        raise AssertionError(
            "Mismatched source was accepted"
        )

    except SnapshotValidationError:
        print(
            "PASS: Mismatched source rejected"
        )

    # Test a negative predicted delay.
    delay = {
        "disrupted_node": source,
        "initial_delay_days": 14,
        "results": [
            {
                "node_id": node_id,
                "predicted_delay_days": (
                    -5 if node_id == source else 0
                ),
                "is_disruption_source": (
                    node_id == source
                ),
            }
            for node_id in node_ids
        ],
    }

    try:
        validate_snapshot(
            source_node_id=source,
            allowed_node_ids=set(node_ids),
            prediction=prediction,
            delay=delay,
        )

        raise AssertionError(
            "Negative delay was accepted"
        )

    except SnapshotValidationError:
        print("PASS: Negative delay rejected")

    print(
        "\nSnapshot validation tests completed."
    )


if __name__ == "__main__":
    main()
