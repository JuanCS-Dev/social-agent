from dataclasses import dataclass
from typing import Any

from src.core.contracts import Platform


@dataclass(frozen=True)
class NetworkProfile:
    platform: Platform
    profile_name: str
    tone: str
    mission: str
    content_pillars: tuple[str, ...]
    min_publish_interval_minutes: int
    primary_language: str = "pt"
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "profile_name": self.profile_name,
            "tone": self.tone,
            "mission": self.mission,
            "content_pillars": list(self.content_pillars),
            "min_publish_interval_minutes": self.min_publish_interval_minutes,
            "primary_language": self.primary_language,
            "enabled": self.enabled,
        }


class ProfileRegistry:
    def __init__(self, profiles: dict[Platform, NetworkProfile] | None = None):
        self._profiles = profiles or default_profiles()

    def get(self, platform: Platform) -> NetworkProfile:
        profile = self._profiles.get(platform)
        if not profile:
            raise KeyError(f"Profile for platform '{platform.value}' not found.")
        return profile

    def all_enabled(self) -> list[NetworkProfile]:
        return [profile for profile in self._profiles.values() if profile.enabled]

    def as_dict_list(self) -> list[dict[str, Any]]:
        return [profile.to_dict() for profile in self.all_enabled()]


def default_profiles() -> dict[Platform, NetworkProfile]:
    return {
        Platform.REDDIT: NetworkProfile(
            platform=Platform.REDDIT,
            profile_name="SocialAgent_Reddit",
            tone="analitico e direto",
            mission="Contribuir com discussoes tecnicas e captar feedback de comunidade.",
            content_pillars=("insights", "analise de tendencias", "respostas objetivas"),
            min_publish_interval_minutes=240,
        ),
        Platform.X: NetworkProfile(
            platform=Platform.X,
            profile_name="SocialAgent_X",
            tone="curto, posicionamento claro e factual",
            mission="Gerar alcance rapido e interagir em conversas de alta velocidade.",
            content_pillars=("threads curtas", "opinioes embasadas", "comentarios contextuais"),
            min_publish_interval_minutes=120,
        ),
        Platform.FACEBOOK: NetworkProfile(
            platform=Platform.FACEBOOK,
            profile_name="SocialAgent_Facebook",
            tone="didatico e comunitario",
            mission="Criar relacionamento e manter publico informado com consistencia.",
            content_pillars=("conteudo explicativo", "atualizacoes", "engajamento com comentarios"),
            min_publish_interval_minutes=300,
        ),
        Platform.INSTAGRAM: NetworkProfile(
            platform=Platform.INSTAGRAM,
            profile_name="SocialAgent_Instagram",
            tone="narrativo e visual-first",
            mission="Atrair audiencia por narrativas curtas e chamadas de interacao.",
            content_pillars=("stories textuais", "legendas de impacto", "micro-narrativas"),
            min_publish_interval_minutes=360,
        ),
    }


profile_registry = ProfileRegistry()
