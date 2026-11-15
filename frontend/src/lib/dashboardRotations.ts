import type { Rotation } from "../types";
import { acresToHa } from "./labels";

/** Farm size the dashboard comparison assumes. Farmers can change it in Compare Rotations. */
export const DASHBOARD_FARM_ACRES = 5;

/**
 * The three rotations the dashboard compares. Season dates are planning assumptions (typical Sindh/Punjab
 * calendars) replayed on past NASA POWER weather, so every score is historical, not a forecast.
 *
 * Wheat and berseem are both winter (rabi) crops, so "Wheat -> Berseem -> Maize" cannot fit in one year:
 * it runs as a two-year cycle with a summer gap after wheat. The engine counts that gap as bare soil.
 */
export function dashboardRotations(acres = DASHBOARD_FARM_ACRES): { current: Rotation; alternatives: Rotation[] } {
  const area_hectares = acresToHa(acres);
  return {
    current: {
      name: "Wheat → Rice",
      is_current: true,
      seasons: [
        { crop: "wheat", sowing_date: "2024-11-15", harvest_date: "2025-04-15", area_hectares },
        { crop: "rice", sowing_date: "2025-06-15", harvest_date: "2025-10-20", area_hectares },
      ],
    },
    alternatives: [
      {
        name: "Wheat → Mung bean → Maize",
        is_current: false,
        seasons: [
          { crop: "wheat", sowing_date: "2024-11-15", harvest_date: "2025-04-15", area_hectares },
          { crop: "mung_bean", sowing_date: "2025-04-25", harvest_date: "2025-07-05", area_hectares },
          { crop: "maize", sowing_date: "2025-07-15", harvest_date: "2025-10-30", area_hectares },
        ],
      },
      {
        name: "Wheat → Berseem → Maize",
        is_current: false,
        seasons: [
          { crop: "wheat", sowing_date: "2024-11-10", harvest_date: "2025-04-10", area_hectares },
          { crop: "berseem", sowing_date: "2025-10-28", harvest_date: "2026-04-10", area_hectares },
          { crop: "maize", sowing_date: "2026-04-20", harvest_date: "2026-08-10", area_hectares },
        ],
      },
    ],
  };
}

/** Equal weights: the dashboard does not assume what a farmer cares about most. */
export const DASHBOARD_PRIORITIES = { soil_health: 25, water: 25, income: 25, resilience: 25 };
