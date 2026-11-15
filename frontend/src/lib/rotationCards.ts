import type { CropName, RankedRotation, Recommendation, Rotation } from "../types";
import { HA_PER_ACRE } from "./labels";

/** Farmer-facing view of one engine result. All numbers come from the comparison engine; nothing is invented. */
export interface RotationCardModel {
  option: string; // "A", "B", "C"
  name: string;
  crops: CropName[]; // in sowing order, for the crop pictures
  isCurrent: boolean;
  suitability: number | null; // 0-100, relative to the options compared
  partial: boolean; // score leaves out dimensions with missing data
  partialNote: string | null;
  waterM3PerAcreYear: number | null;
  waterVsCurrentPct: number | null; // negative = less water than current
  climate: number | null; // resilience, 0-100
  soil: number | null; // soil-health indicator, 0-100
  explanation: string;
  cycleYears: number;
  isTopScore: boolean;
}

const DIMENSION_LABEL: Record<string, string> = {
  income: "income (no local yield or price yet)",
  water: "water use (a crop's water data is missing)",
  resilience: "climate risk (some crop limits are missing)",
  soil_health: "soil health",
};

const pct = (x: number | null) => (x == null ? null : Math.round(x * 100));

function farmAcres(rotation: Rotation): number {
  const ha = Math.max(...rotation.seasons.map((s) => s.area_hectares));
  return ha / HA_PER_ACRE;
}

function explain(r: RankedRotation): string {
  if (r.is_current) return "Your existing rotation, used as the baseline for comparison.";
  return r.strategy?.benefits[0] ?? r.strategy?.why_considered[0] ?? "Alternative rotation to compare with your current one.";
}

/**
 * Cards in the order the rotations were sent (A = current, then the alternatives), not in ranked order,
 * so no option is presented as "the answer" by position. The top score is flagged from the data.
 */
export function rotationCards(rec: Recommendation, sent: Rotation[]): RotationCardModel[] {
  const byName = new Map(rec.ranked.map((r) => [r.rotation_name, r]));
  const current = rec.ranked.find((r) => r.is_current);
  const currentWater = current?.evaluation.water?.irrigation_need_m3_per_year ?? null;
  // Only full scores compete for "Highest score": a partial score rests on less evidence.
  const scored = rec.ranked.filter((r) => r.preference_score != null && !r.partial);
  const top = scored.length > 1 ? scored.reduce((a, b) => (b.preference_score! > a.preference_score! ? b : a)) : null;

  return sent.flatMap((rot, i) => {
    const r = byName.get(rot.name);
    if (!r) return [];
    const acres = farmAcres(rot);
    const water = r.evaluation.water?.irrigation_need_m3_per_year ?? null;
    return [
      {
        option: String.fromCharCode(65 + i),
        name: r.rotation_name,
        crops: [...rot.seasons].sort((a, b) => a.sowing_date.localeCompare(b.sowing_date)).map((s) => s.crop),
        isCurrent: r.is_current,
        suitability: pct(r.preference_score),
        partial: r.partial,
        partialNote: r.partial
          ? `Partial score: leaves out ${r.missing_dimensions.map((d) => DIMENSION_LABEL[d] ?? d).join(", ")}.`
          : r.preference_score == null
            ? "Not scored: none of the dimensions could be worked out."
            : null,
        waterM3PerAcreYear: water == null ? null : water / acres,
        waterVsCurrentPct:
          water == null || currentWater == null || r.is_current ? null : ((water - currentWater) / currentWater) * 100,
        climate: pct(r.dimension_scores.resilience),
        soil: pct(r.dimension_scores.soil_health),
        explanation: explain(r),
        cycleYears: r.evaluation.cycle_years,
        isTopScore: top?.rotation_name === r.rotation_name,
      },
    ];
  });
}
