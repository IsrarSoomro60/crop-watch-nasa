import { Gauge } from "./visuals";

/**
 * One big weather tile: picture, plain name, the number, and a meter that places it within this farm's own
 * past 12 months (lowest month to highest month). "Low / Normal / High" is relative to the farm, not a crop limit.
 */
export default function WeatherTile({
  image,
  title,
  value,
  unit,
  fraction,
  color,
  low,
  high,
  loading,
}: {
  image: string;
  title: string;
  value: string | null;
  unit: string;
  fraction: number | null;
  color: string;
  low: string;
  high: string;
  loading: boolean;
}) {
  const word =
    fraction == null ? "No data" : fraction < 0.34 ? "Low for your area" : fraction < 0.67 ? "Normal for your area" : "High for your area";
  return (
    <article className="dcard weather-tile">
      <div className="weather-head">
        <img src={image} alt="" />
        <div>
          <h3>{title}</h3>
          <div className="weather-value">
            {loading ? <span className="skeleton" /> : value == null ? "—" : value}
            {!loading && value != null && <small>{unit}</small>}
          </div>
        </div>
      </div>
      {!loading && <Gauge fraction={fraction} color={color} word={word} low={low} high={high} />}
    </article>
  );
}
