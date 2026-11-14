# Growth-stage lengths from FAO-56

Source: Allen et al. (1998), *FAO Irrigation and Drainage Paper 56*, Chapter 6, **Table 11**
"Lengths of crop development stages for various planting periods and climatic regions (days)".
<https://www.fao.org/4/x0490e/x0490e0b.htm> (read 2026-11-14).

FAO's own caveat, from the table footnote: the lengths "are indicative of general conditions, but
may vary substantially from region to region, with climate and cropping conditions, and with crop
variety", and users are encouraged to get local information.

## Rows used

| Crop | Table 11 row | Plant date | Region | Init. | Dev. | Mid | Late | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wheat | Grains (small) | Oct/Nov | Pakistan; Arid Reg. | 25 | 35 | 65 | 40 | 165 |
| Rice | Rice | Dec; May | Tropics; Mediterranean | 30 | 30 | 60 | 30 | 150 |
| Maize | Maize (grain) | June | Nigeria (humid) | 20 | 35 | 40 | 30 | 125 |
| Mung bean | Green gram, cowpeas | March | Mediterranean | 20 | 30 | 30 | 20 | 110 |
| Berseem | *not in Table 11* | | | | | | | |

Choices made:

- **Wheat:** the table's wheat-specific rows are for Central India, California and Idaho. The
  "Grains (small)" row is the only one listing Pakistan, so it is used. The Central India
  "Barley/Oats/Wheat" row (November, 15/25/50/30 = 120) is an alternative if local data favours it.
- **Rice:** no Pakistan row; the 150-day row is used (the other is 30/30/80/40 = 180, May, Tropics).
- **Maize:** the June planting row matches kharif sowing. The "India (dry, cool)" October row has
  the same lengths.
- **Mung bean:** green gram is mung bean. Pakistani mung is often a short summer crop; scaling
  (below) keeps the proportions but local lengths would be better.

## How the engine uses them

FAO-56 has four periods. They map to the profiles' stage types as:

| FAO-56 period | `stage_type` | Weight (provisional) |
| --- | --- | --- |
| Initial | `establishment` | 1.25 |
| Crop development | `vegetative` | 1.0 |
| Mid-season (flowering through most grain/pod filling) | `reproductive` | 2.0 (higher of flowering 2.0 and grain filling 1.75) |
| Late season (maturity to harvest) | `maturity` | 1.0 |

The lengths are **scaled to each season's actual sowing-to-harvest length**, keeping each period's
share. For example, a 120-day wheat season gets 18/26/47/29 days. This is an engineering choice;
the response's `evidence_gaps` says when it happened.

Research-brief temperature limits were moved onto these periods. The brief's "Flowering to grain
fill" row maps to mid-season. Where the brief gives a flowering-only limit (maize 38 °C, rice), it
is now applied to the whole mid-season, which is noted in the threshold. No limits exist yet for the
late season, so heat or cold in that period is reported as not assessed.
