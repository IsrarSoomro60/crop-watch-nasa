import { NASA_LAYERS, type NasaLayer, dateLabel, worldviewUrl } from "../lib/nasaLayers";

/** Controls under the map: which NASA layer to overlay, which date, and how to read it. */
export default function NasaLayerPanel({
  layer,
  onLayer,
  back,
  onBack,
  date,
  missing,
  lat,
  lon,
}: {
  layer: NasaLayer | null;
  onLayer: (key: string | null) => void;
  back: number;
  onBack: (n: number) => void;
  date: string | null;
  missing: boolean;
  lat: number;
  lon: number;
}) {
  return (
    <div className="layer-panel">
      <div className="row">
        <label className="field">
          NASA data on the map
          <select value={layer?.key ?? ""} onChange={(e) => onLayer(e.target.value || null)}>
            <option value="">None</option>
            {NASA_LAYERS.map((l) => (
              <option key={l.key} value={l.key}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        {layer && layer.time !== "none" && (
          <label className="field layer-date">
            <span>
              Date: <strong>{dateLabel(layer, date)}</strong>
            </span>
            {/* Slider runs oldest (left) to newest (right); `back` counts steps back from the newest image. */}
            <input
              type="range"
              min={0}
              max={layer.steps}
              value={layer.steps - back}
              onChange={(e) => onBack(layer.steps - Number(e.target.value))}
              aria-label={`Date for ${layer.label}`}
            />
            <span className="layer-steps">
              <button type="button" className="secondary small-btn" onClick={() => onBack(Math.min(layer.steps, back + 1))}>
                ← Earlier
              </button>
              <button type="button" className="secondary small-btn" onClick={() => onBack(Math.max(0, back - 1))} disabled={back === 0}>
                Later →
              </button>
            </span>
          </label>
        )}
      </div>

      {layer && (
        <div className="layer-help">
          <p>
            <strong>{layer.label}.</strong> {layer.what} {layer.read}
          </p>
          {missing && <p className="note small">NASA has no image for this date here. Try an earlier or later date.</p>}
          {layer.legend && <img className="layer-legend" src={layer.legend} alt={`Colour key for ${layer.label}`} />}
          <p className="muted small">
            {layer.caveat}{" "}
            <a href={worldviewUrl(layer, date, lat, lon)} target="_blank" rel="noreferrer">
              Open in NASA Worldview
            </a>{" "}
            for the colour key and more dates.
          </p>
        </div>
      )}
    </div>
  );
}
