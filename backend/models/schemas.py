"""
Pydantic response schemas for the HEMS REST API.

These are separate from the SQLModel DB models so that API shapes
can evolve independently from the storage format.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Integration / config schemas
# ---------------------------------------------------------------------------

class ConfigFieldSchema(BaseModel):
    """Serialised representation of a ConfigField for the frontend."""

    name: str
    label: str
    type: str
    required: bool
    default: Optional[Any] = None
    options: Optional[List[str]] = None
    help_text: str


class IntegrationTypeSchema(BaseModel):
    """One available plugin type returned by GET /api/v1/integration-types."""

    id: str
    name: str
    category: str
    description: str
    author: str
    supports_control: bool
    icon: str
    config_fields: List[ConfigFieldSchema]


class IntegrationInstanceSchema(BaseModel):
    """A configured integration instance returned by GET /api/v1/integrations."""

    id: str
    type_id: str
    name: str
    enabled: bool
    last_seen: Optional[datetime] = None
    last_error: Optional[str] = None
    config: Optional[Dict[str, Any]] = None  # included in detail endpoint only


class IntegrationCreateSchema(BaseModel):
    """Request body for POST /api/v1/integrations."""

    id: str
    type_id: str
    name: str
    config: Dict[str, Any]
    enabled: bool = True


class IntegrationUpdateSchema(BaseModel):
    """Request body for PUT /api/v1/integrations/{id}."""

    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class TestConnectionSchema(BaseModel):
    """Response for POST /api/v1/integrations/{id}/test."""

    success: bool
    message: str


class TestByConfigSchema(BaseModel):
    """Request body for POST /api/v1/integration-types/{type_id}/test."""

    config: Dict[str, Any]


# ---------------------------------------------------------------------------
# Status / live data schemas
# ---------------------------------------------------------------------------

class DeviceReadingSchema(BaseModel):
    """Current readings for one integration, as returned in /api/v1/status."""

    id: str
    name: str
    type_id: str
    category: str
    readings: Dict[str, float]
    last_seen: Optional[datetime] = None
    error: Optional[str] = None


class ChargingStateSchema(BaseModel):
    """Current charging state, embedded in /api/v1/status."""

    mode: str           # off | min | solar | fast
    state: str          # idle | solar_charging | min_charging | fast_charging | paused
    current_setpoint_a: float = 0.0
    power_w: float = 0.0


class StatusSchema(BaseModel):
    """Full response for GET /api/v1/status and WS /ws/live."""

    timestamp: datetime
    devices: List[DeviceReadingSchema]
    charging: ChargingStateSchema
    current_price_eur_kwh: Optional[float] = None


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------

class HistoryPointSchema(BaseModel):
    """One time-series data point."""

    timestamp: datetime
    value: float


class HistorySeriesSchema(BaseModel):
    """Named time-series for one source+field combination."""

    source_id: str
    field: str
    points: List[HistoryPointSchema]


class HistoryResponseSchema(BaseModel):
    """Response for GET /api/v1/history."""

    range: str
    series: List[HistorySeriesSchema]


# ---------------------------------------------------------------------------
# Pricing schemas
# ---------------------------------------------------------------------------

class PricePointSchema(BaseModel):
    """Hourly electricity price."""

    hour: datetime
    price_eur_kwh: float


class PricingResponseSchema(BaseModel):
    """Response for GET /api/v1/pricing/today and /tomorrow."""

    date: str
    prices: List[PricePointSchema]
    average_eur_kwh: Optional[float] = None


# ---------------------------------------------------------------------------
# Forecast schemas
# ---------------------------------------------------------------------------

class ForecastPointSchema(BaseModel):
    """One-hour PV production forecast data point."""

    hour: datetime
    power_w: float


class ForecastResponseSchema(BaseModel):
    """Response for GET /api/v1/forecast."""

    system_kwp: float
    points: List[ForecastPointSchema]


# ---------------------------------------------------------------------------
# Solar arrays
# ---------------------------------------------------------------------------

class SolarArraySchema(BaseModel):
    """A configured solar array, as returned by GET /api/v1/solar-arrays."""

    id: int
    name: str
    panel_count: int
    wp_per_panel: int
    tilt_degrees: float
    azimuth_degrees: float
    enabled: bool
    system_kwp: float   # computed: panel_count * wp_per_panel / 1000


class SolarArrayCreateSchema(BaseModel):
    """Request body for POST and PUT /api/v1/solar-arrays."""

    name: str
    panel_count: int
    wp_per_panel: int
    tilt_degrees: float = 35.0
    azimuth_degrees: float = 180.0
    enabled: bool = True


# ---------------------------------------------------------------------------
# Charging mode
# ---------------------------------------------------------------------------

class ChargingModeUpdateSchema(BaseModel):
    """Request body for PUT /api/v1/charging/mode."""

    mode: str   # off | min | solar | fast
