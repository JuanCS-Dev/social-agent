import pytest
from unittest.mock import AsyncMock
from src.agent.loop import AutonomyLoop
from src.core.contracts import ActionResult, Platform, ActionType
import json

@pytest.fixture
def loop():
    return AutonomyLoop()

@pytest.mark.asyncio
async def test_loop_tick_no_event(loop, mocker):
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = AsyncMock(return_value=None)
    
    await loop.tick()
    mock_storage.fetch_next_event.assert_called_once()
    # Nothing else should be called

@pytest.mark.asyncio
async def test_loop_tick_urgent_event(loop, mocker):
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = AsyncMock(return_value={
        "id": "evt_1",
        "event_type": "reddit_webhook",
        "payload": {"text": "URGENT COMPLAINT", "name": "t3_123"}
    })
    mock_storage.delete_event = AsyncMock()
    mock_storage.save_to_dlq = AsyncMock()
    
    mock_understand = mocker.patch("src.agent.loop.understand_engine")
    import src.agent.understand as un
    mock_understand.classify.return_value = un.ContextClassification(intent="complaint", urgency="high", language="en")
    
    mock_dispatcher = mocker.patch("src.agent.loop.dispatcher")
    mock_dispatcher.execute_reply.return_value = ActionResult(
        ok=True, platform=Platform.REDDIT, action_type=ActionType.REPLY, 
        idempotency_key="key", policy_decision_id="pol"
    )
    
    await loop.tick()
    
    mock_understand.classify.assert_called_once()
    mock_dispatcher.execute_reply.assert_called_once()
    mock_storage.delete_event.assert_called_once_with("evt_1")

@pytest.mark.asyncio
async def test_loop_tick_ignore_event(loop, mocker):
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = AsyncMock(return_value={
        "id": "evt_2",
        "event_type": "meta_webhook",
        "payload": {"text": "Just looking around."}
    })
    mock_storage.delete_event = AsyncMock()
    
    mock_understand = mocker.patch("src.agent.loop.understand_engine")
    import src.agent.understand as un
    mock_understand.classify.return_value = un.ContextClassification(intent="neutral", urgency="low", language="en")
    
    mock_dispatcher = mocker.patch("src.agent.loop.dispatcher")
    
    await loop.tick()
    
    mock_understand.classify.assert_called_once()
    mock_dispatcher.execute_reply.assert_not_called()
    mock_storage.delete_event.assert_called_once_with("evt_2")
