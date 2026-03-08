/**
 * PriceChart — 24h hourly electricity price bar chart.
 *
 * Bars are coloured:
 *   green  = below daily average (cheap)
 *   yellow = within 25% of average
 *   red    = top 25% (expensive)
 *
 * Current hour is highlighted with a white border.
 */

import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "../types";

interface Props {
  prices: PricePoint[];
  average: number | null;
  currentPrice: number | null;
  highlightCurrent?: boolean;
}

function barColor(price: number, avg: number): string {
  if (price > avg * 1.25) return "#ef4444"; // red — expensive
  if (price < avg * 0.75) return "#22c55e"; // green — cheap
  return "#eab308";                          // yellow — average
}

function fmtHour(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function PriceChart({ prices, average, currentPrice, highlightCurrent = true }: Props) {
  if (prices.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 text-slate-400 text-sm">
        No price data available.
      </div>
    );
  }

  const avg = average ?? prices.reduce((s, p) => s + p.price_eur_kwh, 0) / prices.length;
  const nowHour = new Date().getHours();

  const data = prices.map((p) => ({
    hour: fmtHour(p.hour),
    hourIndex: new Date(p.hour).getHours(),
    price: p.price_eur_kwh,
  }));

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-slate-100">Electricity price</span>
        {currentPrice != null && (
          <span className="text-lg font-bold text-white">
            €{currentPrice.toFixed(3)}/kWh
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
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
            tickFormatter={(v: number) => `€${v.toFixed(2)}`}
          />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            itemStyle={{ color: "#f1f5f9" }}
            formatter={(value: number) => [`€${value.toFixed(4)}/kWh`, "Price"]}
          />
          <ReferenceLine
            y={avg}
            stroke="#475569"
            strokeDasharray="4 4"
            label={{ value: "avg", fill: "#475569", fontSize: 10 }}
          />
          <Bar dataKey="price" radius={[3, 3, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.hour}
                fill={barColor(entry.price, avg)}
                stroke={highlightCurrent && entry.hourIndex === nowHour ? "#ffffff" : "transparent"}
                strokeWidth={2}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
