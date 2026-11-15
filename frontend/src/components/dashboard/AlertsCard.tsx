import type { DashboardAlert } from "../../lib/dashboardAlerts";

/** "What to do now": big picture, short title, one plain sentence per item. */
export default function AlertsCard({ alerts, loading }: { alerts: DashboardAlert[]; loading: boolean }) {
  if (!alerts.length) {
    return <p className="muted">{loading ? "Loading…" : "Nothing to do right now."}</p>;
  }
  return (
    <ul className="todo-list" id="alerts">
      {alerts.map((a) => (
        <li key={a.id} className={`dcard todo ${a.kind}`}>
          <img src={a.image} alt="" />
          <div>
            <strong>{a.title}</strong>
            <p>{a.short}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
