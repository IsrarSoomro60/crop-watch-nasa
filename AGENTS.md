# Crop-Watch AI

Project context for Crop-Watch AI, a NASA Space Apps Challenge 2026 project in the **Field Shift** challenge. This file describes the intended product and current working assumptions; it is context, not a fixed technical specification. Check the repository and task at hand before deciding how to implement anything.

## Product goal

Help farmers compare multi-season crop rotations and understand which options may fit their farm conditions and priorities. The intended comparison includes the farmer's current rotation and at least two alternatives.

Possible priorities include water conservation, soil health, income, and climate resilience. The system is intended to use environmental and agricultural information to explain risks and tradeoffs. Some information may come from the farmer or be estimated; full automation should not be assumed.

## Prototype scope

The initial crop set is:

- Wheat
- Rice
- Maize
- Mung bean
- Berseem

This is the initial prototype scope, not a permanent limit. Crop profiles are one possible way to support growth, but the repository's existing design and the needs of a task should guide implementation choices.

## Agricultural context

Relevant environmental risks include heat, cold and frost, drought and water stress, excessive rainfall and waterlogging, and humidity or other disease-conducive conditions. Their significance depends on crop, growth stage, exposure duration and severity, and the available environmental and historical data.

Examples to consider when researching or modeling crop-specific sensitivity:

- Rice can be especially sensitive to heat during flowering.
- Wheat cold sensitivity varies by growth stage.
- Maize can be sensitive to water stress around tasseling and silking.
- Mung bean can be vulnerable to drought during pod filling and to prolonged waterlogging.
- Managed flooding in rice is different from harmful waterlogging in other crops.

These examples do not provide numeric thresholds. Crop-specific thresholds and durations require credible supporting evidence; where evidence is unavailable, identify the gap rather than treating an estimate as established fact.

## Data and evidence

Potential inputs include NASA Earth observation data and relevant weather, rainfall, soil moisture, and agricultural datasets. Agricultural references may include FAO, CGIAR, CIMMYT, IRRI, CABI, and peer-reviewed research.

No single source should be assumed to provide every needed measurement or crop-specific threshold. Confirm the contents and limitations of a dataset before relying on it. Keep clear whether an input is measured, satellite-derived, estimated, or provided by the farmer, and make important missing data and uncertainty visible.

It is useful to distinguish two kinds of knowledge:

1. **Agricultural evidence:** crop-specific conditions, sensitivities, stages, thresholds, and exposure durations supported by research or credible sources.
2. **Scoring choices:** engineering methods that turn inputs into comparable values. These may be useful design proposals, but are not automatically scientific findings.

## Example scoring proposal

The values below were proposed as an initial engineering framework. They are provisional, not validated universal coefficients, and can be revised or replaced as the project develops.

Daily severity proposal: no detected risk = 0, warning = 0.5, critical = 1.0.

Growth-stage weight proposal: normal vegetative growth = 1.0, establishment or early seedling = 1.25, flowering or pollination = 2.0, grain or pod filling = 1.75.

One possible crop risk calculation is:

`R_crop = 100 * sum(w_d * s_d) / (D * w_max)`

Here `D` is crop-season days, `w_d` is the stage weight for day `d`, `s_d` is that day's severity, and `w_max` is the maximum stage weight. The proposal calculates heat, cold, drought, waterlogging, and disease-conducive weather risks separately, so a combined value does not obscure a severe individual risk.

One possible area-weighted rotation risk is:

`R_rotation = sum(A_i * R_i) / sum(A_i)`

Here `A_i` is the area assigned to crop `i` and `R_i` is its crop risk. Reporting the highest individual crop-season risk alongside an average can help expose concentrated risks. These formulas are starting points, not required implementation details.

## Comparing rotations

Potential comparison dimensions include environmental and climate risk, water efficiency, soil-health indicators, bare-soil duration and soil cover, expected income and costs, and feasibility under local conditions and planting calendars.

Examples of interpretation limits:

- Legume inclusion and crop diversity may serve as soil-health indicators; they do not by themselves prove improved soil health.
- NDVI can indicate living vegetation but may not reliably distinguish all crop residue from bare soil.
- Lower water use does not automatically mean better water productivity if yield also falls.
- Income estimates depend on credible local yield, price, and production-cost information.

Scores from different dimensions may need normalization to make comparisons understandable. Feasibility constraints such as planting windows, water availability, and soil suitability may affect whether a rotation is a viable candidate. The precise method is an implementation decision.

An earlier proposed preference score was:

`S = W_s * S_s + W_w * S_w + W_e * S_e + W_r * S_r`

The terms represent farmer-selected weights and scores for soil health, water, income, and resilience; the proposed weights sum to 1. This is an example, not a mandated ranking formula. Farmer priorities should inform comparisons rather than be assumed to have universal fixed values.

## Intended workflow

The envisioned flow is for a farmer to provide location, resources, current rotation, and priorities; the system then gathers available data, identifies seasons and growth stages, assesses crop risks, compares candidate rotations, and explains results and limitations. The exact workflow may evolve with the repository and project decisions.

## Working context for future changes

- Treat the project description and scoring examples as intended direction, not proof that features already exist or immutable requirements.
- Inspect relevant code and existing conventions before changing implementation.
- Favor understandable, traceable results: users should be able to see important inputs, evidence, assumptions, and calculations behind a comparison.
- Choose the simplest approach that fits the task and current codebase. Add structure, dependencies, or automation when the concrete need warrants them.
- Do not present unsupported agricultural thresholds, estimates, or scoring assumptions as established facts.
