-- ═══════════════════════════════════════════════════════════════
-- Supabase table for persisting scraped job data across
-- Vercel cold starts (since /tmp is ephemeral).
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scraped_data (
    kind TEXT PRIMARY KEY,          -- 'jobs', 'tn_jobs', 'india_jobs'
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Allow the anon/service role to read/write
ALTER TABLE scraped_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to scraped_data"
    ON scraped_data
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_scraped_data_kind ON scraped_data(kind);
