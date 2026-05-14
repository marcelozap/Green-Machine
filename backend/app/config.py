from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GM_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://green:green@localhost:5432/greenmachine"
    risk_free_annual: float = 0.04
    commission_per_contract: float = 0.0065
    max_drawdown_circuit_breaker: float = 0.5


settings = Settings()
