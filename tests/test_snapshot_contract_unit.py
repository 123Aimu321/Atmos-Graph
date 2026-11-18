"""Dependency-free contract tests for validated synthetic impact snapshots.

Runs in GitHub Actions without Neo4j or model checkpoints.
"""
import copy
import unittest

from backend.app.services.snapshot_validation import (
    SnapshotValidationError,
    validate_snapshot,
)


SOURCE = "PORT_001"
IDS = {SOURCE, "WH_001", "RET_001"}


def valid_payload():
    prediction = {
        "disrupted_node": SOURCE,
        "results": [
            {"node_id": SOURCE, "predicted_status": "DISRUPTED"},
            {"node_id": "WH_001", "predicted_status": "AFFECTED"},
            {"node_id": "RET_001", "predicted_status": "NORMAL"},
        ],
        "summary": {"normal": 1, "affected": 1, "disrupted": 1},
    }
    delay = {
        "disrupted_node": SOURCE,
        "initial_delay_days": 14,
        "results": [
            {
                "node_id": node_id,
                "predicted_delay_days": amount,
                "is_disruption_source": node_id == SOURCE,
            }
            for node_id, amount in [
                (SOURCE, 14.0),
                ("WH_001", 8.0),
                ("RET_001", 0.0),
            ]
        ],
    }
    forecast = {
        "disrupted_node": SOURCE,
        "initial_delay_days": 14,
        "recovery_half_life_days": 30,
        "horizons": [
            {
                "horizon_days": horizon,
                "entities": [
                    {
                        "node_id": node_id,
                        "baseline_delay_days": amount,
                        "residual_delay_days": amount * factor,
                    }
                    for node_id, amount in [
                        (SOURCE, 14.0),
                        ("WH_001", 8.0),
                        ("RET_001", 0.0),
                    ]
                ],
            }
            for horizon, factor in [
                (30, 0.5),
                (60, 0.25),
                (90, 0.125),
            ]
        ],
    }
    return {
        "prediction": prediction,
        "delay": delay,
        "forecast": forecast,
    }


class SnapshotContractTests(unittest.TestCase):
    def validate(self, payload):
        return validate_snapshot(
            source_node_id=SOURCE,
            allowed_node_ids=IDS,
            **payload,
        )

    def test_valid_prediction_delay_forecast(self):
        self.assertTrue(self.validate(valid_payload()))

    def test_wrong_disrupted_source_rejected(self):
        data = valid_payload()
        data["prediction"]["disrupted_node"] = "WH_001"
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_unknown_graph_entity_rejected(self):
        data = valid_payload()
        data["prediction"]["results"][1]["node_id"] = "BENCH_999999"
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_duplicate_node_rejected(self):
        data = valid_payload()
        data["delay"]["results"][1]["node_id"] = SOURCE
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_multiple_disrupted_nodes_rejected(self):
        data = valid_payload()
        data["prediction"]["results"][1]["predicted_status"] = "DISRUPTED"
        data["prediction"]["summary"] = {
            "normal": 1,
            "affected": 0,
            "disrupted": 2,
        }
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_negative_delay_rejected(self):
        data = valid_payload()
        data["delay"]["results"][1]["predicted_delay_days"] = -2
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_nonfinite_delay_rejected(self):
        data = valid_payload()
        data["delay"]["results"][1]["predicted_delay_days"] = float("nan")
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_missing_forecast_horizon_rejected(self):
        data = valid_payload()
        data["forecast"]["horizons"].pop()
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_forecast_delay_mismatch_rejected(self):
        data = valid_payload()
        data["forecast"]["initial_delay_days"] = 20
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_invalid_boolean_delay_rejected(self):
        data = valid_payload()
        data["delay"]["results"][1]["predicted_delay_days"] = True
        with self.assertRaises(SnapshotValidationError):
            self.validate(data)

    def test_inputs_not_mutated(self):
        data = valid_payload()
        original = copy.deepcopy(data)
        self.validate(data)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()
