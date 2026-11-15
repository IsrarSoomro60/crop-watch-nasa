import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { CropSeason, HistoryResult, Location } from "../types";
import type { Loadable } from "./useDashboardData";

/**
 * 20 past seasons of the given crop calendar at this location (POST /api/history).
 * Starts only once `active` is true: it downloads ~20 years of NASA POWER data, so it waits
 * until the farmer opens the page that shows it.
 */
export function useSeasonHistory(location: Location, seasons: CropSeason[], active: boolean): Loadable<HistoryResult> {
  const [state, setState] = useState<Loadable<HistoryResult>>({ data: null, loading: false, error: null });
  const key = seasons.map((s) => `${s.crop}:${s.sowing_date}:${s.harvest_date}`).join("|");

  useEffect(() => {
    if (!active) return;
    let live = true;
    setState({ data: null, loading: true, error: null });
    const timer = setTimeout(() => {
      api
        .history({ location, seasons })
        .then((data) => live && setState({ data, loading: false, error: null }))
        .catch((e) => live && setState({ data: null, loading: false, error: e instanceof Error ? e.message : String(e) }));
    }, 700);
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // Keyed on coordinates and the calendar, not object identity.
  }, [active, location.latitude, location.longitude, key]); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
