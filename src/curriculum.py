"""Approved curriculum data and constraint checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import CurriculumError, DataError


@dataclass(frozen=True)
class Outcome:
    id: str
    text: str
    assessment: str
    prerequisite_tags: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "assessment": self.assessment,
            "prerequisite_tags": list(self.prerequisite_tags),
        }


@dataclass(frozen=True)
class Topic:
    subject: str
    class_name: str
    topic: str
    min_duration_minutes: int
    max_duration_minutes: int
    required_activity_tags: tuple[str, ...]
    outcomes: tuple[Outcome, ...]

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "class_name": self.class_name,
            "topic": self.topic,
            "min_duration_minutes": self.min_duration_minutes,
            "max_duration_minutes": self.max_duration_minutes,
            "required_activity_tags": list(self.required_activity_tags),
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }

    def outcome_ids(self) -> list[str]:
        return [outcome.id for outcome in self.outcomes]


class Curriculum:
    """Load approved outcomes and enforce curriculum constraints."""

    def __init__(
        self,
        subjects: dict,
        *,
        curriculum_version: str = "unknown",
        schema_version: int = 1,
    ) -> None:
        self.subjects = subjects
        self.curriculum_version = curriculum_version
        self.schema_version = schema_version

    @classmethod
    def load(cls, path: str | Path) -> "Curriculum":
        data_path = Path(path)
        try:
            text = data_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataError(
                f"Could not read curriculum file: {data_path.name}",
                details=str(exc),
            ) from None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataError(
                f"Curriculum file is not valid JSON: {data_path.name}",
                details=f"line {exc.lineno}, column {exc.colno}",
            ) from None
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "Curriculum":
        if not isinstance(raw, dict):
            raise DataError("Curriculum must be a JSON object.")
        if raw.get("schema_version") != 1:
            raise DataError("Unsupported curriculum schema_version; expected 1.")
        version = raw.get("curriculum_version")
        if not isinstance(version, str) or not version.strip():
            raise DataError("Curriculum must include a non-empty curriculum_version.")
        subjects = raw.get("subjects")
        if not isinstance(subjects, dict) or not subjects:
            raise DataError("Curriculum 'subjects' must be a non-empty object.")

        seen_outcomes: set[str] = set()
        for subject, classes in subjects.items():
            _require_text(subject, "curriculum subject")
            if not isinstance(classes, dict) or not classes:
                raise DataError(f"Curriculum subject '{subject}' must contain classes.")
            for class_name, topics in classes.items():
                _require_text(class_name, f"class under '{subject}'")
                if not isinstance(topics, dict) or not topics:
                    raise DataError(
                        f"Curriculum class '{subject} / {class_name}' must contain topics."
                    )
                for topic_name, topic_data in topics.items():
                    _require_text(topic_name, f"topic under '{subject} / {class_name}'")
                    if not isinstance(topic_data, dict):
                        raise DataError(
                            f"Topic '{subject} / {class_name} / {topic_name}' must be an object."
                        )
                    _validate_topic_data(topic_data, topic_name, seen_outcomes)
        return cls(subjects, curriculum_version=version, schema_version=1)

    def get_topic(self, subject: str, class_name: str, topic: str) -> Topic:
        """Return a topic or raise a helpful curriculum error."""

        if subject not in self.subjects:
            raise CurriculumError(
                f"Subject '{subject}' is not in the approved curriculum.",
                field="subject",
                details={"available_subjects": sorted(self.subjects)},
            )
        classes = self.subjects[subject]
        if class_name not in classes:
            raise CurriculumError(
                f"Class '{class_name}' is not approved for {subject}.",
                field="class_name",
                details={"available_classes": sorted(classes)},
            )
        topics = classes[class_name]
        if topic not in topics:
            raise CurriculumError(
                f"Topic '{topic}' is not approved for {subject} / {class_name}.",
                field="topic",
                details={"available_topics": sorted(topics)},
            )
        data = topics[topic]
        outcomes = tuple(
            Outcome(
                id=item["id"],
                text=item["text"],
                assessment=item["assessment"],
                prerequisite_tags=tuple(item.get("prerequisite_tags", [])),
            )
            for item in data["outcomes"]
        )
        return Topic(
            subject=subject,
            class_name=class_name,
            topic=topic,
            min_duration_minutes=data["min_duration_minutes"],
            max_duration_minutes=data["max_duration_minutes"],
            required_activity_tags=tuple(data.get("required_activity_tags", [])),
            outcomes=outcomes,
        )

    def list_subjects(self) -> list[str]:
        return sorted(self.subjects)

    def list_classes(self, subject: str) -> list[str]:
        if subject not in self.subjects:
            raise CurriculumError(
                f"Subject '{subject}' is not in the approved curriculum.",
                field="subject",
                details={"available_subjects": sorted(self.subjects)},
            )
        return sorted(self.subjects[subject])

    def list_topics(self, subject: str, class_name: str) -> list[str]:
        if subject not in self.subjects:
            raise CurriculumError(
                f"Subject '{subject}' is not in the approved curriculum.",
                field="subject",
                details={"available_subjects": sorted(self.subjects)},
            )
        if class_name not in self.subjects[subject]:
            raise CurriculumError(
                f"Class '{class_name}' is not approved for {subject}.",
                field="class_name",
                details={"available_classes": sorted(self.subjects[subject])},
            )
        return sorted(self.subjects[subject][class_name])

    def all_topics(self) -> list[Topic]:
        topics: list[Topic] = []
        for subject, classes in self.subjects.items():
            for class_name, topic_map in classes.items():
                for topic_name in topic_map:
                    topics.append(self.get_topic(subject, class_name, topic_name))
        return topics

    def validate_duration(self, topic: Topic, duration_minutes: int) -> None:
        if duration_minutes < topic.min_duration_minutes or duration_minutes > topic.max_duration_minutes:
            raise CurriculumError(
                (
                    f"Duration must be between {topic.min_duration_minutes} and "
                    f"{topic.max_duration_minutes} minutes for {topic.subject} / "
                    f"{topic.class_name} / {topic.topic}."
                ),
                field="duration_minutes",
                details={
                    "min_duration_minutes": topic.min_duration_minutes,
                    "max_duration_minutes": topic.max_duration_minutes,
                },
            )

    def validate_outcomes(self, topic: Topic, outcome_ids: list[str]) -> list[Outcome]:
        """Check that every requested outcome is approved for this topic."""

        if not isinstance(outcome_ids, list) or not outcome_ids:
            raise CurriculumError(
                "At least one approved learning outcome is required.",
                field="approved_outcome_ids",
                details={"available_outcome_ids": topic.outcome_ids()},
            )
        if len(set(outcome_ids)) != len(outcome_ids):
            raise CurriculumError(
                "Approved learning outcomes must not contain duplicates.",
                field="approved_outcome_ids",
            )
        by_id = {outcome.id: outcome for outcome in topic.outcomes}
        unknown = [outcome_id for outcome_id in outcome_ids if outcome_id not in by_id]
        if unknown:
            raise CurriculumError(
                f"Outcome '{unknown[0]}' is not approved for {topic.topic}.",
                field="approved_outcome_ids",
                details={
                    "unknown_outcome_ids": unknown,
                    "available_outcome_ids": topic.outcome_ids(),
                },
            )
        return [by_id[outcome_id] for outcome_id in outcome_ids]


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{label} must be a non-empty string.")
    return value.strip()


def _validate_topic_data(topic_data: dict, topic_name: str, seen_outcomes: set[str]) -> None:
    min_duration = topic_data.get("min_duration_minutes")
    max_duration = topic_data.get("max_duration_minutes")
    for value, label in (
        (min_duration, "min_duration_minutes"),
        (max_duration, "max_duration_minutes"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise DataError(
                f"Topic '{topic_name}' {label} must be a positive whole number."
            )
    if min_duration > max_duration:
        raise DataError(f"Topic '{topic_name}' minimum duration exceeds maximum duration.")

    tags = topic_data.get("required_activity_tags", [])
    if not isinstance(tags, list) or any(
        not isinstance(tag, str) or not tag.strip() for tag in tags
    ):
        raise DataError(
            f"Topic '{topic_name}' required_activity_tags must be a list of strings."
        )

    outcomes = topic_data.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        raise DataError(f"Topic '{topic_name}' must contain at least one outcome.")
    for item in outcomes:
        if not isinstance(item, dict):
            raise DataError(f"Topic '{topic_name}' outcomes must be objects.")
        outcome_id = _require_text(item.get("id"), f"outcome id in '{topic_name}'")
        if outcome_id in seen_outcomes:
            raise DataError(f"Duplicate outcome id: {outcome_id}")
        seen_outcomes.add(outcome_id)
        _require_text(item.get("text"), f"outcome text for {outcome_id}")
        _require_text(item.get("assessment"), f"outcome assessment for {outcome_id}")
        prerequisite_tags = item.get("prerequisite_tags", [])
        if not isinstance(prerequisite_tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in prerequisite_tags
        ):
            raise DataError(
                f"Outcome '{outcome_id}' prerequisite_tags must be a list of strings."
            )
