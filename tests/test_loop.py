import pytest
from unittest.mock import AsyncMock

from src.agent.loop import AutonomyLoop
from src.agent.strategy import ActionProposal
from src.core.contracts import ActionResult, Platform, ActionType


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
    mock_storage.fetch_next_event = AsyncMock(
        return_value={
            "id": "evt_1",
            "event_type": "reddit_webhook",
            "payload": {"text": "URGENT COMPLAINT", "name": "t3_123"},
        }
    )
    mock_storage.delete_event = AsyncMock()
    mock_storage.save_to_dlq = AsyncMock()

    mock_understand = mocker.patch("src.agent.loop.understand_engine")
    import src.agent.understand as un

    mock_understand.classify.return_value = un.ContextClassification(
        intent="complaint",
        urgency="high",
        language="en",
    )

    mock_dispatcher = mocker.patch("src.agent.loop.dispatcher")
    mock_dispatcher.execute_reply.return_value = ActionResult(
        ok=True,
        platform=Platform.REDDIT,
        action_type=ActionType.REPLY,
        idempotency_key="key",
        policy_decision_id="pol",
    )

    await loop.tick()

    mock_understand.classify.assert_called_once()
    mock_dispatcher.execute_reply.assert_called_once()
    mock_storage.delete_event.assert_called_once_with("evt_1")


@pytest.mark.asyncio
async def test_loop_tick_ignore_event(loop, mocker):
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.fetch_next_event = AsyncMock(
        return_value={
            "id": "evt_2",
            "event_type": "meta_webhook",
            "payload": {"text": "Just looking around."},
        }
    )
    mock_storage.delete_event = AsyncMock()

    mock_understand = mocker.patch("src.agent.loop.understand_engine")
    import src.agent.understand as un

    mock_understand.classify.return_value = un.ContextClassification(
        intent="neutral",
        urgency="low",
        language="en",
    )

    mock_dispatcher = mocker.patch("src.agent.loop.dispatcher")

    await loop.tick()

    mock_understand.classify.assert_called_once()
    mock_dispatcher.execute_reply.assert_not_called()
    mock_storage.delete_event.assert_called_once_with("evt_2")


@pytest.mark.asyncio
async def test_loop_proactive_cycle_uses_reflection(loop, mocker):
    mock_storage = mocker.patch("src.agent.loop.storage")
    latest_reflection = {
        "payload": {
            "strategy": {
                "narrative": {
                    "conversion_cta": "Siga agora",
                    "core_narrative": "Disciplina > desculpas",
                }
            }
        }
    }
    mock_storage.get_latest_reflection = AsyncMock(return_value=latest_reflection)
    mock_storage.save_signal = AsyncMock()
    mock_storage.save_action_log = AsyncMock()

    mock_strategy = mocker.MagicMock()
    mock_strategy.build_proactive_proposals.return_value = [
        ActionProposal(
            platform=Platform.X,
            action_type=ActionType.PUBLISH,
            content="Post base",
            reason="proactive_growth_macro",
            options={
                "campaign_cta": "Siga agora",
                "core_narrative": "Disciplina > desculpas",
            },
        )
    ]
    loop.strategy = mock_strategy
    loop._execute_proposal = AsyncMock(
        return_value=ActionResult(
            ok=True,
            platform=Platform.X,
            action_type=ActionType.PUBLISH,
            idempotency_key="idp",
            policy_decision_id="pol",
        )
    )

    await loop._run_proactive_cycle()

    mock_strategy.build_proactive_proposals.assert_called_once_with(latest_reflection)
    assert mock_storage.save_signal.call_count == 1
    metadata = mock_storage.save_signal.call_args.kwargs["metadata"]
    assert metadata["campaign_cta"] == "Siga agora"
    assert metadata["core_narrative"] == "Disciplina > desculpas"


@pytest.mark.asyncio
async def test_loop_execute_x_in_operator_mode_queues_task(loop, mocker, monkeypatch):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "x_execution_mode", "operator")
    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.queue_operator_task = AsyncMock(return_value=42)
    mock_storage.save_action_log = AsyncMock()
    mock_scheduler = mocker.patch("src.agent.loop.scheduler")

    proposal = ActionProposal(
        platform=Platform.X,
        action_type=ActionType.PUBLISH,
        content="post no x",
        reason="test_operator",
    )
    result = await loop._execute_proposal("evt_x_test", proposal)

    assert result.ok is True
    assert result.external_id == "x_operator_task_42"
    mock_storage.queue_operator_task.assert_called_once()
    mock_scheduler.record_result.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [Platform.REDDIT, Platform.FACEBOOK, Platform.INSTAGRAM])
async def test_loop_execute_api_failure_falls_back_to_operator_queue(
    loop,
    mocker,
    monkeypatch,
    platform,
):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "operator_fallback_on_api_error", True)
    monkeypatch.setattr(src.core.config.settings, "x_execution_mode", "api")

    mock_storage = mocker.patch("src.agent.loop.storage")
    mock_storage.queue_operator_task = AsyncMock(return_value=99)
    mock_storage.save_action_log = AsyncMock()
    mock_scheduler = mocker.patch("src.agent.loop.scheduler")
    mock_dispatcher = mocker.patch("src.agent.loop.dispatcher")
    mock_dispatcher.execute_reply = AsyncMock(
        return_value=ActionResult(
            ok=False,
            error="upstream_api_unavailable",
            platform=platform,
            action_type=ActionType.REPLY,
            idempotency_key="idk_fail",
            policy_decision_id="allow",
        )
    )

    proposal = ActionProposal(
        platform=platform,
        action_type=ActionType.REPLY,
        thread_ref="thread_1",
        content="resposta",
        reason="test_api_fallback",
        options={"source": "test"},
    )
    result = await loop._execute_proposal("evt_fallback", proposal)

    assert result.ok is True
    assert result.external_id == f"{platform.value}_operator_task_99"
    assert result.raw_data["queue_reason"] == "api_fallback"
    assert result.raw_data["api_error"] == "upstream_api_unavailable"
    mock_storage.queue_operator_task.assert_called_once()
    queued_options = mock_storage.queue_operator_task.call_args.kwargs["options"]
    assert queued_options["operator_queue_reason"] == "api_fallback"
    assert queued_options["api_error"] == "upstream_api_unavailable"
    mock_scheduler.record_result.assert_called_once()
