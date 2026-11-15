import { useCallback, useEffect, useRef, useState } from "react";
import type { Location } from "../types";

export interface MyPosition {
  location: Location;
  accuracyM: number;
}

export type LocateStatus = "idle" | "locating" | "found" | "denied" | "unavailable" | "timeout" | "unsupported";

export interface MyLocation {
  status: LocateStatus;
  position: MyPosition | null;
  message: string | null; // plain-language reason when no position was found
  locate: () => void;
}

const round4 = (n: number) => Math.round(n * 1e4) / 1e4; // ~10 m: enough for a field, without raw GPS noise

/** Farmer-facing reason, with what to do next. */
function reason(status: LocateStatus): string | null {
  switch (status) {
    case "denied":
      return "Your phone did not share its location. To allow it, tap the lock or (i) next to the web address, choose Location → Allow, then press “Use my location”.";
    case "timeout":
      return "Finding your location took too long. Go outside or turn on GPS, then press “Use my location”.";
    case "unavailable":
      return "Your location could not be found right now. Turn on GPS or Location, then press “Use my location”.";
    case "unsupported":
      return "This browser cannot share your location. Pick your farm on the map instead.";
    default:
      return null;
  }
}

/**
 * The device's own position (GPS / network). With `auto`, it asks once as soon as the app opens.
 * Browsers only allow this on https or localhost, and only after the person says yes.
 */
export function useMyLocation(auto: boolean): MyLocation {
  const supported = typeof navigator !== "undefined" && "geolocation" in navigator;
  const [status, setStatus] = useState<LocateStatus>(auto ? (supported ? "locating" : "unsupported") : "idle");
  const [position, setPosition] = useState<MyPosition | null>(null);
  const asked = useRef(false);

  const locate = useCallback(() => {
    if (!supported) {
      setStatus("unsupported");
      return;
    }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({
          location: { latitude: round4(pos.coords.latitude), longitude: round4(pos.coords.longitude) },
          accuracyM: pos.coords.accuracy,
        });
        setStatus("found");
      },
      (err) => {
        setStatus(err.code === err.PERMISSION_DENIED ? "denied" : err.code === err.TIMEOUT ? "timeout" : "unavailable");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 5 * 60 * 1000 },
    );
  }, [supported]);

  useEffect(() => {
    // StrictMode runs effects twice in development: ask only once.
    if (auto && !asked.current) {
      asked.current = true;
      locate();
    }
  }, [auto, locate]);

  return { status, position, message: reason(status), locate };
}
