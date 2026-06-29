"""Base HTTP client with retry and exponential back-off.

Both platform clients inherit from `BaseHTTPClient` and configure
their own retry semantics through `RetryPolicy`. Transient errors
(429, 5xx, network failures) are retried with exponential back-off
capped at the configured maximum. Permanent errors (4xx other than
429) raise immediately so the caller can mark the subject accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self, cast

import httpx
from social_common.errors import PermanentPlatformError, TransientPlatformError
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ..config import SyncSettings
from ..logging_setup import get_logger

logger = get_logger("social_data_collector.clients.base")


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for platform call retries.

    Exponential back-off formula: initial * (2 ** (attempt - 1)) + jitter,
    capped at max_seconds. Tenacity stops after max_attempts.
    """

    max_attempts: int
    initial_seconds: int
    max_seconds: int

    @classmethod
    def from_settings(cls, settings: SyncSettings) -> RetryPolicy:
        return cls(
            max_attempts=settings.max_retries,
            initial_seconds=settings.backoff_initial_seconds,
            max_seconds=settings.backoff_max_seconds,
        )


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors that should be retried."""
    if isinstance(exc, TransientPlatformError):
        return True
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        # 429 (rate limit) and 5xx (server errors) are transient.
        return status == 429 or 500 <= status < 600
    return False


class BaseHTTPClient:
    """Thin wrapper around httpx with retry/back-off and error mapping."""

    def __init__(
        self,
        base_url: str,
        retry_policy: RetryPolicy,
        timeout_seconds: float = 30.0,
        platform_name: str = "unknown",
    ) -> None:
        self._base_url = base_url
        self._retry_policy = retry_policy
        self._timeout = timeout_seconds
        self._platform_name = platform_name
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _retrying(self) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self._retry_policy.max_attempts),
            wait=wait_exponential(
                multiplier=self._retry_policy.initial_seconds,
                max=self._retry_policy.max_seconds,
            ),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET a path and return the parsed JSON body, with retry and back-off."""
        for attempt in self._retrying():
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    delay = attempt.retry_state.idle_for or 0
                    logger.warning(
                        "http.retry",
                        platform=self._platform_name,
                        path=path,
                        attempt=attempt.retry_state.attempt_number,
                        next_delay_seconds=delay,
                    )
                try:
                    response = self._client.get(path, params=params)
                except httpx.TransportError as exc:
                    logger.error(
                        "http.transport_error",
                        platform=self._platform_name,
                        path=path,
                        error=str(exc),
                    )
                    raise TransientPlatformError(str(exc)) from exc
                self._raise_for_status(response, path)
                return cast("dict[str, Any]", response.json())
        # Unreachable: Retrying with reraise=True either raises or returns.
        raise TransientPlatformError("retry loop exited without result")

    def _raise_for_status(self, response: httpx.Response, path: str) -> None:
        """Map HTTP error responses to platform error types.

        - 429 → TransientPlatformError (retry).
        - 5xx → TransientPlatformError (retry).
        - 401/403 → PermanentPlatformError (missing scopes/credentials).
        - 404 → PermanentPlatformError (subject not found).
        - Other 4xx → PermanentPlatformError.
        """
        if response.status_code < 400:
            return

        status = response.status_code
        body: Any
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = response.text

        if status == 429 or 500 <= status < 600:
            logger.warning(
                "http.transient_error",
                platform=self._platform_name,
                path=path,
                status=status,
                body=body,
            )
            raise TransientPlatformError(f"{self._platform_name} returned {status} for {path}")

        logger.error(
            "http.permanent_error",
            platform=self._platform_name,
            path=path,
            status=status,
            body=body,
        )
        raise PermanentPlatformError(f"{self._platform_name} returned {status} for {path}: {body}")
