-- GREEN MACHINE — Vault schema (runs on first Postgres init via docker-compose volume)
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS spy_options_history (
    ts TIMESTAMPTZ NOT NULL,
    underlying_price DOUBLE PRECISION NOT NULL,
    strike DOUBLE PRECISION NOT NULL,
    expiry DATE NOT NULL,
    option_type CHAR(1) NOT NULL CHECK (option_type IN ('C', 'P')),
    delta DOUBLE PRECISION,
    gamma DOUBLE PRECISION,
    theta DOUBLE PRECISION,
    vega DOUBLE PRECISION,
    iv DOUBLE PRECISION,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    volume BIGINT,
    open_interest BIGINT
);

SELECT create_hypertable(
    'spy_options_history',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_spy_options_expiry ON spy_options_history (expiry, ts DESC);
CREATE INDEX IF NOT EXISTS idx_spy_options_strike ON spy_options_history (strike, ts DESC);

COMMENT ON TABLE spy_options_history IS 'SPY options chain history — partitioned by ts (TimescaleDB)';

-- Market states for LLM / vector retrieval (embeddings stored externally or as vector ext later)
CREATE TABLE IF NOT EXISTS market_states (
    trade_date DATE PRIMARY KEY,
    vix_close DOUBLE PRECISION,
    spy_close DOUBLE PRECISION,
    rsi_14 DOUBLE PRECISION,
    macro_news_digest TEXT,
    trend_label TEXT
);

COMMENT ON TABLE market_states IS 'Daily regime features for similarity search / RAG';
