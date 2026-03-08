"""
GET /api/v1/status — current readings for all devices + charging state + price.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from backend import config as cfg
from backend.models.schemas import (
    ChargingStateSchema,
    DeviceReadingSchema,
    StatusSchema,
)
from backend.services.pricing import get_current_price
from backend.state import state

router = APIRouter()


@router.get("/status", response_model=StatusSchema)
async def get_status() -> StatusSchema:
    """Return live readings for all devices, current charging state, and electricity price."""
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

    return StatusSchema(
        timestamp=datetime.utcnow(),
        devices=devices,
        charging=charging,
        current_price_eur_kwh=current_price,
    )
