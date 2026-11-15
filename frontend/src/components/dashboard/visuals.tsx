/**
 * Big, simple visuals for the farmer dashboard: a half-circle meter, a score ring, a bar meter and a
 * month-by-month rain + temperature chart. Plain SVG, no chart library (the project has none).
 */
import { type MonthPoint, monthLabel, monthShort } from "../../lib/climateSummary";
import { fmt } from "../../lib/labels";

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/** Half-circle meter. `fraction` 0-1 places the needle; the word under it says what the position means. */
export function Gauge({
  fraction,
  color,
  word,
  low,
  high,
}: {
  fraction: number | null;
  color: string;
  word: string;
  low: string;
  high: string;
}) {
  const r = 70;
  const cx = 90;
  const cy = 86;
  const f = fraction == null ? null : clamp01(fraction);
  const point = (t: number) => {
    const a = Math.PI * (1 - t);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)] as const;
  };
  const [sx, sy] = point(0);
  const [ex, ey] = point(1);
  const track = `M ${sx} ${sy} A ${r} ${r} 0 0 1 ${ex} ${ey}`;
  let fill = "";
  let needle: readonly [number, number] | null = null;
  if (f != null && f > 0) {
    const [fx, fy] = point(f);
    fill = `M ${sx} ${sy} A ${r} ${r} 0 0 1 ${fx.toFixed(1)} ${fy.toFixed(1)}`;
  }
  if (f != null) needle = point(f);
  return (
    <figure className="gauge" aria-label={`${word}. Scale from ${low} to ${high}.`}>
      <svg viewBox="0 0 180 100" role="img">
        <path d={track} className="gauge-track" />
        {fill && <path d={fill} stroke={color} className="gauge-fill" />}
        {needle && <circle cx={needle[0]} cy={needle[1]} r="9" fill="var(--surface)" stroke={color} strokeWidth="5" />}
      </svg>
      <figcaption>
        <strong style={{ color }}>{word}</strong>
        <span className="gauge-ends">
          <span>{low}</span>
          <span>{high}</span>
        </span>
      </figcaption>
    </figure>
  );
}

/** Round score meter, 0-100. */
export function ScoreRing({ score, size = 110 }: { score: number | null; size?: number }) {
  const stroke = 11;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const f = score == null ? 0 : clamp01(score / 100);
  const color = score == null ? "var(--na)" : score >= 67 ? "var(--accent)" : score >= 40 ? "var(--amber)" : "var(--high)";
  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={score == null ? "No score" : `Score ${score} out of 100`}>
        <circle cx={size / 2} cy={size / 2} r={r} className="ring-track" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${c * f} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="ring-text">
        <strong>{score ?? "?"}</strong>
        <span>out of 100</span>
      </div>
    </div>
  );
}

/** Labelled bar meter with a picture: "Water need ▓▓▓░░ Less than now". */
export function MeterBar({
  image,
  label,
  fraction,
  color,
  word,
}: {
  image: string;
  label: string;
  fraction: number | null;
  color: string;
  word: string;
}) {
  return (
    <div className="meter-bar">
      <img src={image} alt="" />
      <div className="meter-body">
        <div className="meter-top">
          <span>{label}</span>
          <strong style={{ color: fraction == null ? "var(--muted)" : color }}>{word}</strong>
        </div>
        <div className="meter-track" aria-hidden="true">
          {fraction != null && <span style={{ width: `${Math.max(4, clamp01(fraction) * 100)}%`, background: color }} />}
        </div>
      </div>
    </div>
  );
}

/** Rain as blue bars and temperature as an orange line, month by month, with plain month names. */
export function ClimateYearChart({ months }: { months: MonthPoint[] }) {
  const w = 680;
  const h = 260;
  const pad = { l: 64, r: 44, t: 18, b: 34 }; // left fits "158 mm"
  const n = months.length;
  if (n < 2) return <p className="muted">Not enough data to draw.</p>;
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const slot = iw / n;
  const rains = months.map((m) => m.rainMm ?? 0);
  const maxRain = Math.max(10, ...rains);
  const temps = months.map((m) => m.avgTempC).filter((t): t is number => t != null);
  const tMin = Math.floor(Math.min(...temps) / 5) * 5;
  const tMax = Math.ceil(Math.max(...temps) / 5) * 5;
  const ty = (t: number) => pad.t + (1 - (t - tMin) / Math.max(1, tMax - tMin)) * ih;
  const ry = (mm: number) => pad.t + (1 - mm / maxRain) * ih;
  const xMid = (i: number) => pad.l + slot * i + slot / 2;
  let line = "";
  months.forEach((m, i) => {
    if (m.avgTempC == null) return;
    line += `${line ? "L" : "M"}${xMid(i).toFixed(1)},${ty(m.avgTempC).toFixed(1)}`;
  });

  return (
    <svg className="year-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Rain and temperature each month">
      {[0, 0.5, 1].map((g) => (
        <line key={g} x1={pad.l} x2={w - pad.r} y1={pad.t + g * ih} y2={pad.t + g * ih} className="grid" />
      ))}
      <text x={pad.l - 6} y={pad.t + 4} textAnchor="end" className="axis-rain">
        {fmt(maxRain)} mm
      </text>
      <text x={pad.l - 6} y={pad.t + ih} textAnchor="end" className="axis-rain">
        0
      </text>
      <text x={w - pad.r + 6} y={pad.t + 4} className="axis-temp">
        {tMax}°
      </text>
      <text x={w - pad.r + 6} y={pad.t + ih} className="axis-temp">
        {tMin}°
      </text>
      {months.map((m, i) => {
        const mm = m.rainMm ?? 0;
        const bw = slot * 0.56;
        return (
          <g key={m.month}>
            <rect
              x={xMid(i) - bw / 2}
              y={ry(mm)}
              width={bw}
              height={Math.max(0, pad.t + ih - ry(mm))}
              rx="4"
              className="rain-bar"
            >
              <title>{`${monthLabel(m.month)}: ${fmt(m.rainMm)} mm rain, ${fmt(m.avgTempC, 1)} °C`}</title>
            </rect>
            <text x={xMid(i)} y={h - 12} textAnchor="middle" className="month">
              {monthShort(m.month)}
            </text>
          </g>
        );
      })}
      <path d={line} className="temp-line" />
      {months.map((m, i) =>
        m.avgTempC == null ? null : (
          <circle key={m.month} cx={xMid(i)} cy={ty(m.avgTempC)} r="4.5" className="temp-dot">
            <title>{`${monthLabel(m.month)}: ${fmt(m.avgTempC, 1)} °C`}</title>
          </circle>
        ),
      )}
    </svg>
  );
}
