"""Tests for input and curriculum constraint validation."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.curriculum import Curriculum
from src.errors import CurriculumError, ValidationError
from src.validation import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    load_json_object,
    request_template,
    validate_request,
)
from tests.helpers import DATA_DIR, config, curriculum, sample_request


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config()
        self.curriculum = curriculum()

    def validate(self, payload: dict):
        return validate_request(payload, self.curriculum, self.config)

    def test_valid_request_returns_typed_object(self) -> None:
        request = self.validate(sample_request())
        self.assertEqual(request.subject, "Science")
        self.assertEqual(request.class_name, "Year 7")
        self.assertEqual(request.topic, "Photosynthesis")
        self.assertEqual(request.duration_minutes, 60)
        self.assertEqual(request.learner_preferences, ("hands-on", "visual", "group work"))
        self.assertEqual(len(request.approved_outcome_ids), 3)
        self.assertEqual(request.previous_results.class_average, 58.0)

    def test_missing_required_fields(self) -> None:
        for field in REQUIRED_FIELDS:
            payload = sample_request()
            payload.pop(field)
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as context:
                    self.validate(payload)
                self.assertEqual(context.exception.field, field)

    def test_unknown_field_is_rejected(self) -> None:
        payload = sample_request()
        payload["unexpected"] = True
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "unexpected")

    def test_empty_subject_is_rejected(self) -> None:
        payload = sample_request()
        payload["subject"] = "   "
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "subject")

    def test_unknown_subject_is_rejected(self) -> None:
        payload = sample_request()
        payload["subject"] = "Drama"
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "subject")
        self.assertIn("Drama", context.exception.message)

    def test_unknown_class_is_rejected(self) -> None:
        payload = sample_request()
        payload["class_name"] = "Year 9"
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "class_name")

    def test_unknown_topic_is_rejected(self) -> None:
        payload = sample_request()
        payload["topic"] = " Volcanoes"
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "topic")

    def test_duration_must_be_an_integer(self) -> None:
        for value in ("60", 60.5, True, None):
            payload = sample_request()
            payload["duration_minutes"] = value
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as context:
                    self.validate(payload)
                self.assertEqual(context.exception.field, "duration_minutes")

    def test_duration_below_global_minimum(self) -> None:
        payload = sample_request()
        payload["duration_minutes"] = 10
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "duration_minutes")

    def test_duration_below_curriculum_minimum(self) -> None:
        payload = sample_request()
        payload["duration_minutes"] = 25
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "duration_minutes")

    def test_duration_above_curriculum_maximum(self) -> None:
        payload = sample_request()
        payload["duration_minutes"] = 95
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "duration_minutes")

    def test_preferences_cannot_be_empty(self) -> None:
        payload = sample_request()
        payload["learner_preferences"] = []
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "learner_preferences")

    def test_unknown_preference_is_rejected(self) -> None:
        payload = sample_request()
        payload["learner_preferences"] = ["hands-on", "telepathy"]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "learner_preferences")
        self.assertIn("telepathy", context.exception.message)

    def test_duplicate_preference_is_rejected(self) -> None:
        payload = sample_request()
        payload["learner_preferences"] = ["visual", "visual"]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "learner_preferences")

    def test_too_many_preferences(self) -> None:
        payload = sample_request()
        payload["learner_preferences"] = [
            "visual",
            "auditory",
            "reading/writing",
            "kinesthetic",
            "hands-on",
            "group work",
        ]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "learner_preferences")

    def test_previous_results_requires_core_fields(self) -> None:
        payload = sample_request()
        payload["previous_results"].pop("class_average")
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "previous_results.class_average")

    def test_previous_average_range(self) -> None:
        for value in (-1, 101, "58"):
            payload = sample_request()
            payload["previous_results"]["class_average"] = value
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as context:
                    self.validate(payload)
                self.assertEqual(context.exception.field, "previous_results.class_average")

    def test_completion_rate_range(self) -> None:
        for value in (-0.1, 1.1, True):
            payload = sample_request()
            payload["previous_results"]["completion_rate"] = value
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as context:
                    self.validate(payload)
                self.assertEqual(context.exception.field, "previous_results.completion_rate")

    def test_weak_and_mastered_tags_cannot_overlap(self) -> None:
        payload = sample_request()
        payload["previous_results"]["weak_topics"] = ["cells"]
        payload["previous_results"]["mastered_tags"] = ["cells"]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "previous_results")

    def test_duplicate_previous_tag_is_rejected(self) -> None:
        payload = sample_request()
        payload["previous_results"]["weak_topics"] = ["cells", "Cells"]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "previous_results.weak_topics")

    def test_outcomes_cannot_be_empty(self) -> None:
        payload = sample_request()
        payload["approved_outcome_ids"] = []
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "approved_outcome_ids")

    def test_duplicate_outcomes_are_rejected(self) -> None:
        payload = sample_request()
        payload["approved_outcome_ids"] = ["SCI7-PH-01", "SCI7-PH-01"]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "approved_outcome_ids")

    def test_too_many_outcomes(self) -> None:
        payload = sample_request()
        payload["approved_outcome_ids"] = [
            "SCI7-PH-01",
            "SCI7-PH-02",
            "SCI7-PH-03",
            "SCI7-PH-01",
            "SCI7-PH-02",
        ]
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "approved_outcome_ids")

    def test_unknown_outcome_is_rejected(self) -> None:
        payload = sample_request()
        payload["approved_outcome_ids"] = ["SCI7-PH-99"]
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "approved_outcome_ids")

    def test_outcome_from_another_topic_is_rejected(self) -> None:
        payload = sample_request()
        payload["approved_outcome_ids"] = ["SCI7-FM-01"]
        with self.assertRaises(CurriculumError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "approved_outcome_ids")
        self.assertIn("available_outcome_ids", context.exception.details)

    def test_teacher_notes_length_is_limited(self) -> None:
        payload = sample_request()
        payload["teacher_notes"] = "x" * 501
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        self.assertEqual(context.exception.field, "teacher_notes")

    def test_teacher_notes_are_optional(self) -> None:
        payload = sample_request()
        payload.pop("teacher_notes", None)
        request = self.validate(payload)
        self.assertEqual(request.teacher_notes, "")

    def test_template_has_all_request_fields(self) -> None:
        template = request_template()
        self.assertEqual(set(template), set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS))
        self.assertIn("previous_results", template)
        self.assertEqual(
            set(template["previous_results"]),
            {"class_average", "completion_rate", "weak_topics", "mastered_tags"},
        )

    def test_load_json_object_handles_missing_file(self) -> None:
        with self.assertRaises(ValidationError) as context:
            load_json_object(Path(tempfile.gettempdir()) / "does-not-exist-xyz.json")
        self.assertEqual(context.exception.field, "$")

    def test_load_json_object_handles_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValidationError) as context:
                load_json_object(path)
            self.assertEqual(context.exception.field, "$")

    def test_load_json_object_requires_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text(json.dumps([1, 2]), encoding="utf-8")
            with self.assertRaises(ValidationError) as context:
                load_json_object(path)
            self.assertEqual(context.exception.field, "$")

    def test_validation_error_serializes_safely(self) -> None:
        payload = sample_request()
        payload["duration_minutes"] = 0
        with self.assertRaises(ValidationError) as context:
            self.validate(payload)
        rendered = context.exception.to_dict()
        self.assertEqual(rendered["error"]["type"], "validation_error")
        self.assertIn("message", rendered["error"])
        self.assertNotIn("Traceback", json.dumps(rendered))


class CurriculumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.curriculum = curriculum()

    def test_loads_all_sample_topics(self) -> None:
        self.assertEqual(len(self.curriculum.all_topics()), 4)
        self.assertEqual(
            [topic.topic for topic in self.curriculum.all_topics()],
            ["Photosynthesis", "Forces and Motion", "Persuasive Writing", "Fractions"],
        )

    def test_lists_subjects_classes_and_topics(self) -> None:
        self.assertEqual(self.curriculum.list_subjects(), ["English", "Mathematics", "Science"])
        self.assertEqual(self.curriculum.list_classes("Science"), ["Year 7"])
        self.assertEqual(
            self.curriculum.list_topics("Science", "Year 7"),
            ["Forces and Motion", "Photosynthesis"],
        )

    def test_get_topic_returns_outcomes(self) -> None:
        topic = self.curriculum.get_topic("Science", "Year 7", "Photosynthesis")
        self.assertEqual(topic.min_duration_minutes, 30)
        self.assertEqual(topic.max_duration_minutes, 90)
        self.assertEqual(len(topic.outcomes), 3)
        self.assertEqual(topic.outcomes[0].id, "SCI7-PH-01")

    def test_unknown_subject_has_helpful_details(self) -> None:
        with self.assertRaises(CurriculumError) as context:
            self.curriculum.get_topic("Drama", "Year 7", "Photosynthesis")
        self.assertEqual(context.exception.field, "subject")
        self.assertIn("available_subjects", context.exception.details)

    def test_unknown_class_has_helpful_details(self) -> None:
        with self.assertRaises(CurriculumError) as context:
            self.curriculum.get_topic("Science", "Year 8", "Photosynthesis")
        self.assertEqual(context.exception.field, "class_name")
        self.assertIn("available_classes", context.exception.details)

    def test_unknown_topic_has_helpful_details(self) -> None:
        with self.assertRaises(CurriculumError) as context:
            self.curriculum.get_topic("Science", "Year 7", "Volcanoes")
        self.assertEqual(context.exception.field, "topic")
        self.assertIn("available_topics", context.exception.details)

    def test_duration_constraints(self) -> None:
        topic = self.curriculum.get_topic("Science", "Year 7", "Photosynthesis")
        self.curriculum.validate_duration(topic, 30)
        self.curriculum.validate_duration(topic, 90)
        with self.assertRaises(CurriculumError):
            self.curriculum.validate_duration(topic, 29)
        with self.assertRaises(CurriculumError):
            self.curriculum.validate_duration(topic, 91)

    def test_outcome_validation_returns_objects(self) -> None:
        topic = self.curriculum.get_topic("Science", "Year 7", "Photosynthesis")
        outcomes = self.curriculum.validate_outcomes(
            topic,
            ["SCI7-PH-01", "SCI7-PH-03"],
        )
        self.assertEqual([outcome.id for outcome in outcomes], ["SCI7-PH-01", "SCI7-PH-03"])
        with self.assertRaises(CurriculumError):
            self.curriculum.validate_outcomes(topic, ["SCI7-PH-01", "SCI7-PH-01"])
        with self.assertRaises(CurriculumError):
            self.curriculum.validate_outcomes(topic, [])

    def test_duplicate_outcome_ids_in_data_are_rejected(self) -> None:
        raw = {
            "schema_version": 1,
            "curriculum_version": "test",
            "subjects": {
                "Science": {
                    "Year 7": {
                        "Topic": {
                            "min_duration_minutes": 30,
                            "max_duration_minutes": 60,
                            "outcomes": [
                                {
                                    "id": "X-1",
                                    "text": "A",
                                    "assessment": "B",
                                    "prerequisite_tags": [],
                                },
                                {
                                    "id": "X-1",
                                    "text": "C",
                                    "assessment": "D",
                                    "prerequisite_tags": [],
                                },
                            ],
                        }
                    }
                }
            },
        }
        from src.errors import DataError

        with self.assertRaises(DataError):
            Curriculum.from_dict(raw)

    def test_invalid_schema_is_rejected(self) -> None:
        from src.errors import DataError

        with self.assertRaises(DataError):
            Curriculum.from_dict({"schema_version": 2, "subjects": {}})

    def test_missing_file_is_reported(self) -> None:
        from src.errors import DataError

        with self.assertRaises(DataError):
            Curriculum.load(Path(tempfile.gettempdir()) / "missing-curriculum.json")

    def test_sample_curriculum_outcomes_are_unique(self) -> None:
        ids = [
            outcome.id
            for topic in self.curriculum.all_topics()
            for outcome in topic.outcomes
        ]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
