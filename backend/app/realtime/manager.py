
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

        await websocket.send_json({
            "event_id": str(uuid4()),
            "type": "connection.established",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "data": {
                "message": "Connected to AtmoGraph",
                "clients": len(self.active_connections),
            },
        })

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(
        self,
        event_type: str,
        data: dict | None = None,
    ):
        event = {
            "event_id": str(uuid4()),
            "type": event_type,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "data": data or {},
        }

        disconnected = []

        for websocket in tuple(self.active_connections):
            try:
                await websocket.send_json(event)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

        return event


manager = ConnectionManager()
