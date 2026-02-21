import abc
from typing import Optional, Any, Callable, TypeVar, Awaitable
from src.core.contracts import ActionResult, Platform
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from src.core.logger import log

T = TypeVar('T')

class BaseConnector(abc.ABC):
    @property
    @abc.abstractmethod
    def platform(self) -> Platform: # pragma: no cover
        """Returns the platform enum this connector handles."""
        pass
        
    @abc.abstractmethod
    async def publish(self, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult: # pragma: no cover
        """Publishes content to the platform."""
        pass

    @abc.abstractmethod
    async def reply(self, thread_ref: str, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult: # pragma: no cover
        """Replies to a specific thread or message on the platform."""
        pass

    @abc.abstractmethod
    async def moderate(self, object_ref: str, action: str, reason: str) -> ActionResult: # pragma: no cover
        """Performs a moderation action."""
        pass

    @abc.abstractmethod
    async def sync_state(self, scope: str) -> dict[str, Any]: # pragma: no cover
        """Synchronizes platform state (e.g., getting limits, quotas)."""
        pass

    @abc.abstractmethod
    async def get_limits(self) -> dict[str, Any]: # pragma: no cover
        """Gets current rate limit budget."""
        pass

    @staticmethod
    def with_retry() -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """Provides an exponential backoff decorator for transient 429/5xx HTTP errors."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((httpx.HTTPError,)),
            before_sleep=lambda retry_state: log.warning(
                f"Retrying after {retry_state.outcome.exception()}... Attempt {retry_state.attempt_number}"
            ),
            reraise=True
        )
