import httpx
from typing import Optional, Any
import uuid
from src.core.contracts import ActionResult, Platform, ActionType
from src.connectors.base import BaseConnector
from src.core.config import settings
from src.policy.engine import PolicyEngine


class MetaConnector(BaseConnector):
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
        self.page_token = settings.meta_page_access_token
        self.ig_user_id = settings.meta_ig_user_id
        # FB Graph API v25.0 as specified in doc
        self._client = httpx.AsyncClient(
            base_url="https://graph.facebook.com/v25.0",
        )

    @property
    def platform(self) -> Platform:
        # Abstraction covers both IG and FB
        return Platform.FACEBOOK

    async def _enforce_policy(self, action_type: ActionType, content: str) -> Optional[ActionResult]:
        decision = await self.policy_engine.evaluate(self.platform, action_type, content)
        if not decision.allowed:
            return ActionResult(ok=False, platform=self.platform, action_type=action_type, idempotency_key=uuid.uuid4().hex, policy_decision_id=decision.decision_id, error=decision.reason)
        self._last_decision_id = decision.decision_id
        return None

    @BaseConnector.with_retry()
    async def publish(self, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        policy_block = await self._enforce_policy(ActionType.PUBLISH, content)
        if policy_block:
            return policy_block

        options = options or {}
        target = options.get("target", "facebook")  # facebook or instagram

        if target == "instagram" and self.ig_user_id:
            # 1) Upload Container
            resp = await self._client.post(f"/{self.ig_user_id}/media", params={"access_token": self.page_token, "caption": content, "image_url": options.get("image_url", "")})
            resp.raise_for_status()
            creation_id = resp.json().get("id")

            # 2) Publish Container
            resp2 = await self._client.post(f"/{self.ig_user_id}/media_publish", params={"access_token": self.page_token, "creation_id": creation_id})
            resp2.raise_for_status()
            res_data = resp2.json()
            ext_id = res_data.get("id")
        else:
            # Facebook Page Feed
            page_id = "me"  # Since we use page_token
            resp = await self._client.post(f"/{page_id}/feed", params={"access_token": self.page_token}, data={"message": content})
            resp.raise_for_status()
            res_data = resp.json()
            ext_id = res_data.get("id")

        return ActionResult(ok=True, platform=self.platform, action_type=ActionType.PUBLISH, external_id=ext_id, idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id, raw_data=res_data)

    @BaseConnector.with_retry()
    async def reply(self, thread_ref: str, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # pyright: ignore[reportIncompatibleMethodOverride]
        # e.g., Reply to a FB Comment
        policy_block = await self._enforce_policy(ActionType.REPLY, content)
        if policy_block:
            return policy_block

        resp = await self._client.post(f"/{thread_ref}/comments", params={"access_token": self.page_token}, data={"message": content})
        resp.raise_for_status()
        res_data = resp.json()
        return ActionResult(ok=True, platform=self.platform, action_type=ActionType.REPLY, external_id=res_data.get("id"), idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id, raw_data=res_data)

    async def moderate(self, object_ref: str, action: str, reason: str) -> ActionResult:
        # action = 'hide' or 'delete'
        return ActionResult(ok=False, platform=self.platform, action_type=ActionType.MODERATE, error="MVP Not Implemented", idempotency_key=uuid.uuid4().hex, policy_decision_id="none")

    async def sync_state(self, scope: str) -> dict[str, Any]:
        return {}

    async def get_limits(self) -> dict[str, Any]:
        return {}
