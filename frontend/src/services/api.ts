import type {
  ComparisonRequest,
  EnvironmentalData,
  HistoryRequest,
  HistoryResult,
  QuickCheckRequest,
  QuickCheckResult,
  Recommendation,
  SatelliteData,
  SoilInfo,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  dailyWeather: (latitude: number, longitude: number, start: string, end: string) =>
    request<EnvironmentalData>(
      `/environmental-data/daily?${new URLSearchParams({
        latitude: String(latitude),
        longitude: String(longitude),
        start,
        end,
      })}`,
    ),
  soil: (latitude: number, longitude: number) =>
    request<SoilInfo>(`/soil?${new URLSearchParams({ latitude: String(latitude), longitude: String(longitude) })}`),
  satellite: (latitude: number, longitude: number) =>
    request<SatelliteData>(
      `/satellite?${new URLSearchParams({ latitude: String(latitude), longitude: String(longitude) })}`,
    ),
  history: (body: HistoryRequest) =>
    request<HistoryResult>("/history", { method: "POST", body: JSON.stringify(body) }),
  quickCheck: (body: QuickCheckRequest) =>
    request<QuickCheckResult>("/quick-check", { method: "POST", body: JSON.stringify(body) }),
  compareRotations: (body: ComparisonRequest) =>
    request<Recommendation>("/rotations/compare", { method: "POST", body: JSON.stringify(body) }),
};
