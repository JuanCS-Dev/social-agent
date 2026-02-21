from src.core.contracts import Platform, ActionResult, ActionType
from src.connectors.reddit import RedditConnector
from src.connectors.x import XConnector
from src.connectors.meta import MetaConnector
from src.policy.engine import PolicyEngine
from src.planner.scheduler import scheduler
from typing import Dict, Any, Optional
from src.core.logger import log
import httpx

class ActionDispatcher:
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.connectors = {
            Platform.REDDIT: RedditConnector(self.policy_engine),
            Platform.X: XConnector(self.policy_engine),
            Platform.FACEBOOK: MetaConnector(self.policy_engine),
            Platform.INSTAGRAM: MetaConnector(self.policy_engine),
        }

    async def execute_publish(self, platform: Platform, content: str, options: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Routes a publish action to the correct platform if budget allows."""
        if not scheduler.can_operate(platform.value):
            log.warning(f"Budget exceeded for {platform.value}. Postponing action.")
            return ActionResult(
                ok=False, platform=platform, action_type=ActionType.PUBLISH, 
                error="Rate budget exceeded", idempotency_key="none", policy_decision_id="none"
            )
            
        connector = self.connectors.get(platform)
        if not connector:
            raise ValueError(f"No connector implemented for {platform}")

        try:
            result = await connector.publish(content, options)
            if result.ok:
                scheduler.record_usage(platform.value, result.rate_cost)
            return result
        except httpx.HTTPError as e:
            log.error(f"Action publish failed after retries: {e}")
            return ActionResult(
                ok=False, platform=platform, action_type=ActionType.PUBLISH,
                error=str(e), idempotency_key="none", policy_decision_id="none"
            )

    async def execute_reply(self, platform: Platform, thread_ref: str, content: str, options: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Routes a reply action to the correct platform."""
        if not scheduler.can_operate(platform.value):
            return ActionResult(
                ok=False, platform=platform, action_type=ActionType.REPLY, 
                error="Rate budget exceeded", idempotency_key="none", policy_decision_id="none"
            )
            
        connector = self.connectors.get(platform)
        if not connector:
            raise ValueError(f"No connector implemented for {platform}")

        try:
            result = await connector.reply(thread_ref, content, options)
            if result.ok:
                scheduler.record_usage(platform.value, result.rate_cost)
            return result
        except httpx.HTTPError as e:
            log.error(f"Action reply failed after retries: {e}")
            return ActionResult(
                ok=False, platform=platform, action_type=ActionType.REPLY,
                error=str(e), idempotency_key="none", policy_decision_id="none"
            )
        
dispatcher = ActionDispatcher()
