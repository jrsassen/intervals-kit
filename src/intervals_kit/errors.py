"""Typed exceptions for Intervals.ICU API and application errors."""


class IntervalsError(Exception):
    """Base exception for all Intervals.ICU errors."""


class AuthenticationError(IntervalsError):
    """API key missing, invalid, or expired. HTTP 401/403."""


class RateLimitError(IntervalsError):
    """Rate limit exceeded. HTTP 429."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(IntervalsError):
    """Requested resource does not exist. HTTP 404."""


class DownloadError(IntervalsError):
    """File download failed (network error, incomplete stream, disk error)."""
