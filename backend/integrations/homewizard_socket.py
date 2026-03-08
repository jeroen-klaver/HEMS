"""
HomeWizard Energy Socket integration.

Uses the local REST API.
  Read:  GET http://{host}/api/v1/data   → active_power_w, on/off state
  Write: PUT http://{host}/api/v1/state  → {"power_on": true/false}

The API must be enabled in the HomeWizard Energy app.
"""

from __future__ import annotations

import httpx

from backend.integrations.base import (
    ConfigField,
    ControllableIntegration,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register


@register
class HomeWizardSocket(ControllableIntegration):
    """HomeWizard Energy smart plug (HWE-SKT)."""

    manifest = IntegrationManifest(
        id="homewizard_socket",
        name="HomeWizard Energy Socket",
        category=IntegrationCategory.SMART_PLUG,
        description="Local REST API for the HomeWizard Energy smart plug. "
                    "Enable the API in the HomeWizard Energy app first.",
        author="HEMS",
        supports_control=True,
        icon="🔌",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",
                required=True,
                help_text="Local IP of the smart plug, e.g. 192.168.1.101",
            ),
            ConfigField(
                name="rated_watts",
                label="Rated Power (W)",
                type="number",
                required=False,
                default=2000,
                help_text="Nominal power of the connected appliance, used for surplus logic.",
            ),
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._base_url = f"http://{config['host']}/api/v1"
        self.rated_watts: float = float(config.get("rated_watts", 2000))

    async def poll(self) -> dict:
        """Fetch current state and power reading.

        Returns:
            dict with keys:
              - power_w: current active power in watts
              - on: True if the socket is switched on
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self._base_url}/data")
            response.raise_for_status()
            data = response.json()

        return {
            "power_w": float(data.get("active_power_w", 0.0)),
            "on": bool(data.get("wifi_ssid") is not None and data.get("active_power_w", 0) > 0),
        }

    async def set_power(self, watts: float | None) -> None:
        """Turn the socket on (watts > 0 or None) or off (watts == 0).

        HomeWizard sockets are binary — they have no variable power control.

        Args:
            watts: None or >0 → power_on: true; 0 → power_on: false
        """
        power_on = watts is None or watts > 0
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.put(
                f"{self._base_url}/state",
                json={"power_on": power_on},
            )
            response.raise_for_status()
