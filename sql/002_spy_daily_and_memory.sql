-- Daily SPY + regime series for backtests and "similar day" retrieval (no options chain required)
CREATE TABLE IF NOT EXISTS spy_daily (
    trade_date DATE PRIMARY KEY,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT,
    vix_close DOUBLE PRECISION,
    rsi_14 DOUBLE PRECISION,
    spy_return DOUBLE PRECISION,
    put_proxy_return DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_spy_daily_vix ON spy_daily (vix_close);

COMMENT ON TABLE spy_daily IS 'Daily SPY OHLCV + derived features; put_proxy_return optional until chain-linked';

-- Optional OpenAI-compatible embedding for semantic regime match (1536 dims typical)
ALTER TABLE market_states
    ADD COLUMN IF NOT EXISTS embedding JSONB;

COMMENT ON COLUMN market_states.embedding IS 'Optional JSON array of floats for cosine similarity vs query embedding';
