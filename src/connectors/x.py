import httpx
from typing import Optional, Any
import uuid
from src.core.contracts import ActionResult, Platform, ActionType
from src.connectors.base import BaseConnector
from src.core.config import settings
from src.core.logger import log
from src.policy.engine import PolicyEngine

class XConnector(BaseConnector):
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
        self.access_token = settings.x_access_token 
        self._client = httpx.AsyncClient(
            base_url="https://api.x.com/2",
            headers={
                "Authorization": f"Bearer {self.access_token}", 
                "Content-Type": "application/json"
            }
        )

    @property
    def platform(self) -> Platform:
        return Platform.X

    async def _enforce_policy(self, action_type: ActionType, content: str) -> Optional[ActionResult]:
        decision = await self.policy_engine.evaluate(self.platform, action_type, content)
        if not decision.allowed:
            return ActionResult(
                ok=False, platform=self.platform, action_type=action_type,
                idempotency_key=uuid.uuid4().hex, policy_decision_id=decision.decision_id,
                error=decision.reason
            )
        self._last_decision_id = decision.decision_id
        return None

    @BaseConnector.with_retry()
    async def publish(self, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # type: ignore[override]
        policy_block = await self._enforce_policy(ActionType.PUBLISH, content)
        if policy_block:
            return policy_block

        payload = {"text": content}
        resp = await self._client.post("/tweets", json=payload)
        resp.raise_for_status()
        res_data = resp.json()
        return ActionResult(
            ok=True, platform=self.platform, action_type=ActionType.PUBLISH,
            external_id=res_data.get("data", {}).get("id"),
            idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id,
            raw_data=res_data
        )

    @BaseConnector.with_retry()
    async def reply(self, thread_ref: str, content: str, options: Optional[dict[str, Any]] = None) -> ActionResult:  # type: ignore[override]
        policy_block = await self._enforce_policy(ActionType.REPLY, content)
        if policy_block:
            return policy_block

        payload = {
            "text": content,
            "reply": {"in_reply_to_tweet_id": thread_ref}
        }
        resp = await self._client.post("/tweets", json=payload)
        resp.raise_for_status()
        res_data = resp.json()
        return ActionResult(
            ok=True, platform=self.platform, action_type=ActionType.REPLY,
            external_id=res_data.get("data", {}).get("id"),
            idempotency_key=uuid.uuid4().hex, policy_decision_id=self._last_decision_id,
            raw_data=res_data
        )

    async def moderate(self, object_ref: str, action: str, reason: str) -> ActionResult:
        return ActionResult(ok=False, platform=self.platform, action_type=ActionType.MODERATE, error="MVP Not Implemented", idempotency_key=uuid.uuid4().hex, policy_decision_id="none")

    async def sync_state(self, scope: str) -> dict[str, Any]:
        return {}

    async def get_limits(self) -> dict[str, Any]:
        return {}
