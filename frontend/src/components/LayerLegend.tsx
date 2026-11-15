import type { LegendScale } from "../lib/nasaLayers";

/**
 * Colour key for a NASA map layer, built from NASA GIBS's own colour map (same colours as the map tiles),
 * labelled in plain words and farmer units (°C instead of Kelvin).
 */
export default function LayerLegend({ scale }: { scale: LegendScale }) {
  return (
    <figure className="layer-key" aria-label={`Colour key: ${scale.low} to ${scale.high}`}>
      <div className="key-words">
        <span>{scale.low}</span>
        <span>{scale.high}</span>
      </div>
      <div className="key-bar" style={{ background: `linear-gradient(to right, ${scale.stops.join(", ")})` }} />
      <div className="key-ticks" aria-hidden="true">
        {scale.ticks.map((t) => (
          <span key={t.label} style={{ left: `${t.at * 100}%` }}>
            {t.label}
          </span>
        ))}
      </div>
      <figcaption>{scale.caption}</figcaption>
    </figure>
  );
}
