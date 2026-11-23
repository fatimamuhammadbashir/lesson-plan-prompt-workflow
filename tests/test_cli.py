"""Tests for the command-line interface and demo."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.cli import main
from src.storage import PlanStore
from tests.helpers import DATA_DIR, sample_edits


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.store = PlanStore(self.root)
        self.sample = str(DATA_DIR / "sample_request.json")

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--store", str(self.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_template_command(self) -> None:
        code, stdout, stderr = self.run_cli("template")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertIn("subject", payload)
        self.assertIn("previous_results", payload)
        self.assertIn("approved_outcome_ids", payload)

    def test_validate_valid_request(self) -> None:
        code, stdout, stderr = self.run_cli("validate", "--input", self.sample)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["topic"], "Photosynthesis")

    def test_validate_invalid_request_returns_safe_error(self) -> None:
        bad = json.loads(Path(self.sample).read_text(encoding="utf-8"))
        bad["duration_minutes"] = 5
        bad_path = self.root / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        code, stdout, stderr = self.run_cli("validate", "--input", str(bad_path))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "validation_error")
        self.assertNotIn("Traceback", stderr)

    def test_create_writes_plan_and_copy(self) -> None:
        out_path = self.root / "copy.json"
        code, stdout, stderr = self.run_cli(
            "create",
            "--input",
            self.sample,
            "--plan-id",
            "LP-CLI-001",
            "--out",
            str(out_path),
        )
        self.assertEqual(code, 0, stderr)
        self.assertTrue(out_path.exists())
        self.assertEqual(json.loads(stdout)["plan_id"], "LP-CLI-001")
        self.assertEqual(self.store.load("LP-CLI-001")["status"], "Pending Teacher Review")
        self.assertEqual(json.loads(out_path.read_text(encoding="utf-8"))["plan_id"], "LP-CLI-001")

    def test_create_with_bad_json_returns_safe_error(self) -> None:
        bad_path = self.root / "bad.json"
        bad_path.write_text("{not json", encoding="utf-8")
        code, stdout, stderr = self.run_cli("create", "--input", str(bad_path))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["type"], "validation_error")

    def test_list_and_show(self) -> None:
        self.run_cli("create", "--input", self.sample, "--plan-id", "LP-CLI-002")
        code, stdout, stderr = self.run_cli("list")
        self.assertEqual(code, 0, stderr)
        summaries = json.loads(stdout)
        self.assertEqual(summaries[0]["plan_id"], "LP-CLI-002")

        code, stdout, stderr = self.run_cli("show", "LP-CLI-002")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["plan_id"], "LP-CLI-002")

    def test_edit_then_approve(self) -> None:
        self.run_cli("create", "--input", self.sample, "--plan-id", "LP-CLI-003")
        edits_path = self.root / "edits.json"
        edits_path.write_text(json.dumps(sample_edits()), encoding="utf-8")

        code, stdout, stderr = self.run_cli(
            "edit",
            "LP-CLI-003",
            "--file",
            str(edits_path),
            "--actor",
            "Ms. Rivera",
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["status"], "Pending Teacher Review")

        code, stdout, stderr = self.run_cli(
            "review",
            "LP-CLI-003",
            "--decision",
            "approved",
            "--reviewer",
            "Ms. Rivera",
            "--notes",
            "Ready to teach.",
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["status"], "Approved")
        self.assertEqual(self.store.load("LP-CLI-003")["review"]["reviewer"], "Ms. Rivera")

    def test_review_rejection_requires_notes(self) -> None:
        self.run_cli("create", "--input", self.sample, "--plan-id", "LP-CLI-004")
        code, stdout, stderr = self.run_cli(
            "review",
            "LP-CLI-004",
            "--decision",
            "rejected",
            "--reviewer",
            "Mr. Chen",
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["type"], "validation_error")

    def test_demo_runs_all_required_scenarios(self) -> None:
        code, stdout, stderr = self.run_cli("demo")
        self.assertEqual(code, 0, stderr)
        for text in (
            "SUCCESSFUL GENERATION",
            "INVALID INPUT HANDLED SAFELY",
            "TEACHER EDIT BEFORE APPROVAL",
            "TEACHER APPROVAL",
            "TEACHER REJECTION",
            "NEEDS REVISION",
            "Approved",
            "Rejected",
            "Pending Teacher Review",
        ):
            self.assertIn(text, stdout)
        self.assertTrue(self.store.review_log.exists())

    def test_missing_plan_returns_safe_error(self) -> None:
        code, stdout, stderr = self.run_cli("show", "LP-NOT-FOUND")
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["type"], "storage_error")


if __name__ == "__main__":
    unittest.main()
