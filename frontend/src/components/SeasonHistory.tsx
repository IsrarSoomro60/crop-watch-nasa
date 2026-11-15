import { ErrorBox, List } from "./common";
import type { Loadable } from "../hooks/useDashboardData";
import { LEVEL_LABEL, RISK_LABEL, cropLabel, fmt } from "../lib/labels";
import type { HistoryResult, RiskType, SeasonHistory as Season } from "../types";

const RISKS: RiskType[] = ["heat", "cold", "drought", "waterlogging", "disease"];

const monthDay = (md: string) =>
  new Date(`2000-${md}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

function trendText(perDecade: number | null): string | null {
  if (perDecade == null || Math.abs(perDecade) < 0.5) return null;
  return `${perDecade > 0 ? "↑" : "↓"} ${fmt(Math.abs(perDecade), 1)} ${perDecade > 0 ? "more" : "fewer"} high days per decade`;
}

function SeasonGrid({ season }: { season: Season }) {
  const years = season.per_year;
  return (
    <div className="history-season">
      <h3>
        {cropLabel(season.crop)} · sown {monthDay(season.sowing_month_day)}, harvested {monthDay(season.harvest_month_day)}
      </h3>
      <p className="muted small">
        Each square is one past season ({years[0]?.sowing_year}–{years[years.length - 1]?.sowing_year}), coloured by
        the worst level that risk reached.
      </p>
      <div className="table-wrap">
        <table className="yeargrid">
          <thead>
            <tr>
              <th scope="col">Risk</th>
              {years.map((y, i) => (
                <th key={y.sowing_year} scope="col" className="yr">
                  {i === 0 || i === years.length - 1 || y.sowing_year % 5 === 0 ? `'${String(y.sowing_year).slice(2)}` : ""}
                </th>
              ))}
              <th scope="col">How often High</th>
            </tr>
          </thead>
          <tbody>
            {RISKS.map((risk) => {
              const h = season.risks.find((r) => r.risk === risk);
              const assessed = !!h && h.years_assessed > 0;
              return (
                <tr key={risk}>
                  <th scope="row">{RISK_LABEL[risk]}</th>
                  {years.map((y) => {
                    const level = y.levels[risk];
                    const label = level ? LEVEL_LABEL[level] : "Not assessed";
                    return (
                      <td
                        key={y.sowing_year}
                        className={`cell ${level ?? "na"}`}
                        title={`${y.sowing_year}: ${label}${level ? `, ${y.high_days[risk]} high days` : ""}`}
                        aria-label={`${y.sowing_year}: ${label}`}
                      />
                    );
                  })}
                  <td className="small how-often">
                    {assessed ? (
                      <>
                        <strong>
                          {h!.years_high} of {h!.years_assessed}
                        </strong>
                        {trendText(h!.high_days_trend_per_decade) && (
                          <div className="muted">{trendText(h!.high_days_trend_per_decade)}</div>
                        )}
                      </>
                    ) : (
                      <span className="muted">Not assessed (no crop limit yet)</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {season.water && (
        <p className="small">
          Irrigation water needed: about <strong>{fmt(season.water.median_irrigation_need_mm)} mm</strong> in a typical
          season, more than <strong>{fmt(season.water.p80_irrigation_need_mm)} mm</strong> in about 1 season in 5.
        </p>
      )}
      <List items={season.notes} />
    </div>
  );
}

export default function SeasonHistory({
  history,
  rotationName,
}: {
  history: Loadable<HistoryResult>;
  rotationName: string;
}) {
  return (
    <section className="card" id="season-history">
      <h2>Past 20 seasons: when {rotationName} struggled</h2>
      <p className="muted small">
        The same sowing and harvest dates replayed on each of the last 20 years of NASA POWER weather. It shows how
        often each risk reached High, not what will happen next season.
      </p>
      {history.loading && <p className="muted">Loading 20 years of NASA POWER data… this can take a minute the first time.</p>}
      <ErrorBox error={history.error} />
      {history.data && (
        <>
          <h3>What stands out</h3>
          <List items={history.data.summary} />
          <div className="legend small" aria-hidden="true">
            <span><i className="cell low" /> Low</span>
            <span><i className="cell moderate" /> Moderate</span>
            <span><i className="cell high" /> High</span>
            <span><i className="cell na" /> Not assessed</span>
          </div>
          {history.data.seasons.map((s) => (
            <SeasonGrid key={`${s.crop}-${s.sowing_month_day}`} season={s} />
          ))}
          <details>
            <summary>How this is worked out</summary>
            <List items={history.data.method} />
          </details>
        </>
      )}
    </section>
  );
}
