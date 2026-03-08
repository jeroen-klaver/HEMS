"""
GET /api/v1/forecast — hourly PV production forecast for today + tomorrow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend import config as cfg
from backend.database import get_session
from backend.models.readings import SolarArray
from backend.models.schemas import ForecastPointSchema, ForecastResponseSchema
from backend.services.forecast import get_forecast

router = APIRouter()


@router.get("/forecast", response_model=ForecastResponseSchema)
async def get_pv_forecast(session: Session = Depends(get_session)) -> ForecastResponseSchema:
    """Return hourly PV production forecast (watts) for today and tomorrow."""
    conf = cfg.get()
    arrays = list(session.exec(select(SolarArray)).all())
    points_raw = await get_forecast(conf.hems, conf.forecast, arrays)

    # Total kWp: sum of enabled DB arrays, or fall back to config.yaml
    enabled = [a for a in arrays if a.enabled]
    if enabled:
        total_kwp = sum(a.panel_count * a.wp_per_panel / 1000.0 for a in enabled)
    else:
        total_kwp = conf.forecast.system_kwp

    points = [ForecastPointSchema(hour=hour, power_w=power_w) for hour, power_w in points_raw]
    return ForecastResponseSchema(
        system_kwp=total_kwp,
        points=points,
    )
