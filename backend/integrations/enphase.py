"""
Enphase IQ Gateway integration.

Uses the local HTTPS REST API with a long-lived JWT Bearer token.
SSL verification is disabled (self-signed certificate on the gateway).

Endpoint: GET https://{host}/production.json?details=1

Key fields:
  production[].wNow          — current production in watts (inverters)
  consumption[0].wNow        — total consumption inc. solar (net metered)
  consumption[0].wattHoursLifetime — lifetime consumption kWh

Reference: https://github.com/Matthew1471/Enphase-API
"""

import ssl

import httpx

from backend.integrations.base import (
    BaseIntegration,
    ConfigField,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register

# Disable SSL verification for Enphase's self-signed certificate
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


@register
class EnphaseIQGateway(BaseIntegration):
    """Enphase IQ Gateway — local HTTPS solar production data."""

    manifest = IntegrationManifest(
        id="enphase_iq_gateway",
        name="Enphase IQ Gateway",
        category=IntegrationCategory.SOLAR,
        description="Local HTTPS API for Enphase IQ Gateway / Envoy. "
                    "Requires a 1-year JWT token from enlighten.enphaseenergy.com.",
        author="HEMS",
        supports_control=False,
        icon="☀️",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",
                required=True,
                help_text="Local IP of the Enphase IQ Gateway, e.g. 192.168.1.50",
            ),
            ConfigField(
                name="token",
                label="JWT Token",
                type="password",
                required=True,
                help_text="1-year token from enlighten.enphaseenergy.com/entrez-auth-token",
            ),
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._base_url = f"https://{config['host']}"
        self._token = config["token"]

    async def poll(self) -> dict:
        """Fetch current solar production from the IQ Gateway.

        Returns:
            dict with keys:
              - power_w: current solar production in watts
              - lifetime_kwh: lifetime energy produced in kWh
        """
        headers = {"Authorization": f"Bearer {self._token}"}

        async with httpx.AsyncClient(
            verify=False,  # self-signed cert on gateway
            timeout=10.0,
        ) as client:
            response = await client.get(
                f"{self._base_url}/production.json",
                params={"details": "1"},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        # The "production" array contains EIM (production meter) as type "eim"
        production_entries = data.get("production", [])
        eim = next(
            (e for e in production_entries if e.get("type") == "eim"),
            production_entries[0] if production_entries else {},
        )

        power_w = float(eim.get("wNow", 0.0))
        lifetime_kwh = float(eim.get("wattHoursLifetime", 0.0)) / 1000.0

        return {
            "power_w": max(0.0, power_w),   # clamp: never report negative production
            "lifetime_kwh": lifetime_kwh,
        }
