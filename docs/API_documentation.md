# AtmoGraph API reference

Interactive schema: `http://127.0.0.1:8000/docs` when backend is running.

| Method | Route | Use |
| --- | --- | --- |
| GET | /api/graph | Synthetic prediction graph |
| POST | /api/predict | GraphSAGE status classification for one node |
| GET | /api/model/metrics | Synthetic evaluation metrics |
| POST | /api/delay/predict | GraphSAGE node delay estimates |
| GET | /api/delay/metrics | Regression evaluation metrics |
| POST | /api/forecast/predict | 30/60/90-day recovery scenarios |
| POST | /api/analyze-event | Text-to-entity interpretation |
| POST | /api/incidents/ingest | Read news feeds and create/merge PENDING incidents |
| GET | /api/incidents | Filter/query incident records |
| POST | /api/incidents/{incident_id}/confirm | Confirm one synthetic entity; human review |
| POST | /api/incidents/{incident_id}/reject | Reject pending incident |
| GET | /api/explorer/entities | Search graph entities |
| GET | /api/explorer/neighborhood/{node_id} | Limited k-hop graph exploration |
| POST | /api/history/incidents/{incident_id}/snapshots | Validate/persist confirmed synthetic simulation |
| GET | /api/history/incidents/{incident_id}/snapshots | List persisted history |
| GET | /api/history/snapshots/{snapshot_id} | Retrieve complete simulation |
| GET | /api/impact-states/incidents/{incident_id} | Latest incident-scoped risk state per entity |
| WS | /ws/incidents | Real-time incident + validated prediction events |

## Examples

Classification:

    POST /api/predict
    {"disrupted_node":"PORT_001"}

Delay:

    POST /api/delay/predict
    {"disrupted_node":"PORT_001","initial_delay_days":14,"decay":0.75}

Forecast:

    POST /api/forecast/predict
    {"disrupted_node":"PORT_001","initial_delay_days":14,"decay":0.75,"recovery_half_life_days":30}

After confirmation, `POST /api/history/incidents/{incident_id}/snapshots` must include the complete model prediction and, optionally, delay, forecast, ripple, and risk objects; the service checks the actual confirmed source and all 25 entity IDs before writing.

## WebSocket envelopes

An incident status event or snapshot event is sent as an object with keys `event_id`, `type`, `timestamp`, `data`. The event `impact.prediction.updated` contains the persisted snapshot ID, source entity, and the confirmed simulation outputs; other clients apply them to their graph overlay. WebSocket access is limited to local development origins in this prototype; authentication/authorization is not implemented.

## Important constraints

* Most predictions use synthetic inputs and model checkpoints; they do not establish real-world forecast accuracy.
* Live news is advisory; do not treat article entity suggestions as verified links without review.
* The newer incident risk states are *simulated* overlays and are not financial or operational loss probabilities.
