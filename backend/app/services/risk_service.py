
from collections import Counter

# Explainable, heuristic risk score.
# This is not a calibrated probability of disruption.

SEVERITY_WEIGHTS = {
    "LOW": 0.25,
    "MEDIUM": 0.50,
    "HIGH": 0.75,
    "CRITICAL": 1.00,
}

DISRUPTION_SEVERITY = {
    "FLOOD": "HIGH",
    "STRIKE": "MEDIUM",
    "PORT_CLOSURE": "CRITICAL",
    "TRANSPORT_DELAY": "MEDIUM",
    "FIRE": "HIGH",
    "EARTHQUAKE": "CRITICAL",
    "OTHER": "MEDIUM",
}


def classify_risk(score):
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def calculate_risk(prediction, ripple, disruption_type="OTHER"):
    results = prediction.get("results", [])
    summary = prediction.get("summary", {})

    total_nodes = len(results)

    if total_nodes == 0:
        raise ValueError("Prediction contains no entities")

    status_counts = Counter(
        item.get("predicted_status", "NORMAL")
        for item in results
    )

    affected = status_counts["AFFECTED"]
    disrupted = status_counts["DISRUPTED"]

    # Fraction of network predicted affected or disrupted.
    exposure_ratio = (affected + disrupted) / total_nodes

    # Directed graph reachability from disrupted source.
    reachable = ripple.get("reachable_downstream", 0)
    reach_ratio = reachable / max(total_nodes - 1, 1)

    severity = DISRUPTION_SEVERITY.get(
        disruption_type.upper(),
        "MEDIUM"
    )

    severity_weight = SEVERITY_WEIGHTS[severity]

    # Weighted heuristic score: 0-100.
    score = 100 * (
        0.45 * exposure_ratio
        + 0.35 * reach_ratio
        + 0.20 * severity_weight
    )

    score = round(min(max(score, 0), 100), 1)

    return {
        "risk_score": score,
        "risk_level": classify_risk(score),
        "disruption_type": disruption_type.upper(),
        "event_severity": severity,
        "total_entities": total_nodes,
        "predicted_affected": affected,
        "predicted_disrupted": disrupted,
        "reachable_downstream": reachable,
        "max_hops": ripple.get("max_hops", 0),
        "score_components": {
            "prediction_exposure": round(
                exposure_ratio * 100, 1
            ),
            "graph_reachability": round(
                reach_ratio * 100, 1
            ),
            "event_severity_weight": round(
                severity_weight * 100, 1
            ),
        },
        "method": "Weighted heuristic risk assessment",
        "disclaimer": (
            "This is an experimental risk index derived "
            "from synthetic graph predictions and "
            "rule-based severity weights. It is not "
            "a validated probability of real-world loss."
        ),
    }
