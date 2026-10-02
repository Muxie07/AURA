"""
AURA Backend Configuration System.

Uses Pydantic Settings for environment variable binding with validation.
All configuration is sourced from environment variables or a .env file.
No secrets are ever hard-coded.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment identifiers."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    """Log output format."""

    JSON = "json"
    TEXT = "text"


class ModelProvider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    MOCK = "mock"
    HEURISTIC = "heuristic"


class EmbeddingProvider(StrEnum):
    """Supported embedding providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All fields have documented defaults suitable for local development.
    Production deployments MUST override secrets via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Prefix all AURA-specific settings with AURA_
        # Database and external service settings use their natural names
    )

    # =========================================================================
    # Application
    # =========================================================================
    aura_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment.",
    )
    aura_debug: bool = Field(
        default=False,
        description="Enable debug mode. Never use in production.",
    )
    aura_secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key-replace-in-production"),
        description="Application secret key for signing tokens. MUST be overridden in production.",
    )
    aura_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins.",
    )

    # =========================================================================
    # API Server
    # =========================================================================
    aura_api_host: str = Field(default="0.0.0.0", description="API bind host.")
    aura_api_port: int = Field(default=8000, ge=1, le=65535, description="API bind port.")
    aura_api_workers: int = Field(default=1, ge=1, description="Number of uvicorn workers.")
    aura_api_base_url: AnyHttpUrl = Field(
        default="http://localhost:8000",  # type: ignore[assignment]
        description="Public base URL of the API.",
    )

    # =========================================================================
    # Database
    # =========================================================================
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="aura")
    postgres_user: str = Field(default="aura")
    postgres_password: SecretStr = Field(default=SecretStr("aura-dev-password"))

    # Connection pool
    aura_db_pool_size: int = Field(default=10, ge=1, description="SQLAlchemy connection pool size.")
    aura_db_max_overflow: int = Field(default=20, ge=0, description="Max overflow connections.")
    aura_db_pool_timeout: int = Field(default=30, ge=1, description="Pool checkout timeout (s).")

    @property
    def database_url(self) -> str:
        """Async PostgreSQL DSN for SQLAlchemy.

        Uses the dedicated app role if explicitly configured,
        otherwise falls back to the owner credentials so a plain .env works.
        """
        user = self.aura_db_app_user if self.aura_db_app_user != "aura_app" else self.postgres_user
        pwd = (
            self.aura_db_app_password
            if self.aura_db_app_user != "aura_app"
            else self.postgres_password.get_secret_value()
        )
        return (
            f"postgresql+asyncpg://{user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_migrations(self) -> str:
        """Async PostgreSQL DSN for Alembic migrations (owner role)."""
        pwd = self.postgres_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Synchronous PostgreSQL DSN for owner role."""
        pwd = self.postgres_password.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # =========================================================================
    # Redis
    # =========================================================================
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr = Field(default=SecretStr(""))
    redis_db: int = Field(default=0, ge=0)

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        pwd = self.redis_password.get_secret_value()
        auth = f":{pwd}@" if pwd else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # =========================================================================
    # AI — LLM
    # =========================================================================
    primary_llm_provider: ModelProvider = Field(
        default=ModelProvider.GOOGLE,
        validation_alias=AliasChoices("PRIMARY_LLM_PROVIDER", "MODEL_PROVIDER"),
        description="LLM provider to use.",
    )
    primary_llm_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("PRIMARY_LLM_MODEL", "MODEL_NAME"),
        description="Model identifier.",
    )
    fallback_llm_provider: ModelProvider | None = Field(
        default=None, description="Optional fallback provider"
    )
    fallback_llm_model: str | None = Field(default=None, description="Optional fallback model name")
    model_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature.",
    )
    model_max_tokens: int = Field(
        default=4096,
        ge=1,
        description="Maximum tokens to generate.",
    )
    llm_timeout: int = Field(
        default=60,
        ge=1,
        description="Timeout for LLM API requests in seconds.",
    )
    llm_retry_max: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries for transient LLM errors.",
    )
    llm_retry_delay: float = Field(
        default=2.0,
        ge=0.1,
        description="Initial delay between retries in seconds.",
    )

    # Phase 6: Intelligent Model Routing
    fast_model: str = Field(default="gemini-1.5-flash")
    reasoning_model: str = Field(default="gemini-1.5-pro")
    long_context_model: str = Field(default="gemini-1.5-pro")

    # Phase 6: Limits
    max_replan_attempts: int = Field(default=2, ge=0)
    eval_mode: bool = Field(default=False, description="Deterministic mode for evals")
    max_tool_calls: int = Field(default=10, ge=1)
    max_model_fallbacks: int = Field(default=1, ge=0)

    # =========================================================================
    # AI — Embeddings
    # =========================================================================
    embedding_provider: EmbeddingProvider = Field(default=EmbeddingProvider.OPENAI)
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536, ge=1)

    # =========================================================================
    # API Keys (SecretStr prevents accidental logging)
    # =========================================================================
    openai_api_key: SecretStr | None = Field(default=None)
    anthropic_api_key: SecretStr | None = Field(default=None)
    google_ai_api_key: SecretStr | None = Field(default=None)

    # =========================================================================
    # Security / JWT
    # =========================================================================

    # =========================================================================
    # Phase 1: New Settings
    # =========================================================================
    aura_run_migrations_on_startup: bool = Field(default=True)
    mcp_server_url: AnyHttpUrl | None = Field(default=None)
    mcp_enabled: bool = Field(default=False)
    aura_rls_enabled: bool = Field(default=False)
    aura_db_app_user: str = Field(default="aura_app")
    aura_db_app_password: str = Field(default="aura_app_password")
    aura_sentry_dsn: AnyHttpUrl | None = Field(default=None)
    aura_daily_org_budget_usd: float = Field(default=10.0)
    aura_max_request_bytes: int = Field(default=10485760)  # 10MB
    aura_trusted_hosts: list[str] = Field(default=["localhost", "127.0.0.1", "backend", "api", "testserver"])
    aura_jwt_iss: str = Field(default="aura")
    aura_jwt_aud: str = Field(default="aura")
    aura_demo_password: str = Field(default="demo1234")
    aura_agent_run_heartbeat_seconds: int = Field(default=30)

    aura_jwt_algorithm: str = Field(default="HS256")
    aura_jwt_access_token_expire_minutes: int = Field(default=60, ge=1)
    aura_jwt_refresh_token_expire_days: int = Field(default=7, ge=1)
    aura_internal_api_key: SecretStr = Field(
        default=SecretStr("dev-internal-key-replace-in-production"),
    )

    # =========================================================================
    # Observability
    # =========================================================================
    aura_log_level: str = Field(default="INFO")
    aura_log_format: LogFormat = Field(default=LogFormat.JSON)

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    aura_rate_limit_requests: int = Field(default=100, ge=1)
    aura_rate_limit_window_seconds: int = Field(default=60, ge=1)

    # =========================================================================
    # Agent
    # =========================================================================
    aura_agent_max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum agent loop iterations before forced stop.",
    )
    aura_agent_timeout_seconds: int = Field(
        default=120,
        ge=10,
        description="Hard timeout for a single agent run (seconds).",
    )
    aura_agent_enable_human_approval: bool = Field(
        default=True,
        description="Whether approval workflows are enforced.",
    )

    # =========================================================================
    # RAG
    # =========================================================================
    aura_rag_chunk_size: int = Field(default=512, ge=64)
    aura_rag_chunk_overlap: int = Field(default=64, ge=0)
    aura_rag_top_k: int = Field(default=5, ge=1, le=100)
    aura_rag_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("aura_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"Invalid log level '{v}'. Must be one of: {valid}")
        return upper

    @model_validator(mode="after")
    def validate_embeddings(self) -> Settings:
        """Validate embedding provider and models."""
        # Simple validation: if we're using OpenAI, we need an API key
        if self.embedding_provider == EmbeddingProvider.OPENAI and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
        if self.embedding_provider == EmbeddingProvider.GOOGLE and not self.google_ai_api_key:
            raise ValueError("GOOGLE_AI_API_KEY required for Google embeddings")
        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Enforce stronger validation in production environments."""
        if self.aura_env in (Environment.PRODUCTION, Environment.STAGING):
            # Check secret key
            secret_key = self.aura_secret_key.get_secret_value()
            if secret_key == "dev-secret-key-replace-in-production" or len(secret_key) < 32:
                raise ValueError("AURA_SECRET_KEY must be a strong key in production/staging.")

            # Check internal API key
            internal_key = self.aura_internal_api_key.get_secret_value()
            if internal_key == "dev-internal-key-replace-in-production":
                raise ValueError("AURA_INTERNAL_API_KEY must be set in production.")
            if internal_key == secret_key:
                raise ValueError("AURA_INTERNAL_API_KEY and AURA_SECRET_KEY must differ.")

            # DB/Redis passwords
            if len(self.postgres_password.get_secret_value()) < 8:
                raise ValueError("postgres_password is too weak for production.")
            if not self.redis_password.get_secret_value():
                raise ValueError("redis_password cannot be empty in production.")

            # Security flags
            if self.aura_debug:
                raise ValueError("AURA_DEBUG must be false in production.")
            if "*" in self.aura_trusted_hosts or "localhost" in self.aura_trusted_hosts:
                raise ValueError("AURA_TRUSTED_HOSTS: must not contain wildcards or localhost in prod.")
            if not str(self.aura_api_base_url).startswith("https"):
                raise ValueError("AURA_API_BASE_URL: must use https in production.")
            if self.aura_log_format != LogFormat.JSON:
                raise ValueError("aura_log_format must be JSON in production.")

            # Primary provider check
            if self.primary_llm_provider == ModelProvider.GOOGLE and not self.google_ai_api_key:
                raise ValueError("Google AI API Key required.")
            if self.primary_llm_provider == ModelProvider.OPENAI and not self.openai_api_key:
                raise ValueError("OpenAI API Key required.")

        return self

    @property
    def is_production(self) -> bool:
        return self.aura_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.aura_env == Environment.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the application settings singleton.

    Uses lru_cache to ensure settings are loaded once and reused.
    In tests, invalidate the cache with get_settings.cache_clear().
    """
    return Settings()
