"""
Alfen Eve EV Charger integration — Modbus TCP.

Connection: Modbus TCP, port 502.
Library: pymodbus >= 3.6

Register map (from Alfen Eve Modbus documentation):
  344  — Active power (float32, 2 registers, Watts, read-only)
         Ref: https://github.com/leonyves/alfen_ical/issues/1
              https://www.alfen.com/file/alfen-eve-modbus-documentation

  1210 — Charge current setpoint (float32, 2 registers, Amps, read/write)
         0A  = pause charging
         6A  = minimum (IEC 61851 minimum safe level)
         32A = maximum for single-phase units

NOTE: If register addresses change with a firmware update, update the
      constants below and add a note with the firmware version. Do NOT
      guess — check the official Alfen Eve Modbus TCP Interface Description
      document (available under NDA from Alfen partner portal).
"""

from __future__ import annotations

import struct

from pymodbus.client import AsyncModbusTcpClient

from backend.integrations.base import (
    ConfigField,
    ControllableIntegration,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register

# Modbus register addresses (0-indexed, i.e. register number - 1 for pymodbus)
_REG_ACTIVE_POWER = 344    # float32, 2 registers, Watts
_REG_CHARGE_CURRENT = 1210  # float32, 2 registers, Amps

_MODBUS_PORT = 502
_MODBUS_UNIT_ID = 1


def _registers_to_float32(registers: list[int]) -> float:
    """Convert two 16-bit Modbus registers to a float32 (big-endian)."""
    raw = struct.pack(">HH", registers[0], registers[1])
    return struct.unpack(">f", raw)[0]


def _float32_to_registers(value: float) -> list[int]:
    """Convert a float32 to two 16-bit Modbus registers (big-endian)."""
    raw = struct.pack(">f", value)
    high, low = struct.unpack(">HH", raw)
    return [high, low]


@register
class AlfenEve(ControllableIntegration):
    """Alfen Eve EV charger — Modbus TCP read/write."""

    manifest = IntegrationManifest(
        id="alfen_eve",
        name="Alfen Eve EV Charger",
        category=IntegrationCategory.CHARGER,
        description="Modbus TCP integration for Alfen Eve single- and three-phase chargers.",
        author="HEMS",
        supports_control=True,
        icon="🚗",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",
                required=True,
                help_text="Local IP of the Alfen Eve charger, e.g. 192.168.1.200",
            ),
            ConfigField(
                name="min_current",
                label="Minimum Current (A)",
                type="number",
                required=False,
                default=6,
                help_text="Minimum safe charge current per IEC 61851. Default: 6A.",
            ),
            ConfigField(
                name="max_current",
                label="Maximum Current (A)",
                type="number",
                required=False,
                default=32,
                help_text="Maximum charge current supported by charger. Default: 32A.",
            ),
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._host = config["host"]
        self.min_current: float = float(config.get("min_current", 6))
        self.max_current: float = float(config.get("max_current", 32))

    async def poll(self) -> dict:
        """Read active power and current setpoint from the charger.

        Returns:
            dict with keys:
              - power_w: current charge power in watts
              - current_setpoint_a: active current setpoint in amps
        """
        async with AsyncModbusTcpClient(
            host=self._host, port=_MODBUS_PORT
        ) as client:
            await client.connect()

            power_result = await client.read_holding_registers(
                address=_REG_ACTIVE_POWER,
                count=2,
                slave=_MODBUS_UNIT_ID,
            )
            current_result = await client.read_holding_registers(
                address=_REG_CHARGE_CURRENT,
                count=2,
                slave=_MODBUS_UNIT_ID,
            )

        if power_result.isError():
            raise RuntimeError(f"Modbus error reading power register: {power_result}")
        if current_result.isError():
            raise RuntimeError(f"Modbus error reading current register: {current_result}")

        power_w = _registers_to_float32(power_result.registers)
        current_a = _registers_to_float32(current_result.registers)

        return {
            "power_w": max(0.0, float(power_w)),
            "current_setpoint_a": float(current_a),
        }

    async def set_power(self, watts: float | None) -> None:
        """Set charge current to achieve target power.

        Converts watts → amps (single-phase 230 V), clamps to [min, max],
        or writes 0A to pause charging.

        Args:
            watts: None = max current; 0 = pause (0A); >0 = target watts
        """
        if watts is None:
            target_amps = self.max_current
        elif watts == 0:
            target_amps = 0.0
        else:
            target_amps = watts / 230.0
            target_amps = max(self.min_current, min(self.max_current, target_amps))

        await self._write_current(target_amps)

    async def set_current(self, amps: float) -> None:
        """Set charge current directly in amps.

        Writes 0A to pause, clamps non-zero values to [min_current, max_current].

        Args:
            amps: target current in amps (0 = pause)
        """
        if amps == 0:
            target = 0.0
        else:
            target = max(self.min_current, min(self.max_current, amps))
        await self._write_current(target)

    async def _write_current(self, amps: float) -> None:
        """Write current setpoint register over Modbus TCP."""
        registers = _float32_to_registers(amps)
        async with AsyncModbusTcpClient(
            host=self._host, port=_MODBUS_PORT
        ) as client:
            await client.connect()
            result = await client.write_registers(
                address=_REG_CHARGE_CURRENT,
                values=registers,
                slave=_MODBUS_UNIT_ID,
            )
        if result.isError():
            raise RuntimeError(f"Modbus error writing current setpoint: {result}")
