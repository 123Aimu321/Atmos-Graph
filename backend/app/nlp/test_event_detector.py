
from backend.app.nlp.event_detector import analyze_event

entities = [
    {
        "node_id": "PORT_001",
        "node_name": "Mumbai Port",
        "node_type": "PORT",
    },
    {
        "node_id": "PORT_002",
        "node_name": "Shanghai Port",
        "node_type": "PORT",
    },
    {
        "node_id": "WAREHOUSE_001",
        "node_name": "Bengaluru Warehouse",
        "node_type": "WAREHOUSE",
    },
]

event = (
    "Heavy rainfall and flooding have disrupted "
    "operations at Mumbai Port."
)

result = analyze_event(event, entities)

print("Event:", result["event_text"])
print("Disruption:", result["disruption_type"])
print("Matched entity:", result["matched_entity"])
print("Confidence:", result["match_confidence"])
print("Requires confirmation:", result["requires_confirmation"])
