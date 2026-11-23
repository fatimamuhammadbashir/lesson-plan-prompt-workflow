"""Tests for structured lesson plan generation."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from src.activities import ActivityLibrary
from src.curriculum import Curriculum
from src.errors import PlanningError
from src.planner import LessonPlanner
from src.ranking import ActivityRanker
from tests.helpers import FIXED_NOW, DATA_DIR, config, make_plan, make_service, sample_request


class PlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = make_service(self.temp_dir.name)
        self.plan = make_plan(self.service)

    def test_plan_has_required_sections(self) -> None:
        for key in (
            "objectives",
            "materials",
            "activities",
            "assessment",
            "conclusion",
        ):
            self.assertIn(key, self.plan)
            self.assertTrue(self.plan[key])

    def test_plan_starts_pending_teacher_review(self) -> None:
        self.assertEqual(self.plan["status"], "Pending Teacher Review")
        self.assertEqual(self.plan["review"]["status"], "Pending Teacher Review")
        self.assertIsNone(self.plan["review"]["reviewer"])
        self.assertEqual(self.plan["review"]["history"][0]["action"], "created")

    def test_objectives_come_from_approved_outcomes(self) -> None:
        source_ids = [objective["source_outcome_id"] for objective in self.plan["objectives"]]
        self.assertEqual(source_ids, ["SCI7-PH-01", "SCI7-PH-02", "SCI7-PH-03"])
        for objective in self.plan["objectives"]:
            self.assertTrue(objective["text"])
            self.assertTrue(objective["success_criteria"])

    def test_materials_are_unique_and_non_empty(self) -> None:
        materials = self.plan["materials"]
        self.assertTrue(materials)
        self.assertEqual(len(materials), len(set(materials)))

    def test_activities_are_sequenced_by_phase(self) -> None:
        phase_order = config()["phase_order"]
        phases = [activity["phase"] for activity in self.plan["activities"]]
        self.assertEqual(phases, sorted(phases, key=phase_order.index))
        self.assertEqual(
            [activity["sequence"] for activity in self.plan["activities"]],
            list(range(1, len(phases) + 1)),
        )

    def test_activity_duration_fits_request(self) -> None:
        planned = sum(activity["duration_minutes"] for activity in self.plan["activities"])
        self.assertLessEqual(planned, self.plan["request"]["duration_minutes"])
        self.assertEqual(planned, self.plan["timing"]["planned_minutes"])
        self.assertEqual(
            self.plan["timing"]["flex_minutes"],
            self.plan["request"]["duration_minutes"] - planned,
        )

    def test_every_activity_has_reasons_and_score_breakdown(self) -> None:
        for activity in self.plan["activities"]:
            self.assertTrue(activity["reasons"])
            self.assertTrue(activity["score_breakdown"])
            self.assertIsInstance(activity["score"], float)

    def test_activity_ids_are_unique(self) -> None:
        ids = [activity["activity_id"] for activity in self.plan["activities"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_coverage_reports_all_outcomes(self) -> None:
        coverage = self.plan["coverage"]
        self.assertEqual(coverage["uncovered_outcomes"], [])
        self.assertEqual(
            set(coverage["requested_outcomes"]),
            {"SCI7-PH-01", "SCI7-PH-02", "SCI7-PH-03"},
        )

    def test_assessment_contains_success_criteria(self) -> None:
        assessment = self.plan["assessment"]
        self.assertTrue(assessment["formative"])
        self.assertTrue(assessment["summative"])
        self.assertEqual(len(assessment["success_criteria"]), 3)

    def test_conclusion_contains_summary_and_next_steps(self) -> None:
        conclusion = self.plan["conclusion"]
        self.assertTrue(conclusion["summary"])
        self.assertTrue(conclusion["next_steps"])
        self.assertTrue(conclusion["exit_prompt"])

    def test_plan_is_saved_and_loadable(self) -> None:
        loaded = self.service.get("LP-TEST-001")
        self.assertEqual(loaded["plan_id"], "LP-TEST-001")
        self.assertEqual(loaded["status"], "Pending Teacher Review")

    def test_custom_plan_id_is_used(self) -> None:
        plan = make_plan(self.service, plan_id="LP-CUSTOM-42")
        self.assertEqual(plan["plan_id"], "LP-CUSTOM-42")
        self.assertTrue((Path(self.temp_dir.name) / "plans" / "LP-CUSTOM-42.json").exists())

    def test_generated_plan_ids_are_unique(self) -> None:
        first = self.service.create(sample_request(), now=FIXED_NOW)
        second = self.service.create(sample_request(), now=FIXED_NOW)
        self.assertNotEqual(first["plan_id"], second["plan_id"])
        self.assertRegex(first["plan_id"], r"^LP-\d{8}-\d{6}-[A-F0-9]{6}$")
        self.assertRegex(second["plan_id"], r"^LP-\d{8}-\d{6}-[A-F0-9]{6}$")

    def test_invalid_plan_id_is_rejected(self) -> None:
        with self.assertRaises(PlanningError) as context:
            make_plan(self.service, plan_id="../escape")
        self.assertEqual(context.exception.field, "plan_id")

    def test_missing_activities_is_reported(self) -> None:
        curriculum = Curriculum.load(DATA_DIR / "curriculum.json")
        planner = LessonPlanner(
            curriculum,
            ActivityLibrary([]),
            config(),
            ranker=ActivityRanker(config()),
        )
        from src.validation import validate_request

        request = validate_request(sample_request(), curriculum, config())
        with self.assertRaises(PlanningError) as context:
            planner.generate(request, plan_id="LP-NO-ACTIVITIES", now=FIXED_NOW)
        self.assertIn("No approved activities", context.exception.message)

    def test_timestamps_are_utc(self) -> None:
        self.assertTrue(self.plan["created_at"].endswith("Z"))
        self.assertTrue(self.plan["updated_at"].endswith("Z"))
        self.assertEqual(self.plan["created_at"], self.plan["updated_at"])

    def test_plan_id_pattern_from_custom_id(self) -> None:
        self.assertTrue(re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", self.plan["plan_id"]))


if __name__ == "__main__":
    unittest.main()
