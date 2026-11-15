import { ILLUSTRATIONS } from "../lib/illustrations";
import { NASA_LAYERS, type NasaLayer, dateLabel, worldviewUrl } from "../lib/nasaLayers";
import LayerLegend from "./LayerLegend";

/** Picture and plain name for each NASA layer button. */
const BUTTONS: Record<string, { image: string; name: string }> = {
  ndvi: { image: ILLUSTRATIONS.plant, name: "Green crops" },
  rain: { image: ILLUSTRATIONS.rain, name: "Rain" },
  soil: { image: ILLUSTRATIONS.droplet, name: "Soil wetness" },
  heat: { image: ILLUSTRATIONS.thermometer, name: "Ground heat" },
  elevation: { image: ILLUSTRATIONS.pin, name: "Land height" },
};

/** Under the map: pick what NASA data to show (picture buttons), move through dates, and read its colour key. */
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
      <p className="layer-ask">What do you want to see on the map?</p>
      <div className="layer-buttons" role="radiogroup" aria-label="NASA data on the map">
        <button
          type="button"
          role="radio"
          aria-checked={layer == null}
          className={`layer-btn${layer == null ? " on" : ""}`}
          onClick={() => onLayer(null)}
        >
          <img src={ILLUSTRATIONS.home} alt="" />
          <span>Just the map</span>
        </button>
        {NASA_LAYERS.map((l) => (
          <button
            key={l.key}
            type="button"
            role="radio"
            aria-checked={layer?.key === l.key}
            className={`layer-btn${layer?.key === l.key ? " on" : ""}`}
            onClick={() => onLayer(l.key)}
          >
            <img src={BUTTONS[l.key]?.image ?? ILLUSTRATIONS.pin} alt="" />
            <span>{BUTTONS[l.key]?.name ?? l.label}</span>
          </button>
        ))}
      </div>

      {layer && (
        <div className="layer-help">
          {layer.time !== "none" && (
            <div className="layer-date">
              <button type="button" className="secondary" onClick={() => onBack(Math.min(layer.steps, back + 1))}>
                ← Earlier
              </button>
              <div className="layer-date-mid">
                <strong>{dateLabel(layer, date)}</strong>
                {/* Slider runs oldest (left) to newest (right); `back` counts steps back from the newest image. */}
                <input
                  type="range"
                  min={0}
                  max={layer.steps}
                  value={layer.steps - back}
                  onChange={(e) => onBack(layer.steps - Number(e.target.value))}
                  aria-label={`Date for ${layer.label}`}
                />
              </div>
              <button type="button" className="secondary" onClick={() => onBack(Math.max(0, back - 1))} disabled={back === 0}>
                Later →
              </button>
            </div>
          )}
          {missing && <p className="note small">NASA has no picture for this date here. Try an earlier or later date.</p>}

          {layer.scale ? (
            <LayerLegend scale={layer.scale} />
          ) : (
            layer.legend && <img className="layer-legend" src={layer.legend} alt={`Colour key for ${layer.label}`} />
          )}

          <p className="layer-read">{layer.read}</p>
          <details className="layer-more">
            <summary>More about this picture</summary>
            <p className="small">
              <strong>{layer.label}.</strong> {layer.what} {layer.caveat}{" "}
              <a href={worldviewUrl(layer, date, lat, lon)} target="_blank" rel="noreferrer">
                Open in NASA Worldview
              </a>
              .
            </p>
          </details>
        </div>
      )}
    </div>
  );
}
