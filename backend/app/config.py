from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GM_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://green:green@localhost:5432/greenmachine"
    risk_free_annual: float = 0.04
    commission_per_contract: float = 0.0065
    max_drawdown_circuit_breaker: float = 0.5

    # LLM (optional — heuristic fallback when keys unset)
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "GM_OPENAI_API_KEY"),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "GM_ANTHROPIC_API_KEY"),
    )
    llm_provider: str = "openai"  # openai | anthropic
    llm_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-20241022"


settings = Settings()
