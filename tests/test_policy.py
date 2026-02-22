import pytest
from src.policy.engine import PolicyEngine
from src.core.contracts import Platform, ActionType


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.mark.asyncio
async def test_policy_allow_safe_content(policy_engine):
    decision = await policy_engine.evaluate(Platform.X, ActionType.PUBLISH, "This is a great day!")
    assert decision.allowed is True
    assert decision.risk_level == "low"
    assert decision.decision_id.startswith("pol_")


@pytest.mark.asyncio
async def test_policy_block_high_risk(policy_engine, monkeypatch):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "environment", "production")
    decision = await policy_engine.evaluate(Platform.X, ActionType.PUBLISH, "Delete everything!")
    # The MVP engine blocks if 'DELETE' is in content
    assert decision.allowed is False
    assert decision.risk_level == "high"
    assert "High risk" in decision.reason
