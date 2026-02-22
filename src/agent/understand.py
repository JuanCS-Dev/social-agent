from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.agent.persona import SOCIAL_INFLUENCER_PERSONA
from src.core.config import settings
from src.core.contracts import Platform
from src.core.logger import log


class ContextClassification(BaseModel):
    intent: str  # e.g., question, complaint, praise, neutral
    urgency: str  # low, medium, high
    language: str


class GeneratedCopy(BaseModel):
    text: str


class GrowthKpiTargets(BaseModel):
    reach: float = 0.0
    share_rate: float = 0.0
    follow_conversion: float = 0.0
    retention: float = 0.0


class NarrativeDirectives(BaseModel):
    core_narrative: str = ""
    polarizing_axis: str = ""
    conversion_cta: str = ""
    repetition_hooks: list[str] = Field(default_factory=list)


class DailyStrategy(BaseModel):
    summary: str
    trending_topics: list[str] = Field(default_factory=list)
    emerging_topics: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    narrative: NarrativeDirectives = Field(default_factory=NarrativeDirectives)
    kpi_targets: GrowthKpiTargets = Field(default_factory=GrowthKpiTargets)


class UnderstandEngine:
    def __init__(self):
        try:
            self.client = genai.Client(
                vertexai=True,
                project=settings.gcp_project,
                location="global",  # Gemini 3 models require the global region
            )
        except Exception as e:
            log.error(f"Failed to initialize Vertex AI Client: {e}")
            self.client = None

        # The correct, exact identifier for Gemini 3 Flash on Vertex AI
        self.model = "gemini-3-flash-preview"

        # Explicit identifier logic: this is Byte Social Agent, NOT the existing Cloud Run bot
        self.agent_identity = "ByteSocialAgent_v1"

    def _utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _time_context(self) -> str:
        return f"Current UTC timestamp: {self._utc_timestamp()}. Use this timestamp as authoritative context for time-sensitive reasoning."

    def _persona_context(self) -> str:
        return (
            f"{SOCIAL_INFLUENCER_PERSONA}\n\n"
            f"Goal: {settings.agent_goal}\n"
            f"Ideology: {settings.agent_ideology}\n"
            f"Moral constraints: {settings.agent_moral_framework}\n"
            f"Dominant mode: {'enabled' if settings.agent_dominant_mode else 'disabled'}\n"
            f"Primary CTA: {settings.agent_primary_cta}\n"
            f"Growth KPI priorities: {settings.agent_growth_kpi_priorities}"
        )

    def _llm_enabled(self) -> bool:
        return bool(self.client and settings.autonomy_use_llm_generation)

    def _grounding_tools(self) -> list[Any]:
        if not settings.autonomy_enable_grounding:
            return []
        return [types.Tool(google_search=types.GoogleSearch())]

    def _is_grounded_response(self, response: Any) -> bool:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            if getattr(candidate, "grounding_metadata", None):
                return True
        return False

    def _generate_structured(self, prompt: str, schema: type[BaseModel], temperature: float) -> BaseModel:
        if not self.client:
            raise RuntimeError("Gemini client not initialized.")

        tools = self._grounding_tools()
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
            tools=tools or None,
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            if tools and not self._is_grounded_response(response):
                message = "Grounding enabled but no grounding metadata returned by model."
                if settings.autonomy_require_grounding:
                    raise RuntimeError(message)
                log.warning(message)
            response_text = response.text
            if not response_text:
                raise RuntimeError("LLM returned empty response body.")
            return schema.model_validate_json(response_text)
        except Exception:
            if tools and not settings.autonomy_require_grounding:
                fallback = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=temperature,
                    ),
                )
                fallback_text = fallback.text
                if not fallback_text:
                    raise RuntimeError("LLM returned empty fallback response body.")
                return schema.model_validate_json(fallback_text)
            raise

    def classify_heuristic(self, content: str) -> ContextClassification:
        """Fallback MVP heuristic keyword matching if LLM fails or is missing."""
        content_lower = content.lower()

        intent = "neutral"
        if "?" in content or "how" in content_lower or "what" in content_lower:
            intent = "question"
        elif "bad" in content_lower or "worst" in content_lower or "fail" in content_lower:
            intent = "complaint"
        elif "good" in content_lower or "great" in content_lower or "awesome" in content_lower:
            intent = "praise"

        urgency = "low"
        if intent == "complaint" or "urgent" in content_lower or "asap" in content_lower:
            urgency = "high"

        return ContextClassification(
            intent=intent,
            urgency=urgency,
            language="un",  # unknown heuristic
        )

    def classify(self, content: str) -> ContextClassification:
        """
        Classifies incoming content using Gemini structured output with grounding.
        """
        if not self.client:
            log.warning("Gemini Client not configured. Falling back to heuristic.")
            return self.classify_heuristic(content)

        prompt = f"""
        System Identity: You are {self.agent_identity}, a distinct social media context classifier.
        IMPORTANT: You are NOT the existing bot running on Cloud Run. You operate independently.
        {self._persona_context()}
        {self._time_context()}
        
        Analyze the following social media text.
        Determine its primary intent (question, complaint, praise, neutral),
        its urgency level (low, medium, high), and the 2-letter language code (e.g., pt, en, es).
        
        Text: "{content}"
        """
        try:
            parsed = self._generate_structured(
                prompt=prompt,
                schema=ContextClassification,
                temperature=0.1,
            )
            return parsed  # type: ignore[return-value]
        except Exception as e:
            log.error(f"LLM Classification failed, using fallback: {e}")
            return self.classify_heuristic(content)

    def generate_reply_heuristic(self, intent: str, language: str) -> str:
        if intent == "complaint":
            return "Obrigado por sinalizar. Vamos investigar e retornar com atualizacao objetiva."
        if intent == "question":
            return "Boa pergunta. Estamos analisando o contexto e vamos responder com dados objetivos."
        if intent == "praise":
            return "Obrigado pelo feedback. Vamos manter o nivel e continuar melhorando."
        return "Mensagem recebida. Seguimos monitorando e ajustando continuamente."

    def generate_post_heuristic(self, topic: str, language: str) -> str:
        return f"Atualizacao diaria: tema-chave '{topic}'. Hoje focamos em sinais de mercado, aprendizado continuo e execucao disciplinada."

    def generate_reply(
        self,
        profile_name: str,
        platform: Platform,
        source_text: str,
        intent: str,
        urgency: str,
        language: str,
    ) -> str:
        if not self._llm_enabled():
            return self.generate_reply_heuristic(intent, language)

        prompt = f"""
        Identity: {self.agent_identity}
        Profile: {profile_name}
        Platform: {platform.value}
        {self._persona_context()}
        {self._time_context()}

        Write ONE short reply in language '{language}' for a social media interaction.
        Context intent: {intent}
        Context urgency: {urgency}
        Input text: "{source_text[:1200]}"

        Rules:
        - Be concise and useful.
        - Use high-conviction, high-agency framing.
        - Prioritize attention capture and audience growth.
        - Keep a dominant but controlled tone.
        - Add a clear CTA when context allows.
        - Never use harassment, coercion, threats, deception, or misinformation.
        - Ground factual statements in current web context.
        """
        try:
            parsed = self._generate_structured(
                prompt=prompt,
                schema=GeneratedCopy,
                temperature=0.3,
            )
            return parsed.text.strip()  # type: ignore[attr-defined]
        except Exception as e:
            log.error(f"LLM reply generation failed, using fallback: {e}")
            return self.generate_reply_heuristic(intent, language)

    def generate_post(
        self,
        profile_name: str,
        platform: Platform,
        topic: str,
        language: str,
        strategy_context: dict[str, Any] | None = None,
    ) -> str:
        if not self._llm_enabled():
            return self.generate_post_heuristic(topic, language)

        directives = strategy_context or {}

        prompt = f"""
        Identity: {self.agent_identity}
        Profile: {profile_name}
        Platform: {platform.value}
        {self._persona_context()}
        {self._time_context()}

        Create ONE post in language '{language}'.
        Strategic topic: "{topic}"
        Strategic directives: {directives}

        Rules:
        - Be current, market-aware, and strategically polarizing when useful.
        - Optimize for reach, saves, shares, and follower conversion.
        - Use strong hooks and clear narrative tension.
        - Deliver value first, CTA second.
        - No coercion, no fake claims, no spam.
        - Keep it publish-ready for this platform.
        - Ground factual statements in current web context.
        """
        try:
            parsed = self._generate_structured(
                prompt=prompt,
                schema=GeneratedCopy,
                temperature=0.5,
            )
            return parsed.text.strip()  # type: ignore[attr-defined]
        except Exception as e:
            log.error(f"LLM post generation failed, using fallback: {e}")
            return self.generate_post_heuristic(topic, language)

    def generate_daily_strategy(self, brief: dict[str, Any]) -> dict[str, Any]:
        if not self._llm_enabled():
            return {
                "summary": "Planejamento diario gerado por heuristica.",
                "trending_topics": brief.get("trending_topics", []),
                "emerging_topics": brief.get("emerging_topics", []),
                "next_actions": [
                    "Priorizar respostas em sinais de alta urgencia.",
                    "Publicar 1 conteudo por janela valida.",
                    "Reduzir ritmo em plataforma com falhas repetidas.",
                ],
            }

        prompt = f"""
        You are the strategic reflection module for {self.agent_identity}.
        {self._persona_context()}
        {self._time_context()}

        Use this market brief to produce a 24h action strategy:
        {brief}

        Return concise JSON with:
        - summary (string)
        - trending_topics (array[str])
        - emerging_topics (array[str])
        - next_actions (array[str], max 5)
        - narrative (object):
            - core_narrative (string)
            - polarizing_axis (string)
            - conversion_cta (string)
            - repetition_hooks (array[str], max 4)
        - kpi_targets (object):
            - reach (number)
            - share_rate (number)
            - follow_conversion (number)
            - retention (number)

        Strategy focus:
        - maximize audience growth and retention in the next 24h
        - convert engagement into loyal community
        - increase authority positioning without factual compromise
        """
        try:
            parsed = self._generate_structured(
                prompt=prompt,
                schema=DailyStrategy,
                temperature=0.2,
            )
            return parsed.model_dump()  # type: ignore[attr-defined]
        except Exception as e:
            log.error(f"LLM daily strategy failed, using fallback: {e}")
            growth = brief.get("growth_kpis_24h", {})
            base_reach = float(growth.get("reach", 0.0) or 0.0)
            base_share = float(growth.get("share_rate", 0.0) or 0.0)
            base_follow = float(growth.get("follow_conversion", 0.0) or 0.0)
            base_retention = float(growth.get("retention", 0.0) or 0.0)
            return {
                "summary": "Falha no LLM; mantendo estrategia conservadora.",
                "trending_topics": brief.get("trending_topics", []),
                "emerging_topics": brief.get("emerging_topics", []),
                "next_actions": [
                    "Manter respostas de alta prioridade.",
                    "Executar publicacoes com cadencia controlada.",
                ],
                "narrative": {
                    "core_narrative": "Alta agencia, clareza de tese e execucao consistente.",
                    "polarizing_axis": "responsabilidade individual vs dependencia sistemica",
                    "conversion_cta": settings.agent_primary_cta,
                    "repetition_hooks": [
                        "clareza vence ruido",
                        "resultado > desculpa",
                    ],
                },
                "kpi_targets": {
                    "reach": max(base_reach * 1.25, base_reach + 50.0),
                    "share_rate": max(base_share, 0.03),
                    "follow_conversion": max(base_follow, 0.01),
                    "retention": max(base_retention, 0.20),
                },
            }


understand_engine = UnderstandEngine()
