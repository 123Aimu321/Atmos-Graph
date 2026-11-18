
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.app.realtime.manager import manager


router = APIRouter(tags=["Real-Time Updates"])

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}


@router.websocket("/ws/incidents")
async def incident_websocket(websocket: WebSocket):
    origin = websocket.headers.get("origin")

    # Restrict browser connections to local
    # development origins.
    if origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)

    try:
        while True:
            message = await websocket.receive_json()

            # Heartbeat used by the React client.
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {},
                })

    except WebSocketDisconnect:
        pass

    except Exception:
        # Invalid client messages or a broken
        # connection should not crash the server.
        pass

    finally:
        manager.disconnect(websocket)
