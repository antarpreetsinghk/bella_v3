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

    # --- Security ---
    BELLA_API_KEY: str | None = None
    ADMIN_USER: str | None = None
    ADMIN_PASS: str | None = None
    CSRF_SECRET: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None

    # --- Redis Session Storage ---
    REDIS_URL: str | None = None

    # --- Monitoring & Logging ---
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    LOG_REQUESTS: bool = False
    LOG_RESPONSES: bool = False
    MAX_LOG_LENGTH: int = 200
    ERROR_CONTEXT_LINES: int = 3

    # --- Performance ---
    SLOW_REQUEST_THRESHOLD: float = 2.0
    ERROR_AGGREGATION_THRESHOLD: int = 10
    METRICS_RETENTION_SAMPLES: int = 1000

    # --- CloudWatch ---
    ENABLE_CLOUDWATCH_METRICS: bool = True
    CLOUDWATCH_NAMESPACE: str = "Bella/Application"

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

    # Monitoring helpers
    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

# Singleton
settings = Settings()
