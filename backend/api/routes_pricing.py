"""
GET /api/v1/pricing/today    — today's hourly all-in prices
GET /api/v1/pricing/tomorrow — tomorrow's prices (available after ~13:00 CET)
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter

from backend import config as cfg
from backend.models.schemas import PricePointSchema, PricingResponseSchema
from backend.services.pricing import get_prices_today, get_prices_tomorrow

router = APIRouter()


@router.get("/pricing/today", response_model=PricingResponseSchema)
async def pricing_today() -> PricingResponseSchema:
    """Return all-in hourly electricity prices for today."""
    conf = cfg.get()
    prices = await get_prices_today(conf.pricing)
    return _build_response(str(date.today()), prices)


@router.get("/pricing/tomorrow", response_model=PricingResponseSchema)
async def pricing_tomorrow() -> PricingResponseSchema:
    """Return all-in hourly electricity prices for tomorrow (if available)."""
    conf = cfg.get()
    prices = await get_prices_tomorrow(conf.pricing)
    return _build_response(str(date.today() + timedelta(days=1)), prices)


def _build_response(date_str: str, prices: list) -> PricingResponseSchema:
    points = [PricePointSchema(hour=hour, price_eur_kwh=price) for hour, price in prices]
    avg = round(sum(p.price_eur_kwh for p in points) / len(points), 5) if points else None
    return PricingResponseSchema(date=date_str, prices=points, average_eur_kwh=avg)
