class ClashRoyaleAPIError(Exception):
    """Base exception for Clash Royale API errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ClanNotFoundError(ClashRoyaleAPIError):
    """Raised when the specified clan tag is not found (HTTP 404)."""


class RateLimitError(ClashRoyaleAPIError):
    """Raised when Supercell rate limit is exceeded (HTTP 429)."""


class AuthenticationError(ClashRoyaleAPIError):
    """Raised when API key is missing or rejected (HTTP 403)."""
