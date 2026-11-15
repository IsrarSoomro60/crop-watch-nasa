import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useRef, useState } from "react";
import {
  Circle,
  CircleMarker,
  LayersControl,
  MapContainer,
  Pane,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { DISTRICTS } from "../lib/labels";
import { GIBS, NASA_LAYERS, layerDate, tileUrl } from "../lib/nasaLayers";
import NasaLayerPanel from "./NasaLayerPanel";
import type { MyPosition } from "../hooks/useMyLocation";
import type { Location } from "../types";

const GIBS_ATTRIBUTION =
  'Imagery: <a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noreferrer">NASA GIBS / EOSDIS</a>';
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>';

/** Radius shown around the farmer's own position: roughly the surrounding farm area. */
const MY_AREA_RADIUS_M = 2500;

/** Daily true-colour imagery is processed with a lag; two days back is reliably complete. */
function imageryDate(): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - 2);
  return d.toISOString().slice(0, 10);
}

const round = (n: number, dp: number) => Math.round(n * 10 ** dp) / 10 ** dp;
const same = (a: Location, b: Location | null) =>
  !!b && a.latitude === b.latitude && a.longitude === b.longitude;

function ClickToPick({ onPick }: { onPick: (l: Location) => void }) {
  useMapEvents({
    click(e) {
      onPick({ latitude: round(e.latlng.lat, 2), longitude: round(e.latlng.lng, 2) });
    },
  });
  return null;
}

/** Bring the selected point into view when it is changed from outside the map (dropdown or typed coordinates). */
function KeepInView({ value, mine }: { value: Location; mine: Location | null }) {
  const map = useMap();
  useEffect(() => {
    if (same(value, mine)) return; // "My location" does its own zoom.
    const target: [number, number] = [value.latitude, value.longitude];
    if (!map.getBounds().contains(target)) map.flyTo(target, Math.max(map.getZoom(), 6), { duration: 0.8 });
  }, [map, value, mine]);
  return null;
}

/** Zoom to the farmer's GPS position (2.5 km circle) whenever a new fix arrives, including the first one. */
function FlyToMine({ mine, isFarm }: { mine: MyPosition | null; isFarm: boolean }) {
  const map = useMap();
  const first = useRef(true);
  useEffect(() => {
    // Only when the GPS position is the chosen farm: a farm picked by hand keeps its own view.
    if (!mine || !isFarm) return;
    // Frame a box 2 x radius wide, so the 2.5 km circle fills the map.
    const bounds = L.latLng(mine.location.latitude, mine.location.longitude).toBounds(MY_AREA_RADIUS_M * 2);
    if (first.current) {
      // Opening the page: jump straight there (an animation would start at the country view).
      map.fitBounds(bounds, { animate: false });
    } else {
      map.flyToBounds(bounds, { duration: 1 }); // a new fix while the map is open: glide to it
    }
    first.current = false;
  }, [map, mine, isFarm]);
  return null;
}

/**
 * Pick a farm by tapping the map, or use the phone's location. The location itself is owned by the app
 * (useMyLocation in HomePage), so the same fix serves the start-up default and this button.
 */
export default function MapPicker({
  value,
  onChange,
  mine,
  locating,
  geoError,
  onLocateMe,
}: {
  value: Location;
  onChange: (l: Location) => void;
  mine: MyPosition | null;
  locating: boolean;
  geoError: string | null;
  onLocateMe: () => void;
}) {
  const date = imageryDate();
  const [map, setMap] = useState<L.Map | null>(null);

  const showMine = mine && same(value, mine.location);

  // NASA overlay: which layer, how many steps back from its newest image, and whether that date has no tiles.
  const [overlayKey, setOverlayKey] = useState<string | null>(null);
  const [back, setBack] = useState(0);
  const [missing, setMissing] = useState(false);
  const tiles = useRef({ loaded: 0, failed: 0 });
  const overlay = NASA_LAYERS.find((l) => l.key === overlayKey) ?? null;
  const overlayDate = overlay ? layerDate(overlay, back) : null;
  const overlayUrl = overlay ? tileUrl(overlay, overlayDate) : "";
  useEffect(() => {
    tiles.current = { loaded: 0, failed: 0 };
    setMissing(false);
  }, [overlayUrl]);

  return (
    <div className="map-wrap">
      <div className="map-box">
        <MapContainer
          ref={setMap}
          center={[value.latitude, value.longitude]}
          zoom={6}
          minZoom={3}
          maxZoom={17}
          className="map"
        >
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="Streets">
              <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution={OSM_ATTRIBUTION} maxZoom={17} />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name={`NASA satellite (${date})`}>
              <TileLayer
                url={`${GIBS}/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`}
                attribution={`${GIBS_ATTRIBUTION} · VIIRS NOAA-20`}
                maxNativeZoom={9}
                maxZoom={17}
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {/* NASA data gets its own pane above the base map (tilePane, z 200) and below markers (z 400).
              Sharing tilePane let whichever layer loaded last cover the other, so the satellite base
              image hid the data until a zoom reloaded the tiles. */}
          <Pane name="nasa-data" style={{ zIndex: 350 }}>
            {overlay && (
            <TileLayer
              key={overlayUrl}
              url={overlayUrl}
              pane="nasa-data"
              opacity={0.75}
              maxNativeZoom={overlay.level}
              maxZoom={17}
              attribution={`${GIBS_ATTRIBUTION} · ${overlay.label}`}
              eventHandlers={{
                tileload: () => {
                  tiles.current.loaded += 1;
                },
                tileerror: () => {
                  tiles.current.failed += 1;
                },
                load: () => setMissing(tiles.current.loaded === 0 && tiles.current.failed > 0),
              }}
            />
            )}
          </Pane>

          {DISTRICTS.map((d) => (
            <CircleMarker
              key={d.name}
              center={[d.location.latitude, d.location.longitude]}
              radius={7}
              pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#2a6f97", fillOpacity: 0.9 }}
              eventHandlers={{
                click: (e) => {
                  e.originalEvent.stopPropagation();
                  onChange(d.location);
                },
              }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                {d.name} · saved satellite sample
              </Tooltip>
            </CircleMarker>
          ))}

          {showMine && (
            <Circle
              center={[mine.location.latitude, mine.location.longitude]}
              radius={MY_AREA_RADIUS_M}
              interactive={false}
              pathOptions={{ color: "#2f6b3a", weight: 2, dashArray: "6 6", fillColor: "#2f6b3a", fillOpacity: 0.08 }}
            />
          )}

          <CircleMarker
            center={[value.latitude, value.longitude]}
            radius={10}
            interactive={false}
            pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#2f6b3a", fillOpacity: 1 }}
          />

          <ClickToPick onPick={onChange} />
          <KeepInView value={value} mine={mine?.location ?? null} />
          <FlyToMine mine={mine} isFarm={!!mine && same(value, mine.location)} />
        </MapContainer>

        <button
          type="button"
          className="map-locate"
          onClick={onLocateMe}
          disabled={locating || !map}
          aria-label="Use my location"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="12" cy="12" r="4" fill="currentColor" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="12" r="7.5" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
          <span>{locating ? "Finding you…" : "My location"}</span>
        </button>
      </div>

      {geoError && <p className="error small">{geoError}</p>}
      <p className="muted small">
        {showMine ? (
          <>
            The green dot is you (GPS, accurate to about {Math.round(mine.accuracyM)} m). The dashed circle is{" "}
            {MY_AREA_RADIUS_M / 1000} km around you.
          </>
        ) : (
          <>Tap the map to move your farm there. Blue dots are the sample districts.</>
        )}
      </p>
      <NasaLayerPanel
        layer={overlay}
        onLayer={(k) => {
          setOverlayKey(k);
          setBack(0);
        }}
        back={back}
        onBack={setBack}
        date={overlayDate}
        missing={missing}
        lat={value.latitude}
        lon={value.longitude}
      />
    </div>
  );
}
