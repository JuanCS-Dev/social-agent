from src.core.contracts import ActionResult, Platform, ActionType
from datetime import datetime, timezone
from src.core.config import Settings


def test_action_result_creation():
    res = ActionResult(ok=True, platform=Platform.FACEBOOK, action_type=ActionType.PUBLISH, idempotency_key="test_key", policy_decision_id="dec_01")
    assert res.ok is True
    assert res.platform == Platform.FACEBOOK
    assert res.action_type == ActionType.PUBLISH
    assert res.idempotency_key == "test_key"
    assert res.policy_decision_id == "dec_01"
    assert res.rate_cost == 1
    assert res.error is None
    assert isinstance(res.timestamp, datetime)
    assert res.timestamp.tzinfo == timezone.utc


def test_config_defaults():
    # Should load correctly with defaults
    s = Settings()
    assert s.environment == "production"
    assert s.database_url == "sqlite+aiosqlite:///./var/data/social_agent.db"
    assert s.reddit_user_agent == "ByteSocialAgent/1.0.0"
