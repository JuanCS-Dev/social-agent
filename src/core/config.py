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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
