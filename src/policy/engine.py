from typing import Optional
from src.core.contracts import ActionType, Platform
from pydantic import BaseModel, Field
import uuid


class PolicyDecision(BaseModel):
    allowed: bool
    decision_id: str = Field(default_factory=lambda: f"pol_{uuid.uuid4().hex[:12]}")
    reason: Optional[str] = None
    risk_level: str = "low"  # low, medium, high


class PolicyEngine:
    def __init__(self):
        # We could inject memory/storage here for idempotency checks
        pass

    async def evaluate(self, platform: Platform, action: ActionType, content: str, **kwargs) -> PolicyDecision:
        """
        Evaluates whether an action is permitted based on current policies.
        MVP: Basic pass-through with simple heuristic.
        """
        # Simple risk heuristic MVP
        risk_level = "high" if "DELETE" in content.upper() else "low"

        # If it's high risk in production, block it for human review
        allowed = True
        reason = "Pass-through MVP policy"

        if risk_level == "high":
            allowed = False
            reason = "High risk action requires human escalation"

        return PolicyDecision(allowed=allowed, reason=reason, risk_level=risk_level)
