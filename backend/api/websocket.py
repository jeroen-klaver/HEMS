"""
WS /ws/live — WebSocket endpoint that pushes live status JSON every 5 seconds.

The server pushes; clients just listen. On connect the current state is sent
immediately, then every 5 seconds thereafter.

Multiple concurrent clients are supported via a simple connection registry.
A disconnected client is silently removed from the registry.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend import config as cfg
from backend.models.schemas import ChargingStateSchema, DeviceReadingSchema, StatusSchema
from backend.services.pricing import get_current_price
from backend.state import state

log = logging.getLogger(__name__)
router = APIRouter()

_connections: Set[WebSocket] = set()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    """Push current status JSON to the client every 5 seconds."""
    await websocket.accept()
    _connections.add(websocket)
    log.info("WebSocket client connected (%d total)", len(_connections))

    try:
        while True:
            payload = await _build_status_json()
            await websocket.send_text(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error")
    finally:
        _connections.discard(websocket)
        log.info("WebSocket client disconnected (%d remaining)", len(_connections))


async def _build_status_json() -> str:
    """Build the status payload as a JSON string."""
    conf = cfg.get()

    devices = [
        DeviceReadingSchema(
            id=d.id,
            name=d.name,
            type_id=d.type_id,
            category=d.category,
            readings=d.readings,
            last_seen=d.last_seen,
            error=d.error,
        )
        for d in state.devices.values()
    ]

    charging = ChargingStateSchema(
        mode=state.charging.mode,
        state=state.charging.state,
        current_setpoint_a=state.charging.current_setpoint_a,
        power_w=state.charging.power_w,
    )

    current_price = await get_current_price(conf.pricing)

    status = StatusSchema(
        timestamp=datetime.utcnow(),
        devices=devices,
        charging=charging,
        current_price_eur_kwh=current_price,
    )

    return status.model_dump_json()
