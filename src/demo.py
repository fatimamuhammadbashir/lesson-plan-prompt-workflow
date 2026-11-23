"""Scripted demonstration of generation, validation, editing and review."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Callable

from .config import PROJECT_ROOT
from .errors import AppError
from .service import LessonPlanService
from .validation import load_json_object


def run_demo(
    service: LessonPlanService,
    *,
    data_dir: str | Path | None = None,
    output: Callable[[str], None] = print,
) -> int:
    data_path = Path(data_dir) if data_dir is not None else PROJECT_ROOT / "data"
    request = load_json_object(data_path / "sample_request.json")
    edits = load_json_object(data_path / "sample_edits.json")

    output("LESSON PLAN PROMPT WORKFLOW - DEMO")
    output("=" * 56)
    output("Rule-based, offline demonstration. No API keys are used.")
    output("")

    output("1. SUCCESSFUL GENERATION")
    output("-" * 56)
    plan = service.create(request, plan_id="LP-DEMO-001")
    _print_plan_summary(plan, output)
    output("")

    output("2. INVALID INPUT HANDLED SAFELY")
    output("-" * 56)
    bad_duration = copy.deepcopy(request)
    bad_duration["duration_minutes"] = 999
    _show_expected_error(
        lambda: service.create(bad_duration, plan_id="LP-DEMO-BAD-1"),
        output,
    )
    bad_outcome = copy.deepcopy(request)
    bad_outcome["approved_outcome_ids"] = ["SCI7-PH-99"]
    _show_expected_error(
        lambda: service.create(bad_outcome, plan_id="LP-DEMO-BAD-2"),
        output,
    )
    output("")

    output("3. TEACHER EDIT BEFORE APPROVAL")
    output("-" * 56)
    edited = service.edit("LP-DEMO-001", edits, actor="Ms. Rivera")
    latest = edited["review"]["history"][-1]
    output(f"Status: {edited['review']['status']}")
    output(f"Changed fields: {', '.join(latest['details']['changed_fields'])}")
    output(f"Edit note: {latest['details']['note']}")
    output(f"First objective: {edited['objectives'][0]['text']}")
    output("")

    output("4. TEACHER APPROVAL")
    output("-" * 56)
    approved = service.review(
        "LP-DEMO-001",
        "approved",
        reviewer="Ms. Rivera",
        notes="Objectives, assessment and timing are ready to teach.",
    )
    output(f"Status: {approved['review']['status']}")
    output(f"Reviewer: {approved['review']['reviewer']}")
    output(f"Notes: {approved['review']['notes']}")
    output(f"History actions: {_history_actions(approved)}")
    output("")

    output("5. TEACHER REJECTION")
    output("-" * 56)
    second = service.create(request, plan_id="LP-DEMO-002")
    rejected = service.review(
        "LP-DEMO-002",
        "rejected",
        reviewer="Mr. Chen",
        notes="The main activity repeats the starter; choose a different practice task.",
    )
    output(f"Original status: {second['review']['status']}")
    output(f"Final status: {rejected['review']['status']}")
    output(f"Reviewer: {rejected['review']['reviewer']}")
    output(f"Notes: {rejected['review']['notes']}")
    output("")

    output("6. NEEDS REVISION, THEN RESUBMISSION")
    output("-" * 56)
    third = service.create(request, plan_id="LP-DEMO-003")
    revision = service.review(
        "LP-DEMO-003",
        "needs_revision",
        reviewer="Head of Science",
        notes="Add a clearer vocabulary check before the main activity.",
    )
    output(f"After review: {revision['review']['status']}")
    resubmitted = service.edit(
        "LP-DEMO-003",
        {
            "conclusion": {
                "summary": "Add a three-word vocabulary check before the main activity.",
                "next_steps": [
                    "Review exit-ticket evidence before the next lesson.",
                    "Re-teach gas exchange for students who need it.",
                ],
                "exit_prompt": "Why is photosynthesis essential for life on Earth?",
            },
            "note": "Added the requested vocabulary check.",
        },
        actor="Ms. Rivera",
    )
    output(f"After teacher edit: {resubmitted['review']['status']}")
    output(f"History actions: {_history_actions(resubmitted)}")
    output("")

    output("DEMO COMPLETE")
    output(f"Plan JSON files are stored under: {_display_path(service.store.plans_dir)}")
    output(f"Review audit log: {_display_path(service.store.review_log)}")
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _print_plan_summary(plan: dict, output: Callable[[str], None]) -> None:
    output(f"Plan ID: {plan['plan_id']}")
    output(f"Status: {plan['status']}")
    output(f"Lesson: {plan['request']['subject']} / {plan['request']['class_name']} / {plan['request']['topic']}")
    output(f"Duration: {plan['timing']['planned_minutes']} of {plan['timing']['requested_minutes']} minutes")
    output(f"Objectives: {len(plan['objectives'])} | Materials: {len(plan['materials'])} | Activities: {len(plan['activities'])}")
    output("")
    output("Activities and explanations:")
    for activity in plan["activities"]:
        output(
            f"  {activity['sequence']}. [{activity['phase']}] {activity['title']} "
            f"({activity['duration_minutes']} min, score {activity['score']})"
        )
        for reason in activity["reasons"]:
            output(f"      + {reason}")
        for warning in activity["warnings"]:
            output(f"      ! {warning}")
    if plan["warnings"]:
        output("Plan warnings:")
        for warning in plan["warnings"]:
            output(f"  ! {warning}")
    output(f"Assessment methods: {len(plan['assessment']['formative'])} formative checks")
    output(f"Conclusion: {plan['conclusion']['summary']}")
    output(f"Flexible minutes: {plan['timing']['flex_minutes']}")


def _show_expected_error(action, output: Callable[[str], None]) -> None:
    try:
        action()
    except AppError as exc:
        output("Handled error (no traceback):")
        output(json.dumps(exc.to_dict(), indent=2))
    else:  # pragma: no cover - defensive
        output("ERROR: expected validation to fail, but it succeeded.")


def _history_actions(plan: dict) -> str:
    return " -> ".join(
        f"{entry['action']}:{entry['to_status']}"
        for entry in plan["review"]["history"]
    )
