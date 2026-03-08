/**
 * History page — historical time-series charts with range selector.
 */

import { useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useHistory } from "../hooks/useHistory";
import type { HistorySeries } from "../types";

type Range = "1h" | "6h" | "24h" | "7d" | "30d";

const RANGES: Range[] = ["1h", "6h", "24h", "7d", "30d"];

// Prioritise which field to show per category (first match wins)
const SERIES_PRIORITY: Record<string, string[]> = {
  solar:      ["power_w"],
  grid:       ["power_w"],
  charger:    ["power_w"],
  heat_pump:  ["input_power_w"],
  smart_plug: ["power_w"],
};

const SERIES_COLORS = [
  "#22c55e", "#f97316", "#3b82f6", "#a855f7", "#facc15", "#ec4899",
];

function fmtTime(iso: string, range: Range): string {
  const d = new Date(iso);
  if (range === "7d" || range === "30d") {
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  }
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtPower(w: number): string {
  if (Math.abs(w) >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}

/** Pick the best series per source_id to avoid duplicate charts. */
function pickSeries(allSeries: HistorySeries[]): HistorySeries[] {
  const seen = new Set<string>();
  const result: HistorySeries[] = [];

  // First pass: preferred fields
  for (const s of allSeries) {
    const preferred = Object.values(SERIES_PRIORITY).flat();
    if (preferred.includes(s.field) && !seen.has(s.source_id + s.field)) {
      result.push(s);
      seen.add(s.source_id + s.field);
    }
  }

  // Second pass: anything not yet included (e.g. unknown categories)
  for (const s of allSeries) {
    const key = s.source_id + s.field;
    if (!seen.has(key) && s.field === "power_w") {
      result.push(s);
      seen.add(key);
    }
  }

  return result;
}

export default function History() {
  const [range, setRange] = useState<Range>("24h");
  const { data, loading, error } = useHistory(range);

  const series = data ? pickSeries(data.series) : [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">History</h1>

        {/* Range selector */}
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                range === r
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-slate-400 text-sm">Loading…</div>
      )}

      {error && (
        <div className="text-red-400 text-sm">{error}</div>
      )}

      {!loading && series.length === 0 && (
        <div className="text-slate-500 text-center py-12">
          No data for this range yet.
        </div>
      )}

      {series.map((s, idx) => {
        const color = SERIES_COLORS[idx % SERIES_COLORS.length];
        const chartData = s.points.map((p) => ({
          time: fmtTime(p.timestamp, range),
          value: p.value,
        }));

        return (
          <div key={`${s.source_id}-${s.field}`} className="bg-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium text-slate-100">
                {s.source_id}
                <span className="text-slate-500 font-normal ml-2 text-sm">
                  {s.field}
                </span>
              </span>
            </div>

            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id={`grad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10, fill: "#64748b" }}
                  tickLine={false}
                  interval="preserveStartEnd"
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
                  formatter={(v: number) => [fmtPower(v), s.field]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#grad-${idx})`}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
