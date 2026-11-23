"""Teacher input validation against configuration and curriculum."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .curriculum import Curriculum, Outcome
from .errors import ValidationError

REQUIRED_FIELDS = (
    "subject",
    "class_name",
    "topic",
    "duration_minutes",
    "learner_preferences",
    "previous_results",
    "approved_outcome_ids",
)
OPTIONAL_FIELDS = ("teacher_notes",)


@dataclass(frozen=True)
class PreviousResults:
    class_average: float
    completion_rate: float
    weak_topics: tuple[str, ...]
    mastered_tags: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "class_average": self.class_average,
            "completion_rate": self.completion_rate,
            "weak_topics": list(self.weak_topics),
            "mastered_tags": list(self.mastered_tags),
        }


@dataclass(frozen=True)
class LessonRequest:
    subject: str
    class_name: str
    topic: str
    duration_minutes: int
    learner_preferences: tuple[str, ...]
    previous_results: PreviousResults
    approved_outcome_ids: tuple[str, ...]
    teacher_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "class_name": self.class_name,
            "topic": self.topic,
            "duration_minutes": self.duration_minutes,
            "learner_preferences": list(self.learner_preferences),
            "previous_results": self.previous_results.to_dict(),
            "approved_outcome_ids": list(self.approved_outcome_ids),
            "teacher_notes": self.teacher_notes,
        }


def request_template() -> dict:
    """Return a copy of the input template with placeholders."""

    return {
        "subject": "<subject, for example Science>",
        "class_name": "<class, for example Year 7>",
        "topic": "<approved curriculum topic>",
        "duration_minutes": 60,
        "learner_preferences": ["<one or more allowed preferences>"],
        "previous_results": {
            "class_average": 0,
            "completion_rate": 0,
            "weak_topics": [],
            "mastered_tags": [],
        },
        "approved_outcome_ids": ["<approved outcome id from data/curriculum.json>"],
        "teacher_notes": "",
    }


def load_json_object(path: str | Path) -> dict:
    """Read a JSON object, turning file and syntax errors into safe errors."""

    data_path = Path(path)
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(
            f"Could not read JSON file: {data_path.name}",
            field="$",
            details=str(exc),
        ) from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"File is not valid JSON: {data_path.name}",
            field="$",
            details=f"line {exc.lineno}, column {exc.colno}",
        ) from None
    if not isinstance(raw, dict):
        raise ValidationError(
            f"JSON file must contain an object: {data_path.name}",
            field="$",
        )
    return raw


def validate_request(payload: dict, curriculum: Curriculum, config: dict) -> LessonRequest:
    """Validate the full lesson request and return a typed object."""

    if not isinstance(payload, dict):
        raise ValidationError("Lesson request must be a JSON object.", field="$")

    allowed = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValidationError(
            f"Unknown request field: {unknown[0]}",
            field=unknown[0],
            details={"unknown_fields": unknown, "allowed_fields": sorted(allowed)},
        )

    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValidationError(f"Missing required field: {field}", field=field)

    input_config = config["input"]
    max_text = input_config["max_text_length"]

    subject = _text(payload["subject"], "subject", 100)
    class_name = _text(payload["class_name"], "class_name", 100)
    topic = _text(payload["topic"], "topic", 120)

    duration = payload["duration_minutes"]
    if not isinstance(duration, int) or isinstance(duration, bool):
        raise ValidationError("duration_minutes must be a whole number.", field="duration_minutes")
    if duration < input_config["min_duration_minutes"] or duration > input_config["max_duration_minutes"]:
        raise ValidationError(
            (
                f"duration_minutes must be between {input_config['min_duration_minutes']} and "
                f"{input_config['max_duration_minutes']}."
            ),
            field="duration_minutes",
        )

    preferences = _preference_list(payload["learner_preferences"], config, input_config)
    previous_results = _previous_results(payload["previous_results"], input_config)
    outcome_ids = _outcome_id_list(payload["approved_outcome_ids"], input_config)

    teacher_notes = payload.get("teacher_notes", "")
    if teacher_notes is None:
        teacher_notes = ""
    teacher_notes = _text(teacher_notes, "teacher_notes", max_text, allow_empty=True)

    topic_context = curriculum.get_topic(subject, class_name, topic)
    curriculum.validate_duration(topic_context, duration)
    curriculum.validate_outcomes(topic_context, outcome_ids)

    return LessonRequest(
        subject=subject,
        class_name=class_name,
        topic=topic,
        duration_minutes=duration,
        learner_preferences=tuple(preferences),
        previous_results=previous_results,
        approved_outcome_ids=tuple(outcome_ids),
        teacher_notes=teacher_notes,
    )


def selected_outcomes(request: LessonRequest, curriculum: Curriculum) -> list[Outcome]:
    topic = curriculum.get_topic(request.subject, request.class_name, request.topic)
    return curriculum.validate_outcomes(topic, list(request.approved_outcome_ids))


def _text(
    value: object,
    field: str,
    max_length: int,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.", field=field)
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise ValidationError(f"{field} must not be empty.", field=field)
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field} must be {max_length} characters or fewer.",
            field=field,
        )
    return cleaned


def _preference_list(value: object, config: dict, input_config: dict) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError("learner_preferences must be a list.", field="learner_preferences")
    if len(value) < 1:
        raise ValidationError(
            "learner_preferences must contain at least one preference.",
            field="learner_preferences",
        )
    if len(value) > input_config["max_learner_preferences"]:
        raise ValidationError(
            (
                "learner_preferences must contain at most "
                f"{input_config['max_learner_preferences']} preferences."
            ),
            field="learner_preferences",
        )

    allowed = {item.lower() for item in config["allowed_preferences"]}
    cleaned: list[str] = []
    for index, item in enumerate(value):
        preference = _text(item, f"learner_preferences[{index}]", 50).lower()
        if preference not in allowed:
            raise ValidationError(
                f"Unknown learner preference: {preference}",
                field="learner_preferences",
                details={"allowed_preferences": sorted(allowed)},
            )
        if preference in cleaned:
            raise ValidationError(
                f"Duplicate learner preference: {preference}",
                field="learner_preferences",
            )
        cleaned.append(preference)
    return cleaned


def _string_tag_list(value: object, field: str, max_items: int = 20) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list of strings.", field=field)
    if len(value) > max_items:
        raise ValidationError(
            f"{field} must contain at most {max_items} items.",
            field=field,
        )
    cleaned: list[str] = []
    for index, item in enumerate(value):
        tag = _text(item, f"{field}[{index}]", 60).lower()
        if tag in cleaned:
            raise ValidationError(f"Duplicate value in {field}: {tag}", field=field)
        cleaned.append(tag)
    return cleaned


def _previous_results(value: object, input_config: dict) -> PreviousResults:
    if not isinstance(value, dict):
        raise ValidationError("previous_results must be an object.", field="previous_results")

    allowed = {"class_average", "completion_rate", "weak_topics", "mastered_tags"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValidationError(
            f"Unknown previous_results field: {unknown[0]}",
            field="previous_results",
            details={"unknown_fields": unknown, "allowed_fields": sorted(allowed)},
        )
    for field in ("class_average", "completion_rate"):
        if field not in value:
            raise ValidationError(
                f"Missing required previous_results field: {field}",
                field=f"previous_results.{field}",
            )

    average = value["class_average"]
    if isinstance(average, bool) or not isinstance(average, (int, float)):
        raise ValidationError(
            "previous_results.class_average must be a number.",
            field="previous_results.class_average",
        )
    average = float(average)
    if average < 0 or average > 100:
        raise ValidationError(
            "previous_results.class_average must be between 0 and 100.",
            field="previous_results.class_average",
        )

    completion = value["completion_rate"]
    if isinstance(completion, bool) or not isinstance(completion, (int, float)):
        raise ValidationError(
            "previous_results.completion_rate must be a number.",
            field="previous_results.completion_rate",
        )
    completion = float(completion)
    if completion < 0 or completion > 1:
        raise ValidationError(
            "previous_results.completion_rate must be between 0 and 1.",
            field="previous_results.completion_rate",
        )

    weak = _string_tag_list(value.get("weak_topics"), "previous_results.weak_topics")
    mastered = _string_tag_list(value.get("mastered_tags"), "previous_results.mastered_tags")
    overlap = sorted(set(weak) & set(mastered))
    if overlap:
        raise ValidationError(
            f"Topic '{overlap[0]}' cannot be both weak and mastered.",
            field="previous_results",
            details={"overlapping_tags": overlap},
        )
    return PreviousResults(
        class_average=average,
        completion_rate=completion,
        weak_topics=tuple(weak),
        mastered_tags=tuple(mastered),
    )


def _outcome_id_list(value: object, input_config: dict) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(
            "approved_outcome_ids must be a list.",
            field="approved_outcome_ids",
        )
    if len(value) < 1:
        raise ValidationError(
            "approved_outcome_ids must contain at least one outcome.",
            field="approved_outcome_ids",
        )
    if len(value) > input_config["max_outcomes"]:
        raise ValidationError(
            f"approved_outcome_ids must contain at most {input_config['max_outcomes']} outcomes.",
            field="approved_outcome_ids",
        )
    cleaned: list[str] = []
    for index, item in enumerate(value):
        outcome_id = _text(item, f"approved_outcome_ids[{index}]", 80)
        if outcome_id in cleaned:
            raise ValidationError(
                f"Duplicate approved outcome id: {outcome_id}",
                field="approved_outcome_ids",
            )
        cleaned.append(outcome_id)
    return cleaned
