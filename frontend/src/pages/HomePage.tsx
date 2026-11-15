import { useState } from "react";
import { LocationPicker } from "../components/common";
import { DISTRICTS } from "../lib/labels";
import type { Location } from "../types";
import AreaView from "./AreaView";
import CompareView from "./CompareView";
import QuickCheckView from "./QuickCheckView";

const TABS = [
  { id: "compare", label: "Compare rotations" },
  { id: "quick", label: "This week's risk" },
  { id: "area", label: "My area" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function HomePage() {
  const [tab, setTab] = useState<Tab>("compare");
  const [location, setLocation] = useState<Location>(DISTRICTS[0].location);
  const [urdu, setUrdu] = useState(false);

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Crop-Watch AI</h1>
          <p>Compare your crop rotation with alternatives on risk, water, soil health and income, using NASA data.</p>
        </div>
        <label className="field">
          Tips language
          <select value={urdu ? "ur" : "en"} onChange={(e) => setUrdu(e.target.value === "ur")}>
            <option value="en">English</option>
            <option value="ur">اردو (draft)</option>
          </select>
        </label>
      </header>

      <section className="card" style={{ marginTop: 16 }}>
        <LocationPicker value={location} onChange={setLocation} />
      </section>

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {/* Keep views mounted so inputs and results survive tab switches. */}
      <div hidden={tab !== "compare"}>
        <CompareView location={location} urdu={urdu} />
      </div>
      <div hidden={tab !== "quick"}>
        <QuickCheckView location={location} urdu={urdu} />
      </div>
      <div hidden={tab !== "area"}>{tab === "area" && <AreaView location={location} />}</div>

      <footer className="muted small" style={{ marginTop: 24 }}>
        Thresholds and scores are provisional and need local agronomist review. Results support, not replace, local
        advice.
      </footer>
    </div>
  );
}
