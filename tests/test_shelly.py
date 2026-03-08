"""
Standalone connectivity test for Shelly smart plug (Gen1 or Gen2).

Usage:
    python tests/test_shelly.py 192.168.1.x 2
    python tests/test_shelly.py 192.168.1.x 1
"""

import asyncio
import sys

sys.path.insert(0, ".")

from backend.integrations.shelly import Shelly


async def main(host: str, generation: int) -> None:
    integration = Shelly({"host": host, "generation": generation, "rated_watts": 2000})
    print(f"Testing Shelly Gen{generation} at {host} ...")
    success, message = await integration.test_connection()
    print(f"  Connection: {'OK' if success else 'FAILED'} — {message}")
    if success:
        data = await integration.poll()
        print("  Readings:")
        for key, value in data.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <host> <generation (1 or 2)>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], int(sys.argv[2])))
