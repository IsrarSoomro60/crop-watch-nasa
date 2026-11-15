import type { ReactNode } from "react";
import { DataNoteLine, ErrorBox, LineChart } from "../components/common";
import type { Loadable } from "../hooks/useDashboardData";
import { monthlySeries, yearFigures } from "../lib/climateSummary";
import { fmt } from "../lib/labels";
import type { EnvironmentalData, HistoryResult, Location } from "../types";
import QuickCheckView from "./QuickCheckView";
import SeasonHistory from "../components/SeasonHistory";

const TRENDS = [
  {
    id: "trend-temp",
    title: "Temperature",
    help: "Average of day and night temperature for each month.",
    unit: "°C",
    digits: 0,
    color: "var(--chart-1)",
    pick: "avgTempC",
  },
  {
    id: "trend-rain",
    title: "Rainfall",
    help: "Total rain in each month (NASA POWER corrected precipitation).",
    unit: "mm per month",
    digits: 0,
    color: "var(--chart-2)",
    pick: "rainMm",
  },
  {
    id: "trend-humidity",
    title: "Humidity",
    help: "Average relative humidity at 2 m. Long humid spells can favour crop diseases.",
    unit: "%",
    digits: 0,
    color: "var(--chart-2)",
    pick: "avgHumidityPct",
  },
  {
    id: "trend-solar",
    title: "Solar radiation",
    help: "Average sunlight energy reaching the ground each day, all-sky.",
    unit: "kWh/m²/day",
    digits: 1,
    color: "var(--chart-3)",
    pick: "avgSolarKwh",
  },
] as const;

export default function ClimateInsightsView({
  weather,
  location,
  urdu,
  header,
  history,
  rotationName,
}: {
  weather: Loadable<EnvironmentalData>;
  history: Loadable<HistoryResult>;
  rotationName: string;
  location: Location;
  urdu: boolean;
  header?: ReactNode; // e.g. the farm line, shown under the title
}) {
  const obs = weather.data?.observations ?? [];
  const latest = weather.data?.data_note.latest_observation_date ?? null;
  const months = weather.data ? monthlySeries(obs, latest) : [];
  const year = weather.data ? yearFigures(obs, latest) : null;

  return (
    <>
      <div className="welcome">
        <div>
          <h1>Climate insights</h1>
          <p className="sub">
            Past 12 months of NASA POWER data around your farm. This is history, not a weather forecast.
          </p>
          {header}
        </div>
      </div>

      <h2 className="page-section">This week's crop risk</h2>
      <QuickCheckView location={location} urdu={urdu} />

      <SeasonHistory history={history} rotationName={rotationName} />

      <h2 className="page-section">Last 12 months</h2>
      {weather.loading && <p className="muted">Loading 12 months of NASA POWER data…</p>}
      <ErrorBox error={weather.error} />
      {weather.data && (
        <>
          <div className="trend-grid">
            {TRENDS.map((t) => {
              const total = t.pick === "rainMm" ? year?.rainTotalMm : null;
              return (
                <section key={t.id} id={t.id} className="card trend">
                  <h2>{t.title}</h2>
                  <p className="muted small">
                    {t.help}
                    {total != null && ` 12-month total: ${fmt(total)} mm.`}
                  </p>
                  <LineChart
                    unit={t.unit}
                    color={t.color}
                    digits={t.digits}
                    points={months.map((m) => ({ x: m.month, y: m[t.pick] }))}
                  />
                </section>
              );
            })}
          </div>
          <section className="card">
            <DataNoteLine note={weather.data.data_note} />
          </section>
        </>
      )}
    </>
  );
}
