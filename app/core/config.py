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

    # --- Database Configuration ---
    DATABASE_URL: str | None = None

    # --- Postgres (fallback if DATABASE_URL not provided) ---
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None

    # --- OpenAI / GPT (NEW) ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    REQUEST_MAX_TOKENS: int = 4000
    RESPONSE_MAX_TOKENS: int = 512

    # --- LLM Fallback Configuration ---
    ENABLE_LLM_FALLBACK: bool = False  # Disabled by default for cost optimization
    LLM_FALLBACK_TIMEOUT: int = 10      # Timeout for LLM API calls in seconds

    # --- Security ---
    BELLA_API_KEY: str | None = None
    ADMIN_USER: str | None = None
    ADMIN_PASS: str | None = None
    CSRF_SECRET: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None

    # --- Redis Session Storage ---
    REDIS_URL: str | None = None

    # --- Google Calendar Integration ---
    GOOGLE_CALENDAR_ENABLED: bool = False
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = None
    GOOGLE_CALENDAR_ID: str | None = None
    BUSINESS_EMAIL: str | None = None

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
    # SECURITY: Restrict CORS to known origins only. "*" allows any website!
    # For single customer: "https://yourdomain.com"
    # For development: "http://localhost:3000,http://localhost:8000,https://yourdomain.com"
    ALLOWED_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"  # comma-separated list

    # Sync URI (Alembic) - PostgreSQL and SQLite
    @property
    def sync_db_uri(self) -> str:
        if self.DATABASE_URL:
            # Convert async PostgreSQL URL to sync URL
            if "postgresql+asyncpg:" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("postgresql+asyncpg:", "postgresql:")
            # Convert async SQLite URL to sync URL for alembic
            if "sqlite+aiosqlite:" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
            return self.DATABASE_URL
        # Fallback to postgres config
        pwd = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Async URI (SQLAlchemy engine) - PostgreSQL only
    @property
    def async_db_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Fallback to postgres config
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
