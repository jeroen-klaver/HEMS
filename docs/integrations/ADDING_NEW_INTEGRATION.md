# Adding a New Integration

HEMS uses a plugin architecture — adding support for new hardware requires
creating exactly **one file**. No changes to core code required.

---

## 1. Create the integration file

Create `backend/integrations/<your_device>.py`.

### Read-only device (solar, grid, heat pump)

```python
from __future__ import annotations

import httpx

from backend.integrations.base import (
    BaseIntegration,
    ConfigField,
    IntegrationCategory,
    IntegrationManifest,
)
from backend.integrations.registry import register


@register
class MyDevice(BaseIntegration):
    """One-line description of the device."""

    manifest = IntegrationManifest(
        id="my_device",                        # unique snake_case ID
        name="My Device",                      # display name
        category=IntegrationCategory.SOLAR,    # SOLAR | GRID | HEAT_PUMP | SMART_PLUG | CHARGER
        description="Longer description shown in the Settings UI.",
        author="Your Name",
        supports_control=False,
        icon="☀️",
        config_fields=[
            ConfigField(
                name="host",
                label="IP Address",
                type="text",                   # text | password | number | select | boolean
                required=True,
                help_text="Local IP of the device.",
            ),
            # Add more fields as needed
        ],
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._host = config["host"]

    async def poll(self) -> dict:
        """Return current readings as a flat dict of numeric values."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{self._host}/api/data")
            response.raise_for_status()
            data = response.json()

        return {
            "power_w": float(data["power"]),
            "today_kwh": float(data["energy_today"]),
        }
```

### Controllable device (charger, smart plug)

Subclass `ControllableIntegration` and implement `set_power()`:

```python
from backend.integrations.base import ControllableIntegration

@register
class MyPlug(ControllableIntegration):
    manifest = IntegrationManifest(
        ...
        supports_control=True,
    )

    async def poll(self) -> dict:
        ...

    async def set_power(self, watts: float | None) -> None:
        """None / >0 = on, 0 = off."""
        on = watts is None or watts > 0
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"http://{self._host}/relay", json={"on": on})
```

---

## 2. Register it in main.py

Add one import line to `backend/main.py` inside `_import_integrations()`:

```python
def _import_integrations() -> None:
    import backend.integrations.my_device   # noqa: F401
    # ... existing imports
```

That's it — the `@register` decorator fires on import and the new type
automatically appears in `GET /api/v1/integration-types` and the Settings UI.

---

## 3. Write a test script

Create `tests/test_my_device.py`:

```python
import asyncio, sys
sys.path.insert(0, ".")
from backend.integrations.my_device import MyDevice

async def main(host: str) -> None:
    integration = MyDevice({"host": host})
    success, message = await integration.test_connection()
    print(f"Connection: {'OK' if success else 'FAILED'} — {message}")
    if success:
        data = await integration.poll()
        for k, v in data.items():
            print(f"  {k}: {v}")

asyncio.run(main(sys.argv[1]))
```

Run against real hardware before opening a PR:

```bash
python tests/test_my_device.py 192.168.1.x
```

---

## poll() contract

| Rule | Detail |
|---|---|
| Return type | `dict[str, float \| int \| bool]` — all values coerced to float internally |
| Keys | Stable snake_case names — they become DB field names and InfluxDB fields |
| On error | Raise any exception — the scheduler catches it, logs it, and marks the device with an error state. Never return partial/garbage data. |
| Async | Must be `async def`. Never use blocking I/O (e.g. `requests`, `time.sleep`). |

## ConfigField types

| type | Rendered as |
|---|---|
| `"text"` | `<input type="text">` |
| `"password"` | `<input type="password">` (masked) |
| `"number"` | `<input type="number">` |
| `"boolean"` | Toggle button |
| `"select"` | `<select>` — set `options=["a", "b"]` |

## IntegrationCategory values

`SOLAR` · `GRID` · `CHARGER` · `HEAT_PUMP` · `SMART_PLUG` · `BATTERY` · `VEHICLE`
