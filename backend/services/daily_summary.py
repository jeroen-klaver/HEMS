"""
Daily summary aggregation service.

Runs at 00:01 each night (via APScheduler) to compute yesterday's totals
from the raw readings table and write a DailySummary row.

Aggregations:
  solar_kwh        — max(lifetime_kwh) - min(lifetime_kwh) for solar sources
                     (delta of lifetime counter = today's production)
  grid_import_kwh  — delta of import_kwh counter on P1 meter
  grid_export_kwh  — delta of export_kwh counter on P1 meter
  net_cost_eur     — estimated from grid_import_kwh * avg price - grid_export_kwh * avg price
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from backend.database import get_engine
from backend.models.readings import DailySummary, Reading

log = logging.getLogger(__name__)


async def write_daily_summary(target_date: date | None = None) -> None:
    """Aggregate yesterday's readings into a DailySummary row.

    Args:
        target_date: date to summarise (defaults to yesterday).
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    day_start = datetime(target_date.year, target_date.month, target_date.day,
                         0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    with Session(get_engine()) as session:
        # Fetch all readings for the target day
        readings = session.exec(
            select(Reading).where(
                Reading.timestamp >= day_start,
                Reading.timestamp < day_end,
            )
        ).all()

    if not readings:
        log.info("No readings for %s — skipping daily summary", target_date)
        return

    solar_kwh = _delta_counter(readings, field="lifetime_kwh", category_hint="solar")
    import_kwh = _delta_counter(readings, field="import_kwh")
    export_kwh = _delta_counter(readings, field="export_kwh")

    summary = DailySummary(
        date=target_date,
        solar_kwh=solar_kwh,
        grid_import_kwh=import_kwh,
        grid_export_kwh=export_kwh,
        net_cost_eur=0.0,   # cost calculation requires pricing data — TODO: enrich later
    )

    with Session(get_engine()) as session:
        existing = session.get(DailySummary, target_date)
        if existing:
            existing.solar_kwh = summary.solar_kwh
            existing.grid_import_kwh = summary.grid_import_kwh
            existing.grid_export_kwh = summary.grid_export_kwh
            session.add(existing)
        else:
            session.add(summary)
        session.commit()

    log.info(
        "Daily summary %s: solar=%.2f kWh, import=%.2f kWh, export=%.2f kWh",
        target_date, solar_kwh, import_kwh, export_kwh,
    )


def _delta_counter(readings: list[Reading], field: str, category_hint: str = "") -> float:
    """Calculate max - min for a lifetime counter field across all sources.

    For cumulative counters (import_kwh, lifetime_kwh), the day's delta
    is the difference between the highest and lowest value seen that day.
    """
    values = [r.value_float for r in readings if r.field == field]
    if not values:
        return 0.0
    return max(0.0, max(values) - min(values))
