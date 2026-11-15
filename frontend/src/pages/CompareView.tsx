import { useEffect, useMemo, useState } from "react";
import { AdviceList, DataNoteLine, ErrorBox, LevelBadge, List, RainSourceNote } from "../components/common";
import RotationCard from "../components/dashboard/RotationCard";
import FieldCalendar from "../components/FieldCalendar";
import { useRotationComparison } from "../hooks/useRotationComparison";
import { CROP_IMAGE, ILLUSTRATIONS } from "../lib/illustrations";
import { rotationCards } from "../lib/rotationCards";
import {
  CROPS,
  HA_PER_ACRE,
  RISK_LABEL,
  acresToHa,
  cropLabel,
  fmt,
  haToAcres,
  presetRotations,
} from "../lib/labels";
import type {
  CropEconomics,
  CropName,
  CropSeason,
  DimensionScores,
  Location,
  Priorities,
  RankedRotation,
  RiskType,
  ClimateScenario,
  Rotation,
} from "../types";

const DIMENSIONS: { key: keyof Priorities & keyof DimensionScores; label: string }[] = [
  { key: "soil_health", label: "Soil health" },
  { key: "water", label: "Water saving" },
  { key: "income", label: "Income" },
  { key: "resilience", label: "Climate resilience" },
];

/** Element id of a plan's full-details card, so "See details" can scroll to it. */
const detailId = (name: string) => `detail-${name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;

/** What the farmer types: per acre, as farmers in Pakistan usually count land. */
interface EconInput {
  yield_t_acre?: number | null;
  price_per_t?: number | null;
  cost_per_acre?: number | null;
}

/** The API takes per-hectare values; an acre is 0.4047 ha, so per-acre figures divide by that. */
function econToApi(v: EconInput | undefined): CropEconomics {
  const perHa = (x: number | null | undefined) => (x == null ? null : x / HA_PER_ACRE);
  return {
    yield_t_ha: perHa(v?.yield_t_acre),
    price_per_t: v?.price_per_t ?? null,
    cost_per_ha: perHa(v?.cost_per_acre),
    currency: "PKR",
  };
}

/** The farmer's own limits; rotations that break them are flagged, not hidden or re-scored. */
interface FarmLimits {
  waterM3PerAcreYear: number | null;
  excluded: CropName[]; // crops the farmer can't grow, sell or get seed/equipment for
}

function limitWarnings(r: RankedRotation, sent: Rotation[], limits: FarmLimits): string[] {
  const out: string[] = [];
  const rot = sent.find((x) => x.name === r.rotation_name);
  const water = r.evaluation.water?.irrigation_need_m3_per_year;
  if (rot && limits.waterM3PerAcreYear != null && water != null) {
    const acres = Math.max(...rot.seasons.map((s) => s.area_hectares)) / HA_PER_ACRE;
    const perAcre = water / acres;
    if (perAcre > limits.waterM3PerAcreYear) {
      out.push(
        `Needs about ${fmt(perAcre)} m³ of irrigation water per acre a year, more than the ${fmt(limits.waterM3PerAcreYear)} m³ you said you have.`,
      );
    }
  }
  const crops = [...new Set(rot?.seasons.map((s) => s.crop) ?? [])].filter((c) => limits.excluded.includes(c));
  if (crops.length) out.push(`Includes ${crops.map(cropLabel).join(", ")}, which you said you can't grow or sell.`);
  return out;
}

/** Same rule as the backend (CropSeason validator): harvest must be after sowing; area above zero. */
export function seasonError(s: CropSeason): string | null {
  if (!s.sowing_date || !s.harvest_date) return "Enter both a sowing and a harvest date.";
  if (s.harvest_date <= s.sowing_date) return "Harvest date must be after the sowing date.";
  if (!(s.area_hectares > 0)) return "Area must be more than 0 acres.";
  return null;
}

function SeasonRow({
  s,
  onChange,
  onRemove,
}: {
  s: CropSeason;
  onChange: (s: CropSeason) => void;
  onRemove?: () => void;
}) {
  const error = seasonError(s);
  return (
    <>
      <div className="season-tile">
        <img className="season-crop-img" src={CROP_IMAGE[s.crop]} alt="" />
        <div className="season-fields">
          <label className="field">
            Crop
            <select value={s.crop} onChange={(e) => onChange({ ...s, crop: e.target.value as CropName })}>
              {CROPS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Sowing date
            <input type="date" value={s.sowing_date} onChange={(e) => onChange({ ...s, sowing_date: e.target.value })} />
          </label>
          <label className="field">
            Harvest date
            <input
              type="date"
              value={s.harvest_date}
              min={s.sowing_date}
              onChange={(e) => onChange({ ...s, harvest_date: e.target.value })}
            />
          </label>
          <label className="field">
            Land (acres)
            <input
              type="number"
              min={0.25}
              step={0.25}
              value={haToAcres(s.area_hectares)}
              onChange={(e) => onChange({ ...s, area_hectares: acresToHa(Number(e.target.value)) })}
            />
          </label>
        </div>
        {onRemove && (
          <button className="link small season-remove" onClick={onRemove} aria-label={`Remove ${cropLabel(s.crop)}`}>
            Remove
          </button>
        )}
      </div>
      {error && (
        <p className="error small" role="alert" style={{ margin: "0 0 10px" }}>
          {error}
        </p>
      )}
    </>
  );
}

function RotationEditor({
  rotation,
  title,
  onChange,
  onRemove,
}: {
  rotation: Rotation;
  title: string;
  onChange: (r: Rotation) => void;
  onRemove?: () => void;
}) {
  const setSeason = (i: number, s: CropSeason) =>
    onChange({ ...rotation, seasons: rotation.seasons.map((x, j) => (j === i ? s : x)) });
  const ordered = [...rotation.seasons].sort((x, y) => x.sowing_date.localeCompare(y.sowing_date));
  return (
    <div className="card plan-editor">
      <div className="plan-editor-head">
        <div>
          <div className="plan-label">{title}</div>
          <div className="crop-strip mini" aria-hidden="true">
            {ordered.map((x, i) => (
              <span key={i} className="crop-step">
                {i > 0 && <span className="crop-arrow">→</span>}
                <img src={CROP_IMAGE[x.crop]} alt="" />
              </span>
            ))}
          </div>
        </div>
        <label className="field plan-name">
          Plan name
          <input value={rotation.name} onChange={(e) => onChange({ ...rotation, name: e.target.value })} />
        </label>
        {onRemove && (
          <button className="link small" onClick={onRemove}>
            Remove plan
          </button>
        )}
      </div>
      {rotation.seasons.map((x, i) => (
        <SeasonRow
          key={i}
          s={x}
          onChange={(ns) => setSeason(i, ns)}
          onRemove={
            rotation.seasons.length > 1
              ? () => onChange({ ...rotation, seasons: rotation.seasons.filter((_, j) => j !== i) })
              : undefined
          }
        />
      ))}
      <button
        className="secondary"
        onClick={() => {
          const last = rotation.seasons[rotation.seasons.length - 1];
          onChange({ ...rotation, seasons: [...rotation.seasons, { ...last }] });
        }}
      >
        + Add a crop
      </button>
    </div>
  );
}

/** Numbered step heading: big number, title and one plain line. */
function StepHead({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <div className="step-head">
      <span className="step-num">{n}</span>
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
    </div>
  );
}

const PRIORITY_IMAGE: Record<keyof Priorities, string> = {
  soil_health: ILLUSTRATIONS.seedling,
  water: ILLUSTRATIONS.droplet,
  income: ILLUSTRATIONS.money,
  resilience: ILLUSTRATIONS.climate,
};

const PRIORITY_TEXT: Record<keyof Priorities, string> = {
  soil_health: "Keep my soil healthy",
  water: "Use less water",
  income: "Earn more money",
  resilience: "Stay safe from bad weather",
};

const importance = (v: number) =>
  v === 0 ? "Not important" : v <= 30 ? "A little" : v <= 60 ? "Important" : "Very important";

function Bar({ value }: { value: number | null }) {
  return (
    <div className="bar" title={value == null ? "Not available" : fmt(value, 2)}>
      <span style={{ width: `${Math.round((value ?? 0) * 100)}%` }} />
    </div>
  );
}

function RankedCard({
  r,
  pos,
  urdu,
  warnings = [],
}: {
  r: RankedRotation;
  pos: number;
  urdu: boolean;
  warnings?: string[];
}) {
  const ev = r.evaluation;
  const risks = Object.keys(RISK_LABEL) as RiskType[];
  return (
    <section className="card" id={detailId(r.rotation_name)}>
      <div className="rank">
        <span className="pos">{pos}</span>
        <h3>
          {r.rotation_name} {r.is_current && <span className="badge na">Your current rotation</span>}
        </h3>
        <strong>
          {r.preference_score == null ? "Not scored" : `Score ${fmt(r.preference_score * 100)}/100`}
          {r.partial && <span className="partial-tag">partial</span>}
        </strong>
      </div>
      {warnings.length > 0 && (
        <ul className="limit-warn" role="alert">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      {r.missing_dimensions.length > 0 && (
        <p className="muted small">
          Partial score: leaves out {r.missing_dimensions.join(", ")}, which could not be worked out for this
          rotation. Missing data is not counted as zero; compare with full scores with care.
        </p>
      )}

      <table style={{ marginTop: 8 }}>
        <tbody>
          {DIMENSIONS.map((d) => (
            <tr key={d.key}>
              <td style={{ width: "40%" }}>{d.label}</td>
              <td>
                <Bar value={r.dimension_scores[d.key]} />
              </td>
              <td className="num" style={{ width: 70 }}>
                {r.dimension_scores[d.key] == null ? "n/a" : fmt(r.dimension_scores[d.key]! * 100)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="grid" style={{ marginTop: 12 }}>
        <div>
          <div className="muted small">Irrigation need per year</div>
          <strong>
            {ev.water?.irrigation_need_m3_per_year == null
              ? "Not calculated"
              : `${fmt(ev.water.irrigation_need_m3_per_year)} m³`}
          </strong>
        </div>
        <div>
          <div className="muted small">
            {ev.income?.basis === "net" ? "Net income per year (after your costs)" : "Gross revenue per year (before costs, not profit)"}
          </div>
          <strong>
            {ev.income && (ev.income.basis === "net" ? ev.income.net_income_per_year : ev.income.gross_revenue_per_year) != null
              ? `${ev.income.currency} ${fmt(ev.income.basis === "net" ? ev.income.net_income_per_year : ev.income.gross_revenue_per_year)}`
              : "Needs local yield and price"}
          </strong>
        </div>
        <div>
          <div className="muted small">Bare-soil days per year</div>
          <strong>{ev.ground_cover ? `${fmt(ev.ground_cover.bare_soil_days_per_year)} days` : "—"}</strong>
        </div>
      </div>
      {ev.cycle_years > 1 && (
        <p className="muted small">
          This rotation repeats every {ev.cycle_years} years; its totals are divided by {ev.cycle_years} to compare
          per year.
        </p>
      )}

      <details>
        <summary>Risk by crop</summary>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Crop</th>
                {risks.map((k) => (
                  <th key={k}>{RISK_LABEL[k]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ev.crop_results.map((c, i) => (
                <tr key={i}>
                  <td>
                    {cropLabel(c.crop)}
                    {c.estimated_from_history && <div className="muted small">typical past years</div>}
                  </td>
                  {risks.map((k) => (
                    <td key={k}>
                      <LevelBadge level={c.levels[k]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {ev.crop_results.map((c, i) =>
          c.advice.length ? (
            <div key={i} style={{ marginTop: 8 }}>
              <strong className="small">{cropLabel(c.crop)} tips</strong>
              <AdviceList tips={c.advice} urdu={urdu} />
            </div>
          ) : null,
        )}
      </details>

      {ev.water && (
        <details>
          <summary>Water by season</summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Crop</th>
                  <th className="num">Crop water use (mm)</th>
                  <th className="num">Useful rain (mm)</th>
                  <th className="num">Irrigation (mm)</th>
                </tr>
              </thead>
              <tbody>
                {ev.water.seasons.map((s, i) => (
                  <tr key={i}>
                    <td>
                      {cropLabel(s.crop)}
                      {s.estimated_from_history && <div className="muted small">past-years median</div>}
                    </td>
                    <td className="num">{fmt(s.crop_water_use_mm)}</td>
                    <td className="num">{fmt(s.effective_rainfall_mm)}</td>
                    <td className="num">{fmt(s.irrigation_need_mm)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <List items={ev.water.method} />
        </details>
      )}

      {ev.income && (
        <details>
          <summary>Income by season</summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Crop</th>
                  <th className="num">Yield (t/acre)</th>
                  <th className="num">Price / t</th>
                  <th className="num">Gross revenue (before costs)</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {ev.income.seasons.map((s, i) => (
                  <tr key={i}>
                    <td>{cropLabel(s.crop)}</td>
                    <td className="num">{fmt(s.yield_t_ha == null ? null : s.yield_t_ha * HA_PER_ACRE, 2)}</td>
                    <td className="num">{fmt(s.price_per_t)}</td>
                    <td className="num">{fmt(s.gross_revenue)}</td>
                    <td className="small">
                      {[s.yield_source, s.price_source].filter(Boolean).join("; ")}
                      {s.notes.map((n, k) => (
                        <div key={k} className="muted">
                          {n}
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {r.strategy && (
        <details>
          <summary>Why this option, evidence and gaps</summary>
          <h4>Why considered</h4>
          <List items={r.strategy.why_considered} />
          {r.strategy.benefits.length > 0 && (
            <>
              <h4>Compared with your current rotation</h4>
              <List items={r.strategy.benefits} />
            </>
          )}
          <h4>Evidence</h4>
          <List items={r.strategy.evidence} />
          <h4>Information gaps</h4>
          <List items={r.strategy.information_gaps} empty="None noted." />
          <h4>Check locally</h4>
          <List items={r.strategy.needs_local_review} empty="None noted." />
        </details>
      )}
    </section>
  );
}

export default function CompareView({
  location,
  urdu,
  initial,
}: {
  location: Location;
  urdu: boolean;
  /** Rotations to start with (e.g. the dashboard's three); they are compared straight away. */
  initial?: { current: Rotation; alternatives: Rotation[] };
}) {
  const preset = useMemo(() => presetRotations(acresToHa(5)), []);
  const [current, setCurrent] = useState<Rotation>(initial?.current ?? preset.current);
  const [alts, setAlts] = useState<Rotation[]>(initial?.alternatives ?? preset.alternatives.slice(0, 2));
  // Equal weights (scaled to 100% by the engine); 50 reads as "Important" on every slider.
  const [prio, setPrio] = useState<Priorities>({ soil_health: 50, water: 50, income: 50, resilience: 50 });
  const [econ, setEcon] = useState<Partial<Record<CropName, EconInput>>>({});
  const { data, error, loading, compare } = useRotationComparison();
  const [limits, setLimits] = useState<FarmLimits>({ waterM3PerAcreYear: null, excluded: [] });
  const [scenario, setScenario] = useState<ClimateScenario>({ temperature_change_c: 0, rainfall_change_pct: 0 });
  // The rotations and scenario the shown result was computed for (inputs may have changed since).
  const [ranWith, setRanWith] = useState<{ rotations: Rotation[]; scenario: ClimateScenario } | null>(null);
  const scenarioOn = scenario.temperature_change_c !== 0 || scenario.rainfall_change_pct !== 0;

  const usedCrops = [...new Set([current, ...alts].flatMap((r) => r.seasons.map((s) => s.crop)))];
  const unusedPreset = preset.alternatives.find((p) => !alts.some((a) => a.name === p.name));

  function setEconField(crop: CropName, field: keyof EconInput, v: string) {
    setEcon((e) => ({ ...e, [crop]: { ...e[crop], [field]: v === "" ? null : Number(v) } }));
  }

  const invalidSeasons = [current, ...alts].flatMap((r) => r.seasons.filter((s) => seasonError(s) !== null)).length;

  function run() {
    if (invalidSeasons > 0) return;
    const economics = Object.fromEntries(
      Object.entries(econ)
        .filter(([c]) => usedCrops.includes(c as CropName))
        .map(([c, v]) => [c, econToApi(v)]),
    ) as Partial<Record<CropName, CropEconomics>>;
    setRanWith({ rotations: [current, ...alts], scenario });
    void compare({
      location,
      current: { ...current, is_current: true },
      alternatives: alts.map((a) => ({ ...a, is_current: false })),
      priorities: prio,
      economics,
      scenario: scenarioOn ? scenario : null,
    });
  }

  // Opened from the dashboard: show the comparison without an extra click (results are cached server-side).
  useEffect(() => {
    if (initial) run();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const cards = data ? rotationCards(data, ranWith?.rotations ?? [current, ...alts]) : null;
  const waters = (cards ?? []).map((c) => c.waterM3PerAcreYear).filter((x): x is number => x != null);
  const maxWater = waters.length ? Math.max(...waters) : null;
  const [detailsOpen, setDetailsOpen] = useState(false);

  function showDetails(name: string) {
    setDetailsOpen(true);
    // After the folded section opens, jump to that plan's full numbers.
    setTimeout(() => document.getElementById(detailId(name))?.scrollIntoView({ block: "start" }), 50);
  }

  return (
    <div className="compare-steps">
      <section>
        <StepHead n={1} title="Your crops now" text="The crops you grow on this land through the year." />
        <RotationEditor rotation={current} title="Your crops now" onChange={setCurrent} />
      </section>

      <section>
        <StepHead n={2} title="Other plans to try" text="Change the crops or dates. You need at least two plans." />
        {alts.map((a, i) => (
          <RotationEditor
            key={i}
            rotation={a}
            title={`Option ${String.fromCharCode(66 + i)}`}
            onChange={(r) => setAlts(alts.map((x, j) => (j === i ? r : x)))}
            onRemove={alts.length > 2 ? () => setAlts(alts.filter((_, j) => j !== i)) : undefined}
          />
        ))}
        <button
          className="secondary"
          onClick={() =>
            setAlts([...alts, unusedPreset ?? { name: `Option ${String.fromCharCode(66 + alts.length)}`, seasons: [...current.seasons] }])
          }
        >
          + Add another plan
        </button>
      </section>

      <FieldCalendar rotations={[current, ...alts]} />

      <section>
        <StepHead n={3} title="What matters most to you?" text="Slide right for things that matter more to you." />
        <div className="prio-grid">
          {DIMENSIONS.map((d) => (
            <label key={d.key} className="dcard prio-card">
              <img src={PRIORITY_IMAGE[d.key]} alt="" />
              <span className="prio-text">{PRIORITY_TEXT[d.key]}</span>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={prio[d.key]}
                onChange={(e) => setPrio({ ...prio, [d.key]: Number(e.target.value) })}
                aria-label={PRIORITY_TEXT[d.key]}
              />
              <strong className="prio-word">{importance(prio[d.key])}</strong>
            </label>
          ))}
        </div>
      </section>

      <details className="card more-options">
        <summary>More options: your prices, your limits, what-if weather</summary>
        <details>
          <summary>Your yields, prices and costs (optional, PKR)</summary>
          <p className="muted small">
            Without these, income uses national averages where available, or is left out rather than guessed.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Crop</th>
                  <th>Yield (t/acre)</th>
                  <th>Price per tonne</th>
                  <th>Cost per acre</th>
                </tr>
              </thead>
              <tbody>
                {usedCrops.map((c) => (
                  <tr key={c}>
                    <td>{cropLabel(c)}</td>
                    {(["yield_t_acre", "price_per_t", "cost_per_acre"] as const).map((f) => (
                      <td key={f}>
                        <input
                          type="number"
                          min={0}
                          step="any"
                          value={econ[c]?.[f] ?? ""}
                          onChange={(e) => setEconField(c, f, e.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>

        <details>
          <summary>Your limits (optional)</summary>
          <p className="muted small">Rotations that break these are flagged in the results. Scores are not changed.</p>
          <div className="row">
            <label className="field">
              Irrigation water you can get (m³ per acre a year)
              <input
                type="number"
                min={0}
                step={100}
                value={limits.waterM3PerAcreYear ?? ""}
                placeholder="e.g. 6000"
                onChange={(e) =>
                  setLimits({ ...limits, waterM3PerAcreYear: e.target.value === "" ? null : Number(e.target.value) })
                }
              />
            </label>
          </div>
          <fieldset className="crop-checks">
            <legend className="small muted">Crops you can't grow or sell (no market, seed or equipment)</legend>
            {CROPS.map((c) => (
              <label key={c.value} className="check">
                <input
                  type="checkbox"
                  checked={limits.excluded.includes(c.value)}
                  onChange={(e) =>
                    setLimits({
                      ...limits,
                      excluded: e.target.checked
                        ? [...limits.excluded, c.value]
                        : limits.excluded.filter((x) => x !== c.value),
                    })
                  }
                />
                {c.label}
              </label>
            ))}
          </fieldset>
        </details>

        <details>
          <summary>What if the weather changes? (optional)</summary>
          <p className="muted small">
            Re-scores the same seasons with every day made hotter or cooler and rain scaled up or down. A "what if" test
            to see which rotation copes better, not a forecast.
          </p>
          <div className="grid">
            <label className="field">
              Temperature: {scenario.temperature_change_c > 0 ? "+" : ""}
              {scenario.temperature_change_c} °C
              <input
                type="range"
                min={-3}
                max={4}
                step={0.5}
                value={scenario.temperature_change_c}
                onChange={(e) => setScenario({ ...scenario, temperature_change_c: Number(e.target.value) })}
              />
            </label>
            <label className="field">
              Rainfall: {scenario.rainfall_change_pct > 0 ? "+" : ""}
              {scenario.rainfall_change_pct}%
              <input
                type="range"
                min={-60}
                max={60}
                step={10}
                value={scenario.rainfall_change_pct}
                onChange={(e) => setScenario({ ...scenario, rainfall_change_pct: Number(e.target.value) })}
              />
            </label>
          </div>
          {scenarioOn && (
            <button className="link" onClick={() => setScenario({ temperature_change_c: 0, rainfall_change_pct: 0 })}>
              Reset to observed weather
            </button>
          )}
        </details>

      </details>

      <div className="compare-cta">
        <button className="primary big" onClick={run} disabled={loading || invalidSeasons > 0}>
          {loading ? "Checking with NASA data…" : scenarioOn ? "Compare with what-if weather" : "Compare my plans"}
        </button>
        {invalidSeasons > 0 && (
          <p className="error small" role="alert">
            Fix {invalidSeasons} crop{invalidSeasons > 1 ? "s" : ""} with wrong dates or land first.
          </p>
        )}
      </div>

      <ErrorBox error={error ? "We could not compare the plans right now. Please try again." : null} />

      {data && cards && (
        <section aria-labelledby="results-h">
          <div className="dash-head">
            <h2 id="results-h">Results</h2>
            <p>Higher score = fits your farm and your choices better. Check with a local farm advisor before you decide.</p>
          </div>
          {ranWith && (ranWith.scenario.temperature_change_c !== 0 || ranWith.scenario.rainfall_change_pct !== 0) && (
            <p className="note">
              What-if weather: temperature {ranWith.scenario.temperature_change_c > 0 ? "+" : ""}
              {ranWith.scenario.temperature_change_c} °C, rain {ranWith.scenario.rainfall_change_pct > 0 ? "+" : ""}
              {ranWith.scenario.rainfall_change_pct}%. This is a test, not a forecast.
            </p>
          )}
          <div className="plan-grid">
            {cards.map((c) => {
              const r = data.ranked.find((x) => x.rotation_name === c.name);
              return (
                <RotationCard
                  key={c.name}
                  card={c}
                  maxWater={maxWater}
                  warnings={r ? limitWarnings(r, ranWith?.rotations ?? [current, ...alts], limits) : []}
                  onDetails={() => showDetails(c.name)}
                />
              );
            })}
          </div>

          <details
            className="card full-details"
            open={detailsOpen}
            onToggle={(e) => setDetailsOpen((e.target as HTMLDetailsElement).open)}
          >
            <summary>See all numbers and evidence</summary>
            <List items={data.explanation} />
            <RainSourceNote rain={data.rain_source} />
            {data.resilience_risks.length > 0 && (
              <p className="muted small">
                Weather safety compares: {data.resilience_risks.map((r) => RISK_LABEL[r]).join(", ")}.
              </p>
            )}
            {data.regional_water && (
              <div className="note small">
                <strong>Regional water (GRACE satellites):</strong> {data.regional_water.message}{" "}
                <span className="muted">{data.regional_water.source}. Context only: it does not change the scores.</span>
              </div>
            )}
            {data.ranked.map((r, i) => (
              <RankedCard
                key={r.rotation_name + i}
                r={r}
                pos={i + 1}
                urdu={urdu}
                warnings={limitWarnings(r, ranWith?.rotations ?? [current, ...alts], limits)}
              />
            ))}
            <h3>Limitations</h3>
            <List items={data.limitations} />
            {data.soil && (
              <p className="muted small">
                Soil: {data.soil.texture_class ?? "texture unknown"} ({data.soil.source}
                {data.soil.distance_km > 0 ? `, ${fmt(data.soil.distance_km, 1)} km away` : ""}).
              </p>
            )}
            <DataNoteLine note={data.data_note} />
          </details>
        </section>
      )}
    </div>
  );
}
