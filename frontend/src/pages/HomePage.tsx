import { useEffect, useState } from "react";
import { LocationPicker } from "../components/common";
import MapPicker from "../components/MapPicker";
import { useDashboardData } from "../hooks/useDashboardData";
import { useMyLocation } from "../hooks/useMyLocation";
import { useSeasonHistory } from "../hooks/useSeasonHistory";
import { DISTRICTS } from "../lib/labels";
import { ILLUSTRATIONS } from "../lib/illustrations";
import { PAGES, type Navigate, type PageId } from "../lib/pages";
import type { Location, Rotation } from "../types";
import AreaView from "./AreaView";
import ClimateInsightsView from "./ClimateInsightsView";
import CompareView from "./CompareView";
import DashboardView from "./DashboardView";
import LearnView from "./LearnView";
import ReportsView from "./ReportsView";

const PROVINCE: Record<string, string> = {
  Multan: "Punjab",
  Bahawalpur: "Punjab",
  Larkana: "Sindh",
  Hyderabad: "Sindh",
};

function placeName(l: Location, fromGps: boolean): string {
  const d = DISTRICTS.find((x) => x.location.latitude === l.latitude && x.location.longitude === l.longitude);
  if (d) return `${d.name}, ${PROVINCE[d.name] ?? ""}, Pakistan`.replace(", ,", ",");
  return `${fromGps ? "My location" : "Your field"} (${l.latitude.toFixed(2)}, ${l.longitude.toFixed(2)})`;
}

/** Where the farm location came from: the phone (gps), the farmer's own pick (manual), or the sample farm. */
type LocationSource = "default" | "gps" | "manual";

export default function HomePage() {
  const [page, setPage] = useState<PageId>("dashboard");
  const [anchor, setAnchor] = useState<string | null>(null);
  const [location, setLocation] = useState<Location>(DISTRICTS[0].location);
  const [urdu, setUrdu] = useState(false);
  // Bumped to restart Compare Rotations with the dashboard's rotations ("View details").
  const [compareStart, setCompareStart] = useState<{ key: number; initial?: { current: Rotation; alternatives: Rotation[] } }>({
    key: 0,
  });
  // Use the phone's location by default; until it answers, no data is loaded for the sample farm.
  const myLoc = useMyLocation(true);
  const [locSource, setLocSource] = useState<LocationSource>("default");
  useEffect(() => {
    // A new GPS fix wins unless the farmer has picked a place by hand since.
    if (myLoc.position && locSource !== "manual") {
      setLocation(myLoc.position.location);
      setLocSource("gps");
    }
  }, [myLoc.position]); // eslint-disable-line react-hooks/exhaustive-deps
  const chooseLocation = (l: Location) => {
    setLocation(l);
    setLocSource("manual");
  };
  const useMyPosition = () => {
    setLocSource("gps"); // the farmer asked for it, so it may replace a manual pick
    myLoc.locate();
  };
  const waitingForGps = myLoc.status === "locating" && locSource === "default";
  const dashboard = useDashboardData(location, !waitingForGps);
  // The 20-season history downloads ~20 years of weather, so it starts the first time Climate Insights opens.
  const [climateOpened, setClimateOpened] = useState(false);
  useEffect(() => {
    if (page === "climate") setClimateOpened(true);
  }, [page]);
  const history = useSeasonHistory(location, dashboard.rotations.current.seasons, climateOpened);
  const place = placeName(location, locSource === "gps");
  const showLocBanner = locSource === "default" && myLoc.status !== "found";

  const navigate: Navigate = (to, target) => {
    setPage(to);
    setAnchor(target ?? null);
  };

  useEffect(() => {
    // Runs after the new page is shown, so the anchor element is visible and measurable.
    if (anchor) document.getElementById(anchor)?.scrollIntoView({ block: "start" });
    else window.scrollTo({ top: 0 });
  }, [page, anchor]);

  function openDashboardComparison() {
    setCompareStart((s) => ({ key: s.key + 1, initial: dashboard.rotations }));
    navigate("compare");
  }

  const farmLine = (
    <p className="location-line page-farm">
      <span aria-hidden="true">⌖</span> Farm: {place}
      <span className="sep">·</span>
      <button className="link-btn inline" onClick={() => navigate("farm")}>
        Change
      </button>
    </p>
  );

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <img src={ILLUSTRATIONS.seedling} alt="" />
          </span>
          <div>
            Crop-Watch AI<small>Smarter crop rotation decisions</small>
          </div>
        </div>
        <div className="top-actions">
          <label className="lang">
            <span className="sr-only">Tips language</span>
            <select value={urdu ? "ur" : "en"} onChange={(e) => setUrdu(e.target.value === "ur")} title="Tips language">
              <option value="en">English</option>
              <option value="ur">اردو (draft)</option>
            </select>
          </label>
          <button
            className="icon-btn"
            aria-label="What to do now"
            title="What to do now"
            onClick={() => navigate("dashboard", "alerts")}
          >
            <img src={ILLUSTRATIONS.bell} alt="" />
          </button>
          <button className="avatar" title="My farm" aria-label="My farm" onClick={() => navigate("farm")}>
            <img src={ILLUSTRATIONS.farmer} alt="" />
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="nav-label">MENU</div>
          <nav className="nav" aria-label="Main navigation">
            {PAGES.map((p) => (
              <button
                key={p.id}
                className={page === p.id ? "active" : ""}
                aria-current={page === p.id ? "page" : undefined}
                onClick={() => navigate(p.id)}
              >
                <img className="ico" src={p.icon} alt="" />
                {p.label}
              </button>
            ))}
          </nav>
          <div className="side-help">
            <strong>Need help?</strong>
            <p>Pick your farm on the map, then compare your rotation with two alternatives.</p>
            <button className="link-btn inline" onClick={() => navigate("farm")}>
              Set my farm →
            </button>
          </div>
        </aside>

        <main className="content">
          {showLocBanner && (
            <div className={`loc-banner dcard${myLoc.status === "locating" ? " busy" : ""}`} role="status">
              <img src={ILLUSTRATIONS.pin} alt="" />
              <div className="loc-text">
                <strong>
                  {myLoc.status === "locating"
                    ? "Finding your location…"
                    : "We could not find your location, so a sample farm (Multan) is shown"}
                </strong>
                <p>
                  {myLoc.status === "locating"
                    ? "If your phone asks, tap “Allow” so we can show the weather and crops for your own farm."
                    : myLoc.message}
                </p>
              </div>
              {myLoc.status !== "locating" && (
                <div className="loc-actions">
                  {myLoc.status !== "unsupported" && (
                    <button className="primary" onClick={useMyPosition}>
                      Use my location
                    </button>
                  )}
                  <button className="secondary" onClick={() => navigate("farm")}>
                    Pick on the map
                  </button>
                </div>
              )}
            </div>
          )}
          {/* Dashboard, Compare and Climate stay mounted so inputs and results survive page switches. */}
          <div hidden={page !== "dashboard"}>
            <DashboardView
              data={dashboard}
              placeName={place}
              navigate={navigate}
              onRotationDetails={openDashboardComparison}
            />
          </div>

          {page === "farm" && (
            <>
              <div className="welcome">
                <div>
                  <h1>My farm</h1>
                  <p className="sub">Choose your district, tap your field on the map, or use your phone's location.</p>
                </div>
              </div>
              <section className="card">
                <LocationPicker value={location} onChange={chooseLocation} />
                <MapPicker
                  value={location}
                  onChange={chooseLocation}
                  mine={myLoc.position}
                  locating={myLoc.status === "locating"}
                  geoError={locSource !== "manual" ? myLoc.message : null}
                  onLocateMe={useMyPosition}
                />
              </section>
              <AreaView location={location} />
            </>
          )}

          <div hidden={page !== "compare"}>
            <div className="welcome">
              <div>
                <h1>Compare crop plans</h1>
                <p className="sub">Find which crop plan fits your farm best, in 3 easy steps.</p>
                {farmLine}
              </div>
            </div>
            <CompareView key={compareStart.key} location={location} urdu={urdu} initial={compareStart.initial} />
          </div>

          <div hidden={page !== "climate"}>
            <ClimateInsightsView
              weather={dashboard.weather}
              history={history}
              rotationName={`your current rotation (${dashboard.rotations.current.name})`}
              location={location}
              urdu={urdu}
              header={farmLine}
            />
          </div>

          {page === "reports" && <ReportsView data={dashboard} placeName={place} />}
          {page === "learn" && <LearnView />}

          <footer className="muted small app-footer">
            Thresholds and scores are provisional and need local agronomist review. Results support, not replace, local
            advice.
          </footer>
        </main>
      </div>
    </div>
  );
}
