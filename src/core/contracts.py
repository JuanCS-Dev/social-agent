from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Any


class Platform(str, Enum):
    REDDIT = "reddit"
    X = "x"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class ActionType(str, Enum):
    PUBLISH = "publish"
    REPLY = "reply"
    MODERATE = "moderate"
    SYNC = "sync"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActionResult(BaseModel):
    ok: bool
    platform: Platform
    action_type: ActionType
    external_id: Optional[str] = None
    idempotency_key: str
    rate_cost: int = 1
    policy_decision_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    error: Optional[str] = None
    raw_data: Optional[Any] = None
