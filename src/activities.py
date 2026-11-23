"""Sample activity library and activity data validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import DataError

DEFAULT_PHASES = ("starter", "main", "practice", "plenary")


@dataclass(frozen=True)
class Activity:
    id: str
    title: str
    description: str
    subject: str
    topics: tuple[str, ...]
    phase: str
    duration_minutes: int
    tags: tuple[str, ...]
    prerequisite_tags: tuple[str, ...]
    targets_tags: tuple[str, ...]
    supports_outcomes: tuple[str, ...]
    materials: tuple[str, ...]
    assessment_evidence: str
    difficulty: str

    def to_dict(self) -> dict:
        return {
            "activity_id": self.id,
            "title": self.title,
            "description": self.description,
            "subject": self.subject,
            "topics": list(self.topics),
            "phase": self.phase,
            "duration_minutes": self.duration_minutes,
            "tags": list(self.tags),
            "prerequisite_tags": list(self.prerequisite_tags),
            "targets_tags": list(self.targets_tags),
            "supports_outcomes": list(self.supports_outcomes),
            "materials": list(self.materials),
            "assessment_evidence": self.assessment_evidence,
            "difficulty": self.difficulty,
        }


class ActivityLibrary:
    """Load and query approved teaching activities."""

    def __init__(self, activities: list[Activity]) -> None:
        self._activities = tuple(activities)

    @classmethod
    def load(
        cls,
        path: str | Path,
        phases: tuple[str, ...] | list[str] | None = None,
    ) -> "ActivityLibrary":
        data_path = Path(path)
        try:
            text = data_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataError(
                f"Could not read activity file: {data_path.name}",
                details=str(exc),
            ) from None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataError(
                f"Activity file is not valid JSON: {data_path.name}",
                details=f"line {exc.lineno}, column {exc.colno}",
            ) from None
        return cls.from_dict(raw, phases=phases)

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        phases: tuple[str, ...] | list[str] | None = None,
    ) -> "ActivityLibrary":
        if not isinstance(raw, dict):
            raise DataError("Activity data must be a JSON object.")
        if raw.get("schema_version") != 1:
            raise DataError("Unsupported activity schema_version; expected 1.")
        items = raw.get("activities")
        if not isinstance(items, list) or not items:
            raise DataError("Activity data must contain a non-empty activities list.")

        allowed_phases = set(phases or DEFAULT_PHASES)
        activities: list[Activity] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise DataError(f"Activity at index {index} must be an object.")
            activity_id = _text(item.get("id"), f"activities[{index}].id", 80)
            if activity_id in seen_ids:
                raise DataError(f"Duplicate activity id: {activity_id}")
            seen_ids.add(activity_id)

            phase = _text(item.get("phase"), f"{activity_id}.phase", 30)
            if phase not in allowed_phases:
                raise DataError(
                    f"Activity '{activity_id}' has invalid phase '{phase}'."
                )

            duration = item.get("duration_minutes")
            if not isinstance(duration, int) or isinstance(duration, bool) or duration < 1:
                raise DataError(
                    f"Activity '{activity_id}' duration_minutes must be a positive whole number."
                )

            topics = _text_list(item.get("topics"), f"{activity_id}.topics", allow_empty=False)
            tags = _text_list(item.get("tags"), f"{activity_id}.tags", allow_empty=False)
            prerequisites = _text_list(
                item.get("prerequisite_tags", []),
                f"{activity_id}.prerequisite_tags",
                allow_empty=True,
            )
            targets = _text_list(
                item.get("targets_tags", []),
                f"{activity_id}.targets_tags",
                allow_empty=True,
            )
            outcomes = _text_list(
                item.get("supports_outcomes"),
                f"{activity_id}.supports_outcomes",
                allow_empty=False,
            )
            materials = _text_list(
                item.get("materials"),
                f"{activity_id}.materials",
                allow_empty=False,
            )

            activities.append(
                Activity(
                    id=activity_id,
                    title=_text(item.get("title"), f"{activity_id}.title", 150),
                    description=_text(
                        item.get("description"),
                        f"{activity_id}.description",
                        600,
                    ),
                    subject=_text(item.get("subject"), f"{activity_id}.subject", 80),
                    topics=tuple(topics),
                    phase=phase,
                    duration_minutes=duration,
                    tags=tuple(tags),
                    prerequisite_tags=tuple(prerequisites),
                    targets_tags=tuple(targets),
                    supports_outcomes=tuple(outcomes),
                    materials=tuple(materials),
                    assessment_evidence=_text(
                        item.get("assessment_evidence"),
                        f"{activity_id}.assessment_evidence",
                        400,
                    ),
                    difficulty=_text(
                        item.get("difficulty", "core"),
                        f"{activity_id}.difficulty",
                        40,
                    ),
                )
            )
        return cls(activities)

    def all(self) -> list[Activity]:
        return list(self._activities)

    def for_topic(self, subject: str, topic: str) -> list[Activity]:
        return [
            activity
            for activity in self._activities
            if activity.subject == subject and topic in activity.topics
        ]


def _text(value: object, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{label} must be a non-empty string.")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise DataError(f"{label} must be {max_length} characters or fewer.")
    return cleaned


def _text_list(value: object, label: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list):
        raise DataError(f"{label} must be a list of strings.")
    if not value and not allow_empty:
        raise DataError(f"{label} must not be empty.")
    cleaned: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{label}[{index}]", 120)
        if text in cleaned:
            raise DataError(f"{label} must not contain duplicates.")
        cleaned.append(text)
    return cleaned
