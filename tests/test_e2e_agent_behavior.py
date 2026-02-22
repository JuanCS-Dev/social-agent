import sqlite3
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import AsyncClient

from src.agent.loop import AutonomyLoop
from src.agent.strategy import AutonomyStrategy
from src.core.contracts import ActionResult, ActionType, Platform
from src.ingestion.app import app
from src.memory.storage import Storage
from src.planner.scheduler import Scheduler


class StubNluEngine:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def generate_post(
        self,
        profile_name: str,
        platform: Platform,
        topic: str,
        language: str,
        strategy_context: dict[str, object] | None = None,
    ) -> str:
        self.calls.append(
            {
                "profile_name": profile_name,
                "platform": platform.value,
                "topic": topic,
                "language": language,
                "strategy_context": strategy_context or {},
            }
        )
        return "Tese central com prova social e chamada objetiva."


@pytest.fixture
async def isolated_storage(tmp_path):
    runtime_storage = Storage()
    runtime_storage.db_path = str(tmp_path / "e2e_agent.db")
    await runtime_storage.init_db()
    yield runtime_storage


def _count_rows(db_path: str, table: str) -> int:
    with sqlite3.connect(db_path) as db:
        return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


@pytest.mark.asyncio
async def test_e2e_webhook_to_reactive_reply_pipeline(isolated_storage, mocker):
    import src.core.config
    from src.agent.understand import ContextClassification

    runtime_scheduler = Scheduler()
    runtime_scheduler.mark_daily_reflection()

    mocker.patch("src.ingestion.routers.webhooks.storage", isolated_storage)
    mocker.patch("src.agent.loop.storage", isolated_storage)
    mocker.patch("src.agent.loop.scheduler", runtime_scheduler)
    mocker.patch.object(src.core.config.settings, "autonomy_enable_proactive", False)
    mocker.patch(
        "src.agent.loop.understand_engine.classify",
        return_value=ContextClassification(
            intent="complaint",
            urgency="high",
            language="pt",
        ),
    )
    mocker.patch(
        "src.agent.loop.dispatcher.execute_reply",
        new_callable=AsyncMock,
        return_value=ActionResult(
            ok=True,
            platform=Platform.REDDIT,
            action_type=ActionType.REPLY,
            idempotency_key="reply_ok",
            policy_decision_id="allow",
        ),
    )

    loop = AutonomyLoop()

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/webhooks/reddit",
            json={
                "name": "t3_pipeline",
                "text": "isso caiu de novo, arrumem urgente",
            },
        )
    assert response.status_code == 200

    await loop.tick()

    stats = await isolated_storage.get_queue_stats()
    assert stats["pending_events"] == 0
    assert stats["dlq_events"] == 0
    assert stats["actions_last_hour"] == 1

    recent_signals = await isolated_storage.get_recent_signals(hours=1)
    assert len(recent_signals) == 1
    assert recent_signals[0]["platform"] == "reddit"
    assert recent_signals[0]["intent"] == "complaint"
    assert recent_signals[0]["urgency"] == "high"

    with sqlite3.connect(isolated_storage.db_path) as db:
        row = db.execute("SELECT platform, action_type, ok FROM action_logs LIMIT 1").fetchone()
    assert row == ("reddit", "reply", 1)


@pytest.mark.asyncio
async def test_e2e_reflection_to_proactive_publish_with_kpi_targets(
    isolated_storage,
    mocker,
    monkeypatch,
):
    import src.core.config

    runtime_scheduler = Scheduler()
    stub_nlu = StubNluEngine()
    strategy = AutonomyStrategy(
        runtime_scheduler=runtime_scheduler,
        nlu_engine=cast(Any, stub_nlu),
    )
    loop = AutonomyLoop(strategy=strategy)

    monkeypatch.setattr(src.core.config.settings, "autonomy_max_proactive_actions_per_tick", 1)
    monkeypatch.setattr(src.core.config.settings, "autonomy_default_language", "pt")
    monkeypatch.setattr(src.core.config.settings, "agent_dominant_mode", True)
    monkeypatch.setattr(src.core.config.settings, "agent_primary_cta", "Siga para o proximo ciclo.")
    monkeypatch.setattr(src.core.config.settings, "reddit_client_id", "id")
    monkeypatch.setattr(src.core.config.settings, "reddit_client_secret", "secret")
    monkeypatch.setattr(src.core.config.settings, "reddit_username", "user")
    monkeypatch.setattr(src.core.config.settings, "reddit_password", "pwd")

    mocker.patch("src.agent.loop.storage", isolated_storage)
    mocker.patch("src.agent.loop.scheduler", runtime_scheduler)
    mocker.patch(
        "src.agent.loop.dispatcher.execute_publish",
        new_callable=AsyncMock,
        return_value=ActionResult(
            ok=True,
            platform=Platform.REDDIT,
            action_type=ActionType.PUBLISH,
            idempotency_key="pub_ok",
            policy_decision_id="allow",
        ),
    )

    def fake_daily_strategy(brief: dict[str, object]) -> dict[str, object]:
        return {
            "summary": "Plano de alta conversao baseado em dados de 24h.",
            "trending_topics": brief.get("trending_topics", []),
            "emerging_topics": brief.get("emerging_topics", []),
            "next_actions": [
                "Concentrar distribuicao em topicos de maior share.",
                "Converter alcance em follow com CTA repetivel.",
            ],
            "narrative": {
                "core_narrative": "Consistencia vence ruido.",
                "polarizing_axis": "execucao vs desculpas",
                "conversion_cta": "Siga para o proximo ciclo.",
                "repetition_hooks": ["dados > achismo", "ritmo diario"],
            },
            "kpi_targets": {
                "reach": 1800.0,
                "share_rate": 0.08,
                "follow_conversion": 0.025,
                "retention": 0.35,
            },
        }

    mocker.patch(
        "src.agent.loop.understand_engine.generate_daily_strategy",
        side_effect=fake_daily_strategy,
    )

    await isolated_storage.save_signal(
        event_id="s1",
        platform="reddit",
        intent="question",
        urgency="medium",
        language="pt",
        metadata={
            "text": "bitcoin etf e ciclo de liquidez global",
            "impressions": 1000,
            "shares": 80,
            "new_followers": 20,
            "engaged_users": 250,
            "returning_users": 90,
        },
    )
    await isolated_storage.save_signal(
        event_id="s2",
        platform="x",
        intent="complaint",
        urgency="high",
        language="pt",
        metadata={
            "text": "bitcoin etf e inflacao importada",
            "reach": 500,
            "reposts": 40,
            "follows": 12,
            "engagements": 120,
            "retained_users": 48,
        },
    )

    await loop._run_daily_reflection_if_due()
    latest_reflection = await isolated_storage.get_latest_reflection()
    assert latest_reflection is not None
    brief = latest_reflection["payload"]["brief"]
    strategy_payload = latest_reflection["payload"]["strategy"]
    assert brief["growth_kpis_24h"]["reach"] == 1500.0
    assert strategy_payload["kpi_targets"]["follow_conversion"] == 0.025

    await loop._run_proactive_cycle()

    stats = await isolated_storage.get_queue_stats()
    assert stats["actions_last_hour"] == 1

    recent_signals = await isolated_storage.get_recent_signals(hours=1)
    proactive_signals = [s for s in recent_signals if s["intent"] == "proactive_publish"]
    assert proactive_signals, "Expected at least one proactive publish signal."
    assert proactive_signals[0]["metadata"]["campaign_cta"] == "Siga para o proximo ciclo."
    assert proactive_signals[0]["metadata"]["core_narrative"] == "Consistencia vence ruido."

    assert stub_nlu.calls
    strategy_context = cast(dict[str, Any], stub_nlu.calls[0]["strategy_context"])
    assert strategy_context["kpi_targets"]["reach"] == 1800.0
    assert strategy_context["core_narrative"] == "Consistencia vence ruido."

    assert _count_rows(isolated_storage.db_path, "action_logs") == 1


@pytest.mark.asyncio
async def test_e2e_repeated_failures_trigger_platform_backoff(isolated_storage, mocker):
    import src.core.config
    from src.agent.understand import ContextClassification

    runtime_scheduler = Scheduler()
    runtime_scheduler.mark_daily_reflection()
    mocker.patch.object(src.core.config.settings, "x_execution_mode", "api")
    mocker.patch.object(src.core.config.settings, "x_access_token", "token_for_test")

    mocker.patch("src.agent.loop.storage", isolated_storage)
    mocker.patch("src.agent.loop.scheduler", runtime_scheduler)
    mocker.patch(
        "src.agent.loop.understand_engine.classify",
        return_value=ContextClassification(
            intent="complaint",
            urgency="high",
            language="en",
        ),
    )
    mocker.patch(
        "src.agent.loop.dispatcher.execute_reply",
        new_callable=AsyncMock,
        return_value=ActionResult(
            ok=False,
            platform=Platform.X,
            action_type=ActionType.REPLY,
            idempotency_key="reply_fail",
            policy_decision_id="allow",
            error="rate_limit",
        ),
    )

    for idx in range(3):
        await isolated_storage.save_event(
            event_id=f"evt_fail_{idx}",
            event_type="x_webhook",
            payload={
                "tweet_id": f"tw_{idx}",
                "text": "this is broken and urgent",
            },
        )

    loop = AutonomyLoop()
    await loop.tick()
    await loop.tick()
    await loop.tick()

    stats = await isolated_storage.get_queue_stats()
    assert stats["pending_events"] == 0
    assert stats["dlq_events"] == 3
    assert _count_rows(isolated_storage.db_path, "action_logs") == 3
    assert runtime_scheduler.backoff_until["x"] is not None


@pytest.mark.asyncio
async def test_e2e_x_operator_mode_queues_tasks_without_x_api(
    isolated_storage,
    mocker,
    monkeypatch,
):
    import src.core.config
    from src.agent.understand import ContextClassification

    runtime_scheduler = Scheduler()
    runtime_scheduler.mark_daily_reflection()
    monkeypatch.setattr(src.core.config.settings, "x_execution_mode", "operator")
    monkeypatch.setattr(src.core.config.settings, "x_webhook_token", "tok_x")
    monkeypatch.setattr(src.core.config.settings, "autonomy_enable_proactive", False)

    mocker.patch("src.ingestion.routers.webhooks.storage", isolated_storage)
    mocker.patch("src.agent.loop.storage", isolated_storage)
    mocker.patch("src.agent.loop.scheduler", runtime_scheduler)
    mocker.patch(
        "src.agent.loop.understand_engine.classify",
        return_value=ContextClassification(
            intent="complaint",
            urgency="high",
            language="pt",
        ),
    )
    mocked_dispatch = mocker.patch(
        "src.agent.loop.dispatcher.execute_reply",
        new_callable=AsyncMock,
    )

    loop = AutonomyLoop()

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/webhooks/x",
            headers={"x-social-agent-token": "tok_x"},
            json={
                "tweet_id": "tw_operator_1",
                "text": "isso aqui falhou, arruma urgente",
            },
        )
    assert response.status_code == 200

    await loop.tick()

    mocked_dispatch.assert_not_called()
    tasks = await isolated_storage.list_operator_tasks(platform="x", status="pending", limit=10)
    assert len(tasks) == 1
    assert tasks[0]["action_type"] == "reply"
    assert tasks[0]["thread_ref"] == "tw_operator_1"
    assert tasks[0]["options"]["operator_queue_reason"] == "x_operator_mode"
