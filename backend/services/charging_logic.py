"""
EV charging control state machine.

Runs every 5 seconds (inside the scheduler's poll_all job) after all
integration readings have been refreshed.

Modes:
  off    — charger always paused (0A)
  min    — always charge at minimum current (6A)
  solar  — charge only on solar surplus; hysteresis prevents rapid cycling
  fast   — charge at maximum current regardless of solar

Solar surplus calculation:
  surplus_w = solar_w - home_consumption_w   (excluding charger load)
  home_consumption_w = grid_w + solar_w - charger_w   (power balance)
  → surplus_w = solar_w - (grid_w + solar_w - charger_w) + charger_w
              = -grid_w + charger_w   (negative grid = export = surplus)

Simplified: surplus_w = charger_w - grid_w   (where grid_w > 0 = import)
Which means: if grid exports (grid_w < 0), surplus = charger + |grid_export|.

Hysteresis:
  - Current may be increased immediately when surplus grows.
  - Current is only reduced (or charging paused) after the threshold has
    been undershot for >= hysteresis_seconds continuously.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from backend.config import Config
from backend.integrations.base import BaseIntegration
from backend.integrations.alfen_eve import AlfenEve
from backend.state import ChargingState, HEMSState

log = logging.getLogger(__name__)

# Hysteresis tracker: timestamp when we first fell below threshold
_below_threshold_since: Optional[datetime] = None
_last_setpoint_a: float = 0.0


async def run_charging_step(
    conf: Config,
    instances: dict[str, BaseIntegration],
    state: HEMSState,
) -> None:
    """Evaluate charging mode and send setpoint to charger if needed.

    Called once per poll cycle (every 5s) by the scheduler.
    """
    global _below_threshold_since, _last_setpoint_a

    # Find the charger instance (first AlfenEve found)
    charger: Optional[AlfenEve] = None
    for instance in instances.values():
        if isinstance(instance, AlfenEve):
            charger = instance
            break

    if charger is None:
        # No charger configured — nothing to do
        return

    mode = conf.charging.mode
    min_a = charger.min_current
    max_a = charger.max_current
    threshold_w = conf.charging.solar_start_threshold_w
    hysteresis_s = conf.charging.hysteresis_seconds

    if mode == "off":
        target_a = 0.0

    elif mode == "min":
        target_a = min_a

    elif mode == "fast":
        target_a = max_a

    elif mode == "solar":
        target_a = _solar_target_amps(
            state, min_a, max_a, threshold_w, hysteresis_s
        )

    else:
        log.warning("Unknown charging mode '%s', defaulting to off", mode)
        target_a = 0.0

    # Only write to charger if setpoint changed (avoids unnecessary Modbus writes)
    if target_a != _last_setpoint_a:
        try:
            await charger.set_current(target_a)
            _last_setpoint_a = target_a
            log.info("Charging setpoint → %.1f A (mode=%s)", target_a, mode)
        except Exception:
            log.exception("Failed to write charging setpoint")

    # Update in-memory charging state
    charging_state_str = _derive_state(mode, target_a, min_a)
    new_charging = ChargingState(
        mode=mode,
        state=charging_state_str,
        current_setpoint_a=target_a,
        power_w=state.get_charger_power_w(),
    )
    await state.set_charging(new_charging)

    # Control smart plugs with surplus logic
    await _control_smart_plugs(conf, instances, state)


def _solar_target_amps(
    state: HEMSState,
    min_a: float,
    max_a: float,
    threshold_w: float,
    hysteresis_s: int,
) -> float:
    """Calculate target charge current from current solar surplus."""
    global _below_threshold_since

    solar_w = state.get_solar_power_w()
    grid_w = state.get_grid_power_w()    # positive = import, negative = export
    charger_w = state.get_charger_power_w()

    # Surplus = what we'd export if charger wasn't running
    # = current export (−grid_w) + charger consumption
    surplus_w = charger_w - grid_w

    # Desired current
    raw_amps = surplus_w / 230.0
    target_a = math.floor(raw_amps)

    if target_a < min_a:
        # Below minimum — apply hysteresis before stopping
        now = datetime.utcnow()
        if _below_threshold_since is None:
            _below_threshold_since = now

        elapsed = (now - _below_threshold_since).total_seconds()
        if elapsed >= hysteresis_s:
            return 0.0  # pause charging
        else:
            # Haven't waited long enough — keep last setpoint
            return _last_setpoint_a
    else:
        # Surplus is sufficient — reset hysteresis tracker
        _below_threshold_since = None
        return min(target_a, max_a)


def _derive_state(mode: str, target_a: float, min_a: float) -> str:
    """Map mode + setpoint to a human-readable state string."""
    if mode == "off" or target_a == 0:
        return "paused" if mode != "off" else "idle"
    if mode == "min":
        return "min_charging"
    if mode == "fast":
        return "fast_charging"
    if mode == "solar":
        return "solar_charging" if target_a >= min_a else "paused"
    return "idle"


# ---------------------------------------------------------------------------
# Smart plug surplus control
# ---------------------------------------------------------------------------

async def _control_smart_plugs(
    conf: Config,
    instances: dict[str, BaseIntegration],
    state: HEMSState,
) -> None:
    """Binary on/off control for smart plugs based on solar surplus.

    Turn ON  when: surplus_w > rated_watts * 0.8  (for ≥ 10s — single check is enough)
    Turn OFF when: surplus_w < rated_watts * 0.3  (hysteresis handled by charger first)
    """
    from backend.integrations.base import ControllableIntegration

    grid_w = state.get_grid_power_w()
    charger_w = state.get_charger_power_w()
    surplus_w = charger_w - grid_w

    for iid, instance in instances.items():
        if not isinstance(instance, ControllableIntegration):
            continue
        # Skip charger — handled above
        if isinstance(instance, AlfenEve):
            continue

        rated_w: float = getattr(instance, "rated_watts", 0.0)
        if rated_w <= 0:
            continue

        device = state.devices.get(iid)
        currently_on = bool(device and device.readings.get("on", False))

        if not currently_on and surplus_w > rated_w * 0.8:
            try:
                await instance.turn_on()
                log.info("Smart plug %s turned ON (surplus=%.0f W)", iid, surplus_w)
            except Exception:
                log.exception("Failed to turn on smart plug %s", iid)

        elif currently_on and surplus_w < rated_w * 0.3:
            try:
                await instance.turn_off()
                log.info("Smart plug %s turned OFF (surplus=%.0f W)", iid, surplus_w)
            except Exception:
                log.exception("Failed to turn off smart plug %s", iid)
