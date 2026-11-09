"""Consistent error responses (root AGENTS.md §3).

Every non-2xx response uses the envelope from docs/api-contracts.md. Routes and services raise
ApiError subclasses; the single handler set in app/main.py maps them to the envelope. One error
formatter, one error enum — duplicated formatting is a review blocker.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    ACTION_NOT_PENDING = "ACTION_NOT_PENDING"
    UNAUTHORIZED = "UNAUTHORIZED"
    NOT_IMPLEMENTED_NOT_WIREABLE = "NOT_IMPLEMENTED_NOT_WIREABLE"
    INTEGRATION_ERROR = "INTEGRATION_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiError(Exception):
    """Base application error — always mapped to the shared envelope."""

    status_code: int = 500

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None,
                 status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code

    def envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": str(self.code),
                "message": self.message,
                "details": self.details,
            }
        }


def validation_error(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.VALIDATION_ERROR, message, details, status_code=422)


def not_found(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.NOT_FOUND, message, details, status_code=404)


def conflict(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.CONFLICT, message, details, status_code=409)


def action_not_pending(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.ACTION_NOT_PENDING, message, details, status_code=409)


def integration_error(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.INTEGRATION_ERROR, message, details, status_code=502)


def model_error(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(ErrorCode.MODEL_ERROR, message, details, status_code=503)
