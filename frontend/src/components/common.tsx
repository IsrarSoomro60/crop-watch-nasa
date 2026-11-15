import { useEffect, useState } from "react";
import { DISTRICTS, LEVEL_LABEL } from "../lib/labels";
import type { AdviceTip, DataNote, Location, RainSource, RiskLevel } from "../types";

export function LevelBadge({ level, big }: { level: RiskLevel | null; big?: boolean }) {
  return (
    <span className={`badge ${level ?? "na"}${big ? " big" : ""}`}>{level ? LEVEL_LABEL[level] : "Not assessed"}</span>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p className="error" role="alert">
      Could not load: {error.length > 300 ? error.slice(0, 300) + "…" : error}
    </p>
  );
}

export function List({ items, empty }: { items: string[]; empty?: string }) {
  if (!items.length) return empty ? <p className="muted small">{empty}</p> : null;
  return (
    <ul className="plain">
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </ul>
  );
}

export function DataNoteLine({ note }: { note: DataNote | null }) {
  if (!note) return null;
  return (
    <p className="muted small">
      Weather: {note.source}
      {note.latest_observation_date ? `, up to ${note.latest_observation_date}` : ""}
      {note.from_sample ? " (saved sample: live service unavailable or demo data)" : ""}. {note.note}
    </p>
  );
}

/** Which rain fed the scores (GPM satellite or NASA POWER), flagged when the two disagree a lot. */
export function RainSourceNote({ rain }: { rain: RainSource | null | undefined }) {
  if (!rain) return null;
  const big = rain.difference_pct != null && Math.abs(rain.difference_pct) >= 30;
  return (
    <p className={`rain-note small ${big ? "warn" : ""}`}>
      <strong>{rain.source === "gpm" ? "Rain: NASA GPM satellite" : "Rain: NASA POWER"}.</strong> {rain.message}
    </p>
  );
}

export function AdviceList({ tips, urdu }: { tips: AdviceTip[]; urdu: boolean }) {
  if (!tips.length) return null;
  return (
    <ul className="plain">
      {tips.map((t, i) => (
        <li key={i}>
          {urdu && t.text_ur ? (
            <span className="urdu">
              {t.text_ur}
              {!t.ur_reviewed && <span className="badge na small"> draft translation</span>}
            </span>
          ) : (
            t.text_en
          )}
          <div className="muted small">Source: {t.source}</div>
        </li>
      ))}
    </ul>
  );
}

export function LocationPicker({ value, onChange }: { value: Location; onChange: (l: Location) => void }) {
  const match = DISTRICTS.find(
    (d) => d.location.latitude === value.latitude && d.location.longitude === value.longitude,
  );
  // "Other location…" can be picked while still on a district's point, so it needs its own flag;
  // a point off the district list (e.g. a map click) is always custom.
  const [forceCustom, setCustom] = useState(false);
  const custom = forceCustom || !match;
  useEffect(() => {
    if (match) setCustom(false);
  }, [match]);
  return (
    <div className="row">
      <label className="field">
        District
        <select
          value={custom ? "custom" : match?.name}
          onChange={(e) => {
            const d = DISTRICTS.find((x) => x.name === e.target.value);
            setCustom(!d);
            if (d) onChange(d.location);
          }}
        >
          {DISTRICTS.map((d) => (
            <option key={d.name} value={d.name}>
              {d.name}
            </option>
          ))}
          <option value="custom">Other location…</option>
        </select>
      </label>
      {custom && (
        <>
          <label className="field">
            Latitude
            <input
              type="number"
              step="0.01"
              min={-90}
              max={90}
              value={value.latitude}
              onChange={(e) => onChange({ ...value, latitude: Number(e.target.value) })}
            />
          </label>
          <label className="field">
            Longitude
            <input
              type="number"
              step="0.01"
              min={-180}
              max={180}
              value={value.longitude}
              onChange={(e) => onChange({ ...value, longitude: Number(e.target.value) })}
            />
          </label>
        </>
      )}
    </div>
  );
}

/** Minimal SVG line chart; values may contain nulls (gaps). */
export function LineChart({
  points,
  color = "var(--chart-1)",
  unit,
  height = 140,
  zeroLine,
  digits = 2,
}: {
  points: { x: string; y: number | null }[];
  color?: string;
  unit: string;
  height?: number;
  zeroLine?: boolean;
  digits?: number; // decimals on the min/max axis labels
}) {
  const ys = points.map((p) => p.y).filter((y): y is number => y != null);
  if (ys.length < 2) return <p className="muted small">Not enough data to draw.</p>;
  const w = 600;
  const pad = { l: 52, r: 8, t: 22, b: 26 };
  let min = Math.min(...ys);
  let max = Math.max(...ys);
  if (zeroLine) {
    min = Math.min(min, 0);
    max = Math.max(max, 0);
  }
  if (max === min) max = min + 1;
  const x = (i: number) => pad.l + (i / (points.length - 1)) * (w - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - min) / (max - min)) * (height - pad.t - pad.b);
  let d = "";
  let pen = false;
  points.forEach((p, i) => {
    if (p.y == null) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`;
    pen = true;
  });
  const first = points[0].x.slice(0, 7);
  const last = points[points.length - 1].x.slice(0, 7);
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${height}`} width="100%" role="img" aria-label={`Chart in ${unit}`}>
      <line className="axis" x1={pad.l} x2={w - pad.r} y1={height - pad.b} y2={height - pad.b} />
      {zeroLine && <line className="axis" strokeDasharray="4 3" x1={pad.l} x2={w - pad.r} y1={y(0)} y2={y(0)} />}
      <text x={pad.l - 4} y={pad.t + 5} textAnchor="end">
        {max.toFixed(digits)}
      </text>
      <text x={pad.l - 4} y={height - pad.b} textAnchor="end">
        {min.toFixed(digits)}
      </text>
      <text x={pad.l} y={height - 6}>
        {first}
      </text>
      <text x={w - pad.r} y={height - 6} textAnchor="end">
        {last}
      </text>
      <text x={pad.l + 4} y={pad.t - 6}>
        {unit}
      </text>
      <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}
