import AlertsCard from "../components/dashboard/AlertsCard";
import RotationCard from "../components/dashboard/RotationCard";
import { ClimateYearChart } from "../components/dashboard/visuals";
import WeatherTile from "../components/dashboard/WeatherTile";
import { ErrorBox, RainSourceNote } from "../components/common";
import type { DashboardData } from "../hooks/useDashboardData";
import { type MonthPoint, monthlySeries, recentFigures } from "../lib/climateSummary";
import { buildAlerts } from "../lib/dashboardAlerts";
import { DASHBOARD_FARM_ACRES } from "../lib/dashboardRotations";
import { ILLUSTRATIONS } from "../lib/illustrations";
import { fmt, fmtDate } from "../lib/labels";
import type { Navigate } from "../lib/pages";
import { rotationCards } from "../lib/rotationCards";

function greeting(now = new Date()) {
  const h = now.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

/** Where `value` sits between this farm's lowest and highest month of the past year (0-1). */
function placeInYear(value: number | null | undefined, months: MonthPoint[], pick: (m: MonthPoint) => number | null) {
  const xs = months.map(pick).filter((x): x is number => x != null);
  if (value == null || xs.length < 3) return { fraction: null, min: null, max: null };
  const min = Math.min(...xs);
  const max = Math.max(...xs);
  return { fraction: max === min ? 0.5 : (value - min) / (max - min), min, max };
}

export default function DashboardView({
  data,
  placeName,
  navigate,
  onRotationDetails,
}: {
  data: DashboardData;
  placeName: string;
  navigate: Navigate;
  onRotationDetails: () => void;
}) {
  const { weather, comparison, rotations } = data;
  const obs = weather.data?.observations ?? [];
  const latest = weather.data?.data_note.latest_observation_date ?? null;
  const recent = weather.data ? recentFigures(obs, latest) : null;
  const months = weather.data ? monthlySeries(obs, latest) : [];
  const sent = [rotations.current, ...rotations.alternatives];
  const cards = comparison.data ? rotationCards(comparison.data, sent) : null;
  const alerts = buildAlerts({ recent, year: null, cards, current: rotations.current });
  const waters = (cards ?? []).map((c) => c.waterM3PerAcreYear).filter((x): x is number => x != null);
  const maxWater = waters.length ? Math.max(...waters) : null;

  const temp = placeInYear(recent?.avgTempC, months, (m) => m.avgTempC);
  const rain = placeInYear(recent?.rainTotalMm, months, (m) => m.rainMm);
  const hum = placeInYear(recent?.avgHumidityPct, months, (m) => m.avgHumidityPct);
  const sun = placeInYear(recent?.avgSolarKwh, months, (m) => m.avgSolarKwh);
  const ends = (r: { min: number | null; max: number | null }, unit: string, d = 0) =>
    [r.min == null ? "" : `${fmt(r.min, d)}${unit}`, r.max == null ? "" : `${fmt(r.max, d)}${unit}`] as const;

  return (
    <div className="farmer-dash">
      <section className="hero dcard">
        <img className="hero-img" src={ILLUSTRATIONS.farmer} alt="" />
        <div className="hero-text">
          <h1>{greeting()}, Farmer!</h1>
          <p className="hero-place">
            <img src={ILLUSTRATIONS.pin} alt="" /> {placeName}
          </p>
          <button className="secondary" onClick={() => navigate("farm")}>
            Change my farm
          </button>
        </div>
        <img className="hero-tractor" src={ILLUSTRATIONS.tractor} alt="" />
      </section>

      {weather.error && (
        <div className="dcard pad">
          <ErrorBox error="We could not load the NASA weather for your farm. Check your internet and try again." />
          <button className="secondary" style={{ marginTop: 10 }} onClick={data.reload}>
            Try again
          </button>
        </div>
      )}

      <section aria-labelledby="weather-h">
        <div className="dash-head">
          <h2 id="weather-h">Weather on your farm</h2>
          <p>
            Last 30 days{latest ? `, up to ${fmtDate(latest)}` : ""}. The meter shows how it compares with the past 12
            months.
          </p>
        </div>
        <div className="weather-grid">
          <WeatherTile
            image={ILLUSTRATIONS.thermometer}
            title="Temperature"
            value={recent?.avgTempC == null ? null : fmt(recent.avgTempC, 1)}
            unit="°C"
            fraction={temp.fraction}
            color="#e0672a"
            low={ends(temp, "°")[0]}
            high={ends(temp, "°")[1]}
            loading={weather.loading}
          />
          <WeatherTile
            image={ILLUSTRATIONS.rain}
            title="Rain"
            value={recent?.rainTotalMm == null ? null : fmt(recent.rainTotalMm)}
            unit="mm"
            fraction={rain.fraction}
            color="#2b67b8"
            low={ends(rain, " mm")[0]}
            high={ends(rain, " mm")[1]}
            loading={weather.loading}
          />
          <WeatherTile
            image={ILLUSTRATIONS.droplet}
            title="Air moisture"
            value={recent?.avgHumidityPct == null ? null : fmt(recent.avgHumidityPct)}
            unit="%"
            fraction={hum.fraction}
            color="#1c9aa8"
            low={ends(hum, "%")[0]}
            high={ends(hum, "%")[1]}
            loading={weather.loading}
          />
          <WeatherTile
            image={ILLUSTRATIONS.sun}
            title="Sunshine"
            value={recent?.avgSolarKwh == null ? null : fmt(recent.avgSolarKwh, 1)}
            unit="kWh/m²"
            fraction={sun.fraction}
            color="#d49a00"
            low={ends(sun, "", 1)[0]}
            high={ends(sun, "", 1)[1]}
            loading={weather.loading}
          />
        </div>
      </section>

      <section aria-labelledby="plans-h">
        <div className="dash-head">
          <h2 id="plans-h">Which crop plan suits your farm?</h2>
          <p>Your crops now and two other plans, checked with NASA weather for a {DASHBOARD_FARM_ACRES}-acre farm.</p>
        </div>
        {comparison.loading && (
          <div className="plan-grid">
            {[0, 1, 2].map((i) => (
              <div key={i} className="dcard plan-card">
                <div className="skeleton" style={{ height: 70, width: "70%" }} />
                <div className="skeleton" style={{ height: 110, width: 110, borderRadius: "50%", marginTop: 16 }} />
                <p className="muted">Checking crop plans… this can take a minute.</p>
              </div>
            ))}
          </div>
        )}
        {comparison.error && (
          <div className="dcard pad">
            <ErrorBox error="We could not compare the crop plans right now. Please try again." />
            <button className="secondary" style={{ marginTop: 10 }} onClick={data.reload}>
              Try again
            </button>
          </div>
        )}
        {cards && (
          <div className="plan-grid">
            {cards.map((c) => (
              <RotationCard key={c.name} card={c} maxWater={maxWater} onDetails={onRotationDetails} />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="todo-h">
        <div className="dash-head">
          <h2 id="todo-h">What to do now</h2>
        </div>
        <AlertsCard alerts={alerts} loading={weather.loading || comparison.loading} />
      </section>

      <section aria-labelledby="year-h" className="dcard pad">
        <div className="dash-head inline">
          <h2 id="year-h">Rain and temperature this year</h2>
          <div className="chart-legend-big">
            <span>
              <i className="key rain" /> Rain (mm)
            </span>
            <span>
              <i className="key temp" /> Temperature (°C)
            </span>
          </div>
        </div>
        {weather.loading ? (
          <div className="skeleton chart-skeleton" />
        ) : (
          <ClimateYearChart months={months} />
        )}
        <button className="link-btn" onClick={() => navigate("climate")}>
          See more weather →
        </button>
      </section>

      <details className="about-data">
        <summary>About this information</summary>
        <p className="small">
          Weather comes from NASA satellites and models for your area (not just your field) and shows the past, not a
          forecast. Crop plan scores (0–100) compare these plans with each other. When some information is missing, that
          part is left out and the score is marked as less sure. Always check your choice with a local farm advisor.
        </p>
        <RainSourceNote rain={comparison.data?.rain_source} />
      </details>
    </div>
  );
}
