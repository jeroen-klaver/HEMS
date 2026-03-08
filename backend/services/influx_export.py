"""
Optional InfluxDB export service.

Writes device readings to InfluxDB v2 after each poll cycle.
Only active when exports.influxdb.enabled = true in config.yaml.

Each device's readings become one InfluxDB point:
  measurement: "hems_readings"
  tags:        source_id, type_id, category
  fields:      one per reading key (e.g. power_w, import_kwh)
  timestamp:   from last_seen
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend import config as cfg

if TYPE_CHECKING:
    from backend.state import DeviceState

log = logging.getLogger(__name__)

# Lazy-initialised InfluxDB client (only created if enabled)
_client = None
_write_api = None


def _get_write_api():
    """Return (and lazily initialise) the InfluxDB write API."""
    global _client, _write_api
    if _write_api is not None:
        return _write_api

    conf = cfg.get().exports.influxdb
    if not conf.enabled:
        return None

    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import ASYNCHRONOUS

        _client = InfluxDBClient(url=conf.url, token=conf.token, org=conf.org)
        _write_api = _client.write_api(write_options=ASYNCHRONOUS)
        log.info("InfluxDB write API initialised → %s / %s", conf.url, conf.bucket)
    except ImportError:
        log.warning("influxdb-client not installed — InfluxDB export disabled")
        _write_api = None

    return _write_api


async def write_devices(devices: list[DeviceState]) -> None:
    """Write a batch of DeviceState readings to InfluxDB.

    Silently skips if InfluxDB is not configured or unavailable.
    """
    write_api = _get_write_api()
    if write_api is None:
        return

    conf = cfg.get().exports.influxdb

    try:
        from influxdb_client import Point

        points = []
        for device in devices:
            if not device.readings or device.error:
                continue
            point = (
                Point("hems_readings")
                .tag("source_id", device.id)
                .tag("type_id", device.type_id)
                .tag("category", device.category)
            )
            for field, value in device.readings.items():
                point = point.field(field, value)
            if device.last_seen:
                point = point.time(device.last_seen)
            points.append(point)

        if points:
            write_api.write(bucket=conf.bucket, org=conf.org, record=points)

    except Exception:
        log.exception("InfluxDB write failed")
