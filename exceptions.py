"""Custom exceptions for the screening pipeline."""
from __future__ import annotations


class ScreeningError(Exception):
    """Base class for all screening-specific errors."""
    user_message: str = "An unexpected error occurred."

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        if user_message:
            self.user_message = user_message
        else:
            self.user_message = message


class DataLoadError(ScreeningError):
    """Raised when a screening file cannot be read at all."""


class ValidationError(ScreeningError):
    """Raised when a file is readable but invalid."""


class ClassificationError(ScreeningError):
    """Raised when the classification engine fails."""
