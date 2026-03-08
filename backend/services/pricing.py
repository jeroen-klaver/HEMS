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
from zoneinfo import ZoneInfo
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

    # Align window to local Amsterdam midnight so bars display as 00:00–23:00 CET/CEST
    _ams = ZoneInfo("Europe/Amsterdam")
    local_midnight = datetime(day.year, day.month, day.day, 0, 0, tzinfo=_ams)
    period_start = local_midnight.astimezone(timezone.utc)
    period_end = period_start + timedelta(hours=24)

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
            # Filter to only hours within the requested UTC day window
            prices = [(h, p) for h, p in prices if period_start <= h < period_end]
            if not prices:
                log.warning("ENTSO-E returned 0 price points for %s after filtering", day)
                return _manual_prices(conf, day)
            log.info("Fetched %d ENTSO-E price points for %s", len(prices), day)
            return prices
    except Exception as exc:
        log.warning("ENTSO-E fetch failed for %s: %s — using manual price", day, exc)
        return _manual_prices(conf, day)


def _resolution_to_delta(resolution: Optional[str]) -> timedelta:
    """Parse ENTSO-E resolution string (PT60M, PT15M, PT30M …) to timedelta."""
    if resolution and resolution.startswith("PT") and resolution.endswith("M"):
        try:
            return timedelta(minutes=int(resolution[2:-1]))
        except ValueError:
            pass
    return timedelta(hours=1)  # default to hourly


def _local_tag(elem: ElementTree.Element) -> str:
    """Return the local (non-namespaced) tag name of an element."""
    tag = elem.tag
    return tag[tag.index("}") + 1:] if "}" in tag else tag


def _ns_tag(ns_uri: str, local: str) -> str:
    """Build a namespaced tag string for use with iter()."""
    return f"{{{ns_uri}}}{local}" if ns_uri else local


def _parse_xml(xml_text: str, conf: PricingConfig) -> list[tuple[datetime, float]]:
    """Parse ENTSO-E XML response into (hour_utc, all_in_price) tuples.

    Uses iter() with the namespace extracted from the root element, so it
    works regardless of whether the XML namespace changes.
    """
    root = ElementTree.fromstring(xml_text)

    # Extract namespace URI from root tag (e.g. '{urn:...}Publication_MarketDocument')
    ns_uri = root.tag[1:root.tag.index("}")] if "}" in root.tag else ""
    log.info("ENTSO-E XML: root=%s, ns=%s", _local_tag(root), ns_uri[:40] if ns_uri else "(none)")

    # Accumulate prices per hour (supports both PT60M and PT15M resolutions)
    hour_prices: dict[datetime, list[float]] = {}

    for ts in root.iter(_ns_tag(ns_uri, "TimeSeries")):
        # Parse resolution (PT60M = 60min, PT15M = 15min, etc.)
        resolution = None
        for res_elem in ts.iter(_ns_tag(ns_uri, "resolution")):
            resolution = (res_elem.text or "").strip()
            break
        delta = _resolution_to_delta(resolution)

        # Find period start time
        start_str = None
        for ti in ts.iter(_ns_tag(ns_uri, "timeInterval")):
            start_elem = ti.find(_ns_tag(ns_uri, "start"))
            if start_elem is not None and start_elem.text:
                start_str = start_elem.text.strip()
            break
        if not start_str:
            continue
        period_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

        # Parse price points and bucket by hour
        for point in ts.iter(_ns_tag(ns_uri, "Point")):
            point_data = {_local_tag(child): child.text for child in point}
            pos_text = point_data.get("position")
            price_text = point_data.get("price.amount")
            if pos_text is None or price_text is None:
                continue
            position = int(pos_text)
            raw_price_mwh = float(price_text)
            point_dt = period_start + delta * (position - 1)
            # Round down to full hour for aggregation
            hour_utc = point_dt.replace(minute=0, second=0, microsecond=0)
            all_in = _apply_markup(raw_price_mwh / 1000.0, conf)  # MWh → kWh
            hour_prices.setdefault(hour_utc, []).append(all_in)

    # Average all sub-hourly prices per hour slot
    results = [(h, sum(prices) / len(prices)) for h, prices in hour_prices.items()]
    log.info("ENTSO-E XML: parsed %d hourly price points", len(results))
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
