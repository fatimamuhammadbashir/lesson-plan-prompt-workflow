"""Teacher review state machine, editing and decision history."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from .errors import ReviewError, ValidationError

PENDING = "Pending Teacher Review"
APPROVED = "Approved"
REJECTED = "Rejected"
NEEDS_REVISION = "Needs Revision"

DECISIONS = {
    "approved": APPROVED,
    "rejected": REJECTED,
    "needs_revision": NEEDS_REVISION,
}
EDITABLE_FIELDS = ("objectives", "materials", "activities", "assessment", "conclusion")


def utc_now_iso(now: datetime | None = None) -> str:
    """Return a stable UTC timestamp."""

    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_history_entry(
    *,
    action: str,
    actor: str,
    from_status: str | None,
    to_status: str,
    details: dict | None = None,
    now: datetime | None = None,
) -> dict:
    return {
        "timestamp_utc": utc_now_iso(now),
        "action": action,
        "actor": actor,
        "from_status": from_status,
        "to_status": to_status,
        "details": details or {},
    }


def created_history(now: datetime | None = None) -> list[dict]:
    return [
        make_history_entry(
            action="created",
            actor="System",
            from_status=None,
            to_status=PENDING,
            details={"message": "Lesson plan draft generated and queued for teacher review."},
            now=now,
        )
    ]


class ReviewWorkflow:
    """Apply edits and teacher decisions while preserving an audit trail."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.phase_order = tuple(config["phase_order"])

    def apply_edit(
        self,
        plan: dict,
        edits: dict,
        *,
        actor: str = "Teacher",
        now: datetime | None = None,
    ) -> dict:
        if not isinstance(plan, dict):
            raise ReviewError("Lesson plan must be an object.")
        review = plan.get("review")
        if not isinstance(review, dict):
            raise ReviewError("Lesson plan is missing review information.")
        previous_status = review.get("status")
        if previous_status not in {PENDING, NEEDS_REVISION}:
            raise ReviewError(
                f"Cannot edit a plan with status '{previous_status}'.",
                details={"allowed_statuses": [PENDING, NEEDS_REVISION]},
            )

        if not isinstance(edits, dict):
            raise ValidationError("Edits must be a JSON object.", field="$")
        allowed = set(EDITABLE_FIELDS) | {"note"}
        unknown = sorted(set(edits) - allowed)
        if unknown:
            raise ValidationError(
                f"Unknown edit field: {unknown[0]}",
                field=unknown[0],
                details={"unknown_fields": unknown, "allowed_fields": sorted(allowed)},
            )
        changed_fields = sorted(field for field in EDITABLE_FIELDS if field in edits)
        if not changed_fields:
            raise ValidationError(
                "Provide at least one editable field.",
                field="$",
                details={"allowed_fields": list(EDITABLE_FIELDS)},
            )

        actor = _short_text(actor, "actor", 100)
        note = _optional_text(edits.get("note", ""), "note", 500)

        updated = copy.deepcopy(plan)
        if "objectives" in edits:
            updated["objectives"] = self._validate_objectives(edits["objectives"])
        if "materials" in edits:
            updated["materials"] = self._validate_materials(edits["materials"])
        if "activities" in edits:
            updated["activities"] = self._validate_activities(
                edits["activities"],
                previous=updated.get("activities", []),
                requested_minutes=updated["request"]["duration_minutes"],
            )
            planned = sum(item["duration_minutes"] for item in updated["activities"])
            updated["timing"] = {
                "requested_minutes": updated["request"]["duration_minutes"],
                "planned_minutes": planned,
                "flex_minutes": updated["request"]["duration_minutes"] - planned,
            }
        if "assessment" in edits:
            updated["assessment"] = self._validate_assessment(edits["assessment"])
        if "conclusion" in edits:
            updated["conclusion"] = self._validate_conclusion(edits["conclusion"])

        timestamp = utc_now_iso(now)
        updated["updated_at"] = timestamp
        updated["status"] = PENDING
        updated["review"]["status"] = PENDING
        updated["review"]["reviewer"] = None
        updated["review"]["decided_at"] = None
        updated["review"]["notes"] = None
        updated["review"].setdefault("history", []).append(
            make_history_entry(
                action="edited",
                actor=actor,
                from_status=previous_status,
                to_status=PENDING,
                details={
                    "changed_fields": changed_fields,
                    "note": note,
                },
                now=now,
            )
        )
        return updated

    def decide(
        self,
        plan: dict,
        decision: str,
        *,
        reviewer: str,
        notes: str = "",
        now: datetime | None = None,
    ) -> dict:
        if not isinstance(plan, dict):
            raise ReviewError("Lesson plan must be an object.")
        review = plan.get("review")
        if not isinstance(review, dict):
            raise ReviewError("Lesson plan is missing review information.")
        previous_status = review.get("status")
        if previous_status not in {PENDING, NEEDS_REVISION}:
            raise ReviewError(
                f"Cannot record a decision for a plan with status '{previous_status}'.",
                details={"allowed_statuses": [PENDING, NEEDS_REVISION]},
            )

        normalized = _normalize_decision(decision)
        target_status = DECISIONS[normalized]
        reviewer = _short_text(reviewer, "reviewer", 100)
        notes = _optional_text(notes, "notes", 1000)
        if normalized in {"rejected", "needs_revision"} and len(notes) < 3:
            raise ValidationError(
                "Notes are required when rejecting a plan or requesting revision.",
                field="notes",
            )

        updated = copy.deepcopy(plan)
        timestamp = utc_now_iso(now)
        updated["updated_at"] = timestamp
        updated["status"] = target_status
        updated["review"]["status"] = target_status
        updated["review"]["reviewer"] = reviewer
        updated["review"]["decided_at"] = timestamp
        updated["review"]["notes"] = notes
        updated["review"].setdefault("history", []).append(
            make_history_entry(
                action="decision",
                actor=reviewer,
                from_status=previous_status,
                to_status=target_status,
                details={
                    "decision": normalized,
                    "notes": notes,
                },
                now=now,
            )
        )
        return updated

    def _validate_objectives(self, value: object) -> list[dict]:
        if not isinstance(value, list) or not 1 <= len(value) <= 10:
            raise ValidationError(
                "objectives must contain between 1 and 10 entries.",
                field="objectives",
            )
        cleaned: list[dict] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValidationError(
                    f"objectives[{index}] must be an object.",
                    field="objectives",
                )
            allowed = {"id", "text", "source_outcome_id", "success_criteria"}
            unknown = sorted(set(item) - allowed)
            if unknown:
                raise ValidationError(
                    f"Unknown objective field: {unknown[0]}",
                    field=f"objectives[{index}]",
                )
            objective = {
                "id": _short_text(item.get("id", f"OBJ-{index + 1}"), f"objectives[{index}].id", 40),
                "text": _short_text(item.get("text"), f"objectives[{index}].text", 600),
            }
            if "source_outcome_id" in item:
                objective["source_outcome_id"] = _short_text(
                    item["source_outcome_id"],
                    f"objectives[{index}].source_outcome_id",
                    80,
                )
            if "success_criteria" in item:
                objective["success_criteria"] = _short_text(
                    item["success_criteria"],
                    f"objectives[{index}].success_criteria",
                    400,
                )
            cleaned.append(objective)
        return cleaned

    def _validate_materials(self, value: object) -> list[str]:
        if not isinstance(value, list) or not 1 <= len(value) <= 50:
            raise ValidationError(
                "materials must contain between 1 and 50 items.",
                field="materials",
            )
        cleaned: list[str] = []
        for index, item in enumerate(value):
            text = _short_text(item, f"materials[{index}]", 200)
            if text in cleaned:
                raise ValidationError(
                    f"Duplicate material: {text}",
                    field="materials",
                )
            cleaned.append(text)
        return cleaned

    def _validate_activities(
        self,
        value: object,
        *,
        previous: list[dict],
        requested_minutes: int,
    ) -> list[dict]:
        if not isinstance(value, list) or not 1 <= len(value) <= 12:
            raise ValidationError(
                "activities must contain between 1 and 12 entries.",
                field="activities",
            )
        previous_by_id = {
            item.get("activity_id"): item
            for item in previous
            if isinstance(item, dict) and item.get("activity_id")
        }
        cleaned: list[dict] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValidationError(
                    f"activities[{index}] must be an object.",
                    field="activities",
                )
            activity_id = _short_text(
                item.get("activity_id", f"TEACHER-{index + 1}"),
                f"activities[{index}].activity_id",
                80,
            )
            if activity_id in seen_ids:
                raise ValidationError(
                    f"Duplicate activity id: {activity_id}",
                    field="activities",
                )
            seen_ids.add(activity_id)

            title = _short_text(item.get("title"), f"activities[{index}].title", 150)
            phase = _short_text(item.get("phase"), f"activities[{index}].phase", 30)
            if phase not in self.phase_order:
                raise ValidationError(
                    f"Invalid activity phase: {phase}",
                    field=f"activities[{index}].phase",
                    details={"allowed_phases": list(self.phase_order)},
                )
            duration = item.get("duration_minutes")
            if not isinstance(duration, int) or isinstance(duration, bool) or duration < 1:
                raise ValidationError(
                    f"activities[{index}].duration_minutes must be a positive whole number.",
                    field=f"activities[{index}].duration_minutes",
                )

            merged = copy.deepcopy(previous_by_id.get(activity_id, {}))
            merged.update(copy.deepcopy(item))
            merged["activity_id"] = activity_id
            merged["title"] = title
            merged["phase"] = phase
            merged["duration_minutes"] = duration
            merged["sequence"] = index + 1
            if "description" in merged:
                merged["description"] = _short_text(
                    merged["description"],
                    f"activities[{index}].description",
                    600,
                )
            reasons = merged.get("reasons")
            if reasons is None:
                reasons = merged.pop("reason", None)
            if reasons is None:
                reasons = ["Teacher-edited activity; rationale recorded in the review history."]
            merged["reasons"] = self._reason_list(reasons, f"activities[{index}].reasons")
            warnings = merged.get("warnings", [])
            if warnings is None:
                warnings = []
            merged["warnings"] = self._reason_list(
                warnings,
                f"activities[{index}].warnings",
                allow_empty=True,
            )
            cleaned.append(merged)

        planned = sum(item["duration_minutes"] for item in cleaned)
        if planned > requested_minutes:
            raise ValidationError(
                (
                    f"Edited activities total {planned} minutes, which exceeds the "
                    f"requested {requested_minutes} minutes."
                ),
                field="activities",
            )
        return cleaned

    def _validate_assessment(self, value: object) -> dict:
        if not isinstance(value, dict) or not value:
            raise ValidationError(
                "assessment must be a non-empty object.",
                field="assessment",
            )
        cleaned = copy.deepcopy(value)
        for key in ("formative", "success_criteria"):
            if key in cleaned:
                items = cleaned[key]
                if not isinstance(items, list) or not items:
                    raise ValidationError(
                        f"assessment.{key} must be a non-empty list.",
                        field="assessment",
                    )
                for index, item in enumerate(items):
                    _short_text(item, f"assessment.{key}[{index}]", 500)
        if "summative" in cleaned:
            _short_text(cleaned["summative"], "assessment.summative", 600)
        return cleaned

    def _validate_conclusion(self, value: object) -> dict:
        if isinstance(value, str):
            return {
                "summary": _short_text(value, "conclusion", 1000),
                "next_steps": [],
                "exit_prompt": "",
            }
        if not isinstance(value, dict) or not value:
            raise ValidationError(
                "conclusion must be a non-empty string or object.",
                field="conclusion",
            )
        cleaned = copy.deepcopy(value)
        if "summary" in cleaned:
            _short_text(cleaned["summary"], "conclusion.summary", 800)
        for key in ("next_steps", "exit_prompt"):
            if key in cleaned:
                if isinstance(cleaned[key], list):
                    for index, item in enumerate(cleaned[key]):
                        _short_text(item, f"conclusion.{key}[{index}]", 400)
                else:
                    _short_text(cleaned[key], f"conclusion.{key}", 500)
        return cleaned

    @staticmethod
    def _reason_list(
        value: object,
        field: str,
        *,
        allow_empty: bool = False,
    ) -> list[str]:
        if not isinstance(value, list):
            raise ValidationError(f"{field} must be a list of strings.", field=field)
        if not value and not allow_empty:
            raise ValidationError(f"{field} must not be empty.", field=field)
        cleaned: list[str] = []
        for index, item in enumerate(value):
            cleaned.append(_short_text(item, f"{field}[{index}]", 500))
        return cleaned


def _normalize_decision(decision: str) -> str:
    if not isinstance(decision, str):
        raise ValidationError("decision must be a string.", field="decision")
    normalized = decision.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in DECISIONS:
        raise ValidationError(
            f"Unknown decision: {decision}",
            field="decision",
            details={"allowed_decisions": sorted(DECISIONS)},
        )
    return normalized


def _short_text(value: object, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string.", field=field)
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field} must be {max_length} characters or fewer.",
            field=field,
        )
    return cleaned


def _optional_text(value: object, field: str, max_length: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.", field=field)
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field} must be {max_length} characters or fewer.",
            field=field,
        )
    return cleaned
