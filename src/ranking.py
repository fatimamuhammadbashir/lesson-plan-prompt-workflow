"""Transparent rule-based ranking of activities."""

from __future__ import annotations

from .activities import Activity
from .curriculum import Outcome
from .errors import DataError
from .validation import LessonRequest

REQUIRED_FACTORS = (
    "preference_match",
    "outcome_alignment",
    "prerequisite_readiness",
    "previous_results_fit",
    "weak_topic_alignment",
)


class ActivityRanker:
    """Score activities using preferences, outcomes, prerequisites and results."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.weights = config["ranking_weights"]
        missing = [name for name in REQUIRED_FACTORS if name not in self.weights]
        if missing:
            raise DataError(
                f"Ranking weights are missing: {', '.join(missing)}",
                details={"available_weights": sorted(self.weights)},
            )
        self.phase_order = {phase: index for index, phase in enumerate(config["phase_order"])}

    def rank(
        self,
        activities: list[Activity],
        request: LessonRequest,
        outcomes: list[Outcome],
    ) -> list[dict]:
        """Return scored activities, highest score first."""

        scored: list[dict] = []
        for activity in activities:
            factors: dict[str, float] = {}
            reasons: list[str] = []
            warnings: list[str] = []

            factors["preference_match"] = self._score_preferences(activity, request, reasons)
            factors["outcome_alignment"] = self._score_outcomes(
                activity, outcomes, reasons, warnings
            )
            factors["prerequisite_readiness"] = self._score_prerequisites(
                activity, request, reasons, warnings
            )
            factors["previous_results_fit"] = self._score_previous_results(
                activity, request, reasons, warnings
            )
            factors["weak_topic_alignment"] = self._score_weak_topics(
                activity, request, reasons
            )

            breakdown: dict[str, dict] = {}
            total = 0.0
            for name in REQUIRED_FACTORS:
                raw = max(0.0, min(1.0, factors[name]))
                weight = float(self.weights[name])
                points = round(raw * weight, 4)
                breakdown[name] = {
                    "raw": round(raw, 4),
                    "weight": weight,
                    "points": points,
                }
                total += points

            if not reasons:
                reasons.append("Meets the curriculum activity requirements.")

            result = activity.to_dict()
            result.update(
                {
                    "score": round(total, 4),
                    "score_breakdown": breakdown,
                    "reasons": reasons,
                    "warnings": warnings,
                }
            )
            scored.append(result)

        scored.sort(
            key=lambda item: (
                -item["score"],
                self.phase_order.get(item["phase"], 99),
                item["activity_id"],
            )
        )
        return scored

    def _score_preferences(
        self,
        activity: Activity,
        request: LessonRequest,
        reasons: list[str],
    ) -> float:
        preferences = set(request.learner_preferences)
        matched = sorted(preferences & set(tag.lower() for tag in activity.tags))
        if not matched:
            return 0.0
        reasons.append(f"Matches learner preferences: {', '.join(matched)}.")
        return len(matched) / len(preferences)

    def _score_outcomes(
        self,
        activity: Activity,
        outcomes: list[Outcome],
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        selected_ids = {outcome.id for outcome in outcomes}
        matched = sorted(selected_ids & set(activity.supports_outcomes))
        if not matched:
            warnings.append("Does not directly support a selected approved outcome.")
            return 0.0
        reasons.append(f"Supports approved outcome(s): {', '.join(matched)}.")
        return len(matched) / len(selected_ids)

    def _score_prerequisites(
        self,
        activity: Activity,
        request: LessonRequest,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        prerequisites = list(activity.prerequisite_tags)
        if not prerequisites:
            reasons.append("No prerequisite tags required.")
            return 1.0

        mastered = set(request.previous_results.mastered_tags)
        weak = set(request.previous_results.weak_topics)
        mastered_hits = [tag for tag in prerequisites if tag in mastered]
        weak_hits = [tag for tag in prerequisites if tag in weak]
        unknown = [tag for tag in prerequisites if tag not in mastered and tag not in weak]

        for tag in mastered_hits:
            reasons.append(f"Prerequisite '{tag}' is recorded as mastered.")
        for tag in weak_hits:
            warnings.append(
                f"Prerequisite '{tag}' is listed as a weak topic; plan a short review."
            )
        for tag in unknown:
            warnings.append(
                f"Prerequisite '{tag}' has no recorded result; check readiness."
            )

        raw = (len(mastered_hits) - 0.5 * len(weak_hits)) / len(prerequisites)
        return max(0.0, min(1.0, raw))

    def _score_previous_results(
        self,
        activity: Activity,
        request: LessonRequest,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        settings = self.config["previous_results"]
        average = request.previous_results.class_average
        completion = request.previous_results.completion_rate
        tags = {tag.lower() for tag in activity.tags}

        if average < settings["low_average_threshold"]:
            if tags & {"scaffolded", "guided", "review"}:
                raw = 1.0
                reasons.append(
                    f"Class average {average:.1f}% is below "
                    f"{settings['low_average_threshold']}%; this activity is scaffolded or review-focused."
                )
            else:
                raw = 0.25
                warnings.append(
                    f"Class average {average:.1f}% is below "
                    f"{settings['low_average_threshold']}%; this activity is not explicitly scaffolded."
                )
        elif average >= settings["high_average_threshold"]:
            if tags & {"challenge", "extension", "independent"}:
                raw = 1.0
                reasons.append(
                    f"Class average {average:.1f}% is {settings['high_average_threshold']}% or higher; "
                    "this activity adds challenge or independence."
                )
            else:
                raw = 0.4
                reasons.append(
                    f"Class average {average:.1f}% is in the secure range; this core activity keeps the lesson balanced."
                )
        else:
            raw = 0.6
            reasons.append(
                f"Class average {average:.1f}% is in the core range; this activity fits the current level."
            )

        if completion < settings["low_completion_threshold"]:
            if tags & {"interactive", "hands-on", "group work"}:
                raw = min(1.0, raw + 0.15)
                reasons.append(
                    f"Completion rate {completion:.0%} is below "
                    f"{settings['low_completion_threshold']:.0%}; an interactive activity may re-engage learners."
                )
            else:
                raw = max(0.0, raw - 0.1)
                warnings.append(
                    f"Completion rate {completion:.0%} is low; consider a more interactive alternative."
                )
        return raw

    def _score_weak_topics(
        self,
        activity: Activity,
        request: LessonRequest,
        reasons: list[str],
    ) -> float:
        weak = set(request.previous_results.weak_topics)
        if not weak:
            return 0.0
        matched = sorted(weak & set(activity.targets_tags))
        if matched:
            reasons.append(f"Targets weak topic(s): {', '.join(matched)}.")
        return len(matched) / len(weak)
