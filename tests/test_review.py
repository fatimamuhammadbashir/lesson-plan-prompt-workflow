"""Tests for the teacher review state machine and editing."""

from __future__ import annotations

import copy
import tempfile
import unittest

from src.errors import ReviewError, ValidationError
from tests.helpers import FIXED_NOW, make_plan, make_service, sample_edits


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = make_service(self.temp_dir.name)
        self.plan = make_plan(self.service)

    def test_created_plan_has_creation_history(self) -> None:
        history = self.plan["review"]["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action"], "created")
        self.assertEqual(history[0]["to_status"], "Pending Teacher Review")
        self.assertIn("timestamp_utc", history[0])

    def test_teacher_can_edit_pending_draft(self) -> None:
        updated = self.service.edit("LP-TEST-001", sample_edits(), actor="Ms. Rivera")
        self.assertEqual(updated["status"], "Pending Teacher Review")
        self.assertEqual(updated["review"]["status"], "Pending Teacher Review")
        latest = updated["review"]["history"][-1]
        self.assertEqual(latest["action"], "edited")
        self.assertEqual(latest["actor"], "Ms. Rivera")
        self.assertEqual(
            latest["details"]["changed_fields"],
            ["assessment", "conclusion", "objectives"],
        )
        self.assertIn("Clarified", latest["details"]["note"])
        self.assertIn("chlorophyll", updated["objectives"][0]["text"])

    def test_edit_requires_at_least_one_field(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.edit("LP-TEST-001", {"note": "No actual edit"})
        self.assertEqual(context.exception.field, "$")

    def test_edit_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.edit("LP-TEST-001", {"title": "New title"})
        self.assertEqual(context.exception.field, "title")

    def test_edit_rejects_invalid_activity_phase(self) -> None:
        activities = copy.deepcopy(self.plan["activities"])
        activities[0]["phase"] = "warm-up"
        with self.assertRaises(ValidationError) as context:
            self.service.edit("LP-TEST-001", {"activities": activities})
        self.assertEqual(context.exception.field, "activities[0].phase")

    def test_edit_rejects_activities_over_duration(self) -> None:
        activities = copy.deepcopy(self.plan["activities"])
        activities[0]["duration_minutes"] = 120
        with self.assertRaises(ValidationError) as context:
            self.service.edit("LP-TEST-001", {"activities": activities})
        self.assertEqual(context.exception.field, "activities")

    def test_edit_recalculates_timing(self) -> None:
        activities = copy.deepcopy(self.plan["activities"])
        activities[0]["duration_minutes"] = 5
        updated = self.service.edit("LP-TEST-001", {"activities": activities})
        planned = sum(item["duration_minutes"] for item in updated["activities"])
        self.assertEqual(updated["timing"]["planned_minutes"], planned)
        self.assertEqual(updated["timing"]["flex_minutes"], 60 - planned)

    def test_edit_after_approval_is_rejected(self) -> None:
        self.service.review(
            "LP-TEST-001",
            "approved",
            reviewer="Ms. Rivera",
            notes="Ready.",
        )
        with self.assertRaises(ReviewError):
            self.service.edit("LP-TEST-001", {"materials": ["New material"]})

    def test_edit_after_rejection_is_rejected(self) -> None:
        self.service.review(
            "LP-TEST-001",
            "rejected",
            reviewer="Mr. Chen",
            notes="Wrong activity sequence.",
        )
        with self.assertRaises(ReviewError):
            self.service.edit("LP-TEST-001", {"materials": ["New material"]})

    def test_approval_records_decision_and_details(self) -> None:
        approved = self.service.review(
            "LP-TEST-001",
            "approved",
            reviewer="Ms. Rivera",
            notes="Ready to teach.",
        )
        self.assertEqual(approved["status"], "Approved")
        self.assertEqual(approved["review"]["status"], "Approved")
        self.assertEqual(approved["review"]["reviewer"], "Ms. Rivera")
        self.assertEqual(approved["review"]["notes"], "Ready to teach.")
        self.assertTrue(approved["review"]["decided_at"].endswith("Z"))
        latest = approved["review"]["history"][-1]
        self.assertEqual(latest["action"], "decision")
        self.assertEqual(latest["to_status"], "Approved")
        self.assertEqual(latest["details"]["decision"], "approved")

    def test_rejection_requires_notes(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.review(
                "LP-TEST-001",
                "rejected",
                reviewer="Mr. Chen",
                notes="",
            )
        self.assertEqual(context.exception.field, "notes")

    def test_rejection_with_notes(self) -> None:
        rejected = self.service.review(
            "LP-TEST-001",
            "rejected",
            reviewer="Mr. Chen",
            notes="The starter is too long for this class.",
        )
        self.assertEqual(rejected["status"], "Rejected")
        self.assertEqual(rejected["review"]["status"], "Rejected")
        self.assertEqual(rejected["review"]["notes"], "The starter is too long for this class.")

    def test_needs_revision_then_edit_resubmits(self) -> None:
        revision = self.service.review(
            "LP-TEST-001",
            "needs_revision",
            reviewer="Head of Science",
            notes="Add a vocabulary check.",
        )
        self.assertEqual(revision["status"], "Needs Revision")
        self.assertEqual(revision["review"]["reviewer"], "Head of Science")
        updated = self.service.edit(
            "LP-TEST-001",
            {"conclusion": "Add a three-word vocabulary check.", "note": "Added."},
            actor="Ms. Rivera",
        )
        self.assertEqual(updated["status"], "Pending Teacher Review")
        self.assertEqual(updated["review"]["status"], "Pending Teacher Review")
        self.assertIsNone(updated["review"]["reviewer"])
        self.assertIsNone(updated["review"]["decided_at"])
        self.assertIsNone(updated["review"]["notes"])
        self.assertEqual(updated["review"]["history"][-1]["action"], "edited")
        self.assertIsInstance(updated["conclusion"], dict)
        self.assertEqual(updated["conclusion"]["summary"], "Add a three-word vocabulary check.")

    def test_decision_after_approval_is_rejected(self) -> None:
        self.service.review("LP-TEST-001", "approved", reviewer="Ms. Rivera", notes="OK")
        with self.assertRaises(ReviewError):
            self.service.review("LP-TEST-001", "rejected", reviewer="Mr. Chen", notes="No")

    def test_decision_after_rejection_is_rejected(self) -> None:
        self.service.review("LP-TEST-001", "rejected", reviewer="Mr. Chen", notes="Rejected plan.")
        with self.assertRaises(ReviewError):
            self.service.review("LP-TEST-001", "approved", reviewer="Ms. Rivera", notes="OK")

    def test_invalid_decision_is_rejected(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.review(
                "LP-TEST-001",
                "maybe",
                reviewer="Ms. Rivera",
                notes="Unsure.",
            )
        self.assertEqual(context.exception.field, "decision")

    def test_reviewer_is_required(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.review("LP-TEST-001", "approved", reviewer="  ", notes="")
        self.assertEqual(context.exception.field, "reviewer")

    def test_notes_length_is_limited(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.service.review(
                "LP-TEST-001",
                "approved",
                reviewer="Ms. Rivera",
                notes="x" * 1001,
            )
        self.assertEqual(context.exception.field, "notes")

    def test_full_history_is_recorded(self) -> None:
        self.service.edit("LP-TEST-001", {"materials": ["Updated material"]})
        self.service.review(
            "LP-TEST-001",
            "needs_revision",
            reviewer="Head of Science",
            notes="Check materials.",
        )
        self.service.edit("LP-TEST-001", {"conclusion": "Revised conclusion."})
        final = self.service.review(
            "LP-TEST-001",
            "approved",
            reviewer="Ms. Rivera",
            notes="Approved after revision.",
        )
        actions = [entry["action"] for entry in final["review"]["history"]]
        self.assertEqual(actions, ["created", "edited", "decision", "edited", "decision"])
        self.assertEqual(final["review"]["history"][-1]["to_status"], "Approved")


if __name__ == "__main__":
    unittest.main()
