"""
Abstract base classes and manifest types for HEMS integrations.

Every integration must subclass BaseIntegration (or ControllableIntegration for
devices that can be commanded) and define a class-level `manifest` attribute.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntegrationCategory(str, Enum):
    """Broad category for each integration type, used for grouping in the UI."""

    SOLAR = "solar"
    GRID = "grid"
    CHARGER = "charger"
    HEAT_PUMP = "heat_pump"
    SMART_PLUG = "smart_plug"
    BATTERY = "battery"    # reserved for future use
    VEHICLE = "vehicle"    # reserved for future use


@dataclass
class ConfigField:
    """Describes a single configuration field for an integration.

    The frontend renders a form input for each ConfigField automatically,
    driven by the `type` attribute.
    """

    name: str
    label: str
    type: str                        # "text" | "password" | "number" | "select" | "boolean"
    required: bool = True
    default: Any = None
    options: list[str] | None = None  # only used when type == "select"
    help_text: str = ""


@dataclass
class IntegrationManifest:
    """Static metadata for an integration plugin.

    Defined once per integration class, at class level. The registry reads
    these manifests to populate /api/v1/integration-types.
    """

    id: str                        # e.g. "enphase_iq_gateway"
    name: str                      # e.g. "Enphase IQ Gateway"
    category: IntegrationCategory
    description: str
    author: str
    config_fields: list[ConfigField] = field(default_factory=list)
    supports_control: bool = False  # True for chargers / smart plugs
    icon: str = ""                  # emoji or icon name


class BaseIntegration(ABC):
    """Base class for all HEMS integrations.

    Subclasses must:
    - Define a class-level `manifest: IntegrationManifest`
    - Implement `async def poll(self) -> dict`
    """

    manifest: IntegrationManifest  # defined per subclass

    def __init__(self, config: dict) -> None:
        """Store raw config dict. Subclasses extract what they need."""
        self.config = config

    @abstractmethod
    async def poll(self) -> dict:
        """Return current device readings as a flat dict.

        Keys become field names in the database and InfluxDB.
        Values must be numeric (int or float) or bool.
        Example: {"power_w": 1230.5, "today_kwh": 12.4}
        """
        ...

    async def test_connection(self) -> tuple[bool, str]:
        """Test whether the device is reachable and responding.

        Returns (success, human-readable message). Used by the Settings UI
        before saving a new integration config.
        """
        try:
            await self.poll()
            return True, "Connection successful"
        except Exception as exc:
            return False, str(exc)


class ControllableIntegration(BaseIntegration):
    """Base class for integrations that can be commanded (chargers, smart plugs).

    Adds `set_power()` and convenience helpers `turn_on()` / `turn_off()`.
    """

    @abstractmethod
    async def set_power(self, watts: float | None) -> None:
        """Set target power output.

        Args:
            watts: None = device default/auto, 0 = off, >0 = target watts.
        """
        ...

    async def turn_on(self) -> None:
        """Restore device to default/auto operation."""
        await self.set_power(None)

    async def turn_off(self) -> None:
        """Switch device off (0 W)."""
        await self.set_power(0)
