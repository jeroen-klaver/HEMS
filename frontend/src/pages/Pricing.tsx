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

      {forecast && forecast.points.length > 0 && (
        <ForecastChart
          points={forecast.points}
          systemKwp={forecast.system_kwp}
        />
      )}
    </div>
  );
}
