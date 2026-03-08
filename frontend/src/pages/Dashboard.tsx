/**
 * Dashboard — main page.
 *
 * Layout:
 *   - Top bar: current price ticker + today's summary
 *   - Energy flow SVG diagram
 *   - Charging mode selector (if a charger is configured)
 *   - Device cards grid
 */

import { useState } from "react";
import ChargingMode from "../components/ChargingMode";
import DeviceCard from "../components/DeviceCard";
import EnergyFlow from "../components/EnergyFlow";
import { useLiveData } from "../hooks/useLiveData";
import type { ChargingState } from "../types";

function PriceTicker({ price }: { price: number | null }) {
  if (price == null) return null;
  return (
    <div className="flex items-center gap-1 text-sm font-semibold">
      <span className="text-slate-400">Now</span>
      <span className="text-white">€{price.toFixed(3)}/kWh</span>
    </div>
  );
}

function SummaryBar({ devices }: { devices: { category: string; readings: Record<string, number> }[] }) {
  const grid = devices.find((d) => d.category === "grid");

  const importKwh = grid?.readings?.import_kwh;
  const exportKwh = grid?.readings?.export_kwh;

  if (importKwh == null && exportKwh == null) return null;

  return (
    <div className="flex gap-4 text-xs text-slate-400">
      {importKwh != null && (
        <span>⬇ {importKwh.toFixed(1)} kWh imported</span>
      )}
      {exportKwh != null && (
        <span>⬆ {exportKwh.toFixed(1)} kWh exported</span>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data, connected, error } = useLiveData();
  const [chargingMode, setChargingMode] = useState<ChargingState["mode"] | null>(null);

  const charging = data?.charging ?? {
    mode: (chargingMode ?? "solar") as ChargingState["mode"],
    state: "idle" as const,
    current_setpoint_a: 0,
    power_w: 0,
  };

  const effectiveCharging: ChargingState = {
    ...charging,
    mode: chargingMode ?? charging.mode,
  };

  const devices = data?.devices ?? [];
  const hasCharger = devices.some((d) => d.category === "charger");

  async function handleTogglePlug(id: string, on: boolean) {
    await fetch(`/api/v1/integrations/${id}/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ on }),
    });
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Connection status */}
      {!connected && (
        <div className="text-xs text-amber-400 bg-amber-900/30 px-3 py-1.5 rounded-lg">
          {error ?? "Connecting to live data…"}
        </div>
      )}

      {/* Top bar */}
      <div className="flex items-center justify-between">
        <PriceTicker price={data?.current_price_eur_kwh ?? null} />
        <SummaryBar devices={devices} />
      </div>

      {/* Energy flow */}
      <div className="bg-slate-800 rounded-xl p-4">
        <EnergyFlow
          devices={devices}
          chargingPowerW={effectiveCharging.power_w}
        />
      </div>

      {/* Charging mode */}
      {hasCharger && (
        <ChargingMode
          charging={effectiveCharging}
          onModeChange={setChargingMode}
        />
      )}

      {/* Device cards */}
      {devices.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {devices.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onToggle={device.category === "smart_plug" ? handleTogglePlug : undefined}
            />
          ))}
        </div>
      )}

      {devices.length === 0 && connected && (
        <div className="text-center text-slate-500 py-12">
          No devices configured yet. Go to{" "}
          <a href="/settings" className="text-blue-400 hover:underline">Settings</a>{" "}
          to add your first integration.
        </div>
      )}
    </div>
  );
}
