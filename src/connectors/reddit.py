import httpx
from typing import Optional, Any
import uuid
from src.core.contracts import ActionResult, Platform, ActionType
from src.connectors.base import BaseConnector
from src.core.config import settings
from src.core.logger import log
from src.policy.engine import PolicyEngine


class RedditConnector(BaseConnector):
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
        self.client_id = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.username = settings.reddit_username
        self.password = settings.reddit_password
        self.user_agent = settings.reddit_user_agent
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(headers={"User-Agent": self.user_agent})

    @property
    def platform(self) -> Platform:
        return Platform.REDDIT

    async def _authenticate(self):
        """Authenticates with Reddit API using password flow."""
        if self._token:
            return  # Cache hit. Production needs expiry tracking.

        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        data = {"grant_type": "password", "username": self.username, "password": self.password}
        try:
            resp = await self._client.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data)
            resp.raise_for_status()
            self._token = resp.json().get("access_token")
            self._client.headers["Authorization"] = f"Bearer {self._token}"
        except httpx.HTTPError as e:
            log.error(f"Reddit Auth failed: {e}")
            raise

    async def _enforce_policy(self, action_type: ActionType, content: str) -> Optional[ActionResult]:
        """Runs the policy engine and returns a failed ActionResult if blocked."""
        decision = await self.policy_engine.evaluate(self.platform, action_type, content)
        if not decision.allowed:
            return ActionResult(ok=False, platform=self.platform, action_type=action_type, idempotency_key=uuid.uuid4().hex, policy_decision_id=decision.decision_id, error=decision.reason)
        # Store decision_id to pass down if permitted
        self._last_decision_id = decision.decision_id
        return None

    @BaseConnector.with_retry()
    async def publish(self, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        await self._authenticate()
        options = options or {}
        sr = options.get("subreddit", "test")
        title = options.get("title", "Automated Post")

        # Policy Gate
        policy_block = await self._enforce_policy(ActionType.PUBLISH, content)
        if policy_block:
            return policy_block

        resp = await self._client.post("https://oauth.reddit.com/api/submit", data={"sr": sr, "kind": "self", "title": title, "text": content})
        resp.raise_for_status()
        res_data = resp.json()
        return ActionResult(ok=True, platform=self.platform, action_type=ActionType.PUBLISH, external_id=res_data.get("json", {}).get("data", {}).get("id"), idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id, raw_data=res_data)

    @BaseConnector.with_retry()
    async def reply(self, thread_ref: str, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        await self._authenticate()

        policy_block = await self._enforce_policy(ActionType.REPLY, content)
        if policy_block:
            return policy_block

        resp = await self._client.post("https://oauth.reddit.com/api/comment", data={"thing_id": thread_ref, "text": content})
        resp.raise_for_status()
        res_data = resp.json()
        return ActionResult(ok=True, platform=self.platform, action_type=ActionType.REPLY, external_id=res_data.get("json", {}).get("data", {}).get("id"), idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id, raw_data=res_data)

    async def moderate(self, object_ref: str, action: str, reason: str) -> ActionResult:
        return ActionResult(ok=False, platform=self.platform, action_type=ActionType.MODERATE, error="MVP Not Implemented", idempotency_key=uuid.uuid4().hex, policy_decision_id="none")

    async def sync_state(self, scope: str) -> dict[str, Any]:
        return {}

    async def get_limits(self) -> dict[str, Any]:
        return {}
