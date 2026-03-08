"""
GET /api/v1/forecast — hourly PV production forecast for today + tomorrow.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend import config as cfg
from backend.models.schemas import ForecastPointSchema, ForecastResponseSchema
from backend.services.forecast import get_forecast

router = APIRouter()


@router.get("/forecast", response_model=ForecastResponseSchema)
async def get_pv_forecast() -> ForecastResponseSchema:
    """Return hourly PV production forecast (watts) for today and tomorrow."""
    conf = cfg.get()
    points_raw = await get_forecast(conf.hems, conf.forecast)
    points = [ForecastPointSchema(hour=hour, power_w=power_w) for hour, power_w in points_raw]
    return ForecastResponseSchema(
        system_kwp=conf.forecast.system_kwp,
        points=points,
    )
