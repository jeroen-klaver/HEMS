"""
APScheduler-based polling and control loop for HEMS.

Two recurring jobs:
  poll_all  — every 5 seconds: poll every enabled integration, write results
              to in-memory state and SQLite, optionally to InfluxDB.
  daily_job — every day at midnight: write DailySummary row to SQLite.

The charging control loop runs inside poll_all (after all readings are fresh)
so it always acts on the most recent data.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlmodel import select

from backend import config as cfg
from backend.database import get_session_ctx
from backend.integrations.base import BaseIntegration
from backend.integrations.registry import get_class
from backend.models.readings import Integration as IntegrationRecord, Reading
from backend.state import ChargingState, DeviceState, state

log = logging.getLogger(__name__)

# Holds live integration instances (keyed by instance ID)
_instances: dict[str, BaseIntegration] = {}
_scheduler: Optional[AsyncIOScheduler] = None


# ---------------------------------------------------------------------------
# Integration instance management
# ---------------------------------------------------------------------------

def build_instances(conf: cfg.Config) -> dict[str, BaseIntegration]:
    """Instantiate all enabled integrations from the database."""
    instances: dict[str, BaseIntegration] = {}
    with get_session_ctx() as session:
        records = session.exec(select(IntegrationRecord)).all()
        for record in records:
            if not record.enabled:
                continue
            try:
                cls = get_class(record.type_id)
                config = json.loads(record.config_json)
                instances[record.id] = cls(config)
            except Exception:
                log.exception("Failed to instantiate integration %s (%s)", record.id, record.type_id)
    return instances


# ---------------------------------------------------------------------------
# Poll job
# ---------------------------------------------------------------------------

async def _poll_one(instance_id: str, instance: BaseIntegration) -> Optional[DeviceState]:
    """Poll a single integration and return its DeviceState.

    Returns None on error (error is logged, not re-raised — one bad integration
    must not block the others).
    """
    try:
        readings = await instance.poll()
        # Coerce all values to float (booleans → 0.0 / 1.0)
        float_readings = {k: float(v) for k, v in readings.items()}
        return DeviceState(
            id=instance_id,
            name=instance_id,       # overridden below from config
            type_id=instance.manifest.id,
            category=instance.manifest.category.value,
            readings=float_readings,
            last_seen=datetime.utcnow(),
            error=None,
        )
    except Exception as exc:
        log.warning("Poll failed for %s: %s", instance_id, exc)
        existing = state.devices.get(instance_id)
        return DeviceState(
            id=instance_id,
            name=existing.name if existing else instance_id,
            type_id=instance.manifest.id,
            category=instance.manifest.category.value,
            readings={},
            last_seen=existing.last_seen if existing else None,
            error=str(exc),
        )


async def _persist_readings(device: DeviceState) -> None:
    """Write fresh readings to SQLite."""
    if not device.readings:
        return
    now = device.last_seen or datetime.utcnow()
    rows = [
        Reading(
            timestamp=now,
            source_id=device.id,
            field=field,
            value_float=value,
        )
        for field, value in device.readings.items()
    ]
    with get_session_ctx() as session:
        session.add_all(rows)
        session.commit()


async def _update_integration_record(device: DeviceState) -> None:
    """Update last_seen / last_error on the Integration DB record."""
    with get_session_ctx() as session:
        record = session.get(IntegrationRecord, device.id)
        if record:
            record.last_seen = device.last_seen
            record.last_error = device.error
            session.add(record)
            session.commit()


async def poll_all() -> None:
    """Poll all active integrations, update state, persist to DB."""
    conf = cfg.get()

    # Build a name lookup from the database
    with get_session_ctx() as session:
        name_by_id = {r.id: r.name for r in session.exec(select(IntegrationRecord)).all()}

    # Poll all instances concurrently
    tasks = [
        _poll_one(iid, inst)
        for iid, inst in _instances.items()
    ]
    results = await asyncio.gather(*tasks)

    # Update state and persist
    persist_tasks = []
    for device in results:
        if device is None:
            continue
        # Apply display name from config
        device.name = name_by_id.get(device.id, device.id)
        await state.update_device(device)
        persist_tasks.append(_persist_readings(device))
        persist_tasks.append(_update_integration_record(device))

    await asyncio.gather(*persist_tasks)

    # Run charging control loop after state is fully updated
    await _run_charging_control(conf)

    # Optional InfluxDB export
    if conf.exports.influxdb.enabled:
        await _export_to_influx(results)


# ---------------------------------------------------------------------------
# Charging control
# ---------------------------------------------------------------------------

async def _run_charging_control(conf: cfg.Config) -> None:
    """Import and run the charging logic service after each poll cycle."""
    try:
        # Lazy import to avoid circular dependency at module load time
        from backend.services.charging_logic import run_charging_step
        await run_charging_step(conf, _instances, state)
    except Exception:
        log.exception("Charging control step failed")


# ---------------------------------------------------------------------------
# InfluxDB export
# ---------------------------------------------------------------------------

async def _export_to_influx(devices: list[Optional[DeviceState]]) -> None:
    """Write fresh readings to InfluxDB if enabled."""
    try:
        from backend.services.influx_export import write_devices
        await write_devices([d for d in devices if d and d.readings])
    except Exception:
        log.exception("InfluxDB export failed")


# ---------------------------------------------------------------------------
# Daily summary job
# ---------------------------------------------------------------------------

async def daily_summary() -> None:
    """Aggregate today's readings into a DailySummary row."""
    try:
        from backend.services.daily_summary import write_daily_summary
        await write_daily_summary()
    except Exception:
        log.exception("Daily summary job failed")


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def start(conf: cfg.Config) -> None:
    """Build integration instances and start the APScheduler."""
    global _instances, _scheduler

    _instances = build_instances(conf)
    log.info("Loaded %d integration(s): %s", len(_instances), list(_instances.keys()))

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(poll_all, "interval", seconds=5, id="poll_all", max_instances=1)
    _scheduler.add_job(daily_summary, "cron", hour=0, minute=1, id="daily_summary")
    _scheduler.start()
    log.info("Scheduler started")


def stop() -> None:
    """Shut down the scheduler cleanly."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")


def reload_instances(conf: cfg.Config) -> None:
    """Re-instantiate all integrations (called after config change via Settings UI)."""
    global _instances
    _instances = build_instances(conf)
    log.info("Integration instances reloaded: %s", list(_instances.keys()))
