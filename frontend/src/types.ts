/** Mirrors backend/models/schemas.py — kept in sync manually. */

export interface DeviceReading {
  id: string;
  name: string;
  type_id: string;
  category: string;
  readings: Record<string, number>;
  last_seen: string | null;
  error: string | null;
}

export interface ChargingState {
  mode: "off" | "min" | "solar" | "fast";
  state: "idle" | "solar_charging" | "min_charging" | "fast_charging" | "paused";
  current_setpoint_a: number;
  power_w: number;
}

export interface StatusPayload {
  timestamp: string;
  devices: DeviceReading[];
  charging: ChargingState;
  current_price_eur_kwh: number | null;
}

export interface HistoryPoint {
  timestamp: string;
  value: number;
}

export interface HistorySeries {
  source_id: string;
  field: string;
  points: HistoryPoint[];
}

export interface HistoryResponse {
  range: string;
  series: HistorySeries[];
}

export interface PricePoint {
  hour: string;
  price_eur_kwh: number;
}

export interface PricingResponse {
  date: string;
  prices: PricePoint[];
  average_eur_kwh: number | null;
}

export interface ForecastPoint {
  hour: string;
  power_w: number;
}

export interface ForecastResponse {
  system_kwp: number;
  points: ForecastPoint[];
}

export interface ConfigField {
  name: string;
  label: string;
  type: "text" | "password" | "number" | "select" | "boolean";
  required: boolean;
  default: string | number | boolean | null;
  options: string[] | null;
  help_text: string;
}

export interface IntegrationType {
  id: string;
  name: string;
  category: string;
  description: string;
  author: string;
  supports_control: boolean;
  icon: string;
  config_fields: ConfigField[];
}

export interface SolarArray {
  id: number;
  name: string;
  panel_count: number;
  wp_per_panel: number;
  tilt_degrees: number;
  azimuth_degrees: number;
  enabled: boolean;
  system_kwp: number;
}

export interface IntegrationInstance {
  id: string;
  type_id: string;
  name: string;
  enabled: boolean;
  last_seen: string | null;
  last_error: string | null;
}
