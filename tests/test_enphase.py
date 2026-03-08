"""
Standalone connectivity test for Enphase IQ Gateway.

Usage:
    python tests/test_enphase.py 192.168.1.x eyJ...token...
"""

import asyncio
import sys

sys.path.insert(0, ".")

from backend.integrations.enphase import EnphaseIQGateway


async def main(host: str, token: str) -> None:
    integration = EnphaseIQGateway({"host": host, "token": token})
    print(f"Testing Enphase IQ Gateway at {host} ...")
    success, message = await integration.test_connection()
    print(f"  Connection: {'OK' if success else 'FAILED'} — {message}")
    if success:
        data = await integration.poll()
        print("  Readings:")
        for key, value in data.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <host> <jwt_token>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
