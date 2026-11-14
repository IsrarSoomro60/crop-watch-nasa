"""Compares the current rotation with alternatives and explains the ranking.

Missing data must never look like safety:

- Resilience compares the risk types assessed for every crop-season of the
  current rotation (`resilience_risks`). An alternative that can't be assessed on
  all of them gets no resilience score, rather than shrinking the comparison for
  every rotation. If the current rotation has no assessed risks, the risks shared
  by all rotations that have any are used instead.
- A rotation missing a dimension the farmer weighted, which other rotations do
  have, gets no overall score and is listed after the scored ones.
"""

from functools import reduce

from app.repositories.crop_profiles import CropProfileRepository
from app.schemas.crop import RiskType
from app.schemas.environment import DailyObservation
from app.schemas.recommendation import (
    ComparisonRequest,
    DimensionScores,
    RankedRotation,
    Recommendation,
)
from app.schemas.rotation import Rotation, RotationEvaluation
from app.schemas.soil import SoilInfo
from app.services.income.income import income_scores, rotation_income
from app.services.recommendation.explanations import explain
from app.services.rotation.rotation_evaluator import RotationEvaluator
from app.services.rotation.scoring import normalise_weights, preference_score, risk_to_resilience

LIMITATIONS = [
    "Income defaults are FAOSTAT national averages for Pakistan (yield, producer price), not local or current "
    "market prices, and exclude costs unless you enter them; enter your own values for a fair comparison.",
    "Water score compares estimated irrigation need only (lowest need = 1.0). Lower water use is not better "
    "water productivity if yield also falls.",
    "Soil-health indicator = average of legume share and ground cover (share of the year under a growing crop). "
    "These are indicators only; they do not prove improved soil health.",
    "Risks without limits are not assessed. A rotation with unassessed crops is not scored rather than "
    "treated as low risk; see each crop's evidence gaps.",
    "Temperature limits are general starting values from the team research brief, not tuned to local varieties.",
    "Weather is for a ~50 km NASA POWER grid cell and lags real time by 2-3 days; it is not field-level.",
    "Most Punjab and Sindh fields are irrigated, so dry readings alone do not prove drought.",
]


def assessed_risks(evaluation: RotationEvaluation) -> set[RiskType]:
    """Risk types assessed in every crop-season of the rotation."""
    per_crop = [{r for r, lvl in c.levels.items() if lvl is not None} for c in evaluation.crop_results]
    return reduce(set.intersection, per_crop) if per_crop else set()


def unassessed_crops(evaluation: RotationEvaluation, risks: set[RiskType]) -> list[str]:
    """Crops missing any of `risks`, or with no assessed risk at all when `risks` is empty."""
    def lacking(levels: dict) -> bool:
        if risks:
            return any(levels.get(r) is None for r in risks)
        return all(v is None for v in levels.values())

    return sorted({c.crop.value for c in evaluation.crop_results if lacking(c.levels)})


def water_scores_for(evaluations: list[RotationEvaluation]) -> list[float | None]:
    """Lowest irrigation need = 1.0; others = lowest / own. None where need could not be calculated."""
    needs = [e.water.irrigation_need_m3 if e.water else None for e in evaluations]
    known = [n for n in needs if n is not None]
    if not known:
        return [None] * len(needs)
    lowest = min(known)
    return [None if n is None else (1.0 if n <= 0 else round(lowest / n, 3)) for n in needs]


class RecommendationEngine:
    def __init__(self, profiles: CropProfileRepository, evaluator: RotationEvaluator | None = None):
        self._profiles = profiles
        self._evaluator = evaluator or RotationEvaluator(profiles)

    def _legume_share(self, rotation: Rotation) -> float:
        total = sum(s.area_hectares for s in rotation.seasons)
        legume = sum(s.area_hectares for s in rotation.seasons if self._profiles.get(s.crop).is_legume)
        return legume / total if total else 0.0

    def _soil_health(self, rotation: Rotation, evaluation: RotationEvaluation) -> float:
        cover = evaluation.ground_cover.cover_fraction if evaluation.ground_cover else 0.0
        return round((self._legume_share(rotation) + cover) / 2, 3)

    def compare(
        self,
        request: ComparisonRequest,
        observations: list[DailyObservation],
        elevation_m: float | None = None,
        soil: SoilInfo | None = None,
        water_fallback: dict | None = None,
        risk_fallback: dict | None = None,
    ) -> Recommendation:
        current = request.current.model_copy(update={"is_current": True})
        rotations = [current, *request.alternatives]
        lat = request.location.latitude
        texture = soil.texture_class if soil else None
        evaluations = [
            self._evaluator.evaluate(r, observations, lat, elevation_m, texture, water_fallback, risk_fallback)
            for r in rotations
        ]
        water_scores = water_scores_for(evaluations)
        for rotation, evaluation in zip(rotations, evaluations, strict=True):
            evaluation.income = rotation_income(rotation, request.economics)
        inc_scores = income_scores([e.income for e in evaluations])  # type: ignore[misc]

        coverage = [assessed_risks(e) for e in evaluations]
        if coverage[0]:
            # Anchor on the current rotation: alternatives are judged on the risks checked for
            # what the farmer grows now; an alternative that can't be checked on them goes unscored.
            common: set[RiskType] = coverage[0]
        else:
            non_empty = [c for c in coverage if c]
            common = reduce(set.intersection, non_empty) if non_empty else set()

        all_scores: list[DimensionScores] = []
        for rotation, evaluation, covered in zip(rotations, evaluations, coverage, strict=True):
            resilience = None
            if common and common <= covered:
                highest = max(max(c.risks[r] for r in common) for c in evaluation.crop_results)
                resilience = round(risk_to_resilience(highest), 3)
            all_scores.append(DimensionScores(
                soil_health=self._soil_health(rotation, evaluation),
                water=water_scores[len(all_scores)],
                income=inc_scores[len(all_scores)],
                resilience=resilience,
            ))

        # Dimensions the farmer weighted that at least one rotation has.
        weights = normalise_weights(request.priorities)
        required = {
            dim for dim, w in weights.items()
            if w > 0 and any(getattr(s, dim) is not None for s in all_scores)
        }

        ranked: list[RankedRotation] = []
        explanation: list[str] = []
        for rotation, evaluation, scores in zip(rotations, evaluations, all_scores, strict=True):
            missing = sorted(d for d in required if getattr(scores, d) is None)
            score = None if missing else preference_score(scores, request.priorities)
            ranked.append(
                RankedRotation(
                    rotation_name=rotation.name,
                    is_current=rotation.is_current,
                    preference_score=score,
                    dimension_scores=scores,
                    missing_dimensions=missing,
                    evaluation=evaluation,
                )
            )
        ranked.sort(key=lambda r: (r.preference_score is None, -(r.preference_score or 0)))
        current_ranked = next(r for r in ranked if r.is_current)
        for r in ranked:
            r.strategy = explain(r, current_ranked, self._profiles)

        for r in ranked:
            ds = r.dimension_scores
            w = r.evaluation.water
            need = f", irrigation need {w.irrigation_need_m3:,.0f} m3" if w and w.irrigation_need_m3 is not None else ""
            gc = r.evaluation.ground_cover
            bare = f", {gc.bare_soil_days} bare-soil days" if gc else ""
            parts = (f"soil-health indicator {ds.soil_health}{bare}, water {ds.water}{need}, "
                     f"resilience {ds.resilience}")
            if r.preference_score is not None:
                explanation.append(f"{r.rotation_name}: score {r.preference_score:.2f} ({parts})")
            else:
                crops = unassessed_crops(r.evaluation, common)
                why = f"; crops without assessed risks: {', '.join(crops)}" if crops else ""
                explanation.append(
                    f"{r.rotation_name}: not scored, missing {', '.join(r.missing_dimensions)}{why} ({parts})"
                )
        if common:
            explanation.append(
                "Resilience compares the risks assessed for every crop in the current rotation: "
                + ", ".join(sorted(r.value for r in common)) + "."
            )

        return Recommendation(
            ranked=ranked,
            explanation=explanation,
            limitations=LIMITATIONS,
            resilience_risks=sorted(common),
            soil=soil,
        )
