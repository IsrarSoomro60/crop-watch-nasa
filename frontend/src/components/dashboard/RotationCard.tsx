import { CROP_IMAGE, ILLUSTRATIONS } from "../../lib/illustrations";
import { cropLabel, fmt } from "../../lib/labels";
import type { RotationCardModel } from "../../lib/rotationCards";
import { MeterBar, ScoreRing } from "./visuals";

/** Plain word for a 0-100 score the engine gives (higher is better). */
const level = (v: number | null, words: [string, string, string]) =>
  v == null ? "Not known yet" : v >= 67 ? words[0] : v >= 40 ? words[1] : words[2];
const levelColor = (v: number | null) =>
  v == null ? "var(--muted)" : v >= 67 ? "var(--accent)" : v >= 40 ? "var(--amber)" : "var(--high)";

function waterWord(c: RotationCardModel): { word: string; color: string } {
  if (c.waterM3PerAcreYear == null) return { word: "Not known yet", color: "var(--muted)" };
  if (c.isCurrent) return { word: `${fmt(c.waterM3PerAcreYear)} m³ / acre`, color: "var(--info)" };
  const d = c.waterVsCurrentPct ?? 0;
  if (Math.abs(d) < 5) return { word: "Same as now", color: "var(--info)" };
  return d < 0
    ? { word: `${fmt(-d)}% less than now`, color: "var(--accent)" }
    : { word: `${fmt(d)}% more than now`, color: "var(--high)" };
}

/** One crop plan, made to be read at a glance: pictures of the crops, a score ring and three simple meters. */
export default function RotationCard({
  card,
  maxWater,
  onDetails,
  warnings = [],
}: {
  card: RotationCardModel;
  maxWater: number | null;
  onDetails: () => void;
  warnings?: string[]; // the farmer's own limits this plan breaks (Compare page)
}) {
  const water = waterWord(card);
  return (
    <article className={`dcard plan-card${card.isTopScore ? " featured" : ""}`}>
      {card.isTopScore && <span className="ribbon">Best score</span>}
      <div className="plan-label">{card.isCurrent ? "Your crops now" : `Option ${card.option}`}</div>

      <div className="crop-strip" aria-label={card.name}>
        {card.crops.map((crop, i) => (
          <div key={`${crop}-${i}`} className="crop-step">
            {i > 0 && <span className="crop-arrow" aria-hidden="true">→</span>}
            <figure>
              <img src={CROP_IMAGE[crop]} alt="" />
              <figcaption>{cropLabel(crop)}</figcaption>
            </figure>
          </div>
        ))}
      </div>

      {warnings.length > 0 && (
        <div className="plan-warn" role="alert">
          <img src={ILLUSTRATIONS.warning} alt="" />
          <ul>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="plan-score">
        <ScoreRing score={card.suitability} />
        <div>
          <strong>How well it fits your farm</strong>
          {card.partial ? (
            <p className="partial-note">
              <img src={ILLUSTRATIONS.warning} alt="" /> Some information is missing, so this score is less sure.
            </p>
          ) : (
            <p className="muted small">Compared with the other plans here.</p>
          )}
        </div>
      </div>

      <div className="plan-meters">
        <MeterBar
          image={ILLUSTRATIONS.droplet}
          label="Water it needs"
          fraction={card.waterM3PerAcreYear == null || !maxWater ? null : card.waterM3PerAcreYear / maxWater}
          color={water.color}
          word={water.word}
        />
        <MeterBar
          image={ILLUSTRATIONS.climate}
          label="Safe from bad weather"
          fraction={card.climate == null ? null : card.climate / 100}
          color={levelColor(card.climate)}
          word={level(card.climate, ["Good", "Fair", "Risky"])}
        />
        <MeterBar
          image={ILLUSTRATIONS.seedling}
          label="Good for the soil"
          fraction={card.soil == null ? null : card.soil / 100}
          color={levelColor(card.soil)}
          word={level(card.soil, ["Good", "Fair", "Low"])}
        />
      </div>

      <span className="rotation-spacer" aria-hidden="true" />
      <button className="rotation-btn" onClick={onDetails}>
        See details
      </button>
    </article>
  );
}
