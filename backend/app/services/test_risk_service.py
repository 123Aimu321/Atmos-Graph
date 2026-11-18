
from backend.app.services.risk_service import calculate_risk

prediction = {
    "results": (
        [{"predicted_status": "NORMAL"}] * 14
        + [{"predicted_status": "AFFECTED"}] * 10
        + [{"predicted_status": "DISRUPTED"}]
    ),
    "summary": {
        "normal": 14,
        "affected": 10,
        "disrupted": 1,
    },
}

ripple = {
    "reachable_downstream": 10,
    "max_hops": 2,
}

result = calculate_risk(
    prediction=prediction,
    ripple=ripple,
    disruption_type="FLOOD",
)

for key, value in result.items():
    print(f"{key}: {value}")
