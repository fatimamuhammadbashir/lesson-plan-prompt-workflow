"""Typed application errors with safe, JSON-friendly messages."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected application failures."""

    code = "app_error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {
            "error": {
                "type": self.code,
                "message": self.message,
            }
        }
        if self.field:
            payload["error"]["field"] = self.field
        if self.details is not None:
            payload["error"]["details"] = self.details
        return payload


class ValidationError(AppError):
    """The teacher's request or edit is not valid."""

    code = "validation_error"


class CurriculumError(AppError):
    """The request does not match the approved curriculum."""

    code = "curriculum_error"


class DataError(AppError):
    """A project data file is missing or malformed."""

    code = "data_error"


class PlanningError(AppError):
    """A lesson plan cannot be generated from the available data."""

    code = "planning_error"


class ReviewError(AppError):
    """A review action is not allowed in the current state."""

    code = "review_error"


class StorageError(AppError):
    """A stored lesson plan cannot be read or written safely."""

    code = "storage_error"
