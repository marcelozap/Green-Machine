from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE = f"sqlite+aiosqlite:///{(_BACKEND_ROOT / 'data' / 'greenmachine.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GM_", env_file=".env", extra="ignore")

    # Default: single SQLite file under backend/data — no Docker or Postgres required.
    # Set GM_DATABASE_URL=postgresql+asyncpg://... when you use Timescale/Postgres.
    database_url: str = Field(default=_DEFAULT_SQLITE)
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
