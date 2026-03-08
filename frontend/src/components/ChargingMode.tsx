/**
 * ChargingMode — four-way selector for EV charging mode.
 * Sends PUT /api/v1/charging/mode on change.
 */

import { useState } from "react";
import type { ChargingState } from "../types";

interface Props {
  charging: ChargingState;
  onModeChange: (mode: ChargingState["mode"]) => void;
}

const MODES: { value: ChargingState["mode"]; label: string; icon: string; description: string }[] = [
  { value: "off",   label: "Off",   icon: "⏹",  description: "Charger paused" },
  { value: "min",   label: "Min",   icon: "🐢",  description: "Always 6A" },
  { value: "solar", label: "Solar", icon: "☀️",  description: "Surplus only" },
  { value: "fast",  label: "Fast",  icon: "⚡",  description: "Max current" },
];

const STATE_LABELS: Record<ChargingState["state"], string> = {
  idle:           "Idle",
  paused:         "Paused — waiting for surplus",
  solar_charging: "Charging on solar",
  min_charging:   "Charging at minimum",
  fast_charging:  "Charging at maximum",
};

export default function ChargingMode({ charging, onModeChange }: Props) {
  const [saving, setSaving] = useState(false);

  async function handleSelect(mode: ChargingState["mode"]) {
    if (mode === charging.mode || saving) return;
    setSaving(true);
    try {
      await fetch("/api/v1/charging/mode", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      onModeChange(mode);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-slate-100">Charging mode</span>
        <span className="text-xs text-slate-400">{STATE_LABELS[charging.state]}</span>
      </div>

      {/* Mode buttons */}
      <div className="grid grid-cols-4 gap-2">
        {MODES.map((m) => {
          const active = charging.mode === m.value;
          return (
            <button
              key={m.value}
              onClick={() => void handleSelect(m.value)}
              disabled={saving}
              title={m.description}
              className={`flex flex-col items-center gap-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              } disabled:opacity-50`}
            >
              <span className="text-xl">{m.icon}</span>
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>

      {/* Current stats */}
      {charging.power_w > 0 && (
        <div className="mt-3 flex gap-4 text-sm text-slate-400">
          <span>
            {charging.current_setpoint_a.toFixed(1)} A
          </span>
          <span>
            {charging.power_w >= 1000
              ? `${(charging.power_w / 1000).toFixed(2)} kW`
              : `${Math.round(charging.power_w)} W`}
          </span>
        </div>
      )}
    </div>
  );
}
