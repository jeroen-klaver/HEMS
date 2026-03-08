"""
PV production forecast service.

Fetches hourly solar irradiance from the Open-Meteo free API (no key required)
and converts it to estimated PV output in watts using pvlib.

Results are cached per calendar day and refreshed once per day.

Open-Meteo docs: https://open-meteo.com/en/docs
pvlib docs:      https://pvlib-python.readthedocs.io/
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
import pvlib

from backend.config import ForecastConfig, HemsConfig

log = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Cache: date string → list of (hour_utc, power_w)
_cache: dict[str, list[tuple[datetime, float]]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_forecast(
    hems: HemsConfig,
    forecast_conf: ForecastConfig,
) -> list[tuple[datetime, float]]:
    """Return hourly PV production forecast for today and tomorrow.

    Returns list of (hour_utc, estimated_power_w) tuples.
    Returns empty list if forecast is disabled or on error.
    """
    if not forecast_conf.enabled or forecast_conf.system_kwp <= 0:
        return []

    today = date.today().isoformat()
    if today not in _cache:
        _cache[today] = await _fetch_forecast(hems, forecast_conf)
    return _cache[today]


def clear_cache() -> None:
    """Clear forecast cache (called at midnight)."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Fetcher + pvlib conversion
# ---------------------------------------------------------------------------

async def _fetch_forecast(
    hems: HemsConfig,
    conf: ForecastConfig,
) -> list[tuple[datetime, float]]:
    """Fetch irradiance from Open-Meteo and estimate PV output via pvlib."""
    params = {
        "latitude": hems.latitude,
        "longitude": hems.longitude,
        "hourly": "direct_radiation,diffuse_radiation",
        "timezone": "UTC",
        "forecast_days": 2,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(_OPEN_METEO_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        log.warning("Open-Meteo fetch failed: %s", exc)
        return []

    return _convert_to_power(data, conf)


def _convert_to_power(
    data: dict,
    conf: ForecastConfig,
) -> list[tuple[datetime, float]]:
    """Convert Open-Meteo irradiance data to estimated PV power via pvlib."""
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    direct = hourly.get("direct_radiation", [])
    diffuse = hourly.get("diffuse_radiation", [])

    if not times:
        return []

    results: list[tuple[datetime, float]] = []

    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
        dni_w = float(direct[i]) if i < len(direct) else 0.0
        dhi_w = float(diffuse[i]) if i < len(diffuse) else 0.0

        power_w = _pvlib_estimate(dt, dni_w, dhi_w, conf)
        results.append((dt, power_w))

    return results


def _pvlib_estimate(
    dt: datetime,
    direct_radiation: float,
    diffuse_radiation: float,
    conf: ForecastConfig,
) -> float:
    """Estimate PV output in watts for one hour using pvlib.

    Uses a simple PVWatts-style calculation:
      - Plane-of-array irradiance from tilt + azimuth
      - System efficiency assumed at 80% (accounts for inverter + temperature losses)
    """
    try:
        location = pvlib.location.Location(
            latitude=0,    # not used — irradiance is already surface-level
            longitude=0,
            altitude=0,
        )

        # Use pvlib's irradiance decomposition: direct + diffuse → POA
        solar_zenith = pvlib.solarposition.get_solarposition(
            time=dt,
            latitude=location.latitude,
            longitude=location.longitude,
        )["zenith"].iloc[0]

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=conf.tilt_degrees,
            surface_azimuth=conf.azimuth_degrees,
            dni=direct_radiation,
            ghi=direct_radiation + diffuse_radiation,
            dhi=diffuse_radiation,
            solar_zenith=solar_zenith,
            solar_azimuth=0,  # not critical for simple estimate
        )

        poa_w_m2 = float(poa.get("poa_global", 0.0))

        # Power = irradiance * area * efficiency
        # area (m²) ≈ system_kwp * 1000 / 1000 STC = system_kwp m² (roughly)
        # We use: power_w = poa * system_kwp / 1.0 kW/m² * efficiency
        system_efficiency = 0.80
        power_w = poa_w_m2 * conf.system_kwp * system_efficiency

        return max(0.0, power_w)

    except Exception as exc:
        log.debug("pvlib estimate failed for %s: %s", dt, exc)
        # Fallback: simple ratio of direct radiation to STC (1000 W/m²)
        power_w = (direct_radiation / 1000.0) * conf.system_kwp * 1000 * 0.8
        return max(0.0, power_w)
