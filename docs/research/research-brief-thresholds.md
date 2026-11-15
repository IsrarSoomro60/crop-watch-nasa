# Thresholds taken from the team research brief

Source: *Crop-Watch AI: research brief*, 11 November 2026, Appendix B. The brief calls these
"general starting values, not tuned to Pakistani varieties or soils". All are stored with
`evidence_status: "provisional"` in `backend/app/domain/crop_profiles/`.

Mapping: the brief's **optimal max** becomes `warning` (strictly above = Moderate); its **critical**
limit becomes `critical` (at or beyond = High). Stages now follow FAO-56's four periods (see
`fao56-stage-lengths.md`): the brief's "Vegetative" row is applied to `establishment` and
`vegetative`; "Flowering to grain fill" (and the rice/maize flowering rows) to `reproductive`
(FAO mid-season). No values are applied to `maturity` (late season).

| Crop | Stage(s) | Max temp warning / critical (°C) | Min temp critical (°C) |
| --- | --- | --- | --- |
| Wheat | establishment, vegetative | 25 / 30 | 0 |
| Wheat | reproductive | 25 / 32 | 2 |
| Rice | establishment, vegetative, reproductive | 33 / 35 | 15 |
| Maize | establishment, vegetative | 35 / 40 | 10 |
| Maize | reproductive | 35 / 38 | 10 |

## Open questions before calling any of these "sourced"

- **Wheat critical 30/32 °C:** the cited sources say above 25 °C at grain filling cuts seed filling;
  the critical values look like the team's own choice.
- **Rice minimum:** the brief's source table says below 10 °C, its rules table 15 °C.
- **Rice and maize mid-season:** the brief's flowering limits now also cover grain filling.
- **Maize:** partly from MapMyCrop, a third-party site, not FAO.
- **Cotton:** in the brief but not yet in the crop set.

## Deliberately not imported

The brief labels its soil-wetness cut-offs and 7-day rain/humidity flags as the team's own
placeholders, to be calibrated. They are not in the profiles. Rice soil-wetness limits also need
checking against managed flooding.
