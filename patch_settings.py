import re

with open("backend/app/config/settings.py", "r") as f:
    c = f.read()

# Replace pydantic imports to include AliasChoices
c = c.replace("from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator", 
              "from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator, AliasChoices")

# ModelProvider (collapse GEMINI)
c = re.sub(
    r'class ModelProvider\(StrEnum\):.*?HEURISTIC = "heuristic"',
    '''class ModelProvider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    MOCK = "mock"
    HEURISTIC = "heuristic"''',
    c, flags=re.DOTALL
)

# Replace primary_llm_provider and model
c = re.sub(
    r'primary_llm_provider: ModelProvider = Field\(\s*default=ModelProvider.OPENAI,\s*description="LLM provider to use.",\s*\)',
    '''primary_llm_provider: ModelProvider = Field(
        default=ModelProvider.GOOGLE,
        validation_alias=AliasChoices("PRIMARY_LLM_PROVIDER", "MODEL_PROVIDER"),
        description="LLM provider to use.",
    )''',
    c
)

c = re.sub(
    r'primary_llm_model: str = Field\(default="gpt-4o", description="Model identifier."\)',
    '''primary_llm_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("PRIMARY_LLM_MODEL", "MODEL_NAME"),
        description="Model identifier.",
    )''',
    c
)

# New settings
new_settings = """
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
    aura_trusted_hosts: list[str] = Field(default=["*"])
    aura_jwt_iss: str = Field(default="aura")
    aura_jwt_aud: str = Field(default="aura")
    aura_demo_password: str = Field(default="demo1234")
    aura_agent_run_heartbeat_seconds: int = Field(default=30)
"""

c = c.replace(
    '    aura_jwt_algorithm: str = Field(default="HS256")',
    new_settings + '\n    aura_jwt_algorithm: str = Field(default="HS256")'
)

# database_url_migrations
c = c.replace(
    '        return (\n            f"postgresql+psycopg2://{self.postgres_user}:{pwd}"\n            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"\n        )',
    '        return (\n            f"postgresql+psycopg2://{self.postgres_user}:{pwd}"\n            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"\n        )'
)

c = c.replace('version: str = Field(default="0.1.0")', 'app_version: str = Field(default="0.1.0")')

with open("backend/app/config/settings.py", "w") as f:
    f.write(c)
