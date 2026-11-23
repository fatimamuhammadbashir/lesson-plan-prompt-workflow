"""Command-line interface for the lesson plan prompt workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import PROJECT_ROOT
from .demo import run_demo
from .errors import AppError, StorageError
from .service import build_service
from .validation import (
    load_json_object,
    request_template,
    validate_request,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="Rule-based lesson plan prompt workflow (FIP Beginner Capstone 2).",
    )
    parser.add_argument(
        "--store",
        default=str(PROJECT_ROOT / "var"),
        help="Directory for plan files and the review log (default: var).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("template", help="Print the lesson request template.")

    validate = subparsers.add_parser("validate", help="Validate a lesson request file.")
    validate.add_argument("--input", required=True, help="Path to a lesson request JSON file.")

    create = subparsers.add_parser("create", help="Generate and save a lesson plan draft.")
    create.add_argument("--input", required=True, help="Path to a lesson request JSON file.")
    create.add_argument("--plan-id", default=None, help="Optional fixed plan id.")
    create.add_argument("--out", default=None, help="Optional path for a JSON copy of the plan.")

    subparsers.add_parser("list", help="List saved lesson plans.")

    show = subparsers.add_parser("show", help="Show one saved lesson plan.")
    show.add_argument("plan_id")

    edit = subparsers.add_parser("edit", help="Edit a draft before approval.")
    edit.add_argument("plan_id")
    edit.add_argument("--file", required=True, help="Path to a JSON file with edits.")
    edit.add_argument("--actor", default="Teacher", help="Name recorded in the edit history.")

    review = subparsers.add_parser("review", help="Record a teacher decision.")
    review.add_argument("plan_id")
    review.add_argument(
        "--decision",
        required=True,
        choices=["approved", "rejected", "needs_revision"],
    )
    review.add_argument("--reviewer", required=True, help="Teacher or reviewer name.")
    review.add_argument("--notes", default="", help="Review notes.")

    serve = subparsers.add_parser(
        "serve",
        help="Start the local API and serve the built React UI.",
    )
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    serve.add_argument("--port", type=int, default=8000, help="Port (default: 8000).")
    serve.add_argument(
        "--static-dir",
        default=None,
        help="Optional frontend build directory (default: frontend/dist).",
    )

    subparsers.add_parser("demo", help="Run the scripted demonstration.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "template":
        print(json.dumps(request_template(), indent=2))
        return 0

    try:
        service = build_service(store_root=args.store)

        if args.command == "validate":
            payload = load_json_object(args.input)
            request = validate_request(
                payload,
                service.planner.curriculum,
                service.planner.config,
            )
            print(
                json.dumps(
                    {
                        "valid": True,
                        "subject": request.subject,
                        "class_name": request.class_name,
                        "topic": request.topic,
                        "duration_minutes": request.duration_minutes,
                        "approved_outcome_ids": list(request.approved_outcome_ids),
                        "learner_preferences": list(request.learner_preferences),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "create":
            payload = load_json_object(args.input)
            plan = service.create(payload, plan_id=args.plan_id)
            if args.out:
                _write_json_copy(Path(args.out), plan)
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            return 0

        if args.command == "list":
            print(json.dumps(service.list_plans(), indent=2))
            return 0

        if args.command == "show":
            print(json.dumps(service.get(args.plan_id), indent=2, ensure_ascii=False))
            return 0

        if args.command == "edit":
            edits = load_json_object(args.file)
            plan = service.edit(args.plan_id, edits, actor=args.actor)
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            return 0

        if args.command == "review":
            plan = service.review(
                args.plan_id,
                args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
            )
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            return 0

        if args.command == "serve":
            from .server import run_server

            return run_server(
                service,
                host=args.host,
                port=args.port,
                static_dir=args.static_dir,
            )

        if args.command == "demo":
            return run_demo(service)

        parser.error(f"Unknown command: {args.command}")
        return 2
    except AppError as exc:
        print(json.dumps(exc.to_dict(), indent=2), file=sys.stderr)
        return 2
    except OSError as exc:
        print(
            json.dumps(
                {
                    "error": {
                        "type": "io_error",
                        "message": "A file operation failed.",
                        "details": str(exc),
                    }
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


def _write_json_copy(path: Path, plan: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise StorageError(
            f"Could not write plan copy: {path.name}",
            details=str(exc),
        ) from None
