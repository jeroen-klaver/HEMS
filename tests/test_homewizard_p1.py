"""
Standalone connectivity test for HomeWizard P1 Meter.

Usage:
    python tests/test_homewizard_p1.py 192.168.1.x
"""

import asyncio
import sys

# Add project root to path so we can import backend modules
sys.path.insert(0, ".")

from backend.integrations.homewizard_p1 import HomeWizardP1


async def main(host: str) -> None:
    integration = HomeWizardP1({"host": host})
    print(f"Testing HomeWizard P1 at {host} ...")
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
