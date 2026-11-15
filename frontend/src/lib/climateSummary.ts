import type { DailyObservation } from "../types";

/** NASA POWER ALLSKY_SFC_SW_DWN comes in MJ/m²/day; 1 kWh = 3.6 MJ. */
export const mjToKwh = (mj: number) => mj / 3.6;

/** Fewer valid days than this and an average would mislead, so the value is shown as unavailable. */
const MIN_DAYS_FOR_30_DAY = 20;
const MIN_DAYS_FOR_MONTH = 15;

export interface ClimateFigures {
  avgTempC: number | null;
  rainTotalMm: number | null;
  avgHumidityPct: number | null;
  avgSolarKwh: number | null;
  days: number; // days with a temperature value
  from: string | null;
  to: string | null;
}

export interface MonthPoint {
  month: string; // YYYY-MM
  avgTempC: number | null;
  rainMm: number | null;
  avgHumidityPct: number | null;
  avgSolarKwh: number | null;
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const vals = (obs: DailyObservation[], f: (o: DailyObservation) => number | null) =>
  obs.map(f).filter((v): v is number => v != null);

function figures(obs: DailyObservation[], minDays: number): ClimateFigures {
  const withTemp = obs.filter((o) => o.tmean_c != null);
  const enough = (xs: number[]) => xs.length >= minDays;
  const t = vals(obs, (o) => o.tmean_c);
  const r = vals(obs, (o) => o.precipitation_mm);
  const h = vals(obs, (o) => o.relative_humidity_pct);
  const s = vals(obs, (o) => o.solar_radiation_mj_m2);
  return {
    avgTempC: enough(t) ? mean(t) : null,
    rainTotalMm: enough(r) ? sum(r) : null,
    avgHumidityPct: enough(h) ? mean(h) : null,
    avgSolarKwh: enough(s) ? mjToKwh(mean(s)!) : null,
    days: withTemp.length,
    from: withTemp[0]?.day ?? null,
    to: withTemp[withTemp.length - 1]?.day ?? null,
  };
}

/** Observations up to the last day NASA POWER actually has data for (it lags real time by 2-3 days). */
function upToLatest(obs: DailyObservation[], latest: string | null): DailyObservation[] {
  return latest ? obs.filter((o) => o.day <= latest) : obs;
}

/** The 30 days ending on the latest observation. */
export function recentFigures(obs: DailyObservation[], latest: string | null, days = 30): ClimateFigures {
  const usable = upToLatest(obs, latest);
  return figures(usable.slice(-days), MIN_DAYS_FOR_30_DAY);
}

/** The whole fetched window (about 12 months). */
export function yearFigures(obs: DailyObservation[], latest: string | null): ClimateFigures {
  return figures(upToLatest(obs, latest), 300);
}

/** Calendar-month averages (rain as a monthly total). Months with too few days are left as gaps. */
export function monthlySeries(obs: DailyObservation[], latest: string | null): MonthPoint[] {
  const byMonth = new Map<string, DailyObservation[]>();
  for (const o of upToLatest(obs, latest)) {
    const m = o.day.slice(0, 7);
    if (!byMonth.has(m)) byMonth.set(m, []);
    byMonth.get(m)!.push(o);
  }
  const months = [...byMonth.entries()].map(([month, os]) => {
    const f = figures(os, MIN_DAYS_FOR_MONTH);
    return {
      month,
      avgTempC: f.avgTempC,
      rainMm: f.rainTotalMm,
      avgHumidityPct: f.avgHumidityPct,
      avgSolarKwh: f.avgSolarKwh,
    };
  });
  // The window starts and ends mid-month; drop partial edge months rather than plot empty ends.
  const has = (m: MonthPoint) => m.avgTempC != null;
  const first = months.findIndex(has);
  const last = months.length - 1 - [...months].reverse().findIndex(has);
  return first === -1 ? [] : months.slice(first, last + 1);
}

/** "June 2026": a short "Jun 26" reads like a date. */
export const monthLabel = (ym: string) =>
  new Date(`${ym}-01T00:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

/** "Jun" for chart axis ticks. */
export const monthShort = (ym: string) => new Date(`${ym}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short" });
