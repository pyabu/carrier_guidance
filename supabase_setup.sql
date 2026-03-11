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

-- ═══════════════════════════════════════════════════════════════
-- Users table
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    skills TEXT DEFAULT '',
    interests TEXT DEFAULT '',
    experience_level TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to users"
    ON users FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════
-- Saved Jobs table
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS saved_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, job_id)
);

ALTER TABLE saved_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to saved_jobs"
    ON saved_jobs FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_saved_jobs_user ON saved_jobs(user_id);

-- ═══════════════════════════════════════════════════════════════
-- Applications table
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    status TEXT DEFAULT 'applied',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, job_id)
);

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access to applications"
    ON applications FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
