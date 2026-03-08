"""
Configuration loader for HEMS.

Reads config.yaml from disk and exposes a typed Config object.
The config is loaded once at startup and cached; call reload() to re-read.

Structure mirrors config.yaml.example — see that file for field documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

import os
_DATA_DIR = Path(os.environ.get("HEMS_DATA_DIR", "."))
_CONFIG_PATH = _DATA_DIR / "config.yaml"
_config: Optional["Config"] = None


# ---------------------------------------------------------------------------
# Dataclasses mirroring config.yaml structure
# ---------------------------------------------------------------------------

@dataclass
class IntegrationConfig:
    """One entry under `integrations:` in config.yaml."""

    id: str
    type_id: str
    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChargingConfig:
    mode: str = "solar"                   # off | min | solar | fast
    solar_start_threshold_w: float = 1380  # 6A * 230V
    hysteresis_seconds: int = 60
    min_soc_percent: int = 20
    target_soc_percent: int = 80
    charge_by_time: Optional[str] = None   # e.g. "07:00"


@dataclass
class PricingConfig:
    source: str = "manual"                # entso-e | manual
    entso_e_token: str = ""
    bidding_zone: str = "10YNL----------L"
    supplier_markup_eur_kwh: float = 0.04
    energy_tax_eur_kwh: float = 0.1228
    vat_percent: float = 21.0
    manual_price_eur_kwh: float = 0.25


@dataclass
class ForecastConfig:
    enabled: bool = False
    system_kwp: float = 0.0
    tilt_degrees: float = 35.0
    azimuth_degrees: float = 180.0


@dataclass
class InfluxConfig:
    enabled: bool = False
    url: str = "http://localhost:8086"
    token: str = ""
    org: str = "hems"
    bucket: str = "energy"


@dataclass
class ExportsConfig:
    influxdb: InfluxConfig = field(default_factory=InfluxConfig)


@dataclass
class HemsConfig:
    name: str = "My Home"
    latitude: float = 52.0
    longitude: float = 5.0


@dataclass
class Config:
    """Root config object — mirrors the top-level keys in config.yaml."""

    hems: HemsConfig = field(default_factory=HemsConfig)
    integrations: list[IntegrationConfig] = field(default_factory=list)
    charging: ChargingConfig = field(default_factory=ChargingConfig)
    pricing: PricingConfig = field(default_factory=PricingConfig)
    forecast: ForecastConfig = field(default_factory=ForecastConfig)
    exports: ExportsConfig = field(default_factory=ExportsConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _parse(raw: dict) -> Config:
    """Convert raw YAML dict into a typed Config object."""
    hems_raw = raw.get("hems", {})
    hems = HemsConfig(
        name=hems_raw.get("name", "My Home"),
        latitude=float(hems_raw.get("latitude", 52.0)),
        longitude=float(hems_raw.get("longitude", 5.0)),
    )

    integrations = [
        IntegrationConfig(
            id=i["id"],
            type_id=i["type"],
            name=i.get("name", i["id"]),
            enabled=i.get("enabled", True),
            config=i.get("config", {}),
        )
        for i in raw.get("integrations", [])
    ]

    c = raw.get("charging", {})
    charging = ChargingConfig(
        mode=c.get("mode", "solar"),
        solar_start_threshold_w=float(c.get("solar_start_threshold_w", 1380)),
        hysteresis_seconds=int(c.get("hysteresis_seconds", 60)),
        min_soc_percent=int(c.get("min_soc_percent", 20)),
        target_soc_percent=int(c.get("target_soc_percent", 80)),
        charge_by_time=c.get("charge_by_time"),
    )

    p = raw.get("pricing", {})
    pricing = PricingConfig(
        source=p.get("source", "manual"),
        entso_e_token=p.get("entso_e_token", ""),
        bidding_zone=p.get("bidding_zone", "10YNL----------L"),
        supplier_markup_eur_kwh=float(p.get("supplier_markup_eur_kwh", 0.04)),
        energy_tax_eur_kwh=float(p.get("energy_tax_eur_kwh", 0.1228)),
        vat_percent=float(p.get("vat_percent", 21.0)),
        manual_price_eur_kwh=float(p.get("manual_price_eur_kwh", 0.25)),
    )

    f = raw.get("forecast", {})
    forecast = ForecastConfig(
        enabled=bool(f.get("enabled", False)),
        system_kwp=float(f.get("system_kwp", 0.0)),
        tilt_degrees=float(f.get("tilt_degrees", 35.0)),
        azimuth_degrees=float(f.get("azimuth_degrees", 180.0)),
    )

    ix = raw.get("exports", {}).get("influxdb", {})
    exports = ExportsConfig(
        influxdb=InfluxConfig(
            enabled=bool(ix.get("enabled", False)),
            url=ix.get("url", "http://localhost:8086"),
            token=ix.get("token", ""),
            org=ix.get("org", "hems"),
            bucket=ix.get("bucket", "energy"),
        )
    )

    return Config(
        hems=hems,
        integrations=integrations,
        charging=charging,
        pricing=pricing,
        forecast=forecast,
        exports=exports,
    )


def load(path: Path = _CONFIG_PATH) -> Config:
    """Load and cache config from disk. Returns cached value on subsequent calls."""
    global _config
    if _config is None:
        _config = reload(path)
    return _config


def reload(path: Path = _CONFIG_PATH) -> Config:
    """Re-read config.yaml from disk and update the cache."""
    global _config
    if not path.exists():
        # No config file — return defaults (useful for first-run / tests)
        _config = Config()
        return _config
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    _config = _parse(raw)
    return _config


def get() -> Config:
    """Return the cached config. Raises if load() has not been called yet."""
    if _config is None:
        return load()
    return _config
