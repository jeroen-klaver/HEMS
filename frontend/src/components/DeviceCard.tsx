/**
 * DeviceCard — displays current status for one integration instance.
 *
 * Shows: icon, name, primary power reading, today's total, status indicator.
 * Controllable devices (charger, smart plugs) render a toggle or ChargingMode selector.
 */

import type { DeviceReading } from "../types";

interface Props {
  device: DeviceReading;
  onToggle?: (id: string, on: boolean) => void; // for smart plugs
}

const CATEGORY_ICONS: Record<string, string> = {
  solar: "☀️",
  grid: "⚡",
  charger: "🚗",
  heat_pump: "🌡️",
  smart_plug: "🔌",
  battery: "🔋",
  vehicle: "🚗",
};

function fmt(w: number): string {
  if (Math.abs(w) >= 1000) return `${(w / 1000).toFixed(2)} kW`;
  return `${Math.round(w)} W`;
}

function fmtKwh(kwh: number): string {
  return `${kwh.toFixed(2)} kWh`;
}

/** Pick the most relevant power reading for each category. */
function primaryPower(device: DeviceReading): number {
  const r = device.readings;
  return (
    r["power_w"] ??
    r["input_power_w"] ??
    0
  );
}

/** Pick today's kWh reading if available. */
function todayKwh(device: DeviceReading): number | null {
  const r = device.readings;
  const kwh = r["today_kwh"] ?? r["energy_kwh"];
  return kwh != null ? kwh : null;
}

export default function DeviceCard({ device, onToggle }: Props) {
  const icon = CATEGORY_ICONS[device.category] ?? "📟";
  const power = primaryPower(device);
  const kwh = todayKwh(device);
  const isOn = device.readings["on"] === 1 || device.readings["on"] === undefined;
  const isPlug = device.category === "smart_plug";
  const hasError = device.error != null;

  // Status dot
  const statusColor = hasError
    ? "bg-red-500"
    : device.last_seen
    ? "bg-green-500"
    : "bg-gray-500";

  return (
    <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-2 relative">
      {/* Status dot */}
      <span
        className={`absolute top-3 right-3 w-2.5 h-2.5 rounded-full ${statusColor}`}
        title={hasError ? device.error ?? "Error" : "OK"}
      />

      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <span className="font-semibold text-slate-100 truncate">{device.name}</span>
      </div>

      {/* Primary reading */}
      <div className="text-3xl font-bold text-white tabular-nums">
        {hasError ? (
          <span className="text-red-400 text-sm">{device.error}</span>
        ) : device.category === "vehicle" ? (
          device.readings["soc_percent"] != null
            ? `${Math.round(device.readings["soc_percent"])}%`
            : "–"
        ) : (
          fmt(power)
        )}
      </div>

      {/* Vehicle details */}
      {device.category === "vehicle" && !hasError && (
        <div className="flex flex-col gap-0.5 text-sm text-slate-400">
          {device.readings["range_km"] != null && (
            <span>Range: {Math.round(device.readings["range_km"])} km</span>
          )}
          <span>
            {device.readings["plug_connected"] === 1 ? "🔌 Aangesloten" : "⛽ Niet aangesloten"}
          </span>
          {device.readings["charging_state"] === 1 && (
            <span className="text-green-400">⚡ Aan het laden</span>
          )}
        </div>
      )}

      {/* Today total */}
      {kwh != null && !hasError && device.category !== "vehicle" && (
        <div className="text-sm text-slate-400">
          Today: {fmtKwh(kwh)}
        </div>
      )}

      {/* COP for heat pump */}
      {device.category === "heat_pump" && device.readings["cop"] != null && (
        <div className="text-sm text-slate-400">
          COP: {device.readings["cop"].toFixed(2)}
        </div>
      )}

      {/* Smart plug toggle */}
      {isPlug && onToggle && (
        <button
          onClick={() => onToggle(device.id, !isOn)}
          className={`mt-1 self-start text-sm px-3 py-1 rounded-full font-medium transition-colors ${
            isOn
              ? "bg-green-600 hover:bg-green-700 text-white"
              : "bg-slate-600 hover:bg-slate-500 text-slate-300"
          }`}
        >
          {isOn ? "On" : "Off"}
        </button>
      )}
    </div>
  );
}
