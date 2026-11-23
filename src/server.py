"""Local JSON API and static host for the React lesson-plan UI."""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__
from .config import PROJECT_ROOT
from .errors import (
    AppError,
    PlanningError,
    StorageError,
)
from .review import APPROVED, NEEDS_REVISION, PENDING, REJECTED
from .service import LessonPlanService

MAX_BODY_BYTES = 1_000_000
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class LessonPlanHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        service: LessonPlanService,
        static_dir: str | Path | None = None,
        cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
    ) -> None:
        super().__init__(address, ApiHandler)
        self.service = service
        self.static_dir = Path(static_dir) if static_dir else PROJECT_ROOT / "frontend" / "dist"
        self.cors_origins = set(cors_origins)


class ApiHandler(BaseHTTPRequestHandler):
    server_version = f"LessonPlanStudio/{__version__}"

    @property
    def app_server(self) -> LessonPlanHTTPServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib naming
        self.send_response(204)
        self._cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "service": "lesson-plan-studio",
                        "version": __version__,
                        "plan_count": len(self.app_server.service.list_plans()),
                    },
                )
                return
            if path == "/api/meta":
                self._send_json(200, self._metadata())
                return
            if path == "/api/plans":
                self._send_json(200, {"plans": self.app_server.service.list_plans()})
                return
            if path.startswith("/api/plans/"):
                parts = [part for part in path.split("/") if part]
                if len(parts) == 3:
                    self._send_json(200, self.app_server.service.get(parts[2]))
                    return
                self._not_found()
                return
            if path.startswith("/api/"):
                self._not_found()
                return
            self._serve_static(path)
        except AppError as exc:
            self._send_json(_status_for(exc), exc.to_dict())
        except Exception as exc:  # pragma: no cover - defensive boundary
            print(f"Unexpected server error: {exc}", file=sys.stderr)
            self._send_json(
                500,
                {"error": {"type": "internal_error", "message": "Unexpected server error."}},
            )

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/plans":
                payload = self._read_json()
                plan = self.app_server.service.create(payload)
                self._send_json(201, plan)
                return
            if path.startswith("/api/plans/"):
                parts = [part for part in path.split("/") if part]
                if len(parts) == 4 and parts[3] == "review":
                    payload = self._read_json()
                    plan = self.app_server.service.review(
                        parts[2],
                        str(payload.get("decision", "")),
                        reviewer=str(payload.get("reviewer", "")),
                        notes=str(payload.get("notes", "")),
                    )
                    self._send_json(200, plan)
                    return
            self._not_found()
        except AppError as exc:
            self._send_json(_status_for(exc), exc.to_dict())
        except Exception as exc:  # pragma: no cover
            print(f"Unexpected server error: {exc}", file=sys.stderr)
            self._send_json(
                500,
                {"error": {"type": "internal_error", "message": "Unexpected server error."}},
            )

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path.startswith("/api/plans/"):
                parts = [part for part in path.split("/") if part]
                if len(parts) == 3:
                    payload = self._read_json()
                    plan = self.app_server.service.edit(parts[2], payload)
                    self._send_json(200, plan)
                    return
            self._not_found()
        except AppError as exc:
            self._send_json(_status_for(exc), exc.to_dict())
        except Exception as exc:  # pragma: no cover
            print(f"Unexpected server error: {exc}", file=sys.stderr)
            self._send_json(
                500,
                {"error": {"type": "internal_error", "message": "Unexpected server error."}},
            )

    def _metadata(self) -> dict:
        service = self.app_server.service
        curriculum = service.planner.curriculum
        config = service.planner.config
        return {
            "topics": [topic.to_dict() for topic in curriculum.all_topics()],
            "allowed_preferences": config["allowed_preferences"],
            "limits": config["input"],
            "phase_order": config["phase_order"],
            "statuses": [PENDING, APPROVED, REJECTED, NEEDS_REVISION],
        }

    def _read_json(self) -> dict:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            raise AppError("A JSON request body is required.", field="$")
        try:
            length = int(length_header)
        except ValueError:
            raise AppError("Content-Length must be a whole number.", field="$") from None
        if length < 0 or length > MAX_BODY_BYTES:
            raise AppError("Request body is too large.", field="$")
        body = self.rfile.read(length)
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            raise AppError("Request body must be UTF-8 encoded.", field="$") from None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(
                "Request body is not valid JSON.",
                field="$",
                details=f"line {exc.lineno}, column {exc.colno}",
            ) from None
        if not isinstance(payload, dict):
            raise AppError("Request body must be a JSON object.", field="$")
        return payload

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(
            404,
            {"error": {"type": "not_found", "message": "Unknown API endpoint."}},
        )

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin in self.app_server.cors_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _serve_static(self, path: str) -> None:
        static_dir = self.app_server.static_dir
        index = static_dir / "index.html"
        if not index.exists():
            self._send_json(
                404,
                {
                    "error": {
                        "type": "frontend_not_built",
                        "message": (
                            "Frontend build not found. Run 'npm install' and "
                            "'npm run build' inside frontend/, or use 'npm run dev'."
                        ),
                    }
                },
            )
            return

        relative = path.lstrip("/")
        candidate = (static_dir / relative).resolve() if relative else index.resolve()
        try:
            candidate.relative_to(static_dir.resolve())
        except ValueError:
            candidate = index.resolve()

        if candidate.is_file():
            self._send_file(candidate)
            return
        if Path(relative).suffix:
            self._send_json(
                404,
                {"error": {"type": "not_found", "message": "Static file not found."}},
            )
            return
        self._send_file(index.resolve())

    def _send_file(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError as exc:
            self._send_json(
                500,
                {"error": {"type": "static_error", "message": str(exc)}},
            )
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
            "image/svg+xml",
        }:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)


def _status_for(exc: AppError) -> int:
    if isinstance(exc, StorageError) and "not found" in exc.message.lower():
        return 404
    if isinstance(exc, PlanningError):
        return 422
    return 400


def create_server(
    service: LessonPlanService,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    static_dir: str | Path | None = None,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
) -> LessonPlanHTTPServer:
    return LessonPlanHTTPServer(
        (host, port),
        service,
        static_dir=static_dir,
        cors_origins=cors_origins,
    )


def run_server(
    service: LessonPlanService,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    static_dir: str | Path | None = None,
) -> int:
    server = create_server(service, host=host, port=port, static_dir=static_dir)
    actual_host, actual_port = server.server_address[:2]
    print(f"Lesson Plan Studio API: http://{actual_host}:{actual_port}")
    print(f"Frontend build: {server.static_dir}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    return 0
