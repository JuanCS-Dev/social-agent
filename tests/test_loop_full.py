import pytest
from src.agent.loop import AutonomyLoop
import asyncio

@pytest.mark.asyncio
async def test_loop_run_lifecycle(mocker):
    loop = AutonomyLoop()
    loop.running = False
    
    # Mock tick to raise an exception to cover exception handling block
    mocker.patch.object(loop, "tick", side_effect=Exception("Tick failed"))
    mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)
    
    # Temporarily set running, but let the loop break out manually
    async def side_effect(*args):
        loop.running = False
    
    mocker.patch("asyncio.sleep", side_effect=side_effect)
    
    await loop.run()
    # If we got here, it caught the exception and broke the loop gracefully
    assert loop.running is False

@pytest.mark.asyncio
async def test_loop_tick_complete_exception(mocker):
    loop = AutonomyLoop()
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = mocker.AsyncMock(return_value={
        "id": "evt_crash", "event_type": "x_webhook", "payload": {"text": "crash"}
    })
    
    # Make classify crash
    mocker.patch("src.agent.loop.understand_engine.classify", side_effect=Exception("Critical engine failure"))
    
    mock_storage.save_to_dlq = mocker.AsyncMock()
    mock_storage.delete_event = mocker.AsyncMock()
    
    await loop.tick()
    
    # Should save to DLQ and Delete
    mock_storage.save_to_dlq.assert_called_once()
    mock_storage.delete_event.assert_called_once_with("evt_crash")

@pytest.mark.asyncio
async def test_loop_tick_urgent_meta(mocker):
    mock_event = {
        "id": "evt_urgent_2",
        "event_type": "meta_webhook",
        "payload": {"entry": [{"id": "meta_thread_1"}]}
    }
    mocker.patch("src.agent.loop.storage.fetch_next_event", return_value=mock_event)
    
    mock_class = mocker.MagicMock()
    mock_class.intent = "some"
    mock_class.urgency = "high"
    mocker.patch("src.agent.loop.understand_engine.classify", return_value=mock_class)
    
    del_mock = mocker.patch("src.agent.loop.storage.delete_event")
    
    # Mock act to succeed
    from src.core.contracts import ActionResult, Platform, ActionType
    res = ActionResult(ok=True, platform=Platform.FACEBOOK, action_type=ActionType.REPLY, idempotency_key="idk", policy_decision_id="pid")
    disp_mock = mocker.patch("src.agent.loop.dispatcher.execute_reply", return_value=res)
    
    loop = AutonomyLoop()
    await loop.tick()
    
    # Should reply on Meta specifically pointing to the thread
    disp_mock.assert_called_once()
    assert disp_mock.call_args[0][0] == Platform.FACEBOOK
    assert disp_mock.call_args[0][1] == "meta_thread_1"
    del_mock.assert_called_with("evt_urgent_2")

@pytest.mark.asyncio
async def test_loop_tick_action_failure(mocker):
    loop = AutonomyLoop()
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = mocker.AsyncMock(return_value={
        "id": "evt_act_fail", "event_type": "x_webhook", "payload": {"text": "urgent but fails"}
    })
    
    from src.agent.understand import ContextClassification
    mocker.patch("src.agent.loop.understand_engine.classify", return_value=ContextClassification(intent="complaint", urgency="high", language="en"))
    
    from src.core.contracts import ActionResult, Platform, ActionType
    mocker.patch("src.agent.loop.dispatcher.execute_reply", return_value=ActionResult(
        ok=False, error="API Limit", platform=Platform.X, action_type=ActionType.REPLY, idempotency_key="key", policy_decision_id="none"
    ))
    
    mock_storage.save_to_dlq = mocker.AsyncMock()
    mock_storage.delete_event = mocker.AsyncMock()
    
    await loop.tick()
    mock_storage.save_to_dlq.assert_called_once()
    mock_storage.delete_event.assert_called_once_with("evt_act_fail")
