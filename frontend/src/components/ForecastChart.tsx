/**
 * ForecastChart — hourly PV production forecast area chart.
 * Shows today + tomorrow from the Open-Meteo / pvlib forecast.
 */

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastPoint } from "../types";

interface Props {
  points: ForecastPoint[];
  systemKwp: number;
}

function fmtHour(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtPower(w: number): string {
  if (w >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}

export default function ForecastChart({ points, systemKwp }: Props) {
  if (points.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 text-slate-400 text-sm">
        No forecast data available.
      </div>
    );
  }

  const data = points.map((p) => ({
    hour: fmtHour(p.hour),
    power: Math.round(p.power_w),
  }));

  const peak = Math.max(...data.map((d) => d.power));

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-slate-100">PV forecast</span>
        <span className="text-sm text-slate-400">
          {systemKwp} kWp · peak {fmtPower(peak)}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="solar-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#facc15" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#facc15" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="hour"
            tick={{ fontSize: 10, fill: "#64748b" }}
            tickLine={false}
            interval={3}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => fmtPower(v)}
          />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            formatter={(value: number) => [fmtPower(value), "Forecast"]}
          />
          <Area
            type="monotone"
            dataKey="power"
            stroke="#facc15"
            strokeWidth={2}
            fill="url(#solar-grad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
