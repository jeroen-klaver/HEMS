"""
Shelly smart plug integration — supports Gen1 and Gen2+ devices.

Gen1 API (HTTP):
  Read:  GET  http://{host}/relay/0
  Write: POST http://{host}/relay/0   body: turn=on | turn=off

Gen2+ API (RPC over HTTP):
  Read:  GET  http://{host}/rpc/Switch.GetStatus?id=0
  Write: POST http://{host}/rpc/Switch.Set  body: {"id": 0, "on": true}

Configure `generation: 1` or `generation: 2` in config.yaml.
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
class Shelly(ControllableIntegration):
    """Shelly smart plug — Gen1 and Gen2+ in a single integration."""

    manifest = IntegrationManifest(
        id="shelly",
        name="Shelly Smart Plug",
        category=IntegrationCategory.SMART_PLUG,
        description="Local HTTP API for Shelly Gen1 and Gen2+ smart plugs.",
        author="HEMS",
        supports_control=True,
        icon="🔌",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",
                required=True,
                help_text="Local IP of the Shelly device, e.g. 192.168.1.102",
            ),
            ConfigField(
                name="generation",
                label="Device Generation",
                type="select",
                required=True,
                default="2",
                options=["1", "2"],
                help_text="Gen1 = older Shelly Plug/PlugS; Gen2 = Shelly Plus/Pro/Mini",
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
        self._host = config["host"]
        self._gen = int(config.get("generation", 2))
        self.rated_watts: float = float(config.get("rated_watts", 2000))

    # ------------------------------------------------------------------
    # BaseIntegration
    # ------------------------------------------------------------------

    async def poll(self) -> dict:
        """Fetch current power and on/off state.

        Returns:
            dict with keys:
              - power_w: current active power in watts
              - on: True if relay is closed (switch on)
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            if self._gen == 1:
                return await self._poll_gen1(client)
            else:
                return await self._poll_gen2(client)

    # ------------------------------------------------------------------
    # ControllableIntegration
    # ------------------------------------------------------------------

    async def set_power(self, watts: float | None) -> None:
        """Turn relay on (watts > 0 or None) or off (watts == 0).

        Shelly plugs are binary — no variable power control.

        Args:
            watts: None or >0 → on; 0 → off
        """
        on = watts is None or watts > 0
        async with httpx.AsyncClient(timeout=5.0) as client:
            if self._gen == 1:
                await self._set_gen1(client, on)
            else:
                await self._set_gen2(client, on)

    # ------------------------------------------------------------------
    # Private helpers — Gen1
    # ------------------------------------------------------------------

    async def _poll_gen1(self, client: httpx.AsyncClient) -> dict:
        """Read relay status from a Gen1 device."""
        response = await client.get(f"http://{self._host}/relay/0")
        response.raise_for_status()
        data = response.json()
        return {
            "power_w": float(data.get("power", 0.0)),
            "on": bool(data.get("ison", False)),
        }

    async def _set_gen1(self, client: httpx.AsyncClient, on: bool) -> None:
        """Toggle relay on a Gen1 device."""
        response = await client.post(
            f"http://{self._host}/relay/0",
            data={"turn": "on" if on else "off"},
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Private helpers — Gen2+
    # ------------------------------------------------------------------

    async def _poll_gen2(self, client: httpx.AsyncClient) -> dict:
        """Read switch status from a Gen2+ device via RPC."""
        response = await client.get(
            f"http://{self._host}/rpc/Switch.GetStatus",
            params={"id": 0},
        )
        response.raise_for_status()
        data = response.json()
        return {
            "power_w": float(data.get("apower", 0.0)),
            "on": bool(data.get("output", False)),
        }

    async def _set_gen2(self, client: httpx.AsyncClient, on: bool) -> None:
        """Toggle switch on a Gen2+ device via RPC."""
        response = await client.post(
            f"http://{self._host}/rpc/Switch.Set",
            json={"id": 0, "on": on},
        )
        response.raise_for_status()
