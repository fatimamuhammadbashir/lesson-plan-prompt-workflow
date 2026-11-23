"""Tests for safe plan storage and review logging."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.errors import StorageError
from src.storage import PlanStore
from tests.helpers import make_plan, make_service


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.store = PlanStore(self.root)
        self.service = make_service(self.root)
        self.plan = make_plan(self.service)

    def test_save_and_load_roundtrip(self) -> None:
        loaded = self.store.load("LP-TEST-001")
        self.assertEqual(loaded["plan_id"], "LP-TEST-001")
        self.assertEqual(loaded["status"], "Pending Teacher Review")
        self.assertTrue((self.root / "plans" / "LP-TEST-001.json").exists())

    def test_list_plans_returns_summaries(self) -> None:
        make_plan(self.service, plan_id="LP-TEST-002")
        summaries = self.store.list_plans()
        self.assertEqual(len(summaries), 2)
        ids = {item["plan_id"] for item in summaries}
        self.assertEqual(ids, {"LP-TEST-001", "LP-TEST-002"})
        self.assertTrue(all(item["status"] == "Pending Teacher Review" for item in summaries))

    def test_missing_plan_is_reported(self) -> None:
        with self.assertRaises(StorageError) as context:
            self.store.load("LP-MISSING")
        self.assertEqual(context.exception.field, "plan_id")

    def test_path_traversal_is_rejected(self) -> None:
        for plan_id in ("../escape", "..\\escape", "", "bad id", "CON", "NUL"):
            with self.subTest(plan_id=plan_id):
                with self.assertRaises(StorageError):
                    self.store.load(plan_id)

    def test_save_rejects_invalid_plan_id(self) -> None:
        with self.assertRaises(StorageError):
            self.store.save({"plan_id": "../escape", "status": "x"})

    def test_corrupt_plan_is_reported(self) -> None:
        path = self.root / "plans" / "LP-CORRUPT.json"
        path.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(StorageError) as context:
            self.store.load("LP-CORRUPT")
        self.assertIn("not valid JSON", context.exception.message)

    def test_review_log_is_append_only_jsonl(self) -> None:
        reviewed = self.service.review(
            "LP-TEST-001",
            "approved",
            reviewer="Ms. Rivera",
            notes="Ready.",
        )
        lines = self.store.review_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["plan_id"], "LP-TEST-001")
        self.assertEqual(record["status"], "Approved")
        self.assertEqual(record["reviewer"], "Ms. Rivera")
        self.assertEqual(record["action"], "decision")

        self.store.append_review(reviewed)
        lines = self.store.review_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)

    def test_save_does_not_leave_temporary_files(self) -> None:
        self.service.edit("LP-TEST-001", {"materials": ["Updated material"]})
        leftovers = list((self.root / "plans").glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_list_plans_empty_store(self) -> None:
        empty = PlanStore(self.root / "empty")
        self.assertEqual(empty.list_plans(), [])


if __name__ == "__main__":
    unittest.main()
