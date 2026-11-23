"""Generate a structured, explained lesson plan draft."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .activities import ActivityLibrary
from .curriculum import Curriculum, Outcome, Topic
from .errors import PlanningError
from .ranking import ActivityRanker
from .review import PENDING, created_history, utc_now_iso
from .validation import LessonRequest

PLAN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class LessonPlanner:
    """Build a plan from approved curriculum, activities and teacher context."""

    def __init__(
        self,
        curriculum: Curriculum,
        activities: ActivityLibrary,
        config: dict,
        ranker: ActivityRanker | None = None,
    ) -> None:
        self.curriculum = curriculum
        self.activities = activities
        self.config = config
        self.ranker = ranker or ActivityRanker(config)
        self.phase_order = tuple(config["phase_order"])

    def generate(
        self,
        request: LessonRequest,
        *,
        plan_id: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        topic = self.curriculum.get_topic(
            request.subject,
            request.class_name,
            request.topic,
        )
        outcomes = self.curriculum.validate_outcomes(
            topic,
            list(request.approved_outcome_ids),
        )
        candidates = self.activities.for_topic(request.subject, request.topic)
        if not candidates:
            raise PlanningError(
                f"No approved activities are available for {request.subject} / {request.topic}.",
                details={
                    "subject": request.subject,
                    "topic": request.topic,
                },
            )

        ranked = self.ranker.rank(candidates, request, outcomes)
        selected = self._select(ranked, request.duration_minutes)
        if not selected:
            raise PlanningError(
                "No activity combination fits the requested lesson duration.",
                details={"duration_minutes": request.duration_minutes},
            )

        planned_minutes = sum(item["duration_minutes"] for item in selected)
        if planned_minutes > request.duration_minutes:
            raise PlanningError(
                "Selected activities exceed the requested lesson duration.",
                details={
                    "requested_minutes": request.duration_minutes,
                    "planned_minutes": planned_minutes,
                },
            )

        plan_id = plan_id or make_plan_id(now)
        if not PLAN_ID_RE.match(plan_id):
            raise PlanningError(
                "plan_id must contain only letters, numbers, hyphens and underscores.",
                field="plan_id",
            )

        timestamp = utc_now_iso(now)
        objectives = self._objectives(outcomes)
        materials = self._materials(selected)
        assessment = self._assessment(outcomes, selected)
        conclusion = self._conclusion(request, outcomes, planned_minutes)
        warnings = self._warnings(selected, outcomes)
        coverage = self._coverage(selected, outcomes)

        plan = {
            "schema_version": 1,
            "plan_id": plan_id,
            "status": PENDING,
            "created_at": timestamp,
            "updated_at": timestamp,
            "request": request.to_dict(),
            "curriculum": {
                "curriculum_version": self.curriculum.curriculum_version,
                "subject": topic.subject,
                "class_name": topic.class_name,
                "topic": topic.topic,
                "outcomes": [outcome.to_dict() for outcome in outcomes],
            },
            "objectives": objectives,
            "materials": materials,
            "activities": selected,
            "assessment": assessment,
            "conclusion": conclusion,
            "timing": {
                "requested_minutes": request.duration_minutes,
                "planned_minutes": planned_minutes,
                "flex_minutes": request.duration_minutes - planned_minutes,
            },
            "selection_summary": {
                "candidate_count": len(ranked),
                "selected_count": len(selected),
                "unallocated_minutes": request.duration_minutes - planned_minutes,
            },
            "warnings": warnings,
            "coverage": coverage,
            "review": {
                "status": PENDING,
                "reviewer": None,
                "decided_at": None,
                "notes": None,
                "history": created_history(now),
            },
        }
        return plan

    def _select(self, ranked: list[dict], duration: int) -> list[dict]:
        """Choose a phase-balanced set that fits the lesson duration."""

        by_phase: dict[str, list[dict]] = {}
        for item in ranked:
            by_phase.setdefault(item["phase"], []).append(item)

        required = [
            phase
            for phase in ("starter", "main", "plenary")
            if by_phase.get(phase)
        ]
        selected: list[dict] = []
        used: set[str] = set()
        remaining = duration
        phase_index = {phase: index for index, phase in enumerate(self.phase_order)}

        phases_to_consider = [
            phase
            for phase in self.phase_order
            if phase in required or phase == "practice"
        ]
        for phase in phases_to_consider:
            candidates = [
                item for item in by_phase.get(phase, []) if item["activity_id"] not in used
            ]
            if not candidates:
                continue
            later_required = [
                later
                for later in required
                if phase_index.get(later, 99) > phase_index.get(phase, 99)
            ]
            reserve = 0
            for later in later_required:
                later_candidates = by_phase.get(later, [])
                if later_candidates:
                    reserve += min(item["duration_minutes"] for item in later_candidates)
            choice = next(
                (
                    item
                    for item in candidates
                    if item["duration_minutes"] <= remaining - reserve
                ),
                None,
            )
            if choice is None:
                fitting = [
                    item
                    for item in candidates
                    if item["duration_minutes"] <= remaining
                ]
                if fitting:
                    choice = min(
                        fitting,
                        key=lambda item: (item["duration_minutes"], -item["score"]),
                    )
            if choice is not None:
                selected.append(choice)
                used.add(choice["activity_id"])
                remaining -= choice["duration_minutes"]

        while remaining > 0:
            extras = [
                item
                for item in ranked
                if item["activity_id"] not in used
                and item["phase"] in {"main", "practice"}
                and item["duration_minutes"] <= remaining
            ]
            if not extras:
                break
            choice = max(
                extras,
                key=lambda item: (
                    item["score"],
                    -item["duration_minutes"],
                    -phase_index.get(item["phase"], 99),
                ),
            )
            selected.append(choice)
            used.add(choice["activity_id"])
            remaining -= choice["duration_minutes"]

        if not selected and ranked:
            selected = [min(ranked, key=lambda item: item["duration_minutes"])]

        selected.sort(
            key=lambda item: (
                phase_index.get(item["phase"], 99),
                -item["score"],
                item["activity_id"],
            )
        )
        for index, item in enumerate(selected, start=1):
            item["sequence"] = index
            reason = (
                f"Selected for the {item['phase']} phase; "
                f"{item['duration_minutes']} minutes fit the lesson sequence."
            )
            item["reasons"] = list(item.get("reasons", [])) + [reason]
        return selected

    def _objectives(self, outcomes: list[Outcome]) -> list[dict]:
        return [
            {
                "id": f"OBJ-{index}",
                "text": outcome.text,
                "source_outcome_id": outcome.id,
                "success_criteria": outcome.assessment,
            }
            for index, outcome in enumerate(outcomes, start=1)
        ]

    def _materials(self, selected: list[dict]) -> list[str]:
        materials = {
            material
            for item in selected
            for material in item.get("materials", [])
            if isinstance(material, str) and material.strip()
        }
        return sorted(materials, key=str.lower)

    def _assessment(self, outcomes: list[Outcome], selected: list[dict]) -> dict:
        formative: list[str] = []
        for item in selected:
            evidence = item.get("assessment_evidence")
            if evidence and evidence not in formative:
                formative.append(evidence)
        return {
            "formative": formative,
            "summative": (
                "Teacher-reviewed exit ticket plus the approved outcome success criteria."
            ),
            "success_criteria": [outcome.assessment for outcome in outcomes],
        }

    def _conclusion(
        self,
        request: LessonRequest,
        outcomes: list[Outcome],
        planned_minutes: int,
    ) -> dict:
        flex = request.duration_minutes - planned_minutes
        next_steps = [
            f"Review the exit-ticket evidence against {outcome.id}."
            for outcome in outcomes
        ]
        if flex:
            next_steps.append(
                f"Use the {flex} flexible minutes for retrieval practice or targeted support."
            )
        return {
            "summary": (
                f"Close the {request.duration_minutes}-minute {request.subject} lesson "
                f"with a short retrieval summary and a check against the approved outcomes."
            ),
            "next_steps": next_steps,
            "exit_prompt": "Which activity helped you explain today's big idea most clearly?",
        }

    def _warnings(self, selected: list[dict], outcomes: list[Outcome]) -> list[str]:
        warnings: list[str] = []
        for item in selected:
            for warning in item.get("warnings", []):
                if warning not in warnings:
                    warnings.append(warning)
        covered = {
            outcome_id
            for item in selected
            for outcome_id in item.get("supports_outcomes", [])
        }
        missing = [outcome.id for outcome in outcomes if outcome.id not in covered]
        if missing:
            warnings.append(
                "Selected activities do not directly cover: " + ", ".join(sorted(missing))
            )
        return warnings

    def _coverage(self, selected: list[dict], outcomes: list[Outcome]) -> dict:
        supported = sorted(
            {
                outcome_id
                for item in selected
                for outcome_id in item.get("supports_outcomes", [])
            }
        )
        requested = [outcome.id for outcome in outcomes]
        return {
            "requested_outcomes": requested,
            "supported_outcomes": supported,
            "uncovered_outcomes": [
                outcome_id for outcome_id in requested if outcome_id not in supported
            ],
        }


def make_plan_id(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"LP-{timestamp}-{uuid.uuid4().hex[:6].upper()}"
