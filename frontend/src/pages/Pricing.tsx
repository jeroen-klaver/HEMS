/**
 * Pricing page — today's + tomorrow's hourly electricity prices + PV forecast.
 */

import { useEffect, useState } from "react";
import ForecastChart from "../components/ForecastChart";
import PriceChart from "../components/PriceChart";
import { useLiveData } from "../hooks/useLiveData";
import type { ForecastResponse, PricingResponse } from "../types";

async function fetchPricing(day: "today" | "tomorrow"): Promise<PricingResponse> {
  const res = await fetch(`/api/v1/pricing/${day}`);
  return res.json() as Promise<PricingResponse>;
}

async function fetchForecast(): Promise<ForecastResponse> {
  const res = await fetch("/api/v1/forecast");
  return res.json() as Promise<ForecastResponse>;
}

export default function Pricing() {
  const { data: liveData } = useLiveData();
  const [today, setToday] = useState<PricingResponse | null>(null);
  const [tomorrow, setTomorrow] = useState<PricingResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([
      fetchPricing("today"),
      fetchPricing("tomorrow").catch(() => null),
      fetchForecast().catch(() => null),
    ]).then(([t, tom, f]) => {
      setToday(t);
      setTomorrow(tom);
      setForecast(f);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="text-slate-400">Loading…</div>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-white">Pricing & Forecast</h1>

      {today && (
        <PriceChart
          prices={today.prices}
          average={today.average_eur_kwh}
          currentPrice={liveData?.current_price_eur_kwh ?? null}
        />
      )}

      {tomorrow && tomorrow.prices.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
            Tomorrow
          </h2>
          <PriceChart
            prices={tomorrow.prices}
            average={tomorrow.average_eur_kwh}
            currentPrice={null}
            highlightCurrent={false}
          />
        </div>
      )}

      {!tomorrow?.prices.length && (
        <div className="text-slate-500 text-sm">
          Tomorrow's prices not yet published (available after ~13:00 CET).
        </div>
      )}

      {forecast && forecast.points.length > 0 && (() => {
        const todayStr = new Date().toLocaleDateString("sv"); // "2026-03-08"
        const tomorrowStr = new Date(Date.now() + 86400000).toLocaleDateString("sv");
        const todayKwh = forecast.points
          .filter((p) => new Date(p.hour).toLocaleDateString("sv") === todayStr)
          .reduce((s, p) => s + p.power_w / 1000, 0);
        const tomorrowKwh = forecast.points
          .filter((p) => new Date(p.hour).toLocaleDateString("sv") === tomorrowStr)
          .reduce((s, p) => s + p.power_w / 1000, 0);
        return (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-1">Verwacht vandaag</div>
                <div className="text-2xl font-bold text-yellow-400">{todayKwh.toFixed(1)} kWh</div>
              </div>
              <div className="bg-slate-800 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-1">Verwacht morgen</div>
                <div className="text-2xl font-bold text-yellow-400">
                  {tomorrowKwh > 0 ? `${tomorrowKwh.toFixed(1)} kWh` : "—"}
                </div>
              </div>
            </div>
            <ForecastChart
              points={forecast.points}
              systemKwp={forecast.system_kwp}
            />
          </>
        );
      })()}
    </div>
  );
}
