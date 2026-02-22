from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reddit config
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_username: str = ""
    reddit_password: str = ""
    reddit_user_agent: str = "ByteSocialAgent/1.0.0"

    # X config
    x_bearer_token: str = ""
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_secret: str = ""
    x_execution_mode: str = "api"  # api | operator
    x_webhook_token: str = ""

    # Meta config
    meta_page_access_token: str = ""
    meta_ig_user_id: str = ""
    meta_app_secret: str = ""
    meta_verify_token: str = ""

    # Infrastructure
    database_url: str = "sqlite+aiosqlite:///./var/data/social_agent.db"

    # Policy
    environment: str = "production"

    # AI Context - Vertex AI
    gcp_project: str = "vertice-ai-42"
    gcp_location: str = "global"

    # Autonomy runtime
    autonomy_poll_seconds: int = 5
    autonomy_enable_proactive: bool = True
    autonomy_use_llm_generation: bool = True
    autonomy_max_proactive_actions_per_tick: int = 1
    autonomy_enable_grounding: bool = True
    autonomy_require_grounding: bool = True
    autonomy_default_language: str = "pt"
    instagram_default_image_url: str = ""
    operator_fallback_on_api_error: bool = True

    # Agent editorial setup (can be overridden via env vars)
    agent_goal: str = "Construir audiencia de alta lealdade e crescer alcance com conteudo de alta conviccao."
    agent_ideology: str = "Lideranca forte, responsabilidade individual, liberdade economica, disciplina e resultado."
    agent_moral_framework: str = "Sem coercao, sem assedio, sem desinformacao, sem manipulacao predatoria."
    agent_dominant_mode: bool = True
    agent_primary_cta: str = "Siga e ative notificacoes para acompanhar os proximos movimentos."
    agent_growth_kpi_priorities: str = "reach,share_rate,follow_conversion,retention"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
