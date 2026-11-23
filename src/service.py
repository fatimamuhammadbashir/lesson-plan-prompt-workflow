"""Application service that joins validation, planning, review and storage."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .activities import ActivityLibrary
from .config import PROJECT_ROOT, load_config
from .curriculum import Curriculum
from .planner import LessonPlanner
from .review import ReviewWorkflow
from .storage import PlanStore
from .validation import validate_request


class LessonPlanService:
    """High-level workflow used by the CLI, demo and tests."""

    def __init__(
        self,
        planner: LessonPlanner,
        review: ReviewWorkflow,
        store: PlanStore,
    ) -> None:
        self.planner = planner
        self.workflow = review
        self.store = store

    def create(
        self,
        payload: dict,
        *,
        plan_id: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        request = validate_request(payload, self.planner.curriculum, self.planner.config)
        plan = self.planner.generate(request, plan_id=plan_id, now=now)
        self.store.save(plan)
        return plan

    def get(self, plan_id: str) -> dict:
        return self.store.load(plan_id)

    def edit(
        self,
        plan_id: str,
        edits: dict,
        *,
        actor: str = "Teacher",
        now: datetime | None = None,
    ) -> dict:
        plan = self.store.load(plan_id)
        updated = self.workflow.apply_edit(plan, edits, actor=actor, now=now)
        self.store.save(updated)
        return updated

    def review(
        self,
        plan_id: str,
        decision: str,
        *,
        reviewer: str,
        notes: str = "",
        now: datetime | None = None,
    ) -> dict:
        plan = self.store.load(plan_id)
        updated = self.workflow.decide(
            plan,
            decision,
            reviewer=reviewer,
            notes=notes,
            now=now,
        )
        self.store.save(updated)
        self.store.append_review(updated)
        return updated

    def list_plans(self) -> list[dict]:
        return self.store.list_plans()


def build_service(
    *,
    store_root: str | Path | None = None,
    config_path: str | Path | None = None,
    curriculum_path: str | Path | None = None,
    activities_path: str | Path | None = None,
) -> LessonPlanService:
    config = load_config(config_path or PROJECT_ROOT / "config.json")
    curriculum = Curriculum.load(curriculum_path or PROJECT_ROOT / "data" / "curriculum.json")
    activities = ActivityLibrary.load(
        activities_path or PROJECT_ROOT / "data" / "activities.json",
        phases=config["phase_order"],
    )
    store = PlanStore(store_root or PROJECT_ROOT / "var")
    planner = LessonPlanner(curriculum, activities, config)
    review = ReviewWorkflow(config)
    return LessonPlanService(planner, review, store)
