/**
 * Plain-language explanations of the science and of how the app works. Statements here are general,
 * well-established agronomy; anything that would need a local number stays a "may" or points to local review.
 */

const STEPS = [
  "You choose your farm on the map and enter your current crops, sowing and harvest dates, and area.",
  "The app downloads NASA POWER daily weather for your area: temperature, rain, humidity, sunlight and wind.",
  "Each crop's season is split into growth stages (from FAO-56). Every day is checked against that stage's limits for heat, cold, drought, waterlogging and disease-friendly weather.",
  "Crop water use is worked out with the FAO Penman-Monteith method, minus useful rain, to give the irrigation water needed.",
  "Soil health is judged from indicators: legumes in the rotation, how many days the field lies bare, and SoilGrids soil data.",
  "Scores for soil, water, income and climate risk are combined using the weights you choose. If something cannot be worked out, the score is left out rather than guessed.",
  "Each option comes with why it was suggested, its benefits, the evidence, the gaps, and what needs checking locally.",
];

const TERMS: { term: string; text: string }[] = [
  {
    term: "Evapotranspiration (ET)",
    text: "Water leaving the field as vapour: evaporation from the soil plus transpiration through the leaves. Reference ET (ETo) is what a standard grass field would use in the same weather; multiplying it by a crop coefficient (Kc) gives each crop's water use.",
  },
  {
    term: "Irrigation need / water balance",
    text: "Crop water use minus the part of the rain the crop can actually use. What is left has to come from canal, tubewell or other irrigation. Shown in m³ per acre or mm (1 mm on one acre ≈ 4 m³).",
  },
  {
    term: "NDVI (green cover)",
    text: "A satellite index from red and near-infrared light. Healthy green leaves score high; bare soil, dry plants and water score low. It shows when fields are green or bare, but cannot tell crop residue from bare soil.",
  },
  {
    term: "Soil moisture and anomalies",
    text: "How much water is in the soil. An anomaly compares it with what is normal for that time of year: a negative anomaly means drier than usual, a sign of drought stress.",
  },
  {
    term: "Heat stress",
    text: "Days when temperature goes above what a crop can take at its current stage. Flowering is the most sensitive time for many crops, for example rice and maize.",
  },
  {
    term: "Frost and cold risk",
    text: "Nights cold enough to damage a crop at its stage. The app uses the daily minimum temperature at 2 m height; the ground surface can be colder than that on clear nights.",
  },
  {
    term: "Waterlogging",
    text: "Soil so wet that roots lack air. Planned flooding in rice paddies is different and is not counted as harm for rice.",
  },
  {
    term: "Land-surface temperature",
    text: "How hot the ground or crop surface is, measured by satellite. On sunny days it is usually hotter than the air temperature that weather stations measure.",
  },
  {
    term: "Groundwater storage (GRACE)",
    text: "GRACE satellites sense tiny changes in Earth's gravity to estimate how much water is stored underground over large regions (hundreds of km). A falling trend means water is being used faster than it is refilled.",
  },
  {
    term: "Grid cell",
    text: "Satellite and model data come in squares. NASA POWER squares are about 50 km wide, so the values describe your area, not your single field.",
  },
];

const CROP_ROLES: { title: string; text: string }[] = [
  {
    title: "Nitrogen-fixing crops (legumes): mung bean, berseem",
    text: "Bacteria in their root nodules take nitrogen from the air and turn it into a form plants can use. Part of it stays in roots and residues for the next crop, which can reduce fertiliser needs. How much depends on the crop, the soil and how it is managed, so the app treats it as an indicator, not a guaranteed saving.",
  },
  {
    title: "Cover and fodder crops: berseem",
    text: "Keep the soil covered between main crops, which protects it from sun, wind and heavy rain, adds roots and organic matter, and gives animal feed. They also use water, so check your supply.",
  },
  {
    title: "Deep-rooting crops",
    text: "Roots that reach deeper layers can use water and nutrients the previous crop left behind and leave channels that help rain soak in. Rooting depth depends on the crop and the soil.",
  },
  {
    title: "Short-season and lower-water crops: mung bean, maize",
    text: "Short-season crops such as mung bean can fit into gaps between main crops. Maize usually needs much less irrigation water than flooded rice, but it is sensitive to water shortage around tasselling and silking.",
  },
  {
    title: "Breaking pest and disease cycles",
    text: "Rice, wheat and maize are all grasses, so many pests and diseases can carry over between them. Adding a crop from a different family, such as a legume, can interrupt that build-up. The app does not score pests yet; discuss them with a local advisor.",
  },
];

const DATA: { name: string; use: string; where: string }[] = [
  { name: "NASA POWER (daily)", use: "Temperature, rain, humidity, sunlight, wind; crop risks and water use", where: "All scores, Home, Weather" },
  { name: "MODIS NDVI", use: "Green cover and bare periods", where: "My Farm map and charts (4 demo districts)" },
  { name: "SMAP soil moisture", use: "Root-zone soil water", where: "My Farm map and charts" },
  {
    name: "GPM IMERG",
    use: "Daily rainfall from satellites (~10 km); replaces NASA POWER rain in the scores where saved",
    where: "Scores for the 4 demo districts (Nov 2024 – Aug 2026), My Farm map",
  },
  { name: "MODIS land-surface temperature", use: "Heat hot spots", where: "My Farm map" },
  { name: "SRTM elevation", use: "Slopes where water runs off", where: "My Farm map" },
  { name: "GRACE / GRACE-FO", use: "Regional groundwater trend", where: "Compare results, My Farm" },
  { name: "SoilGrids (ISRIC)", use: "Soil texture, organic carbon, pH", where: "Compare scores, My Farm" },
  { name: "FAOSTAT", use: "National average yields and prices", where: "Income estimate" },
];

export default function LearnView() {
  return (
    <>
      <div className="welcome">
        <div>
          <h1>Learn</h1>
          <p className="sub">What the words mean, where the data comes from, and how the comparison is made.</p>
        </div>
      </div>

      <section className="card">
        <h2>How Crop-Watch AI compares rotations</h2>
        <ol className="steps">
          {STEPS.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
        <p className="note small">
          Where you need local judgement: crop limits are provisional and need agronomist review; prices, yields,
          seed, markets and equipment are local; and NASA data describes your area, not your exact field. The tool
          supports your decision; it does not make it.
        </p>
      </section>

      <section className="card">
        <h2>Satellite data vs ground measurements</h2>
        <div className="grid">
          <div>
            <h3>Satellites and models</h3>
            <p className="small">
              Cover every field, every day or every few days, for many years. But each value is an average over a
              square several kilometres wide, and some (like NASA POWER and SMAP Level 4) are models that combine satellite
              and weather-station data.
            </p>
          </div>
          <div>
            <h3>Ground measurements</h3>
            <p className="small">
              A rain gauge, soil test or thermometer in your field is exact for that spot, but covers one place and
              often only a short time.
            </p>
          </div>
        </div>
        <p className="small">
          Together they are stronger: satellites show the long-term pattern for your area, and your own observations
          check whether your field is wetter, drier, hotter or cooler than the average.
        </p>
      </section>

      <section className="card">
        <h2>Words explained</h2>
        <dl className="glossary">
          {TERMS.map((t) => (
            <div key={t.term}>
              <dt>{t.term}</dt>
              <dd>{t.text}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h2>How crops can help the soil</h2>
        <dl className="glossary">
          {CROP_ROLES.map((c) => (
            <div key={c.title}>
              <dt>{c.title}</dt>
              <dd>{c.text}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h2>NASA and other data used</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>What for</th>
                <th>Where you see it</th>
              </tr>
            </thead>
            <tbody>
              {DATA.map((d) => (
                <tr key={d.name}>
                  <td>
                    <strong>{d.name}</strong>
                  </td>
                  <td>{d.use}</td>
                  <td className="small">{d.where}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">
          Not yet included: ECOSTRESS, Landsat and GEDI field-scale data (need an Earthdata login), and scoring for
          pests, erosion and organic matter (no local evidence for limits yet).
        </p>
      </section>
    </>
  );
}
