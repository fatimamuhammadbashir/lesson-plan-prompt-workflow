"""Integration tests for the local JSON API and static React host."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.server import create_server
from tests.helpers import make_service, sample_edits, sample_request


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.static_dir = self.root / "static"
        self.static_dir.mkdir()
        (self.static_dir / "index.html").write_text(
            "<!doctype html><html><body><div id='root'>Lesson Studio</div></body></html>",
            encoding="utf-8",
        )
        (self.static_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")
        self.service = make_service(self.root / "store")
        self.server = create_server(
            self.service,
            port=0,
            static_dir=self.static_dir,
            cors_origins=("http://localhost:5173",),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method: str, path: str, payload: dict | None = None, headers=None):
        data = None
        request_headers = dict(headers or {})
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
                return response.status, body, dict(response.headers)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return exc.code, body, dict(exc.headers)

    def json_request(self, method: str, path: str, payload: dict | None = None):
        status, body, headers = self.request(method, path, payload)
        return status, json.loads(body), headers

    def test_health(self) -> None:
        status, payload, _ = self.json_request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["plan_count"], 0)

    def test_meta_exposes_curriculum_and_limits(self) -> None:
        status, payload, _ = self.json_request("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["topics"]), 4)
        self.assertIn("visual", payload["allowed_preferences"])
        self.assertIn("Pending Teacher Review", payload["statuses"])
        self.assertEqual(payload["topics"][0]["subject"], "Science")

    def test_create_list_and_get_plan(self) -> None:
        status, plan, _ = self.json_request("POST", "/api/plans", sample_request())
        self.assertEqual(status, 201)
        self.assertEqual(plan["status"], "Pending Teacher Review")
        plan_id = plan["plan_id"]

        status, listing, _ = self.json_request("GET", "/api/plans")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["plans"]), 1)
        self.assertEqual(listing["plans"][0]["plan_id"], plan_id)

        status, loaded, _ = self.json_request("GET", f"/api/plans/{plan_id}")
        self.assertEqual(status, 200)
        self.assertEqual(loaded["plan_id"], plan_id)

    def test_invalid_request_returns_safe_error(self) -> None:
        payload = sample_request()
        payload["duration_minutes"] = 5
        status, body, _ = self.json_request("POST", "/api/plans", payload)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["type"], "validation_error")
        self.assertEqual(body["error"]["field"], "duration_minutes")

    def test_edit_plan(self) -> None:
        _, plan, _ = self.json_request("POST", "/api/plans", sample_request())
        status, updated, _ = self.json_request(
            "PATCH",
            f"/api/plans/{plan['plan_id']}",
            sample_edits(),
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["status"], "Pending Teacher Review")
        self.assertIn("chlorophyll", updated["objectives"][0]["text"])
        self.assertEqual(updated["review"]["history"][-1]["action"], "edited")

    def test_review_plan(self) -> None:
        _, plan, _ = self.json_request("POST", "/api/plans", sample_request())
        status, reviewed, _ = self.json_request(
            "POST",
            f"/api/plans/{plan['plan_id']}/review",
            {
                "decision": "approved",
                "reviewer": "Ms. Rivera",
                "notes": "Ready to teach.",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["status"], "Approved")
        self.assertEqual(reviewed["review"]["reviewer"], "Ms. Rivera")

    def test_rejection_requires_notes(self) -> None:
        _, plan, _ = self.json_request("POST", "/api/plans", sample_request())
        status, body, _ = self.json_request(
            "POST",
            f"/api/plans/{plan['plan_id']}/review",
            {"decision": "rejected", "reviewer": "Mr. Chen", "notes": ""},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["field"], "notes")

    def test_unknown_plan_returns_404(self) -> None:
        status, body, _ = self.json_request("GET", "/api/plans/LP-MISSING")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["type"], "storage_error")

    def test_unknown_api_route_returns_404(self) -> None:
        status, body, _ = self.json_request("GET", "/api/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["type"], "not_found")

    def test_bad_json_returns_400(self) -> None:
        request = urllib.request.Request(
            self.base + "/api/plans",
            data=b"{bad json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(context.exception.code, 400)
        body = json.loads(context.exception.read().decode("utf-8"))
        self.assertEqual(body["error"]["type"], "app_error")

    def test_static_index_and_spa_fallback(self) -> None:
        status, body, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Lesson Studio", body)
        self.assertIn("text/html", headers["Content-Type"])

        status, body, _ = self.request("GET", "/plans/LP-TEST-001")
        self.assertEqual(status, 200)
        self.assertIn("Lesson Studio", body)

        status, body, headers = self.request("GET", "/app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])

    def test_cors_preflight(self) -> None:
        status, body, headers = self.request(
            "OPTIONS",
            "/api/plans",
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, "")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("PATCH", headers["Access-Control-Allow-Methods"])


if __name__ == "__main__":
    unittest.main()
