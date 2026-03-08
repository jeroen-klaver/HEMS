"""
HomeWizard Energy P1 Meter integration.

Uses the local REST API (must be enabled in the HomeWizard Energy app).
Endpoint: GET http://{host}/api/v1/data

Key fields returned:
  active_power_w          — current net grid power (+import, -export)
  total_power_import_kwh  — lifetime import from grid
  total_power_export_kwh  — lifetime export to grid

No authentication required on the local API.
"""

import httpx

from backend.integrations.base import (
    BaseIntegration,
    ConfigField,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register


@register
class HomeWizardP1(BaseIntegration):
    """HomeWizard Energy P1 smart meter reader."""

    manifest = IntegrationManifest(
        id="homewizard_p1",
        name="HomeWizard Energy P1 Meter",
        category=IntegrationCategory.GRID,
        description="Local REST API for the HomeWizard Energy P1 dongle. "
                    "Enable the API in the HomeWizard Energy app first.",
        author="HEMS",
        supports_control=False,
        icon="⚡",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",
                required=True,
                help_text="Local IP of the P1 meter, e.g. 192.168.1.100",
            ),
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._base_url = f"http://{config['host']}/api/v1"

    async def poll(self) -> dict:
        """Fetch current grid readings from the P1 meter.

        Returns:
            dict with keys:
              - power_w: current net power in watts (+import / -export)
              - import_kwh: lifetime grid import in kWh
              - export_kwh: lifetime grid export in kWh
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self._base_url}/data")
            response.raise_for_status()
            data = response.json()

        return {
            "power_w": float(data.get("active_power_w", 0.0)),
            "import_kwh": float(data.get("total_power_import_kwh", 0.0)),
            "export_kwh": float(data.get("total_power_export_kwh", 0.0)),
        }
