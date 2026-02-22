from collections import Counter, defaultdict
from typing import Any


class SocialIntelligence:
    _stopwords = {
        "a",
        "o",
        "e",
        "de",
        "do",
        "da",
        "the",
        "to",
        "for",
        "in",
        "on",
        "is",
        "it",
        "que",
        "com",
        "para",
        "uma",
        "um",
    }

    def _tokenize(self, text: str) -> list[str]:
        clean = "".join(ch if ch.isalnum() else " " for ch in text.lower())
        tokens = [token for token in clean.split() if len(token) >= 4 and token not in self._stopwords]
        return tokens

    def _as_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def estimate_growth_kpis(self, signals: list[dict[str, Any]]) -> dict[str, float]:
        impressions = 0.0
        shares = 0.0
        new_followers = 0.0
        returning_users = 0.0
        engaged_users = 0.0

        for signal in signals:
            metadata = signal.get("metadata") or {}
            impressions += self._as_float(metadata.get("impressions") or metadata.get("reach"))
            shares += self._as_float(metadata.get("shares") or metadata.get("reposts"))
            new_followers += self._as_float(metadata.get("new_followers") or metadata.get("follows"))
            returning_users += self._as_float(metadata.get("returning_users") or metadata.get("retained_users"))
            engaged_users += self._as_float(metadata.get("engaged_users") or metadata.get("engagements"))

        share_rate = (shares / impressions) if impressions > 0 else 0.0
        follow_conversion = (new_followers / impressions) if impressions > 0 else 0.0
        retention = (returning_users / engaged_users) if engaged_users > 0 else 0.0

        return {
            "reach": round(impressions, 3),
            "share_rate": round(share_rate, 6),
            "follow_conversion": round(follow_conversion, 6),
            "retention": round(retention, 6),
        }

    def dominant_narrative_axes(
        self,
        urgency_counter: Counter[str],
        intent_by_platform: dict[str, Counter[str]],
    ) -> list[str]:
        axes: list[str] = []
        if urgency_counter.get("high", 0) > 0:
            axes.append("urgencia por solucao concreta")

        for platform, intents in intent_by_platform.items():
            if intents.get("complaint", 0) >= intents.get("question", 0):
                axes.append(f"{platform}: resolver friccao com autoridade")
            else:
                axes.append(f"{platform}: liderar debate com tese clara")

        return axes[:6]

    def build_daily_brief(self, signals: list[dict[str, Any]]) -> dict[str, Any]:
        keyword_counter: Counter[str] = Counter()
        platform_counter: Counter[str] = Counter()
        urgency_counter: Counter[str] = Counter()
        intent_by_platform: dict[str, Counter[str]] = defaultdict(Counter)

        for signal in signals:
            platform = signal.get("platform", "unknown")
            intent = signal.get("intent", "neutral")
            urgency = signal.get("urgency", "low")
            metadata = signal.get("metadata") or {}
            text = str(metadata.get("text", ""))

            platform_counter[platform] += 1
            urgency_counter[urgency] += 1
            intent_by_platform[platform][intent] += 1
            keyword_counter.update(self._tokenize(text))

        trending_topics = [topic for topic, _ in keyword_counter.most_common(8)]
        emerging_topics = [topic for topic, count in keyword_counter.items() if count >= 2][:8]
        growth_kpis = self.estimate_growth_kpis(signals)
        dominant_axes = self.dominant_narrative_axes(urgency_counter, intent_by_platform)

        return {
            "signals_count": len(signals),
            "trending_topics": trending_topics,
            "emerging_topics": emerging_topics,
            "growth_kpis_24h": growth_kpis,
            "dominant_narrative_axes": dominant_axes,
            "platform_mix": dict(platform_counter),
            "urgency_mix": dict(urgency_counter),
            "intent_by_platform": {platform: dict(counter) for platform, counter in intent_by_platform.items()},
        }


social_intelligence = SocialIntelligence()
