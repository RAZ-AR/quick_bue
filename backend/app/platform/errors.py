"""Domain errors raised by services; app.main turns them into HTTP responses.

Body format (docs/03-architecture.md §3.9): {"code": "...", "message": "...", "details": {...}}
"""

from typing import Any


class DomainError(Exception):
    status_code = 400

    def __init__(self, code: str, message: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.details = details or {}


class NotAllowed(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    """The object changed meanwhile or is in a state that forbids the action."""

    status_code = 409


class ValidationFailed(DomainError):
    """Business validation failed; details["problems"] lists what to fix."""

    status_code = 422

    def __init__(self, problems: list[dict[str, Any]], message: str = "validation_failed"):
        super().__init__("validation_failed", message, {"problems": problems})
        self.problems = problems
