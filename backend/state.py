"""
Global in-memory state for HEMS.

Holds the most recent poll results for every active integration, plus the
current charging state. Updated by the scheduler every 5 seconds.

The WebSocket handler and /api/v1/status read from this module directly —
no database query needed for the live view.

Thread-safety: all mutations go through a single asyncio.Lock so the
scheduler (one writer) and API routes (many readers) never race.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DeviceState:
    """Latest known state for one integration instance."""

    id: str                          # integration instance ID, e.g. "my_enphase"
    name: str
    type_id: str
    category: str
    readings: dict[str, float] = field(default_factory=dict)
    last_seen: Optional[datetime] = None
    error: Optional[str] = None      # set when last poll raised an exception


@dataclass
class ChargingState:
    """Current EV charging state managed by the charging logic service."""

    mode: str = "solar"              # off | min | solar | fast
    state: str = "idle"              # idle | solar_charging | min_charging | fast_charging | paused
    current_setpoint_a: float = 0.0
    power_w: float = 0.0


class HEMSState:
    """Singleton container for all live runtime state."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.devices: dict[str, DeviceState] = {}
        self.charging: ChargingState = ChargingState()
        self.current_price_eur_kwh: Optional[float] = None
        self.last_updated: Optional[datetime] = None

    async def update_device(self, device: DeviceState) -> None:
        """Replace the stored state for one integration instance."""
        async with self._lock:
            self.devices[device.id] = device
            self.last_updated = datetime.utcnow()

    async def set_charging(self, charging: ChargingState) -> None:
        """Update the charging state."""
        async with self._lock:
            self.charging = charging

    async def set_price(self, price_eur_kwh: Optional[float]) -> None:
        """Update the current electricity price."""
        async with self._lock:
            self.current_price_eur_kwh = price_eur_kwh

    def snapshot(self) -> dict:
        """Return a plain-dict snapshot of the current state (no lock needed for reads)."""
        return {
            "devices": list(self.devices.values()),
            "charging": self.charging,
            "current_price_eur_kwh": self.current_price_eur_kwh,
            "last_updated": self.last_updated,
        }

    # Convenience accessors used by charging logic
    def get_solar_power_w(self) -> float:
        """Sum of power_w across all SOLAR category devices."""
        return sum(
            d.readings.get("power_w", 0.0)
            for d in self.devices.values()
            if d.category == "solar" and d.error is None
        )

    def get_grid_power_w(self) -> float:
        """Net grid power in watts (positive = import, negative = export).

        Returns power_w from the first healthy GRID device found.
        """
        for d in self.devices.values():
            if d.category == "grid" and d.error is None:
                return d.readings.get("power_w", 0.0)
        return 0.0

    def get_charger_power_w(self) -> float:
        """Current EV charger power draw in watts."""
        for d in self.devices.values():
            if d.category == "charger" and d.error is None:
                return d.readings.get("power_w", 0.0)
        return 0.0


# Module-level singleton — import and use directly
state = HEMSState()
