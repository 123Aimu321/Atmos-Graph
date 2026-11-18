
import math

VALID_STATUSES = {
    "NORMAL",
    "AFFECTED",
    "DISRUPTED",
}

EXPECTED_HORIZONS = {30, 60, 90}


class SnapshotValidationError(ValueError):
    pass


def require_object(value, name):
    if not isinstance(value, dict):
        raise SnapshotValidationError(
            f"{name} must be a JSON object"
        )
    return value


def require_list(value, name):
    if not isinstance(value, list):
        raise SnapshotValidationError(
            f"{name} must be a JSON array"
        )
    return value


def require_number(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(
        value, (int, float)
    ):
        raise SnapshotValidationError(
            f"{name} must be numeric"
        )

    if (
        not math.isfinite(value)
        or value < minimum
    ):
        raise SnapshotValidationError(
            f"{name} must be finite and >= {minimum}"
        )

    return float(value)


def validate_prediction(
    prediction,
    source_node_id,
    allowed_node_ids,
):
    prediction = require_object(
        prediction, "prediction"
    )

    results = require_list(
        prediction.get("results"),
        "prediction.results",
    )

    if not results:
        raise SnapshotValidationError(
            "prediction.results cannot be empty"
        )

    statuses = {}
    disrupted = []

    for item in results:
        require_object(
            item,
            "prediction result",
        )

        node_id = item.get("node_id")
        status = item.get(
            "predicted_status"
        )

        if node_id not in allowed_node_ids:
            raise SnapshotValidationError(
                f"Unknown prediction node: {node_id}"
            )

        if node_id in statuses:
            raise SnapshotValidationError(
                f"Duplicate prediction node: {node_id}"
            )

        if status not in VALID_STATUSES:
            raise SnapshotValidationError(
                f"Invalid prediction status: {status}"
            )

        statuses[node_id] = status

        if status == "DISRUPTED":
            disrupted.append(node_id)

    if set(statuses) != allowed_node_ids:
        raise SnapshotValidationError(
            "Prediction must contain every "
            "synthetic graph entity exactly once"
        )

    if disrupted != [source_node_id]:
        raise SnapshotValidationError(
            "The confirmed incident entity must "
            "be the only DISRUPTED node"
        )

    supplied_source = prediction.get(
        "disrupted_node"
    )

    if (
        supplied_source is not None
        and supplied_source != source_node_id
    ):
        raise SnapshotValidationError(
            "Prediction source does not match "
            "the confirmed incident"
        )

    summary = prediction.get("summary")

    if summary is not None:
        require_object(
            summary,
            "prediction.summary",
        )

        for status, key in (
            ("NORMAL", "normal"),
            ("AFFECTED", "affected"),
            ("DISRUPTED", "disrupted"),
        ):
            expected = sum(
                value == status
                for value in statuses.values()
            )

            if summary.get(key) != expected:
                raise SnapshotValidationError(
                    f"Prediction summary {key} "
                    f"must equal {expected}"
                )

    return statuses


def validate_delay(
    delay,
    source_node_id,
    allowed_node_ids,
):
    if delay is None:
        return

    delay = require_object(delay, "delay")

    if delay.get("disrupted_node") != source_node_id:
        raise SnapshotValidationError(
            "Delay source does not match "
            "the confirmed incident"
        )

    initial_days = require_number(
        delay.get("initial_delay_days"),
        "delay.initial_delay_days",
        minimum=1,
    )

    if initial_days > 90:
        raise SnapshotValidationError(
            "Initial delay exceeds 90 days"
        )

    results = require_list(
        delay.get("results"),
        "delay.results",
    )

    seen = set()
    source_count = 0

    for item in results:
        require_object(item, "delay result")

        node_id = item.get("node_id")

        if node_id not in allowed_node_ids:
            raise SnapshotValidationError(
                f"Unknown delay node: {node_id}"
            )

        if node_id in seen:
            raise SnapshotValidationError(
                f"Duplicate delay node: {node_id}"
            )

        seen.add(node_id)

        require_number(
            item.get("predicted_delay_days"),
            f"Delay for {node_id}",
        )

        if not isinstance(
            item.get("is_disruption_source"),
            bool,
        ):
            raise SnapshotValidationError(
                "is_disruption_source must be boolean"
            )

        if item["is_disruption_source"]:
            source_count += 1

            if node_id != source_node_id:
                raise SnapshotValidationError(
                    "Wrong delay disruption source"
                )

    if seen != allowed_node_ids:
        raise SnapshotValidationError(
            "Delay results must contain "
            "every synthetic entity"
        )

    if source_count != 1:
        raise SnapshotValidationError(
            "Exactly one delay source is required"
        )


def validate_forecast(
    forecast,
    source_node_id,
    allowed_node_ids,
    delay,
):
    if forecast is None:
        return

    forecast = require_object(
        forecast, "forecast"
    )

    if forecast.get("disrupted_node") != source_node_id:
        raise SnapshotValidationError(
            "Forecast source does not match "
            "the confirmed incident"
        )

    half_life = require_number(
        forecast.get("recovery_half_life_days"),
        "forecast.recovery_half_life_days",
        minimum=1,
    )

    if half_life > 180:
        raise SnapshotValidationError(
            "Recovery half-life exceeds 180 days"
        )

    if delay is not None:
        if not math.isclose(
            require_number(
    forecast.get("initial_delay_days"),
    "forecast.initial_delay_days",
    minimum=1,
),
            float(delay["initial_delay_days"]),
            abs_tol=0.001,
        ):
            raise SnapshotValidationError(
                "Forecast and delay initial "
                "durations do not match"
            )

    horizons = require_list(
        forecast.get("horizons"),
        "forecast.horizons",
    )

    observed_horizons = set()

    for snapshot in horizons:
        require_object(
            snapshot,
            "forecast horizon",
        )

        horizon = snapshot.get("horizon_days")

        if (
            isinstance(horizon, bool)
            or not isinstance(horizon, int)
            or horizon not in EXPECTED_HORIZONS
            or horizon in observed_horizons
        ):
            raise SnapshotValidationError(
                "Invalid or duplicate forecast horizon"
            )

        observed_horizons.add(horizon)

        entities = require_list(
            snapshot.get("entities"),
            "forecast horizon entities",
        )

        seen = set()

        for item in entities:
            require_object(
                item, "forecast entity"
            )

            node_id = item.get("node_id")

            if (
                node_id not in allowed_node_ids
                or node_id in seen
            ):
                raise SnapshotValidationError(
                    "Unknown or duplicate "
                    "forecast entity"
                )

            seen.add(node_id)

            require_number(
                item.get("residual_delay_days"),
                f"Residual delay for {node_id}",
            )

            require_number(
                item.get("baseline_delay_days"),
                f"Baseline delay for {node_id}",
            )

        if seen != allowed_node_ids:
            raise SnapshotValidationError(
                "Every forecast horizon must "
                "contain all synthetic entities"
            )

    if observed_horizons != EXPECTED_HORIZONS:
        raise SnapshotValidationError(
            "Forecast must contain 30, 60, "
            "and 90-day horizons"
        )


def validate_snapshot(
    source_node_id,
    allowed_node_ids,
    prediction,
    delay=None,
    forecast=None,
):
    if source_node_id not in allowed_node_ids:
        raise SnapshotValidationError(
            "Confirmed entity is not in "
            "the synthetic supply-chain network"
        )

    validate_prediction(
        prediction,
        source_node_id,
        allowed_node_ids,
    )

    validate_delay(
        delay,
        source_node_id,
        allowed_node_ids,
    )

    validate_forecast(
        forecast,
        source_node_id,
        allowed_node_ids,
        delay,
    )

    return True
