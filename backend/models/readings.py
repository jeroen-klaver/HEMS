"""
SQLModel database models for HEMS.

Tables:
  readings          — lightweight time-series: one row per (timestamp, source, field)
  integrations      — configured integration instances
  charging_sessions — EV charging session records
  daily_summary     — aggregated daily totals
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Reading(SQLModel, table=True):
    """One data point from a polled integration.

    Each poll() call produces N rows — one per key in the returned dict.
    Kept intentionally wide (EAV style) to avoid schema migrations as
    integrations evolve.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(index=True)
    source_id: str = Field(index=True)   # e.g. "my_enphase"
    field: str                            # e.g. "power_w"
    value_float: float


class Integration(SQLModel, table=True):
    """A configured integration instance (from config.yaml or Settings UI)."""

    id: str = Field(primary_key=True)    # user-defined, e.g. "my_enphase"
    type_id: str                          # registered plugin ID, e.g. "enphase_iq_gateway"
    name: str                             # display name
    config_json: str                      # JSON-serialised config dict
    enabled: bool = True
    last_seen: Optional[datetime] = None  # timestamp of last successful poll
    last_error: Optional[str] = None      # last error message, if any


class ChargingSession(SQLModel, table=True):
    """Records a completed or ongoing EV charging session."""

    id: Optional[int] = Field(default=None, primary_key=True)
    start: datetime
    end: Optional[datetime] = None
    energy_kwh: float = 0.0
    mode: str = "solar"       # off | min | solar | fast
    cost_eur: float = 0.0


class DailySummary(SQLModel, table=True):
    """Aggregated daily energy totals, updated at end of day."""

    date: date = Field(primary_key=True)
    solar_kwh: float = 0.0
    grid_import_kwh: float = 0.0
    grid_export_kwh: float = 0.0
    net_cost_eur: float = 0.0
