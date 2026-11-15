import type { CropName, Location, RiskLevel, RiskType, Rotation, StageType } from "../types";

export const CROPS: { value: CropName; label: string }[] = [
  { value: "wheat", label: "Wheat" },
  { value: "rice", label: "Rice" },
  { value: "maize", label: "Maize" },
  { value: "mung_bean", label: "Mung bean" },
  { value: "berseem", label: "Berseem" },
];

export const cropLabel = (c: CropName) => CROPS.find((x) => x.value === c)?.label ?? c;

export const RISK_LABEL: Record<RiskType, string> = {
  heat: "Heat",
  cold: "Cold / frost",
  drought: "Drought",
  waterlogging: "Waterlogging",
  disease: "Disease weather",
};

export const LEVEL_LABEL: Record<RiskLevel, string> = { low: "Low", moderate: "Moderate", high: "High" };

export const STAGES: { value: StageType; label: string }[] = [
  { value: "establishment", label: "Establishment" },
  { value: "vegetative", label: "Vegetative" },
  { value: "flowering", label: "Flowering" },
  { value: "grain_filling", label: "Grain filling" },
  { value: "reproductive", label: "Reproductive" },
  { value: "maturity", label: "Maturity" },
];

export const stageLabel = (s: StageType | null) => STAGES.find((x) => x.value === s)?.label ?? "Unknown";

/** Districts with saved NASA samples, so the demo works even if a NASA service is down. */
export const DISTRICTS: { name: string; location: Location }[] = [
  { name: "Multan", location: { latitude: 30.2, longitude: 71.47 } },
  { name: "Bahawalpur", location: { latitude: 29.4, longitude: 71.68 } },
  { name: "Larkana", location: { latitude: 27.56, longitude: 68.21 } },
  { name: "Hyderabad", location: { latitude: 25.4, longitude: 68.37 } },
];

/** Farmers enter land in acres; the API works in hectares. 1 international acre = 0.40468564224 ha. */
export const HA_PER_ACRE = 0.40468564224;
export const acresToHa = (acres: number) => acres * HA_PER_ACRE;
/** Rounded to 2 decimals so 5 acres typed in shows back as 5, not 4.999999. */
export const haToAcres = (ha: number) => Math.round((ha / HA_PER_ACRE) * 100) / 100;

/** Example rotations for one kharif + rabi cycle inside the saved sample (June 2025 - May 2026). */
export function presetRotations(area: number): { current: Rotation; alternatives: Rotation[] } {
  return {
    current: {
      name: "Rice - Wheat",
      is_current: true,
      seasons: [
        { crop: "rice", sowing_date: "2025-06-15", harvest_date: "2025-10-20", area_hectares: area },
        { crop: "wheat", sowing_date: "2025-11-15", harvest_date: "2026-04-15", area_hectares: area },
      ],
    },
    alternatives: [
      {
        name: "Maize - Wheat",
        seasons: [
          { crop: "maize", sowing_date: "2025-06-20", harvest_date: "2025-10-05", area_hectares: area },
          { crop: "wheat", sowing_date: "2025-11-10", harvest_date: "2026-04-10", area_hectares: area },
        ],
      },
      {
        name: "Rice - Berseem",
        seasons: [
          { crop: "rice", sowing_date: "2025-06-15", harvest_date: "2025-10-20", area_hectares: area },
          { crop: "berseem", sowing_date: "2025-10-28", harvest_date: "2026-04-10", area_hectares: area },
        ],
      },
      {
        name: "Mung bean - Wheat",
        seasons: [
          { crop: "mung_bean", sowing_date: "2025-07-01", harvest_date: "2025-09-20", area_hectares: area },
          { crop: "wheat", sowing_date: "2025-11-10", harvest_date: "2026-04-10", area_hectares: area },
        ],
      },
    ],
  };
}

export const fmt = (n: number | null | undefined, digits = 0) =>
  n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const fmtDate = (iso: string) =>
  new Date(iso + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
