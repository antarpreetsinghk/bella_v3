# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
import urllib.parse

class Settings(BaseSettings):
    # Read env from .env; ignore unknown keys so extra lines don't crash startup
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # <-- key fix: prevents "extra inputs are not permitted"
    )

    # --- Postgres ---
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # --- OpenAI / GPT (NEW) ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    REQUEST_MAX_TOKENS: int = 4000
    RESPONSE_MAX_TOKENS: int = 512

    # (Optional app knobs you can use later)
    ALLOWED_CORS_ORIGINS: str = "*"  # comma-separated list, e.g. "http://localhost:3000,https://your.app"

    # Sync URI (Alembic)
    @property
    def sync_db_uri(self) -> str:
        pwd = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Async URI (SQLAlchemy engine)
    @property
    def async_db_uri(self) -> str:
        pwd = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Helper for CORS lists (optional)
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_CORS_ORIGINS.split(",") if o.strip()]

# Singleton
settings = Settings()
