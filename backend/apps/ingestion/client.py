import time
from urllib.parse import quote

import httpx
from django.conf import settings

from .exceptions import (
    AuthenticationError,
    ClanNotFoundError,
    ClashRoyaleAPIError,
    RateLimitError,
)


class ClashRoyaleClient:
    """Client for the official Supercell Clash Royale REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 0.2,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or getattr(settings, "CLASH_ROYALE_API_KEY", "")
        self.base_url = (
            base_url or getattr(settings, "CLASH_ROYALE_BASE_URL", "https://api.clashroyale.com/v1")
        ).rstrip("/")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    @staticmethod
    def encode_tag(tag: str) -> str:
        """Normalize and URL-encode a Supercell tag (e.g. #2PP -> %232PP)."""
        clean_tag = tag.strip().upper()
        if not clean_tag.startswith("#"):
            clean_tag = f"#{clean_tag}"
        return quote(clean_tag, safe="")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._headers()

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(method, url, headers=headers, params=params)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 404:
                    raise ClanNotFoundError(
                        f"Resource not found at {endpoint}",
                        status_code=404,
                        response_body=response.text,
                    )

                if response.status_code == 403:
                    raise AuthenticationError(
                        "Supercell API key rejected or unauthorized for IP",
                        status_code=403,
                        response_body=response.text,
                    )

                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2**attempt))
                        continue
                    raise RateLimitError(
                        "Clash Royale API rate limit exceeded (HTTP 429)",
                        status_code=429,
                        response_body=response.text,
                    )

                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2**attempt))
                        continue

                raise ClashRoyaleAPIError(
                    f"Supercell API returned status {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                    continue
                raise ClashRoyaleAPIError(
                    f"Network error connecting to Clash Royale API: {exc}",
                ) from exc

        if last_exception:
            raise ClashRoyaleAPIError(f"Request failed after retries: {last_exception}")

        raise ClashRoyaleAPIError("Unknown request failure")

    def get_clan(self, clan_tag: str) -> dict:
        """Fetch clan details and member roster from /v1/clans/{clanTag}."""
        encoded_tag = self.encode_tag(clan_tag)
        return self._request("GET", f"clans/{encoded_tag}")

    def get_current_river_race(self, clan_tag: str) -> dict:
        """Fetch current river race data from /v1/clans/{clanTag}/currentriverrace."""
        encoded_tag = self.encode_tag(clan_tag)
        return self._request("GET", f"clans/{encoded_tag}/currentriverrace")
