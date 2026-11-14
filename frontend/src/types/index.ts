// Mirrors backend/app/schemas. Keep in sync when backend schemas change.

export type CropName = "wheat" | "rice" | "maize" | "mung_bean" | "berseem";
export type RiskType = "heat" | "cold" | "drought" | "waterlogging" | "disease";
export type RiskLevel = "low" | "moderate" | "high";
export type StageType =
  | "establishment"
  | "vegetative"
  | "flowering"
  | "grain_filling"
  | "reproductive"
  | "maturity";

export interface Location {
  latitude: number;
  longitude: number;
}

export interface Priorities {
  soil_health: number;
  water: number;
  income: number;
  resilience: number;
}

export interface CropSeason {
  crop: CropName;
  sowing_date: string; // ISO date
  harvest_date: string;
  area_hectares: number;
}

export interface Rotation {
  name: string;
  seasons: CropSeason[];
  is_current?: boolean;
}

export interface ComparisonRequest {
  location: Location;
  current: Rotation;
  alternatives: Rotation[];
  priorities: Priorities;
}

export interface AdviceTip {
  risk: RiskType;
  level: RiskLevel;
  text_en: string;
  text_ur: string | null; // null until translated and reviewed
  source: string;
}

export interface CropRiskResult {
  crop: CropName;
  sowing_date: string;
  risks: Record<RiskType, number>;
  max_risk: number;
  high_days: Record<RiskType, number>;
  moderate_days: Record<RiskType, number>;
  levels: Record<RiskType, RiskLevel | null>; // null = not assessed
  advice: AdviceTip[];
  evidence_gaps: string[];
}

export interface SeasonWater {
  crop: CropName;
  sowing_date: string;
  area_hectares: number;
  // mm over the season; null = not calculated (see notes)
  et0_mm: number | null;
  crop_water_use_mm: number | null;
  rainfall_mm: number | null;
  effective_rainfall_mm: number | null;
  paddy_extra_mm: number | null;
  irrigation_need_mm: number | null;
  estimated_from_history: boolean;
  notes: string[];
}

export interface RotationWater {
  seasons: SeasonWater[];
  irrigation_need_m3: number | null;
  method: string[];
}

export interface GroundCover {
  cycle_start: string;
  cycle_end: string;
  bare_soil_days: number;
  cover_fraction: number; // 0-1, growing crops only
}

export interface SoilLayer {
  depth: string;
  top_cm: number;
  bottom_cm: number;
  clay_pct: number | null;
  sand_pct: number | null;
  silt_pct: number | null;
  organic_carbon_g_kg: number | null;
  ph_h2o: number | null;
  bulk_density_kg_dm3: number | null;
}

export interface SoilInfo {
  requested_location: Location;
  used_location: Location;
  distance_km: number;
  layers: SoilLayer[];
  topsoil_0_30cm: SoilLayer;
  texture_class: string | null;
  source: string;
  data_source: "measured" | "satellite" | "estimated" | "farmer";
  from_sample: boolean;
  notes: string[];
}

export interface RotationEvaluation {
  rotation_name: string;
  crop_results: CropRiskResult[];
  area_weighted_risk: Record<RiskType, number>;
  highest_crop_season_risk: number;
  assumptions: string[];
  water: RotationWater | null;
  ground_cover: GroundCover | null;
}

export interface DimensionScores {
  soil_health: number | null;
  water: number | null;
  income: number | null;
  resilience: number | null;
}

export interface StrategyExplanation {
  why_considered: string[];
  benefits: string[]; // versus the current rotation
  evidence: string[];
  information_gaps: string[];
  needs_local_review: string[];
}

export interface RankedRotation {
  rotation_name: string;
  is_current: boolean;
  preference_score: number | null;
  dimension_scores: DimensionScores;
  missing_dimensions: string[]; // score withheld when non-empty
  evaluation: RotationEvaluation;
  strategy: StrategyExplanation | null;
}

export interface DailyObservation {
  day: string;
  tmean_c: number | null;
  tmax_c: number | null;
  tmin_c: number | null;
  precipitation_mm: number | null;
  relative_humidity_pct: number | null;
  wind_speed_ms: number | null;
  solar_radiation_mj_m2: number | null;
  surface_soil_moisture: number | null;
  soil_moisture: number | null;
  source: "measured" | "satellite" | "estimated" | "farmer";
}

export interface DataNote {
  source: string;
  grid_cell_center: Location;
  elevation_m: number | null;
  requested_start: string;
  requested_end: string;
  latest_observation_date: string | null; // the "as of" date
  from_cache: boolean;
  from_sample: boolean;
  note: string;
}

export interface EnvironmentalData {
  observations: DailyObservation[];
  data_note: DataNote;
}

export interface Recommendation {
  ranked: RankedRotation[];
  explanation: string[];
  limitations: string[];
  resilience_risks: RiskType[]; // risks the resilience comparison is based on
  data_note: DataNote | null;
  soil: SoilInfo | null;
}

// ---- Historical vulnerability (POST /api/history) ----

export interface HistoryRequest {
  location: Location;
  seasons: CropSeason[]; // only month-day of sowing/harvest is used
  start_year?: number;
  end_year?: number;
}

export interface SeasonYear {
  sowing_year: number;
  levels: Record<RiskType, RiskLevel | null>;
  high_days: Record<RiskType, number>;
  risk_scores: Record<RiskType, number>;
  irrigation_need_mm: number | null;
}

export interface RiskHistory {
  risk: RiskType;
  years_assessed: number;
  years_high: number;
  years_moderate: number;
  share_high: number | null;
  mean_high_days: number | null;
  mean_risk_score: number | null;
  high_days_trend_per_decade: number | null; // descriptive only
}

export interface WaterHistory {
  years_calculated: number;
  median_irrigation_need_mm: number;
  p80_irrigation_need_mm: number;
  median_crop_water_use_mm: number;
}

export interface SeasonHistory {
  crop: CropName;
  sowing_month_day: string;
  harvest_month_day: string;
  season_days: number;
  years: number[];
  risks: RiskHistory[];
  water: WaterHistory | null;
  per_year: SeasonYear[];
  notes: string[];
}

export interface HistoryResult {
  location: Location;
  start_year: number;
  end_year: number;
  seasons: SeasonHistory[];
  summary: string[];
  method: string[];
  data_note: DataNote;
}

// ---- Quick check (POST /api/quick-check) ----

export interface QuickCheckRequest {
  location: Location;
  crop: CropName;
  sowing_date?: string;
  stage?: StageType;
}

export interface RiskCard {
  risk: RiskType;
  level: RiskLevel;
  reason: string;
  days_beyond_limit: number;
}

export interface DayStrip {
  day: string;
  tmax_c: number | null;
  tmin_c: number | null;
  precipitation_mm: number | null;
  soil_moisture: number | null;
}

export interface QuickCheckResult {
  crop: CropName;
  stage: StageType | null;
  stage_basis: string;
  overall: RiskLevel | null;
  cards: RiskCard[];
  not_assessed: RiskType[];
  advice: AdviceTip[];
  last_7_days: DayStrip[];
  data_note: DataNote;
  notes: string[];
}
