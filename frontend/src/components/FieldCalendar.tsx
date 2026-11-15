import { cropLabel } from "../lib/labels";
import type { CropName, Rotation } from "../types";

const DAY = 86400000;
const parse = (iso: string) => new Date(`${iso}T00:00:00Z`).getTime();
const addYears = (t: number, n: number) => {
  const d = new Date(t);
  d.setUTCFullYear(d.getUTCFullYear() + n);
  return d.getTime();
};

/** Same rule as the backend (services/rotation/cycle.py): the cycle grows until it contains the last sowing. */
function cycleYears(r: Rotation): number {
  const sow = r.seasons.map((s) => parse(s.sowing_date));
  const first = Math.min(...sow);
  const last = Math.max(...sow);
  let years = 1;
  while (last >= addYears(first, years)) years += 1;
  return years;
}

interface Segment {
  kind: "crop" | "bare";
  crop?: CropName;
  from: number; // 0-1 position in the cycle
  to: number;
  days: number;
  label: string;
}

const fmtDay = (t: number) => new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

/** Crop and bare-field segments over one repeat of the rotation, starting at the first sowing month. */
function segments(r: Rotation): { segs: Segment[]; start: number; end: number; years: number } {
  const valid = r.seasons.filter((s) => s.sowing_date && s.harvest_date && s.harvest_date > s.sowing_date);
  const years = valid.length ? cycleYears({ ...r, seasons: valid }) : 1;
  const firstSow = Math.min(...valid.map((s) => parse(s.sowing_date)));
  const d0 = new Date(firstSow);
  const start = Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth(), 1);
  const end = addYears(start, years);
  const span = end - start;
  const pos = (t: number) => Math.min(1, Math.max(0, (t - start) / span));

  const crops = valid
    .map((s) => ({ crop: s.crop, a: parse(s.sowing_date), b: Math.min(parse(s.harvest_date), end) }))
    .sort((x, y) => x.a - y.a);
  const segs: Segment[] = [];
  // Before the first sowing, the field is still bare from the previous cycle's last harvest (wraps round).
  let cursor = start;
  const lastHarvestPrev = crops.length ? crops[crops.length - 1].b - span : start;
  for (const c of crops) {
    const gapFrom = Math.max(cursor, lastHarvestPrev);
    if (c.a > gapFrom + DAY) {
      segs.push({ kind: "bare", from: pos(gapFrom), to: pos(c.a), days: Math.round((c.a - gapFrom) / DAY), label: "" });
    }
    segs.push({
      kind: "crop",
      crop: c.crop,
      from: pos(c.a),
      to: pos(c.b),
      days: Math.round((c.b - c.a) / DAY),
      label: `${cropLabel(c.crop)}: ${fmtDay(c.a)} – ${fmtDay(c.b)}`,
    });
    cursor = Math.max(cursor, c.b);
  }
  if (end > cursor + DAY) {
    segs.push({ kind: "bare", from: pos(cursor), to: 1, days: Math.round((end - cursor) / DAY), label: "" });
  }
  for (const s of segs) if (s.kind === "bare") s.label = `Bare field for about ${s.days} days`;
  return { segs, start, end, years };
}

export default function FieldCalendar({ rotations }: { rotations: Rotation[] }) {
  const usable = rotations.filter((r) => r.seasons.some((s) => s.sowing_date && s.harvest_date > s.sowing_date));
  if (!usable.length) return null;
  return (
    <section className="card">
      <h2>Field calendar</h2>
      <p className="muted small">
        When each rotation keeps the field planted, and when it lies bare (hatched). Bare soil can lose moisture and
        topsoil to sun, wind and heavy rain; a short cover or fodder crop can fill the gap.
      </p>
      <div className="calendar">
        {usable.map((r) => {
          const { segs, start, years } = segments(r);
          const bareDays = segs.filter((s) => s.kind === "bare").reduce((a, s) => a + s.days, 0);
          const months = Array.from({ length: 12 * years }, (_, i) => {
            const d = new Date(start);
            d.setUTCMonth(d.getUTCMonth() + i);
            return d.toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
          });
          return (
            <div key={r.name} className="cal-row">
              <div className="cal-name">
                <strong>{r.name}</strong>
                <span className="muted small">
                  {Math.round(bareDays / years)} bare days a year{years > 1 ? ` · ${years}-year cycle` : ""}
                </span>
              </div>
              <div className="cal-track" role="img" aria-label={segs.map((s) => s.label).join("; ")}>
                {segs.map((s, i) => (
                  <span
                    key={i}
                    className={s.kind === "crop" ? `cal-seg crop-${s.crop}` : "cal-seg bare"}
                    style={{ left: `${s.from * 100}%`, width: `${(s.to - s.from) * 100}%` }}
                    title={s.label}
                  >
                    {s.kind === "crop" && s.to - s.from > 0.08 ? cropLabel(s.crop!) : ""}
                  </span>
                ))}
              </div>
              <div className="cal-months" aria-hidden="true">
                {months.map((m, i) => (
                  <span key={i}>{years > 1 && i % 2 ? "" : m}</span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
