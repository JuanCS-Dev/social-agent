from dataclasses import dataclass, field
from typing import Any, Optional

from src.agent.profiles import ProfileRegistry, profile_registry
from src.agent.understand import ContextClassification, UnderstandEngine, understand_engine
from src.core.config import settings
from src.core.contracts import ActionType, Platform
from src.planner.scheduler import Scheduler, scheduler


@dataclass
class ActionProposal:
    platform: Platform
    action_type: ActionType
    content: str
    reason: str
    thread_ref: Optional[str] = None
    options: dict[str, Any] = field(default_factory=dict)


class AutonomyStrategy:
    def __init__(
        self,
        profiles: ProfileRegistry | None = None,
        runtime_scheduler: Scheduler | None = None,
        nlu_engine: UnderstandEngine | None = None,
    ):
        self.profiles = profiles or profile_registry
        self.scheduler = runtime_scheduler or scheduler
        self.nlu_engine = nlu_engine or understand_engine
        self._rotation = [Platform.REDDIT, Platform.X, Platform.FACEBOOK, Platform.INSTAGRAM]
        self._rotation_idx = 0

    def _next_platforms(self) -> list[Platform]:
        ordered = self._rotation[self._rotation_idx :] + self._rotation[: self._rotation_idx]
        self._rotation_idx = (self._rotation_idx + 1) % len(self._rotation)
        return ordered

    def infer_platform(self, event_type: str, payload: dict[str, Any]) -> Optional[Platform]:
        event_type_l = event_type.lower()
        if "reddit" in event_type_l:
            return Platform.REDDIT
        if "twitter" in event_type_l or event_type_l.startswith("x_") or payload.get("tweet_id"):
            return Platform.X
        if "facebook" in event_type_l:
            return Platform.FACEBOOK
        if "instagram" in event_type_l:
            return Platform.INSTAGRAM
        if "meta" in event_type_l:
            object_type = str(payload.get("object", "")).lower()
            if "instagram" in object_type or payload.get("ig_user_id"):
                return Platform.INSTAGRAM
            return Platform.FACEBOOK
        return None

    def extract_event_text(self, payload: dict[str, Any]) -> str:
        for key in ("text", "message", "caption", "body", "title"):
            if payload.get(key):
                return str(payload[key])
        entry = payload.get("entry", [])
        if isinstance(entry, list) and entry:
            first_entry = entry[0]
            if isinstance(first_entry, dict):
                for key in ("message", "text", "description"):
                    if first_entry.get(key):
                        return str(first_entry[key])
        return str(payload)[:500]

    def extract_thread_ref(self, platform: Platform, payload: dict[str, Any]) -> Optional[str]:
        if platform == Platform.REDDIT:
            return payload.get("name") or payload.get("thing_id") or payload.get("thread_ref") or "unknown"
        if platform == Platform.X:
            return payload.get("tweet_id") or payload.get("id") or payload.get("thread_ref") or "unknown"

        entry = payload.get("entry")
        if isinstance(entry, list) and entry and isinstance(entry[0], dict):
            first_entry = entry[0]
            if first_entry.get("id"):
                return str(first_entry["id"])
            changes = first_entry.get("changes", [])
            if isinstance(changes, list) and changes and isinstance(changes[0], dict):
                value = changes[0].get("value", {})
                if isinstance(value, dict):
                    for key in ("comment_id", "post_id", "item_id"):
                        if value.get(key):
                            return str(value[key])
        return payload.get("thread_ref") or payload.get("id") or "unknown"

    def should_reply(self, classification: ContextClassification) -> bool:
        return classification.urgency == "high" or classification.intent in {"question", "complaint", "praise"}

    def build_reactive_proposals(
        self,
        event_type: str,
        payload: dict[str, Any],
        classification: ContextClassification,
    ) -> list[ActionProposal]:
        platform = self.infer_platform(event_type, payload)
        if not platform:
            return []

        if not self.should_reply(classification):
            return []

        if platform == Platform.X and not self._x_ready():
            return []

        thread_ref = self.extract_thread_ref(platform, payload)
        profile = self.profiles.get(platform)
        source_text = self.extract_event_text(payload)
        language = classification.language if len(classification.language) == 2 else profile.primary_language
        response = self.nlu_engine.generate_reply(
            profile_name=profile.profile_name,
            platform=platform,
            source_text=source_text,
            intent=classification.intent,
            urgency=classification.urgency,
            language=language,
        )

        return [
            ActionProposal(
                platform=platform,
                action_type=ActionType.REPLY,
                thread_ref=thread_ref,
                content=response,
                reason=f"reactive_{classification.intent}_{classification.urgency}",
            )
        ]

    def _pick_topic(self, platform: Platform, strategic_topics: list[str] | None = None) -> str:
        if strategic_topics:
            idx = self._rotation_idx % len(strategic_topics)
            return strategic_topics[idx]
        profile = self.profiles.get(platform)
        idx = self._rotation_idx % len(profile.content_pillars)
        return profile.content_pillars[idx]

    def _extract_strategy_context(self, reflection_payload: dict[str, Any] | None) -> dict[str, Any]:
        if not reflection_payload:
            return {
                "topics": [],
                "conversion_cta": settings.agent_primary_cta,
                "core_narrative": "",
                "kpi_targets": {},
            }

        payload = reflection_payload.get("payload", reflection_payload)
        if not isinstance(payload, dict):
            payload = {}
        strategy = payload.get("strategy", payload)
        if not isinstance(strategy, dict):
            strategy = {}
        brief = payload.get("brief", {})
        if not isinstance(brief, dict):
            brief = {}
        narrative = strategy.get("narrative", {})
        if not isinstance(narrative, dict):
            narrative = {}

        topics: list[str] = []
        for bucket in (
            strategy.get("trending_topics", []),
            strategy.get("emerging_topics", []),
            brief.get("trending_topics", []),
        ):
            if not isinstance(bucket, list):
                continue
            for raw in bucket:
                topic = str(raw).strip()
                if topic and topic not in topics:
                    topics.append(topic)

        kpi_targets = strategy.get("kpi_targets", {})
        if not isinstance(kpi_targets, dict):
            kpi_targets = {}

        conversion_cta = str(narrative.get("conversion_cta") or strategy.get("conversion_cta") or settings.agent_primary_cta).strip()
        core_narrative = str(narrative.get("core_narrative") or strategy.get("summary") or "").strip()

        return {
            "topics": topics,
            "conversion_cta": conversion_cta,
            "core_narrative": core_narrative,
            "kpi_targets": kpi_targets,
        }

    def _append_campaign_cta(self, content: str, cta: str, platform: Platform) -> str:
        base = content.strip()
        cta = cta.strip()
        if not cta:
            return base
        if cta.lower() in base.lower():
            return base

        merged = f"{base}\n\n{cta}" if base else cta
        if platform == Platform.X and len(merged) > 280:
            return merged[:277].rstrip() + "..."
        return merged

    def _build_publish_options(self, platform: Platform, topic: str) -> dict[str, Any]:
        if platform == Platform.REDDIT:
            return {"subreddit": "test", "title": f"[Autonomous] {topic}"}
        if platform == Platform.FACEBOOK:
            return {"target": "facebook"}
        if platform == Platform.INSTAGRAM:
            if not settings.instagram_default_image_url:
                return {}
            return {"target": "instagram", "image_url": settings.instagram_default_image_url}
        return {}

    def _x_ready(self) -> bool:
        mode = settings.x_execution_mode.strip().lower()
        if mode == "operator":
            return True
        return bool(settings.x_access_token)

    def _platform_ready_for_publish(self, platform: Platform) -> bool:
        if platform == Platform.REDDIT:
            return bool(settings.reddit_client_id and settings.reddit_client_secret and settings.reddit_username and settings.reddit_password)
        if platform == Platform.X:
            return self._x_ready()
        if platform == Platform.FACEBOOK:
            return bool(settings.meta_page_access_token)
        if platform == Platform.INSTAGRAM:
            return bool(settings.meta_page_access_token and settings.meta_ig_user_id and settings.instagram_default_image_url)
        return False

    def build_proactive_proposals(
        self,
        reflection_payload: dict[str, Any] | None = None,
    ) -> list[ActionProposal]:
        proposals: list[ActionProposal] = []
        max_actions = max(0, settings.autonomy_max_proactive_actions_per_tick)
        strategy_context = self._extract_strategy_context(reflection_payload)

        if max_actions == 0:
            return proposals

        for platform in self._next_platforms():
            profile = self.profiles.get(platform)
            if not profile.enabled:
                continue
            if not self._platform_ready_for_publish(platform):
                continue
            if not self.scheduler.can_operate(platform.value):
                continue
            if not self.scheduler.can_publish_now(platform.value, profile.min_publish_interval_minutes):
                continue

            topic = self._pick_topic(platform, strategy_context["topics"])
            options = self._build_publish_options(platform, topic)
            if platform == Platform.INSTAGRAM and not options.get("image_url"):
                # Avoid guaranteed 4xx from Meta API when no media URL is available.
                continue

            content = self.nlu_engine.generate_post(
                profile_name=profile.profile_name,
                platform=platform,
                topic=topic,
                language=profile.primary_language or settings.autonomy_default_language,
                strategy_context={
                    "core_narrative": strategy_context["core_narrative"],
                    "kpi_targets": strategy_context["kpi_targets"],
                },
            )
            if settings.agent_dominant_mode:
                content = self._append_campaign_cta(
                    content=content,
                    cta=strategy_context["conversion_cta"],
                    platform=platform,
                )
            options.update(
                {
                    "campaign_cta": strategy_context["conversion_cta"],
                    "core_narrative": strategy_context["core_narrative"],
                }
            )
            proposals.append(
                ActionProposal(
                    platform=platform,
                    action_type=ActionType.PUBLISH,
                    content=content,
                    options=options,
                    reason=f"proactive_growth_{topic}",
                )
            )
            if len(proposals) >= max_actions:
                break

        return proposals


autonomy_strategy = AutonomyStrategy()
