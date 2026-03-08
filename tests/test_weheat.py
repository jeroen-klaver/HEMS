"""
Standalone connectivity test for WeHeat heat pump (OAuth2 cloud API).

Usage:
    python tests/test_weheat.py <client_id> <client_secret> <heat_pump_uuid>
"""

import asyncio
import sys

sys.path.insert(0, ".")

from backend.integrations.weheat import WeHeatHeatPump


async def main(client_id: str, client_secret: str, uuid: str) -> None:
    integration = WeHeatHeatPump({
        "client_id": client_id,
        "client_secret": client_secret,
        "heat_pump_uuid": uuid,
    })
    print(f"Testing WeHeat heat pump (uuid={uuid}) ...")
    success, message = await integration.test_connection()
    print(f"  Connection: {'OK' if success else 'FAILED'} — {message}")
    if success:
        data = await integration.poll()
        print("  Readings:")
        for key, value in data.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <client_id> <client_secret> <heat_pump_uuid>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
