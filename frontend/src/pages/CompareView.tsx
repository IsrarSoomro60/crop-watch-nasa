import { useMemo, useState } from "react";
import { AdviceList, DataNoteLine, ErrorBox, LevelBadge, List } from "../components/common";
import { useRotationComparison } from "../hooks/useRotationComparison";
import { CROPS, RISK_LABEL, cropLabel, fmt, presetRotations } from "../lib/labels";
import type {
  CropEconomics,
  CropName,
  CropSeason,
  DimensionScores,
  Location,
  Priorities,
  RankedRotation,
  RiskType,
  Rotation,
} from "../types";

const DIMENSIONS: { key: keyof Priorities & keyof DimensionScores; label: string }[] = [
  { key: "soil_health", label: "Soil health" },
  { key: "water", label: "Water saving" },
  { key: "income", label: "Income" },
  { key: "resilience", label: "Climate resilience" },
];

function SeasonRow({
  s,
  onChange,
  onRemove,
}: {
  s: CropSeason;
  onChange: (s: CropSeason) => void;
  onRemove?: () => void;
}) {
  return (
    <div className="row" style={{ marginBottom: 8 }}>
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
        Sowing
        <input type="date" value={s.sowing_date} onChange={(e) => onChange({ ...s, sowing_date: e.target.value })} />
      </label>
      <label className="field">
        Harvest
        <input
          type="date"
          value={s.harvest_date}
          min={s.sowing_date}
          onChange={(e) => onChange({ ...s, harvest_date: e.target.value })}
        />
      </label>
      <label className="field">
        Area (ha)
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={s.area_hectares}
          onChange={(e) => onChange({ ...s, area_hectares: Number(e.target.value) })}
        />
      </label>
      {onRemove && (
        <button className="link small" onClick={onRemove}>
          Remove season
        </button>
      )}
    </div>
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
  return (
    <div className="card">
      <div className="rank">
        <h3>{title}</h3>
        {onRemove && (
          <button className="link small" onClick={onRemove}>
            Remove
          </button>
        )}
      </div>
      <label className="field" style={{ marginBottom: 8 }}>
        Name
        <input value={rotation.name} onChange={(e) => onChange({ ...rotation, name: e.target.value })} />
      </label>
      {rotation.seasons.map((s, i) => (
        <SeasonRow
          key={i}
          s={s}
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
        + Add season
      </button>
    </div>
  );
}

function Bar({ value }: { value: number | null }) {
  return (
    <div className="bar" title={value == null ? "Not available" : fmt(value, 2)}>
      <span style={{ width: `${Math.round((value ?? 0) * 100)}%` }} />
    </div>
  );
}

function RankedCard({ r, pos, urdu }: { r: RankedRotation; pos: number; urdu: boolean }) {
  const ev = r.evaluation;
  const risks = Object.keys(RISK_LABEL) as RiskType[];
  return (
    <section className="card">
      <div className="rank">
        <span className="pos">{pos}</span>
        <h3>
          {r.rotation_name} {r.is_current && <span className="badge na">Your current rotation</span>}
        </h3>
        <strong>{r.preference_score == null ? "Score withheld" : `Score ${fmt(r.preference_score * 100)}/100`}</strong>
      </div>
      {r.missing_dimensions.length > 0 && (
        <p className="muted small">
          Overall score withheld: missing {r.missing_dimensions.join(", ")}. Missing data is not counted as zero.
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
          <div className="muted small">Irrigation need</div>
          <strong>{ev.water?.irrigation_need_m3 == null ? "Not calculated" : `${fmt(ev.water.irrigation_need_m3)} m³`}</strong>
        </div>
        <div>
          <div className="muted small">Income ({ev.income?.basis ?? "gross"})</div>
          <strong>
            {ev.income && (ev.income.net_income ?? ev.income.gross_revenue) != null
              ? `${ev.income.currency} ${fmt(ev.income.net_income ?? ev.income.gross_revenue)}`
              : "Needs your yield and price"}
          </strong>
        </div>
        <div>
          <div className="muted small">Bare soil in the year</div>
          <strong>{ev.ground_cover ? `${ev.ground_cover.bare_soil_days} days` : "—"}</strong>
        </div>
      </div>

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
                  <th className="num">Yield (t/ha)</th>
                  <th className="num">Price / t</th>
                  <th className="num">Gross</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {ev.income.seasons.map((s, i) => (
                  <tr key={i}>
                    <td>{cropLabel(s.crop)}</td>
                    <td className="num">{fmt(s.yield_t_ha, 2)}</td>
                    <td className="num">{fmt(s.price_per_t)}</td>
                    <td className="num">{fmt(s.gross_revenue)}</td>
                    <td className="small">{[s.yield_source, s.price_source].filter(Boolean).join("; ") || s.notes.join(" ")}</td>
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

export default function CompareView({ location, urdu }: { location: Location; urdu: boolean }) {
  const preset = useMemo(() => presetRotations(2), []);
  const [current, setCurrent] = useState<Rotation>(preset.current);
  const [alts, setAlts] = useState<Rotation[]>(preset.alternatives.slice(0, 2));
  const [prio, setPrio] = useState<Priorities>({ soil_health: 25, water: 25, income: 25, resilience: 25 });
  const [econ, setEcon] = useState<Partial<Record<CropName, CropEconomics>>>({});
  const { data, error, loading, compare } = useRotationComparison();

  const usedCrops = [...new Set([current, ...alts].flatMap((r) => r.seasons.map((s) => s.crop)))];
  const unusedPreset = preset.alternatives.find((p) => !alts.some((a) => a.name === p.name));

  function setEconField(crop: CropName, field: keyof CropEconomics, v: string) {
    setEcon((e) => ({ ...e, [crop]: { ...e[crop], currency: "PKR", [field]: v === "" ? null : Number(v) } }));
  }

  function run() {
    const economics = Object.fromEntries(
      Object.entries(econ).filter(([c]) => usedCrops.includes(c as CropName)),
    ) as Partial<Record<CropName, CropEconomics>>;
    void compare({
      location,
      current: { ...current, is_current: true },
      alternatives: alts.map((a) => ({ ...a, is_current: false })),
      priorities: prio,
      economics,
    });
  }

  return (
    <>
      <RotationEditor rotation={current} title="Your current rotation" onChange={setCurrent} />
      {alts.map((a, i) => (
        <RotationEditor
          key={i}
          rotation={a}
          title={`Alternative ${i + 1}`}
          onChange={(r) => setAlts(alts.map((x, j) => (j === i ? r : x)))}
          onRemove={alts.length > 2 ? () => setAlts(alts.filter((_, j) => j !== i)) : undefined}
        />
      ))}
      <p>
        <button
          className="secondary"
          onClick={() =>
            setAlts([...alts, unusedPreset ?? { name: `Alternative ${alts.length + 1}`, seasons: [...current.seasons] }])
          }
        >
          + Add alternative
        </button>
      </p>

      <section className="card">
        <h2>What matters most to you?</h2>
        <div className="grid">
          {DIMENSIONS.map((d) => (
            <label key={d.key} className="field">
              {d.label}: {prio[d.key]}
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={prio[d.key]}
                onChange={(e) => setPrio({ ...prio, [d.key]: Number(e.target.value) })}
              />
            </label>
          ))}
        </div>
        <p className="muted small">Weights are scaled to add up to 100%.</p>

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
                  <th>Yield (t/ha)</th>
                  <th>Price per tonne</th>
                  <th>Cost per ha</th>
                </tr>
              </thead>
              <tbody>
                {usedCrops.map((c) => (
                  <tr key={c}>
                    <td>{cropLabel(c)}</td>
                    {(["yield_t_ha", "price_per_t", "cost_per_ha"] as const).map((f) => (
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

        <p>
          <button className="primary" onClick={run} disabled={loading}>
            {loading ? "Comparing… (fetching NASA data)" : "Compare rotations"}
          </button>
        </p>
      </section>

      <ErrorBox error={error} />

      {data && (
        <>
          <section className="card">
            <h2>Result</h2>
            <List items={data.explanation} />
            {data.resilience_risks.length > 0 && (
              <p className="muted small">
                Resilience compares: {data.resilience_risks.map((r) => RISK_LABEL[r]).join(", ")}.
              </p>
            )}
          </section>
          {data.ranked.map((r, i) => (
            <RankedCard key={r.rotation_name + i} r={r} pos={i + 1} urdu={urdu} />
          ))}
          <section className="card">
            <h3>Limitations</h3>
            <List items={data.limitations} />
            {data.soil && (
              <p className="muted small">
                Soil: {data.soil.texture_class ?? "texture unknown"} ({data.soil.source}
                {data.soil.distance_km > 0 ? `, ${fmt(data.soil.distance_km, 1)} km away` : ""}).
              </p>
            )}
            <DataNoteLine note={data.data_note} />
          </section>
        </>
      )}
    </>
  );
}
