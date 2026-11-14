import { useEffect, useState } from "react";
import { ErrorBox, LineChart, List } from "../components/common";
import { fmt } from "../lib/labels";
import { api } from "../services/api";
import type { Location, SatelliteData, SoilInfo } from "../types";

export default function AreaView({ location }: { location: Location }) {
  const [soil, setSoil] = useState<SoilInfo | null>(null);
  const [sat, setSat] = useState<SatelliteData | null>(null);
  const [soilErr, setSoilErr] = useState<string | null>(null);
  const [satErr, setSatErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setSoil(null);
    setSat(null);
    setSoilErr(null);
    setSatErr(null);
    const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
    Promise.allSettled([api.soil(location.latitude, location.longitude), api.satellite(location.latitude, location.longitude)])
      .then(([s, t]) => {
        if (!live) return;
        if (s.status === "fulfilled") setSoil(s.value);
        else setSoilErr(msg(s.reason));
        if (t.status === "fulfilled") setSat(t.value);
        else setSatErr(msg(t.reason).startsWith("404") ? "No saved satellite sample here (demo districts only)." : msg(t.reason));
      })
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [location.latitude, location.longitude]);

  return (
    <>
      {loading && <p className="muted">Loading soil and satellite data…</p>}

      <section className="card">
        <h2>Soil</h2>
        <ErrorBox error={soilErr} />
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

          {sat.grace && (
            <section className="card">
              <h2>Regional water storage (GRACE)</h2>
              <p>
                Trend:{" "}
                <strong>
                  {sat.grace.trend_cm_per_year == null ? "—" : `${fmt(sat.grace.trend_cm_per_year, 2)} cm per year`}
                </strong>
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
