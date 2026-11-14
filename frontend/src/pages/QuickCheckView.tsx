import { useState } from "react";
import { AdviceList, DataNoteLine, ErrorBox, LevelBadge, List } from "../components/common";
import { CROPS, RISK_LABEL, STAGES, cropLabel, fmt, stageLabel } from "../lib/labels";
import { api } from "../services/api";
import type { CropName, Location, QuickCheckResult, StageType } from "../types";

const daysAgo = (n: number) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);

export default function QuickCheckView({ location, urdu }: { location: Location; urdu: boolean }) {
  const [crop, setCrop] = useState<CropName>("wheat");
  const [mode, setMode] = useState<"date" | "stage">("date");
  const [sowing, setSowing] = useState(daysAgo(20));
  const [stage, setStage] = useState<StageType>("vegetative");
  const [result, setResult] = useState<QuickCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(
        await api.quickCheck({
          location,
          crop,
          ...(mode === "date" ? { sowing_date: sowing } : { stage }),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="card">
        <h2>How is my crop doing this week?</h2>
        <p className="muted small">Checks the last 7 days of NASA POWER weather against the crop's limits.</p>
        <div className="row">
          <label className="field">
            Crop
            <select value={crop} onChange={(e) => setCrop(e.target.value as CropName)}>
              {CROPS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            I know the
            <select value={mode} onChange={(e) => setMode(e.target.value as "date" | "stage")}>
              <option value="date">sowing date</option>
              <option value="stage">growth stage</option>
            </select>
          </label>
          {mode === "date" ? (
            <label className="field">
              Sowing date
              <input type="date" value={sowing} max={daysAgo(0)} onChange={(e) => setSowing(e.target.value)} />
            </label>
          ) : (
            <label className="field">
              Growth stage
              <select value={stage} onChange={(e) => setStage(e.target.value as StageType)}>
                {STAGES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button className="primary" onClick={run} disabled={loading}>
            {loading ? "Checking…" : "Check risk"}
          </button>
        </div>
      </section>

      <ErrorBox error={error} />

      {result && (
        <>
          <section className="card">
            <div className="rank">
              <h3>
                {cropLabel(result.crop)} · {stageLabel(result.stage)}
              </h3>
              <LevelBadge level={result.overall} big />
            </div>
            <p className="muted small">{result.stage_basis}</p>
            {result.cards.length === 0 ? (
              <p>No risk above Low in the last 7 days.</p>
            ) : (
              <div className="grid">
                {result.cards.map((c) => (
                  <div key={c.risk} className="card" style={{ marginBottom: 0 }}>
                    <div className="rank">
                      <strong style={{ flex: 1 }}>{RISK_LABEL[c.risk]}</strong>
                      <LevelBadge level={c.level} />
                    </div>
                    <p className="small">{c.reason}</p>
                    <p className="muted small">Days beyond limit: {c.days_beyond_limit}</p>
                  </div>
                ))}
              </div>
            )}
            {result.not_assessed.length > 0 && (
              <p className="muted small">
                Not assessed (no supported limit for this crop/stage):{" "}
                {result.not_assessed.map((r) => RISK_LABEL[r]).join(", ")}
              </p>
            )}
          </section>

          {result.advice.length > 0 && (
            <section className="card">
              <h3>What you can do</h3>
              <AdviceList tips={result.advice} urdu={urdu} />
            </section>
          )}

          <section className="card">
            <h3>Last 7 days</h3>
            <div className="strip">
              {result.last_7_days.map((d) => (
                <div key={d.day}>
                  <strong>{d.day.slice(5)}</strong>
                  <br />↑ {fmt(d.tmax_c, 0)}°C
                  <br />↓ {fmt(d.tmin_c, 0)}°C
                  <br />
                  {fmt(d.precipitation_mm, 1)} mm
                </div>
              ))}
            </div>
            <List items={result.notes} />
            <DataNoteLine note={result.data_note} />
          </section>
        </>
      )}
    </>
  );
}
