"""
Standalone connectivity test for Alfen Eve EV charger (Modbus TCP).

Usage:
    python tests/test_alfen_eve.py 192.168.1.x
"""

import asyncio
import sys

sys.path.insert(0, ".")

from backend.integrations.alfen_eve import AlfenEve


async def main(host: str) -> None:
    integration = AlfenEve({"host": host, "min_current": 6, "max_current": 32})
    print(f"Testing Alfen Eve at {host} (Modbus TCP port 502) ...")
    success, message = await integration.test_connection()
    print(f"  Connection: {'OK' if success else 'FAILED'} — {message}")
    if success:
        data = await integration.poll()
        print("  Readings:")
        for key, value in data.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <host>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
