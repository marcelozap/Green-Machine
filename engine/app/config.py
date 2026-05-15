from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Monorepo root: engine/app/config.py -> parents[2] == repository root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE = f"sqlite+aiosqlite:///{(_REPO_ROOT / 'data' / 'greenmachine.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GM_", env_file=".env", extra="ignore")

    # Default: single SQLite file under <repo>/data/ — no Docker or Postgres required.
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

    # Comma-separated browser origins (e.g. https://your-app.vercel.app) for CORS.
    cors_origins: str = ""

    # Nexus (XIV life domains) — same DB as GM_DATABASE_URL (SQLite or Postgres).
    nexus_volatility_low_below: float = Field(
        default=0.35,
        description="State-switcher: volatility_score below this ⇒ 'boring tape' if no 6/6 signal.",
    )
    xiv_voice_passphrase: str = Field(
        default="",
        description="POST /auth/voice-pass. Env: GM_XIV_VOICE_PASSPHRASE or XIV_VOICE_PASSPHRASE.",
    )

    @model_validator(mode="after")
    def _xiv_passphrase_fallback(self) -> "Settings":
        import os

        if self.xiv_voice_passphrase.strip():
            return self
        alt = os.getenv("XIV_VOICE_PASSPHRASE", "").strip()
        if alt:
            object.__setattr__(self, "xiv_voice_passphrase", alt)
        return self

    # Risk rail: path to realized_analysis.json rollup (absolute, or relative to repo root).
    realized_analysis_path: str = Field(
        default="data/realized_analysis.json",
        description="Env: GM_REALIZED_ANALYSIS_PATH. Absolute path or relative to repo root.",
    )
    # Daily hard-stop in USD (positive number = max loss before cockpit warns OVER).
    daily_loss_budget_usd: float = Field(
        default=500.0,
        description="Env: GM_DAILY_LOSS_BUDGET. Session P&L below negative this triggers OVER.",
    )

    # Phone / tunnel: set GM_COCKPIT_PASSWORD to require HTTP Basic Auth on the whole app.
    cockpit_user: str = Field(default="green", description="Basic auth username (default green).")
    cockpit_password: str = Field(
        default="",
        description="If non-empty, browser must send Basic auth (use with HTTPS tunnel).",
    )


settings = Settings()
