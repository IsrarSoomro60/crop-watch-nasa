import type { ClimateFigures } from "./climateSummary";
import { cropLabel, fmt } from "./labels";
import type { RotationCardModel } from "./rotationCards";
import type { Rotation } from "../types";
import { ILLUSTRATIONS } from "./illustrations";

export type AlertKind = "warning" | "info" | "neutral";
export type AlertTag = "FARM ACTION" | "CLIMATE INSIGHT" | "PLANNING REMINDER" | "ROTATION INSIGHT";

export interface DashboardAlert {
  id: string;
  kind: AlertKind;
  icon: string;
  image: string; // big picture shown on the dashboard
  title: string;
  short: string; // one plain sentence for the dashboard
  text: string; // full sentence for the report
  tag: AlertTag;
}

const DAY_MS = 86400000;

/** Next date (from today) on which one of the rotation's sowing month-days falls. */
function nextSowing(rotation: Rotation, today: Date) {
  const options = rotation.seasons.map((s) => {
    const [, m, d] = s.sowing_date.split("-").map(Number);
    let next = new Date(today.getFullYear(), m - 1, d);
    if (next.getTime() < today.getTime() - DAY_MS) next = new Date(today.getFullYear() + 1, m - 1, d);
    return { crop: s.crop, date: next };
  });
  return options.sort((a, b) => a.date.getTime() - b.date.getTime())[0];
}

/**
 * Alerts built only from data the app actually has: NASA POWER history, the comparison engine's results,
 * and the crop calendar in the farmer's current rotation. None of them is a live weather warning.
 */
export function buildAlerts({
  recent,
  year,
  cards,
  current,
  today = new Date(),
}: {
  recent: ClimateFigures | null;
  year: ClimateFigures | null;
  cards: RotationCardModel[] | null;
  current: Rotation;
  today?: Date;
}): DashboardAlert[] {
  const alerts: DashboardAlert[] = [];
  const cur = cards?.find((c) => c.isCurrent);

  if (cur?.waterM3PerAcreYear != null) {
    alerts.push({
      id: "water",
      kind: "warning",
      icon: "💧",
      image: ILLUSTRATIONS.droplet,
      title: "Check your water supply",
      short: `Your crops need about ${fmt(cur.waterM3PerAcreYear)} m³ of water per acre each year. Can your canal or tubewell give this much?`,
      text: `Your current rotation (${cur.name}) needs about ${fmt(cur.waterM3PerAcreYear)} m³ of irrigation water per acre each year (estimate). Check that your canal or tubewell supply can cover it.`,
      tag: "FARM ACTION",
    });
  }

  if (recent?.rainTotalMm != null) {
    const dry = recent.rainTotalMm < 10;
    alerts.push({
      id: "rain",
      kind: "info",
      icon: "🌧️",
      image: ILLUSTRATIONS.rain,
      title: dry ? "Very little rain lately" : "Rain in the last month",
      short: dry
        ? `Only ${fmt(recent.rainTotalMm)} mm of rain in the last 30 days. Plan to irrigate.`
        : `${fmt(recent.rainTotalMm)} mm of rain fell in the last 30 days.`,
      text:
        `${fmt(recent.rainTotalMm)} mm of rain fell in the last 30 days` +
        (year?.rainTotalMm != null ? ` and ${fmt(year.rainTotalMm)} mm in the past 12 months` : "") +
        (dry ? ". Plan irrigation rather than relying on rain." : ". These are past totals, not a forecast."),
      tag: "CLIMATE INSIGHT",
    });
  }

  const next = nextSowing(current, today);
  if (next) {
    const days = Math.round((next.date.getTime() - today.getTime()) / DAY_MS);
    const when = next.date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    alerts.push({
      id: "sowing",
      kind: "neutral",
      icon: "🗓️",
      image: ILLUSTRATIONS.calendar,
      title: days <= 14 ? `${cropLabel(next.crop)} sowing time is near` : `Next sowing: ${cropLabel(next.crop)}`,
      short: `Around ${when}${days <= 0 ? " (today)" : ` (in ${days} day${days === 1 ? "" : "s"})`}. Check the date with your local farm advisor.`,
      text: `Next sowing in your current plan: ${cropLabel(next.crop)} around ${when}${
        days <= 0 ? " (today)" : ` (in ${days} day${days === 1 ? "" : "s"})`
      }. Confirm local sowing dates with an agricultural advisor.`,
      tag: "PLANNING REMINDER",
    });
  }

  const lessWater = cards
    ?.filter((c) => c.waterVsCurrentPct != null && c.waterVsCurrentPct < -5)
    .sort((a, b) => a.waterVsCurrentPct! - b.waterVsCurrentPct!)[0];
  const noWater = cards?.filter((c) => c.waterM3PerAcreYear == null) ?? [];
  if (lessWater) {
    alerts.push({
      id: "crop-water",
      kind: "info",
      icon: "🌱",
      image: ILLUSTRATIONS.seedling,
      title: "Save water with a new crop plan",
      short: `Option ${lessWater.option} could use about ${fmt(-lessWater.waterVsCurrentPct!)}% less water than now.`,
      text: `Option ${lessWater.option} (${lessWater.name}) would need about ${fmt(-lessWater.waterVsCurrentPct!)}% less irrigation water than your current rotation.`,
      tag: "ROTATION INSIGHT",
    });
  } else if (noWater.length) {
    alerts.push({
      id: "crop-water",
      kind: "neutral",
      icon: "🌱",
      image: ILLUSTRATIONS.seedling,
      title: "Some water figures are missing",
      short: `We could not work out water use for ${noWater.map((c) => `Option ${c.option}`).join(", ")} yet.`,
      text: `Water use could not be estimated for ${noWater.map((c) => `Option ${c.option}`).join(", ")}: some crop water data is still missing.`,
      tag: "ROTATION INSIGHT",
    });
  }

  return alerts;
}
