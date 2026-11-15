# Phase 2–3 sources: mung bean, berseem, crop coefficients, irrigation need

All read on 2026-11-14. Values are stored in `backend/app/domain/crop_profiles/`.

## Mung bean (Vigna radiata)

| Item | Value used | Source |
| --- | --- | --- |
| Cold (all stages) | daily **mean** ≤ 15 °C = High | Feedipedia, citing Mogotsi 2006 (PROTA): optimal about 28–30 °C, "always above 15 °C". The source doesn't say mean or minimum; mean is our reading. <https://www.feedipedia.org/node/235> |
| Heat (mid-season only) | Tmax > 35 °C Moderate, ≥ 40 °C High | Frontiers in Genetics 2023 (10.3389/fgene.2023.1206451) and Scientia Horticulturae 2016 (S0304423816305350): above 40 °C at the reproductive stage is highly damaging to flowering and pod set. 35 °C is the top of the 27–35 °C efficient-growth range (Russ. J. Plant Physiol. 2024, 10.1134/S1021443724605421), which also calls mung bean thermotolerant in the vegetative phase. |

Status: provisional. Waterlogging sensitivity and seed spoilage from high moisture at maturity are
noted in the sources, without numbers.

## Berseem (Trifolium alexandrinum)

| Item | Value used | Source |
| --- | --- | --- |
| Cold (all stages) | Tmin ≤ −6 °C = High | Feedipedia, citing Suttie 1999 (FAO): frost tolerance down to −6 °C, as low as −15 °C for some cultivars. <https://www.feedipedia.org/node/248> |
| Heat | not set | Same source: "does not grow well under hot summer conditions", no number. |
| Cutting cycle | notes only | First cut 50–60 days after planting, then every 30–40 days; 5–6 cuts under irrigation. Not enough for FAO-style stage lengths, so berseem growth stages and water use stay uncalculated. |

The fuller FAO book *Egyptian Clover (Trifolium alexandrinum)* (FAO, I3500E), which has a Pakistan
chapter, wasn't read yet and is the next place to look for heat limits and stage lengths.

## FAO-56 Table 12 crop coefficients (Kc)

<https://www.fao.org/4/x0490e/x0490e0b.htm>. Table 12 assumes a subhumid climate (minimum RH about
45%, wind about 2 m/s); the FAO-56 eq. 62 climate adjustment is not applied.

| Crop | Row | Kc ini | Kc mid | Kc end | Choice |
| --- | --- | --- | --- | --- | --- |
| Wheat | Spring Wheat (Kc ini from cereals group) | 0.3 | 1.15 | 0.4 | 0.4 = hand-harvested (footnote 10); 0.25 otherwise |
| Rice | Rice | 1.05 | 1.20 | 0.75 | midpoint of FAO's 0.90–0.60 |
| Maize | Maize, Field (grain) (Kc ini from cereals group) | 0.3 | 1.20 | 0.35 | field-dried grain (footnote 11); 0.60 at high grain moisture |
| Mung bean | Green Gram and Cowpeas (Kc ini from legume group) | 0.4 | 1.05 | 0.35 | harvested dry (footnote 6); 0.60 fresh |
| Berseem | Clover hay, Berseem, averaged cutting effects | 0.40 | 0.90 | 0.85 | stored but unused until stage lengths exist |

## Irrigation need

FAO Irrigation Water Management Training Manual 3, chapter 4
(<https://www.fao.org/4/s2022e/s2022e08.htm>):

- Effective rainfall per month: `Pe = 0.8P − 25` if P > 75 mm, else `0.6P − 10`, never negative.
  The manual gives these as simple formulas for slopes up to 4–5%. Part-months are scaled to 30 days
  and back.
- Irrigation need `IN = ETc − Pe`.
- Paddy rice: `IN = ETc + SAT + PERC + WL − Pe` with the manual's simplified values SAT = 200 mm,
  PERC = 6 mm/day (4 heavy clay to 8 sandy), WL = 100 mm.

Not included: groundwater capillary rise, irrigation efficiency losses, salt leaching.
