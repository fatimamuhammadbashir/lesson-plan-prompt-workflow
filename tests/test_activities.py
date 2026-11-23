"""Tests for activity data loading and querying."""

from __future__ import annotations

import copy
import unittest

from src.activities import ActivityLibrary
from src.errors import DataError
from tests.helpers import DATA_DIR, config, curriculum


class ActivityLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config()
        self.library = ActivityLibrary.load(
            DATA_DIR / "activities.json",
            phases=self.config["phase_order"],
        )
        self.raw = __import__("json").loads(
            (DATA_DIR / "activities.json").read_text(encoding="utf-8")
        )

    def test_loads_all_sample_activities(self) -> None:
        self.assertEqual(len(self.library.all()), 29)

    def test_activity_ids_are_unique(self) -> None:
        ids = [activity.id for activity in self.library.all()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_phase_is_configured(self) -> None:
        for activity in self.library.all():
            self.assertIn(activity.phase, self.config["phase_order"])

    def test_for_topic_filters_by_subject_and_topic(self) -> None:
        photosynthesis = self.library.for_topic("Science", "Photosynthesis")
        self.assertEqual(len(photosynthesis), 8)
        self.assertTrue(all(activity.subject == "Science" for activity in photosynthesis))
        self.assertTrue(all("Photosynthesis" in activity.topics for activity in photosynthesis))

    def test_for_topic_returns_empty_for_unknown_topic(self) -> None:
        self.assertEqual(self.library.for_topic("Science", "Volcanoes"), [])

    def test_all_activity_outcomes_exist_in_curriculum(self) -> None:
        valid_ids = {
            outcome.id
            for topic in curriculum().all_topics()
            for outcome in topic.outcomes
        }
        for activity in self.library.all():
            for outcome_id in activity.supports_outcomes:
                self.assertIn(outcome_id, valid_ids, activity.id)

    def test_invalid_schema_is_rejected(self) -> None:
        with self.assertRaises(DataError):
            ActivityLibrary.from_dict({"schema_version": 2, "activities": []})

    def test_empty_activity_list_is_rejected(self) -> None:
        with self.assertRaises(DataError):
            ActivityLibrary.from_dict({"schema_version": 1, "activities": []})

    def test_duplicate_activity_id_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["activities"].append(copy.deepcopy(raw["activities"][0]))
        with self.assertRaises(DataError) as context:
            ActivityLibrary.from_dict(raw, phases=self.config["phase_order"])
        self.assertIn("Duplicate activity id", context.exception.message)

    def test_invalid_phase_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["activities"][0]["phase"] = "warm-up"
        with self.assertRaises(DataError) as context:
            ActivityLibrary.from_dict(raw, phases=self.config["phase_order"])
        self.assertIn("invalid phase", context.exception.message)

    def test_negative_duration_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["activities"][0]["duration_minutes"] = -5
        with self.assertRaises(DataError) as context:
            ActivityLibrary.from_dict(raw, phases=self.config["phase_order"])
        self.assertIn("duration_minutes", context.exception.message)

    def test_empty_materials_are_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["activities"][0]["materials"] = []
        with self.assertRaises(DataError) as context:
            ActivityLibrary.from_dict(raw, phases=self.config["phase_order"])
        self.assertIn("materials", context.exception.message)

    def test_empty_title_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["activities"][0]["title"] = "  "
        with self.assertRaises(DataError):
            ActivityLibrary.from_dict(raw, phases=self.config["phase_order"])

    def test_missing_file_is_reported(self) -> None:
        from pathlib import Path
        import tempfile

        with self.assertRaises(DataError):
            ActivityLibrary.load(Path(tempfile.gettempdir()) / "missing-activities.json")


if __name__ == "__main__":
    unittest.main()
