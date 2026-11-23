"""Safe JSON persistence for lesson plans and review history."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from .errors import StorageError

PLAN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class PlanStore:
    """Store one JSON file per plan plus an append-only review log."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.plans_dir = self.root / "plans"
        self.review_log = self.root / "review_history.jsonl"

    def save(self, plan: dict) -> None:
        if not isinstance(plan, dict):
            raise StorageError("Lesson plan must be an object.")
        plan_id = self._plan_id(plan.get("plan_id"))
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        target = self.plans_dir / f"{plan_id}.json"
        temporary = self.plans_dir / f".{plan_id}.{uuid.uuid4().hex}.tmp"
        try:
            temporary.write_text(
                json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, target)
        except OSError as exc:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            raise StorageError(
                f"Could not save lesson plan: {plan_id}",
                details=str(exc),
            ) from None

    def load(self, plan_id: str) -> dict:
        safe_id = self._plan_id(plan_id)
        path = self.plans_dir / f"{safe_id}.json"
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise StorageError(
                f"Lesson plan not found: {safe_id}",
                field="plan_id",
            ) from None
        except OSError as exc:
            raise StorageError(
                f"Could not read lesson plan: {safe_id}",
                details=str(exc),
            ) from None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Stored lesson plan is not valid JSON: {safe_id}",
                details=f"line {exc.lineno}, column {exc.colno}",
            ) from None
        if not isinstance(raw, dict):
            raise StorageError(f"Stored lesson plan is not an object: {safe_id}")
        return raw

    def list_plans(self) -> list[dict]:
        if not self.plans_dir.exists():
            return []
        summaries: list[dict] = []
        for path in sorted(self.plans_dir.glob("*.json")):
            plan = self.load(path.stem)
            request = plan.get("request", {})
            review = plan.get("review", {})
            summaries.append(
                {
                    "plan_id": plan.get("plan_id", path.stem),
                    "status": review.get("status", plan.get("status")),
                    "reviewer": review.get("reviewer"),
                    "decided_at": review.get("decided_at"),
                    "subject": request.get("subject"),
                    "class_name": request.get("class_name"),
                    "topic": request.get("topic"),
                    "duration_minutes": request.get("duration_minutes"),
                    "activity_count": len(plan.get("activities", [])),
                    "objective_count": len(plan.get("objectives", [])),
                    "updated_at": plan.get("updated_at"),
                }
            )
        return summaries

    def append_review(self, plan: dict) -> None:
        """Append the latest review decision to the JSONL audit log."""

        if not isinstance(plan, dict):
            raise StorageError("Lesson plan must be an object.")
        plan_id = self._plan_id(plan.get("plan_id"))
        review = plan.get("review", {})
        history = review.get("history", [])
        latest = history[-1] if history else {}
        record = {
            "timestamp_utc": latest.get("timestamp_utc", plan.get("updated_at")),
            "plan_id": plan_id,
            "status": review.get("status", plan.get("status")),
            "reviewer": review.get("reviewer"),
            "decided_at": review.get("decided_at"),
            "notes": review.get("notes"),
            "action": latest.get("action"),
        }
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            with self.review_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise StorageError(
                "Could not append to the review history log.",
                details=str(exc),
            ) from None

    @staticmethod
    def _plan_id(value: object) -> str:
        if (
            not isinstance(value, str)
            or not PLAN_ID_RE.match(value)
            or value.upper() in WINDOWS_RESERVED_NAMES
        ):
            raise StorageError(
                "Invalid plan_id. Use letters, numbers, hyphens and underscores only.",
                field="plan_id",
            )
        return value
