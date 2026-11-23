"""Shared test helpers."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.curriculum import Curriculum
from src.service import build_service

FIXED_NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
DATA_DIR = PROJECT_ROOT / "data"


def load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def sample_request() -> dict:
    return load_json("sample_request.json")


def sample_edits() -> dict:
    return load_json("sample_edits.json")


def make_service(store_root: str | Path):
    return build_service(store_root=store_root)


def make_plan(service, payload: dict | None = None, plan_id: str = "LP-TEST-001") -> dict:
    return service.create(payload or sample_request(), plan_id=plan_id, now=FIXED_NOW)


def curriculum() -> Curriculum:
    return Curriculum.load(DATA_DIR / "curriculum.json")


def config() -> dict:
    return load_config(PROJECT_ROOT / "config.json")
