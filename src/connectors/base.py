import abc
from typing import Any, Callable, Coroutine, Optional, ParamSpec, TypeVar

import httpx
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.contracts import ActionResult, Platform
from src.core.logger import log

P = ParamSpec("P")
R = TypeVar("R")


class BaseConnector(abc.ABC):
    @property
    @abc.abstractmethod
    def platform(self) -> Platform:  # pragma: no cover
        """Returns the platform enum this connector handles."""
        pass

    @abc.abstractmethod
    async def publish(self, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pragma: no cover
        """Publishes content to the platform."""
        pass

    @abc.abstractmethod
    async def reply(self, thread_ref: str, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pragma: no cover
        """Replies to a specific thread or message on the platform."""
        pass

    @abc.abstractmethod
    async def moderate(self, object_ref: str, action: str, reason: str) -> ActionResult:  # pragma: no cover
        """Performs a moderation action."""
        pass

    @abc.abstractmethod
    async def sync_state(self, scope: str) -> dict[str, Any]:  # pragma: no cover
        """Synchronizes platform state (e.g., getting limits, quotas)."""
        pass

    @abc.abstractmethod
    async def get_limits(self) -> dict[str, Any]:  # pragma: no cover
        """Gets current rate limit budget."""
        pass

    @staticmethod
    def _log_retry(retry_state: RetryCallState) -> None:
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        if exception:
            log.warning(f"Retrying after {exception}... Attempt {retry_state.attempt_number}")
            return
        log.warning(f"Retrying transient error... Attempt {retry_state.attempt_number}")

    @staticmethod
    def with_retry() -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
        """Provides an exponential backoff decorator for transient 429/5xx HTTP errors."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((httpx.HTTPError,)),
            before_sleep=BaseConnector._log_retry,
            reraise=True,
        )
