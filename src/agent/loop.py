import asyncio
import inspect

from src.agent.act import dispatcher
from src.agent.intelligence import social_intelligence
from src.agent.strategy import ActionProposal, AutonomyStrategy, autonomy_strategy
from src.agent.understand import understand_engine
from src.core.config import settings
from src.core.contracts import ActionResult, ActionType
from src.core.logger import log
from src.memory.storage import storage
from src.planner.scheduler import scheduler


class AutonomyLoop:
    def __init__(self, strategy: AutonomyStrategy | None = None):
        self.running = False
        self.strategy = strategy or autonomy_strategy

    async def run(self):
        self.running = True
        poll_seconds = max(1, settings.autonomy_poll_seconds)
        log.info("Starting REAL Autonomy OODA Loop...")
        while self.running:
            try:
                await self.tick()
            except Exception as e:
                log.error(f"Loop error: {e}")
            await asyncio.sleep(poll_seconds)

    async def tick(self):
        await self._run_daily_reflection_if_due()

        event = await storage.fetch_next_event()
        if event:
            await self._process_event(event)
            return

        if settings.autonomy_enable_proactive:
            await self._run_proactive_cycle()

    async def _call_maybe_async(self, result):
        if inspect.isawaitable(result):
            return await result
        return result

    async def _process_event(self, event: dict):
        event_id = event["id"]
        event_type = event["event_type"]
        payload = event["payload"]
        log.info(f"[Autonomy Loop] Processing event {event_id} ({event_type})")

        try:
            content_to_analyze = self.strategy.extract_event_text(payload)
            classification = understand_engine.classify(content_to_analyze)
            platform = self.strategy.infer_platform(event_type, payload)
            language = classification.language if isinstance(classification.language, str) and classification.language else settings.autonomy_default_language

            if platform:
                await self._call_maybe_async(
                    storage.save_signal(
                        event_id=event_id,
                        platform=platform.value,
                        intent=str(classification.intent),
                        urgency=str(classification.urgency),
                        language=language,
                        metadata={
                            "event_type": event_type,
                            "text": content_to_analyze,
                        },
                    )
                )

            proposals = self.strategy.build_reactive_proposals(
                event_type=event_type,
                payload=payload,
                classification=classification,
            )
            if not proposals:
                log.info(f"Event {event_id} skipped by strategy.")
                await self._call_maybe_async(storage.delete_event(event_id))
                return

            errors: list[str] = []
            for proposal in proposals:
                result = await self._execute_proposal(event_id, proposal)
                if not result.ok:
                    errors.append(result.error or "unknown_error")

            if errors:
                await self._call_maybe_async(storage.save_to_dlq(event_id, event_type, payload, "; ".join(errors)))

            await self._call_maybe_async(storage.delete_event(event_id))

        except Exception as e:
            log.error(f"Failed to process event {event_id}: {e}")
            await self._call_maybe_async(storage.save_to_dlq(event_id, event_type, payload, str(e)))
            await self._call_maybe_async(storage.delete_event(event_id))

    async def _queue_operator_proposal(
        self,
        event_id: str,
        proposal: ActionProposal,
        queue_reason: str,
        api_error: str | None = None,
    ) -> ActionResult:
        options = dict(proposal.options)
        options["operator_queue_reason"] = queue_reason
        if api_error:
            options["api_error"] = api_error

        task_id = await self._call_maybe_async(
            storage.queue_operator_task(
                event_id=event_id,
                platform=proposal.platform.value,
                action_type=proposal.action_type.value,
                thread_ref=proposal.thread_ref,
                content=proposal.content,
                options=options,
            )
        )
        return ActionResult(
            ok=True,
            platform=proposal.platform,
            action_type=proposal.action_type,
            external_id=f"{proposal.platform.value}_operator_task_{task_id}",
            idempotency_key=f"{proposal.platform.value}_operator_{event_id}_{task_id}",
            policy_decision_id=f"{proposal.platform.value}_operator_queue",
            raw_data={
                "task_id": task_id,
                "status": "pending",
                "queue_reason": queue_reason,
                "api_error": api_error,
            },
        )

    async def _execute_proposal(self, event_id: str, proposal: ActionProposal) -> ActionResult:
        if proposal.platform.value == "x" and settings.x_execution_mode.strip().lower() == "operator":
            result = await self._queue_operator_proposal(
                event_id=event_id,
                proposal=proposal,
                queue_reason="x_operator_mode",
            )
        elif proposal.action_type == ActionType.PUBLISH:
            result = await dispatcher.execute_publish(
                proposal.platform,
                proposal.content,
                proposal.options,
            )
        elif proposal.action_type == ActionType.REPLY and proposal.thread_ref:
            result = await dispatcher.execute_reply(
                proposal.platform,
                proposal.thread_ref,
                proposal.content,
                proposal.options,
            )
        else:
            result = ActionResult(
                ok=False,
                platform=proposal.platform,
                action_type=proposal.action_type,
                idempotency_key="none",
                policy_decision_id="none",
                error="Invalid proposal: missing thread_ref for reply",
            )

        if not result.ok and proposal.platform.value in {"reddit", "facebook", "instagram"} and settings.operator_fallback_on_api_error and proposal.action_type in {ActionType.PUBLISH, ActionType.REPLY}:
            task_id = await self._call_maybe_async(
                storage.queue_operator_task(
                    event_id=event_id,
                    platform=proposal.platform.value,
                    action_type=proposal.action_type.value,
                    thread_ref=proposal.thread_ref,
                    content=proposal.content,
                    options={
                        **proposal.options,
                        "operator_queue_reason": "api_fallback",
                        "api_error": result.error or "unknown_error",
                    },
                )
            )
            result = ActionResult(
                ok=True,
                platform=proposal.platform,
                action_type=proposal.action_type,
                external_id=f"{proposal.platform.value}_operator_task_{task_id}",
                idempotency_key=f"{proposal.platform.value}_operator_{event_id}_{task_id}",
                policy_decision_id=f"{proposal.platform.value}_operator_fallback",
                raw_data={
                    "task_id": task_id,
                    "status": "pending",
                    "queue_reason": "api_fallback",
                    "api_error": result.error or "unknown_error",
                },
            )

        scheduler.record_result(
            proposal.platform.value,
            result.ok,
            proposal.action_type.value,
        )
        await self._call_maybe_async(
            storage.save_action_log(
                event_id=event_id,
                platform=proposal.platform.value,
                action_type=proposal.action_type.value,
                ok=result.ok,
                policy_decision_id=result.policy_decision_id,
                idempotency_key=result.idempotency_key,
                error=result.error,
            )
        )
        return result

    async def _run_proactive_cycle(self):
        latest_reflection = await self._call_maybe_async(storage.get_latest_reflection())
        if not isinstance(latest_reflection, dict):
            latest_reflection = None

        proposals = self.strategy.build_proactive_proposals(latest_reflection)
        for proposal in proposals:
            await self._call_maybe_async(
                storage.save_signal(
                    event_id="proactive",
                    platform=proposal.platform.value,
                    intent="proactive_publish",
                    urgency="medium",
                    language=settings.autonomy_default_language,
                    metadata={
                        "reason": proposal.reason,
                        "campaign_cta": proposal.options.get("campaign_cta"),
                        "core_narrative": proposal.options.get("core_narrative"),
                    },
                )
            )
            log.info(f"EVENT: proactive_action_scheduled platform={proposal.platform.value} reason={proposal.reason}")
            result = await self._execute_proposal("proactive", proposal)
            if not result.ok:
                log.warning(f"Proactive action failed for {proposal.platform.value}: {result.error}")

    async def _run_daily_reflection_if_due(self):
        if not scheduler.should_run_daily_reflection():
            return
        try:
            signals = await storage.get_recent_signals(hours=24)
            brief = social_intelligence.build_daily_brief(signals)
            strategy_payload = understand_engine.generate_daily_strategy(brief)
            await self._call_maybe_async(
                storage.save_daily_reflection(
                    {
                        "brief": brief,
                        "strategy": strategy_payload,
                    }
                )
            )
            scheduler.mark_daily_reflection()
            log.info("EVENT: daily_reflection_completed")
            log.info("Daily self-reflection completed.")
        except Exception as e:
            log.warning(f"Daily reflection skipped: {e}")


autonomy_loop = AutonomyLoop()
