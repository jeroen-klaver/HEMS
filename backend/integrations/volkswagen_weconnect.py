"""
Volkswagen We Connect ID integration — Cloud API.

Uses the `weconnect` Python library (tillsteinbach/WeConnect-python) which
handles the complex multi-step OAuth2 flow with VW's identity servers.

This is READ-ONLY — reads battery/charging state from the vehicle API.

Auth flow:
  Handled internally by the weconnect library using username + password
  against VW's identity.vwgroup.io OAuth2 server.

Key data:
  soc_percent      — state of charge (%)
  range_km         — electric range remaining (km)
  charging_state   — 1.0 if actively charging, else 0.0
  plug_connected   — 1.0 if plug is physically connected, else 0.0

Config fields:
  username  — VW We Connect ID account e-mail
  password  — VW We Connect ID password
  vin       — Vehicle Identification Number (17 characters)
"""

from __future__ import annotations

import asyncio
import logging
import time

from backend.integrations.base import (
    BaseIntegration,
    ConfigField,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register

_log = logging.getLogger(__name__)


@register
class VolkswagenWeConnect(BaseIntegration):
    """Volkswagen We Connect ID — cloud API read-only integration."""

    manifest = IntegrationManifest(
        id="volkswagen_weconnect",
        name="Volkswagen We Connect ID",
        category=IntegrationCategory.VEHICLE,
        description="Reads battery SoC, range, and charging status from the VW We Connect ID "
                    "cloud API. Works with VW eHybrid and ID. vehicles.",
        author="HEMS",
        supports_control=False,
        icon="🚗",
        config_fields=[
            ConfigField(
                name="username",
                label="We Connect ID e-mail",
                type="text",
                required=True,
                help_text="The e-mail address of your Volkswagen We Connect ID account.",
            ),
            ConfigField(
                name="password",
                label="We Connect ID wachtwoord",
                type="password",
                required=True,
                help_text="Het wachtwoord van je Volkswagen We Connect ID account.",
            ),
            ConfigField(
                name="vin",
                label="VIN (kentekennummer)",
                type="text",
                required=True,
                help_text="Het 17-tekens Vehicle Identification Number van je auto "
                          "(zichtbaar in de We Connect ID app onder Voertuiginfo).",
            ),
        ],
    )

    _POLL_INTERVAL = 300  # seconds between actual API calls (VW rate-limits at 5s polling)

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._username: str = config["username"]
        self._password: str = config["password"]
        self._vin: str = config["vin"].upper().strip()
        self._client = None  # lazy-initialised on first poll
        self._last_fetch: float = 0.0
        self._cached: dict = {}

    def _get_client(self):
        """Return the WeConnect client, creating and logging in if needed."""
        if self._client is None:
            from weconnect import weconnect as wc  # import here to avoid load-time errors
            self._client = wc.WeConnect(
                username=self._username,
                password=self._password,
                updateAfterLogin=False,
                loginOnInit=True,
            )
        return self._client

    def _fetch(self) -> dict:
        """Synchronous data fetch — called via run_in_executor."""
        client = self._get_client()
        client.update()

        vehicle = client.vehicles.get(self._vin)
        if vehicle is None:
            available = list(client.vehicles.keys())
            raise ValueError(
                f"VIN '{self._vin}' niet gevonden in account. "
                f"Beschikbare VINs: {available}"
            )

        result: dict[str, float] = {}

        # --- Battery / SoC ---
        try:
            battery = vehicle.domains["charging"]["batteryStatus"].value
            result["soc_percent"] = float(battery.currentSOC_pct.value)
            result["range_km"] = float(battery.cruisingRangeElectric_km.value)
        except (KeyError, AttributeError, TypeError) as exc:
            _log.debug("batteryStatus niet beschikbaar: %s", exc)

        # --- Charging state ---
        try:
            charging = vehicle.domains["charging"]["chargingStatus"].value
            state = str(charging.chargingState.value).lower()
            result["charging_state"] = 1.0 if state == "charging" else 0.0
        except (KeyError, AttributeError, TypeError) as exc:
            _log.debug("chargingStatus niet beschikbaar: %s", exc)

        # --- Plug connection ---
        try:
            plug = vehicle.domains["charging"]["plugStatus"].value
            connection = str(plug.plugConnectionState.value).lower()
            result["plug_connected"] = 1.0 if connection == "connected" else 0.0
        except (KeyError, AttributeError, TypeError) as exc:
            _log.debug("plugStatus niet beschikbaar: %s", exc)

        return result

    async def poll(self) -> dict:
        """Fetch current vehicle status, at most once per 5 minutes."""
        if self._cached and time.monotonic() - self._last_fetch < self._POLL_INTERVAL:
            return self._cached
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._fetch)
        self._cached = result
        self._last_fetch = time.monotonic()
        return result
