import { useEffect, useMemo, useState } from "react";
import { DASHBOARD_PRIORITIES, dashboardRotations } from "../lib/dashboardRotations";
import { api } from "../services/api";
import type { EnvironmentalData, Location, Recommendation, Rotation } from "../types";

const isoDaysAgo = (n: number) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

export interface Loadable<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface DashboardData {
  weather: Loadable<EnvironmentalData>;
  comparison: Loadable<Recommendation>;
  rotations: { current: Rotation; alternatives: Rotation[] };
  reload: () => void;
}

/**
 * Loads everything the dashboard, Climate Insights and Reports share for one location:
 * 12 months of NASA POWER history and the engine's comparison of the three dashboard rotations.
 */
export function useDashboardData(location: Location, enabled = true): DashboardData {
  const rotations = useMemo(() => dashboardRotations(), []);
  // Start as loading so the first paint shows placeholders, not "No data".
  const [weather, setWeather] = useState<Loadable<EnvironmentalData>>({ data: null, loading: true, error: null });
  const [comparison, setComparison] = useState<Loadable<Recommendation>>({ data: null, loading: true, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Not yet (e.g. still asking the phone for its location): stay in "loading" without fetching a wrong place.
    if (!enabled) return;
    let live = true;
    setWeather({ data: null, loading: true, error: null });
    setComparison({ data: null, loading: true, error: null });
    // Wait until the location stops changing (map clicks, typing) before calling NASA.
    const timer = setTimeout(() => {
      api
        .dailyWeather(location.latitude, location.longitude, isoDaysAgo(366), isoDaysAgo(1))
        .then((data) => live && setWeather({ data, loading: false, error: null }))
        .catch((e) => live && setWeather({ data: null, loading: false, error: message(e) }));
      api
        .compareRotations({
          location,
          current: rotations.current,
          alternatives: rotations.alternatives,
          priorities: DASHBOARD_PRIORITIES,
        })
        .then((data) => live && setComparison({ data, loading: false, error: null }))
        .catch((e) => live && setComparison({ data: null, loading: false, error: message(e) }));
    }, 700);
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // Keyed on the coordinates, not the object, so a re-render with the same place does not refetch.
  }, [location.latitude, location.longitude, rotations, attempt, enabled]);

  return { weather, comparison, rotations, reload: () => setAttempt((n) => n + 1) };
}
