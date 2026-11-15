import { useEffect, useState } from "react";
import { ErrorBox, LineChart, List } from "../components/common";
import { ILLUSTRATIONS } from "../lib/illustrations";
import { fmt } from "../lib/labels";
import { api } from "../services/api";
import type { Location, SatelliteData, SoilInfo } from "../types";

const capitalise = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** Standard pH classes (USDA): below 6.5 acidic, 6.5-7.5 neutral, above 7.5 alkaline. */
function phWord(ph: number | null): string {
  if (ph == null) return "unknown";
  return ph < 6.5 ? "acidic" : ph <= 7.5 ? "neutral" : "alkaline";
}

/** Section heading with a picture, like the steps on the other pages. */
function StepHead({ image, title, text }: { image: string; title: string; text: string }) {
  return (
    <div className="step-head">
      <img className="step-img" src={image} alt="" />
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
    </div>
  );
}

/** Clay / silt / sand as one coloured bar: what the soil is made of. */
function SoilMix({ clay, silt, sand }: { clay: number | null; silt: number | null; sand: number | null }) {
  if (clay == null || sand == null) return null;
  const siltPct = silt ?? Math.max(0, 100 - clay - sand);
  const parts = [
    { name: "Clay", pct: clay, cls: "clay", note: "holds water" },
    { name: "Silt", pct: siltPct, cls: "silt", note: "fine, fertile" },
    { name: "Sand", pct: sand, cls: "sand", note: "drains fast" },
  ];
  const total = parts.reduce((t, p) => t + p.pct, 0) || 1;
  return (
    <div className="soil-mix">
      <div className="soil-mix-bar" role="img" aria-label={parts.map((p) => `${p.name} ${fmt(p.pct)}%`).join(", ")}>
        {parts.map((p) => (
          <span key={p.name} className={p.cls} style={{ width: `${(p.pct / total) * 100}%` }} />
        ))}
      </div>
      <div className="soil-mix-keys">
        {parts.map((p) => (
          <span key={p.name}>
            <i className={p.cls} /> <strong>{p.name} {fmt(p.pct)}%</strong> <small>{p.note}</small>
          </span>
        ))}
      </div>
    </div>
  );
}

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

  const top = soil?.topsoil_0_30cm;
  const grace = sat?.grace ?? null;
  const trend = grace?.recent_trend_cm_per_year ?? grace?.trend_cm_per_year ?? null;

  return (
    <div className="farm-sections">
      <section>
        <StepHead image={ILLUSTRATIONS.plant} title="Your soil" text="From SoilGrids soil maps for the top 30 cm (not a soil test)." />
        <div className="dcard pad soil-card">
          {soilLoading && <p className="muted">Looking up your soil… this can take up to a minute.</p>}
          {soilErr && (
            <div className="note">
              <p style={{ margin: "0 0 8px" }}>{soilErr}</p>
              <button className="secondary" onClick={() => setSoilAttempt((n) => n + 1)} disabled={soilLoading}>
                Try again
              </button>
            </div>
          )}
          {soil && top && (
            <>
              <div className="soil-type">
                <span>Soil type</span>
                <strong>{soil.texture_class ? capitalise(soil.texture_class) : "Unknown"}</strong>
              </div>
              <SoilMix clay={top.clay_pct} silt={top.silt_pct} sand={top.sand_pct} />
              <div className="soil-facts">
                <div className="soil-fact">
                  <span>Organic matter (carbon)</span>
                  <strong>{fmt(top.organic_carbon_g_kg, 1)} g/kg</strong>
                  <small>More means healthier, richer soil.</small>
                </div>
                <div className="soil-fact">
                  <span>pH</span>
                  <strong>
                    {fmt(top.ph_h2o, 1)} · {phWord(top.ph_h2o)}
                  </strong>
                  <small>Below 6.5 acidic, 6.5–7.5 neutral, above 7.5 alkaline.</small>
                </div>
              </div>
              <details className="layer-more">
                <summary>More about this soil data</summary>
                <p className="small">
                  {soil.source} ({soil.data_source}
                  {soil.from_sample ? ", saved sample" : ""}
                  {soil.distance_km > 0 ? `, ${fmt(soil.distance_km, 1)} km from your point` : ""}).
                </p>
                <List items={soil.notes} />
              </details>
            </>
          )}
        </div>
      </section>

      {satLoading && <p className="muted">Loading satellite data…</p>}
      <ErrorBox error={satErr} />
      {sat && (
        <section>
          <StepHead image={ILLUSTRATIONS.climate} title="How your area changed this year" text="Seen by NASA satellites." />
          {!sat.district ? (
            <p className="note">
              These yearly charts are saved for the four sample districts only (Multan, Bahawalpur, Larkana, Hyderabad).
              Pick one of them to see them.
            </p>
          ) : (
            <div className="farm-charts">
              <div className="dcard pad">
                <div className="chart-title">
                  <img src={ILLUSTRATIONS.plant} alt="" />
                  <div>
                    <h3>Green crops</h3>
                    <p>Higher = more growing plants. Low parts are bare or harvested fields.</p>
                  </div>
                </div>
                <LineChart unit="green cover (NDVI)" digits={2} points={sat.ndvi.map((p) => ({ x: p.date, y: p.usable ? p.ndvi : null }))} />
              </div>
              <div className="dcard pad">
                <div className="chart-title">
                  <img src={ILLUSTRATIONS.droplet} alt="" />
                  <div>
                    <h3>Water in the soil</h3>
                    <p>Higher = wetter soil around the roots.</p>
                  </div>
                </div>
                <LineChart
                  unit="m³ water per m³ soil"
                  color="var(--chart-2)"
                  digits={2}
                  points={sat.soil_moisture.map((p) => ({ x: p.date, y: p.rootzone_m3m3 }))}
                />
              </div>
            </div>
          )}

          {grace && (
            <div className="dcard pad grace-card">
              <div className="chart-title">
                <img src={ILLUSTRATIONS.droplet} alt="" />
                <div>
                  <h3>Underground water in your region</h3>
                  {trend != null && (
                    <p className={`grace-word ${trend < 0 ? "down" : "up"}`}>
                      {trend < 0 ? "↓ Going down" : "↑ Going up"}: about {fmt(Math.abs(trend), 1)} cm of water{" "}
                      {trend < 0 ? "lost" : "gained"} each year
                      {grace.recent_trend_years ? ` over the last ${grace.recent_trend_years} years` : ""}.
                    </p>
                  )}
                </div>
              </div>
              <LineChart
                unit="cm of water vs 2004-2009"
                color="var(--chart-3)"
                zeroLine
                digits={0}
                points={grace.series.map((p) => ({ x: p.date, y: p.lwe_cm }))}
              />
              <p className="muted small">
                From NASA GRACE satellites, which weigh the water in a large region (about 300 km), not your own well.
              </p>
            </div>
          )}

          <details className="layer-more">
            <summary>About these satellite data</summary>
            <List items={sat.limitations} />
            <List items={Object.values(sat.sources)} />
          </details>
        </section>
      )}
    </div>
  );
}
