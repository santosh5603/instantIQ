from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class AutomationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database & Supabase
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    SUPABASE_URL: str = "https://dummy.supabase.co"
    SUPABASE_SERVICE_KEY: str = "dummy_service_key"
    SUPABASE_STORAGE_BUCKET: str = "reelise-resources"

    # Redis Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Notion
    NOTION_API_KEY: str = "secret_dummy_notion_key"
    NOTION_RESOURCES_DB_ID: str = "dummy_db_id"

    # Instagram automation config
    INSTAGRAM_USERNAME: str = "reelise_collector"
    INSTAGRAM_PASSWORD: str = "dummy_password"
    INSTAGRAM_SESSION_PATH: str = "session/instagram_session.json"
    INSTAGRAM_ADMIN_USERNAME: str = "its_me.santoshh"
    INSTAGRAPI_SESSION_PATH: str = "session/instagrapi_session.json"
    MAX_DAILY_FOLLOWS: int = 10
    FOLLOW_COOLDOWN_SECONDS: int = 300
    
    COMMENT_DELAY_MIN: int = 10
    COMMENT_DELAY_MAX: int = 30
    
    DM_POLL_INTERVAL_MIN: int = 45
    DM_POLL_INTERVAL_MAX: int = 90
    DM_MAX_WAIT_MINUTES: int = 30

    # RQ Dashboard
    RQ_DASHBOARD_USERNAME: str = "admin"
    RQ_DASHBOARD_PASSWORD: str = "admin"

settings = AutomationSettings()
