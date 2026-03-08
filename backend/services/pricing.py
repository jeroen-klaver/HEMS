"""
ENTSO-E day-ahead electricity pricing service.

Fetches hourly prices for the Netherlands (or any configured bidding zone)
from the ENTSO-E Transparency Platform and applies the configured markup,
energy tax, and VAT to compute all-in consumer prices.

Prices are cached per calendar day (fetched once, reused until midnight).
Falls back to the configured manual_price_eur_kwh if ENTSO-E is unavailable
or not configured.

ENTSO-E API docs: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from xml.etree import ElementTree

import httpx

from backend.config import PricingConfig

log = logging.getLogger(__name__)

_ENTSO_E_URL = "https://web-api.tp.entsoe.eu/api"
_NS = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"}

# In-memory cache: date string → list of (hour_utc, price_eur_kwh)
_cache: dict[str, list[tuple[datetime, float]]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_prices_today(conf: PricingConfig) -> list[tuple[datetime, float]]:
    """Return all-in hourly prices for today (local date, CET/CEST).

    Returns list of (hour_utc, all_in_price_eur_kwh) tuples.
    Falls back to manual price if ENTSO-E is unavailable.
    """
    today = date.today().isoformat()
    if today not in _cache:
        _cache[today] = await _fetch_day(conf, date.today())
    return _cache[today]


async def get_prices_tomorrow(conf: PricingConfig) -> list[tuple[datetime, float]]:
    """Return all-in hourly prices for tomorrow.

    Available from ~13:00 CET. Returns empty list if not yet published.
    """
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    if tomorrow not in _cache:
        _cache[tomorrow] = await _fetch_day(conf, date.today() + timedelta(days=1))
    return _cache[tomorrow]


async def get_current_price(conf: PricingConfig) -> Optional[float]:
    """Return the current all-in electricity price in EUR/kWh."""
    prices = await get_prices_today(conf)
    if not prices:
        return conf.manual_price_eur_kwh
    now_utc = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    for hour_utc, price in prices:
        if hour_utc == now_utc:
            return price
    # Fall back to last known price if current hour not found
    return prices[-1][1] if prices else conf.manual_price_eur_kwh


def clear_cache() -> None:
    """Clear the in-memory price cache (e.g. after midnight)."""
    _cache.clear()


# ---------------------------------------------------------------------------
# ENTSO-E fetcher
# ---------------------------------------------------------------------------

async def _fetch_day(conf: PricingConfig, day: date) -> list[tuple[datetime, float]]:
    """Fetch and parse ENTSO-E day-ahead prices for `day`.

    Returns all-in prices with markup + tax + VAT applied.
    Falls back to manual price list on any error.
    """
    if conf.source != "entso-e" or not conf.entso_e_token:
        return _manual_prices(conf, day)

    period_start = datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
    period_end = period_start + timedelta(days=1)

    params = {
        "securityToken": conf.entso_e_token,
        "documentType": "A44",          # day-ahead prices
        "in_Domain": conf.bidding_zone,
        "out_Domain": conf.bidding_zone,
        "periodStart": period_start.strftime("%Y%m%d%H%M"),
        "periodEnd": period_end.strftime("%Y%m%d%H%M"),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(_ENTSO_E_URL, params=params)
            response.raise_for_status()
            prices = _parse_xml(response.text, conf)
            log.info("Fetched %d ENTSO-E price points for %s", len(prices), day)
            return prices
    except Exception as exc:
        log.warning("ENTSO-E fetch failed for %s: %s — using manual price", day, exc)
        return _manual_prices(conf, day)


def _parse_xml(xml_text: str, conf: PricingConfig) -> list[tuple[datetime, float]]:
    """Parse ENTSO-E XML response into (hour_utc, all_in_price) tuples."""
    root = ElementTree.fromstring(xml_text)
    results: list[tuple[datetime, float]] = []

    for ts in root.findall(".//ns:TimeSeries", _NS):
        # Resolution should be PT60M (hourly); skip others
        resolution = ts.findtext(".//ns:resolution", namespaces=_NS)
        if resolution != "PT60M":
            continue

        start_str = ts.findtext(".//ns:timeInterval/ns:start", namespaces=_NS)
        if not start_str:
            continue
        period_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

        for point in ts.findall(".//ns:Point", _NS):
            pos_text = point.findtext("ns:position", namespaces=_NS)
            price_text = point.findtext("ns:price.amount", namespaces=_NS)
            if pos_text is None or price_text is None:
                continue
            position = int(pos_text)
            raw_price_mwh = float(price_text)

            hour_utc = period_start + timedelta(hours=position - 1)
            all_in = _apply_markup(raw_price_mwh / 1000.0, conf)  # MWh → kWh
            results.append((hour_utc, all_in))

    return sorted(results, key=lambda x: x[0])


def _apply_markup(base_eur_kwh: float, conf: PricingConfig) -> float:
    """Apply supplier markup, energy tax, and VAT to a base price."""
    price = base_eur_kwh + conf.supplier_markup_eur_kwh + conf.energy_tax_eur_kwh
    price *= 1 + conf.vat_percent / 100
    return round(price, 5)


def _manual_prices(conf: PricingConfig, day: date) -> list[tuple[datetime, float]]:
    """Return 24 identical hourly prices using the configured manual price."""
    base = datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
    price = _apply_markup(conf.manual_price_eur_kwh, conf)
    return [(base + timedelta(hours=h), price) for h in range(24)]
