import { useEffect, useState } from "react";
import { ErrorBox, LineChart, List } from "../components/common";
import { fmt } from "../lib/labels";
import { api } from "../services/api";
import type { Location, SatelliteData, SoilInfo } from "../types";

/** Plain-language soil error: the API's own sentence where it gives one, never a raw HTTP dump. */
function soilMessage(e: unknown): string {
  const text = e instanceof Error ? e.message : String(e);
  const detail = text.match(/"detail"\s*:\s*"([^"]+)"/)?.[1];
  if (detail) return detail;
  if (text.startsWith("503") || /fetch|network/i.test(text))
    return "The SoilGrids soil service is not responding right now. Try again in a few minutes.";
  return "Soil data could not be loaded. Try again in a few minutes.";
}

export default function AreaView({ location }: { location: Location }) {
  const [soil, setSoil] = useState<SoilInfo | null>(null);
  const [sat, setSat] = useState<SatelliteData | null>(null);
  const [soilErr, setSoilErr] = useState<string | null>(null);
  const [satErr, setSatErr] = useState<string | null>(null);
  const [soilLoading, setSoilLoading] = useState(false);
  const [satLoading, setSatLoading] = useState(false);
  const [soilAttempt, setSoilAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setSoil(null);
    setSoilErr(null);
    // Wait until typing stops: SoilGrids allows only ~5 requests a minute.
    const timer = setTimeout(() => {
      setSoilLoading(true);
      api
        .soil(location.latitude, location.longitude)
        .then((s) => live && setSoil(s))
        .catch((e) => live && setSoilErr(soilMessage(e)))
        .finally(() => live && setSoilLoading(false));
    }, 700);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [location.latitude, location.longitude, soilAttempt]);

  useEffect(() => {
    let live = true;
    setSat(null);
    setSatErr(null);
    const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
    const timer = setTimeout(() => {
      setSatLoading(true);
      api
        .satellite(location.latitude, location.longitude)
        .then((t) => live && setSat(t))
        .catch((e) => live && setSatErr(msg(e).startsWith("404") ? "No satellite data here (Pakistan only)." : msg(e)))
        .finally(() => live && setSatLoading(false));
    }, 700);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [location.latitude, location.longitude]);

  return (
    <>
      {satLoading && <p className="muted">Loading satellite data…</p>}

      <section className="card">
        <h2>Soil</h2>
        {soilLoading && <p className="muted small">Loading SoilGrids (can take up to a minute)…</p>}
        {soilErr && (
          <div className="note small">
            <p style={{ margin: "0 0 8px" }}>{soilErr}</p>
            <button className="secondary small-btn" onClick={() => setSoilAttempt((n) => n + 1)} disabled={soilLoading}>
              Try again
            </button>
          </div>
        )}
        {soil && (
          <>
            <p>
              Texture: <strong>{soil.texture_class ?? "unknown"}</strong> · topsoil 0-30 cm: clay{" "}
              {fmt(soil.topsoil_0_30cm.clay_pct)}%, sand {fmt(soil.topsoil_0_30cm.sand_pct)}%, organic carbon{" "}
              {fmt(soil.topsoil_0_30cm.organic_carbon_g_kg, 1)} g/kg, pH {fmt(soil.topsoil_0_30cm.ph_h2o, 1)}
            </p>
            <p className="muted small">
              {soil.source} ({soil.data_source}
              {soil.from_sample ? ", saved sample" : ""}
              {soil.distance_km > 0 ? `, ${fmt(soil.distance_km, 1)} km from your point` : ""}).
            </p>
            <List items={soil.notes} />
          </>
        )}
      </section>

      <ErrorBox error={satErr} />
      {sat && (
        <>
          {!sat.district && (
            <p className="note">
              Green cover and soil moisture are saved samples for the four demo districts only; pick one to see them.
            </p>
          )}
          {sat.district && (
          <>
          <section className="card">
            <h2>Green cover (MODIS NDVI) · {sat.district}</h2>
            <p className="muted small">
              Higher = more living green plants. Cloudy readings are left as gaps. June 2025 - May 2026.
            </p>
            <LineChart unit="NDVI" points={sat.ndvi.map((p) => ({ x: p.date, y: p.usable ? p.ndvi : null }))} />
          </section>

          <section className="card">
            <h2>Soil moisture (SMAP L4)</h2>
            <p className="muted small">Root zone, m³ of water per m³ of soil (model analysis, 9 km).</p>
            <LineChart
              unit="m³/m³"
              color="var(--chart-2)"
              points={sat.soil_moisture.map((p) => ({ x: p.date, y: p.rootzone_m3m3 }))}
            />
          </section>
          </>
          )}

          {sat.grace && (
            <section className="card">
              <h2>Regional water storage (GRACE)</h2>
              <p>
                Trend:{" "}
                <strong>
                  {sat.grace.trend_cm_per_year == null ? "—" : `${fmt(sat.grace.trend_cm_per_year, 2)} cm per year`}
                </strong>{" "}
                since {sat.grace.series[0]?.date.slice(0, 4)}
                {sat.grace.recent_trend_cm_per_year != null &&
                  ` (${fmt(sat.grace.recent_trend_cm_per_year, 2)} cm/yr over the last ${sat.grace.recent_trend_years} years)`}
                {sat.grace.latest && (
                  <span className="muted small">
                    {" "}
                    · latest {sat.grace.latest.date.slice(0, 7)}: {fmt(sat.grace.latest.lwe_cm, 1)} ±{" "}
                    {fmt(sat.grace.latest.uncertainty_cm, 1)} cm vs 2004-2009 average
                  </span>
                )}
              </p>
              <LineChart
                unit="cm"
                color="var(--chart-3)"
                zeroLine
                points={sat.grace.series.map((p) => ({ x: p.date, y: p.lwe_cm }))}
              />
            </section>
          )}

          <section className="card">
            <h3>About these data</h3>
            <List items={sat.limitations} />
            <List items={Object.values(sat.sources)} />
          </section>
        </>
      )}
    </>
  );
}
