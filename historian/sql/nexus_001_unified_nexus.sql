-- Nexus unified_nexus (Postgres / Timescale / Supabase). Optional if you use SQLAlchemy create_all from the Engine app instead.

CREATE TABLE IF NOT EXISTS unified_nexus (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain VARCHAR(32) NOT NULL CHECK (domain IN (
    'trading_signals', 'work_tasks', 'physical_state', 'creative_mode'
  )),
  title VARCHAR(512) NOT NULL DEFAULT '',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  volatility_score DOUBLE PRECISION,
  signal_6_6 BOOLEAN NOT NULL DEFAULT false,
  market_boredom_status VARCHAR(64),
  pivot_suggestions JSONB,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_unified_nexus_domain ON unified_nexus (domain);
CREATE INDEX IF NOT EXISTS ix_unified_nexus_updated ON unified_nexus (updated_at DESC);
