/**
 * NASA GIBS map overlays (no login needed). Layer ids, tile levels and time steps were checked against the
 * GIBS WMTS capabilities (epsg3857/best) on 2026-11-15. Imagery only: these layers are for looking, not scoring.
 */
export const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";

export type TimeStep = "day" | "month" | "none";

export interface NasaLayer {
  key: string;
  label: string;
  gibs: string;
  level: number; // GoogleMapsCompatible_Level<n>: max native zoom
  time: TimeStep;
  stepDays: number; // for "day" layers: product period (1 = daily, 8 = 8-day)
  lagDays: number; // how far behind today the newest image usually is
  steps: number; // how far back the slider goes, in steps
  what: string;
  read: string;
  caveat: string;
  legend?: string; // official GIBS colour key, where GIBS publishes one
}

export const NASA_LAYERS: NasaLayer[] = [
  {
    key: "ndvi",
    label: "Green cover (MODIS NDVI)",
    gibs: "MODIS_Terra_NDVI_8Day",
    level: 9,
    time: "day",
    stepDays: 8,
    lagDays: 10,
    steps: 92, // ~2 years
    what: "How much living green vegetation there was, as an 8-day composite at 250 m.",
    read: "Greener means more growing plants; pale or brown means bare, dry or harvested land. Slide through the year to see when fields are green and when they lie bare.",
    caveat: "It cannot tell crop residue from bare soil, and one pixel is bigger than most fields.",
    legend: "https://gibs.earthdata.nasa.gov/legends/MODIS_NDVI_H.svg",
  },
  {
    key: "rain",
    label: "Rainfall (GPM IMERG)",
    gibs: "IMERG_Precipitation_Rate",
    level: 6,
    time: "day",
    stepDays: 1,
    lagDays: 2,
    steps: 365,
    what: "Rain on the chosen day from NASA's GPM satellites (IMERG, about 10 km).",
    read: "Coloured areas had rain that day; stronger colours mean heavier rain. Slide day by day to find storms and dry spells.",
    caveat: "A satellite estimate for the whole area, not a rain-gauge reading at your field.",
  },
  {
    key: "soil",
    label: "Soil moisture (SMAP)",
    gibs: "SMAP_L4_Analyzed_Root_Zone_Soil_Moisture",
    level: 6,
    time: "day",
    stepDays: 1,
    lagDays: 5,
    steps: 365,
    what: "Water in the root zone (top metre of soil) from SMAP Level 4, about 9 km.",
    read: "Compare wetter and drier areas and how they change after rain or irrigation seasons.",
    caveat: "A model analysis that uses satellite data, not a measurement in your field. Some days have no image.",
  },
  {
    key: "heat",
    label: "Ground heat (MODIS land temperature)",
    gibs: "MODIS_Terra_L3_Land_Surface_Temp_Monthly_Day",
    level: 6,
    time: "month",
    stepDays: 0,
    lagDays: 45,
    steps: 36,
    what: "Average daytime temperature of the ground surface for the month (MODIS Terra).",
    read: "Shows heat hot spots and how the hot season builds month by month.",
    caveat: "Ground-surface temperature, not air temperature; bare ground heats more than crops. ECOSTRESS gives field-scale detail but needs an Earthdata login.",
  },
  {
    key: "elevation",
    label: "Elevation and slope (SRTM)",
    gibs: "SRTM_Color_Index",
    level: 12,
    time: "none",
    stepDays: 0,
    lagDays: 0,
    steps: 0,
    what: "Height above sea level from the Shuttle Radar Topography Mission.",
    read: "Where colours change quickly over a short distance the land slopes: rain runs off faster and soil erodes more easily there.",
    caveat: "Elevation only; erosion risk also depends on soil, rain intensity and ground cover.",
    legend: "https://gibs.earthdata.nasa.gov/legends/SRTM_Color_Index_H.png",
  },
];

const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Date for slider position `back` (0 = newest image). */
export function layerDate(layer: NasaLayer, back: number, today = new Date()): string | null {
  if (layer.time === "none") return null;
  const newest = new Date(today.getTime() - layer.lagDays * 86400000);
  if (layer.time === "month") {
    return iso(new Date(Date.UTC(newest.getUTCFullYear(), newest.getUTCMonth() - back, 1)));
  }
  return iso(new Date(newest.getTime() - back * layer.stepDays * 86400000));
}

export function tileUrl(layer: NasaLayer, date: string | null): string {
  return `${GIBS}/${layer.gibs}/default/${date ?? "default"}/GoogleMapsCompatible_Level${layer.level}/{z}/{y}/{x}.png`;
}

/** NASA Worldview shows the same layer with its official colour key. */
export function worldviewUrl(layer: NasaLayer, date: string | null, lat: number, lon: number): string {
  const v = [lon - 4, lat - 3, lon + 4, lat + 3].map((n) => n.toFixed(2)).join(",");
  const params = new URLSearchParams({ v, l: `${layer.gibs},Coastlines_15m,Reference_Labels_15m` });
  if (date) params.set("t", date);
  return `https://worldview.earthdata.nasa.gov/?${params}`;
}

export const dateLabel = (layer: NasaLayer, date: string | null) =>
  date == null
    ? "Single map (no dates)"
    : new Date(`${date}T00:00:00`).toLocaleDateString("en-GB", {
        day: layer.time === "month" ? undefined : "numeric",
        month: "long",
        year: "numeric",
      });
