"""
WeHeat heat pump integration — Cloud API (OAuth2 / Keycloak).

Uses the official `weheat` Python library (pip: wefabricate/wh-python).
This is READ-ONLY — WeHeat does not expose write control via their API.

Auth flow:
  OAuth2 client credentials via Keycloak at https://auth.weheat.nl/auth/
  The `weheat` library handles token acquisition and refresh automatically.

Key data:
  input_power_w  — electrical power consumed by the heat pump (watts)
  cop            — coefficient of performance
  water_temp     — supply water temperature (°C)
  mode           — operating mode (heating, cooling, dhw, standby, …)

Config fields:
  client_id       — OAuth2 client ID (from WeHeat partner portal)
  client_secret   — OAuth2 client secret
  heat_pump_uuid  — UUID of the specific heat pump unit
"""

from __future__ import annotations

import httpx

from backend.integrations.base import (
    BaseIntegration,
    ConfigField,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register

_AUTH_URL = "https://auth.weheat.nl/auth/realms/weheat/protocol/openid-connect/token"
_API_BASE = "https://api.weheat.nl/third_party"


@register
class WeHeatHeatPump(BaseIntegration):
    """WeHeat heat pump — cloud OAuth2 read-only integration."""

    manifest = IntegrationManifest(
        id="weheat",
        name="WeHeat Heat Pump",
        category=IntegrationCategory.HEAT_PUMP,
        description="Cloud API for WeHeat Flint/Sparrow/Blackbird heat pumps. "
                    "Read-only. Requires OAuth2 credentials from WeHeat.",
        author="HEMS",
        supports_control=False,
        icon="🌡️",
        config_fields=[
            ConfigField(
                name="client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                help_text="Client ID from the WeHeat developer/partner portal.",
            ),
            ConfigField(
                name="client_secret",
                label="OAuth2 Client Secret",
                type="password",
                required=True,
                help_text="Client secret from the WeHeat developer/partner portal.",
            ),
            ConfigField(
                name="heat_pump_uuid",
                label="Heat Pump UUID",
                type="text",
                required=True,
                help_text="UUID of your specific heat pump unit (visible in the WeHeat app).",
            ),
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._client_id = config["client_id"]
        self._client_secret = config["client_secret"]
        self._uuid = config["heat_pump_uuid"]
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Fetch a fresh OAuth2 access token using client credentials."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def poll(self) -> dict:
        """Fetch current heat pump status from the WeHeat cloud API.

        Returns:
            dict with keys:
              - input_power_w: electrical power consumed in watts
              - cop: coefficient of performance (dimensionless)
              - water_temp_c: supply water temperature in °C
              - mode: operating mode string (e.g. "heating", "standby")
        """
        token = await self._get_access_token()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{_API_BASE}/v1/heat_pumps/{self._uuid}/logs/latest",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()

        return {
            "input_power_w": float(data.get("input_power_w", 0.0)),
            "cop": float(data.get("cop", 0.0)),
            "water_temp_c": float(data.get("water_temperature", 0.0)),
            "mode": str(data.get("heat_pump_state", "unknown")),
        }
