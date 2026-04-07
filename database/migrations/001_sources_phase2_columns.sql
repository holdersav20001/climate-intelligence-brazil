-- Migration 001: Add Phase 2 columns to sources table
SET search_path TO climate;

ALTER TABLE sources ADD COLUMN IF NOT EXISTS feed_type TEXT;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS credibility_tier TEXT;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS fetch_count INTEGER DEFAULT 0;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
