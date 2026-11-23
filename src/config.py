"""Configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import DataError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config(path: str | Path | None = None) -> dict:
    """Load and validate ``config.json``."""

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataError(
            f"Could not read config file: {config_path.name}",
            details=str(exc),
        ) from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataError(
            f"Config file is not valid JSON: {config_path.name}",
            details=f"line {exc.lineno}, column {exc.colno}",
        ) from None
    return validate_config(raw)


def validate_config(raw: dict) -> dict:
    """Validate the configuration shape and return it unchanged."""

    if not isinstance(raw, dict):
        raise DataError("Config must be a JSON object.")

    for key in ("version", "input", "allowed_preferences", "phase_order", "ranking_weights"):
        if key not in raw:
            raise DataError(f"Config is missing required key: {key}")

    input_config = raw["input"]
    if not isinstance(input_config, dict):
        raise DataError("Config 'input' must be an object.")
    for key in (
        "min_duration_minutes",
        "max_duration_minutes",
        "max_learner_preferences",
        "max_outcomes",
        "max_text_length",
    ):
        value = input_config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise DataError(f"Config input.{key} must be a positive whole number.")
    if input_config["min_duration_minutes"] > input_config["max_duration_minutes"]:
        raise DataError("Config minimum duration cannot exceed maximum duration.")

    preferences = raw["allowed_preferences"]
    if not isinstance(preferences, list) or not preferences:
        raise DataError("Config allowed_preferences must be a non-empty list.")
    if any(not isinstance(item, str) or not item.strip() for item in preferences):
        raise DataError("Config allowed_preferences must contain non-empty strings.")
    if len({item.strip().lower() for item in preferences}) != len(preferences):
        raise DataError("Config allowed_preferences must not contain duplicates.")

    phases = raw["phase_order"]
    if not isinstance(phases, list) or not phases:
        raise DataError("Config phase_order must be a non-empty list.")
    if any(not isinstance(item, str) or not item.strip() for item in phases):
        raise DataError("Config phase_order must contain non-empty strings.")
    if len(set(phases)) != len(phases):
        raise DataError("Config phase_order must not contain duplicates.")

    weights = raw["ranking_weights"]
    if not isinstance(weights, dict) or not weights:
        raise DataError("Config ranking_weights must be a non-empty object.")
    for name, value in weights.items():
        if not isinstance(name, str) or not isinstance(value, (int, float)) or isinstance(value, bool):
            raise DataError("Config ranking weights must be numbers.")
        if value < 0:
            raise DataError(f"Ranking weight '{name}' cannot be negative.")
    total = sum(float(value) for value in weights.values())
    if abs(total - 1.0) > 1e-9:
        raise DataError("Ranking weights must add up to 1.0.")

    return raw
