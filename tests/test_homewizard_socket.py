"""
Standalone connectivity test for HomeWizard Energy Socket.

Usage:
    python tests/test_homewizard_socket.py 192.168.1.x
"""

import asyncio
import sys

sys.path.insert(0, ".")

from backend.integrations.homewizard_socket import HomeWizardSocket


async def main(host: str) -> None:
    integration = HomeWizardSocket({"host": host, "rated_watts": 2000})
    print(f"Testing HomeWizard Socket at {host} ...")
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
