import { DataNoteLine, List, RainSourceNote } from "../components/common";
import type { DashboardData } from "../hooks/useDashboardData";
import { recentFigures, yearFigures } from "../lib/climateSummary";
import { buildAlerts } from "../lib/dashboardAlerts";
import { DASHBOARD_FARM_ACRES } from "../lib/dashboardRotations";
import { cropLabel, fmt, fmtDate } from "../lib/labels";
import { rotationCards } from "../lib/rotationCards";

/** A printable one-page summary of what the dashboard shows. "Save as PDF" comes from the browser's print dialog. */
export default function ReportsView({ data, placeName }: { data: DashboardData; placeName: string }) {
  const { weather, comparison, rotations } = data;
  const obs = weather.data?.observations ?? [];
  const latest = weather.data?.data_note.latest_observation_date ?? null;
  const recent = weather.data ? recentFigures(obs, latest) : null;
  const year = weather.data ? yearFigures(obs, latest) : null;
  const sent = [rotations.current, ...rotations.alternatives];
  const cards = comparison.data ? rotationCards(comparison.data, sent) : null;
  const alerts = buildAlerts({ recent, year, cards, current: rotations.current });
  const ready = !weather.loading && !comparison.loading;

  return (
    <>
      <div className="welcome">
        <div>
          <h1>My report</h1>
          <p className="sub">A summary of your farm's climate and rotation comparison to print or save as PDF.</p>
        </div>
        <button className="primary no-print" onClick={() => window.print()} disabled={!ready}>
          {ready ? "Print or save as PDF" : "Loading…"}
        </button>
      </div>

      <section className="card report">
        <h2>Crop-Watch AI farm report</h2>
        <p>
          <strong>Farm:</strong> {placeName} · {DASHBOARD_FARM_ACRES} acres (assumed) · Prepared {fmtDate(new Date().toISOString().slice(0, 10))}
        </p>

        <h3>Climate around the farm (NASA POWER, historical)</h3>
        {year && recent ? (
          <table>
            <thead>
              <tr>
                <th></th>
                <th className="num">Last 30 days</th>
                <th className="num">Past 12 months</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Average temperature</td>
                <td className="num">{fmt(recent.avgTempC, 1)} °C</td>
                <td className="num">{fmt(year.avgTempC, 1)} °C</td>
              </tr>
              <tr>
                <td>Rainfall (total)</td>
                <td className="num">{fmt(recent.rainTotalMm)} mm</td>
                <td className="num">{fmt(year.rainTotalMm)} mm</td>
              </tr>
              <tr>
                <td>Relative humidity</td>
                <td className="num">{fmt(recent.avgHumidityPct)} %</td>
                <td className="num">{fmt(year.avgHumidityPct)} %</td>
              </tr>
              <tr>
                <td>Solar radiation</td>
                <td className="num">{fmt(recent.avgSolarKwh, 1)} kWh/m²/day</td>
                <td className="num">{fmt(year.avgSolarKwh, 1)} kWh/m²/day</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p className="muted">{weather.loading ? "Loading…" : "Climate data is not available."}</p>
        )}

        <h3>Rotations compared</h3>
        {cards ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Option</th>
                  <th>Seasons used</th>
                  <th className="num">Suitability</th>
                  <th className="num">Water (m³/acre/yr)</th>
                  <th className="num">Climate</th>
                  <th className="num">Soil health</th>
                </tr>
              </thead>
              <tbody>
                {cards.map((c, i) => (
                  <tr key={c.name}>
                    <td>
                      <strong>
                        {c.option}. {c.name}
                      </strong>
                      {c.isCurrent && <div className="muted small">Current</div>}
                    </td>
                    <td className="small">
                      {sent[i].seasons.map((s) => `${cropLabel(s.crop)} ${fmtDate(s.sowing_date)}`).join(" → ")}
                    </td>
                    <td className="num">
                      {c.suitability ?? "—"}
                      {c.partial && " (partial)"}
                    </td>
                    <td className="num">{fmt(c.waterM3PerAcreYear)}</td>
                    <td className="num">{c.climate ?? "—"}</td>
                    <td className="num">{c.soil ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">{comparison.loading ? "Loading…" : "The comparison is not available."}</p>
        )}
        <RainSourceNote rain={comparison.data?.rain_source} />
        {cards?.some((c) => c.partialNote) && (
          <List items={cards.filter((c) => c.partialNote).map((c) => `Option ${c.option}: ${c.partialNote}`)} />
        )}

        <h3>Things to check</h3>
        <List items={alerts.map((a) => `${a.title}: ${a.text}`)} empty="Nothing to check." />

        {comparison.data && (
          <>
            <h3>Limits of this report</h3>
            <List items={comparison.data.limitations} />
          </>
        )}
        <DataNoteLine note={weather.data?.data_note ?? null} />
        <p className="muted small">
          Scores are relative to the three options (0–100, equal weights) and use past seasons' weather, not a forecast.
          Confirm crop choices with local agricultural experts.
        </p>
      </section>
    </>
  );
}
