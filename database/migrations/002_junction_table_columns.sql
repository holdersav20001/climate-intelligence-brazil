-- database/migrations/002_junction_table_columns.sql
-- Add metadata columns to junction/cross-reference tables used by Phase 2 db.py methods.

SET search_path TO climate;

-- article_tags: add tagged_by + created_at
ALTER TABLE article_tags ADD COLUMN IF NOT EXISTS tagged_by   TEXT;
ALTER TABLE article_tags ADD COLUMN IF NOT EXISTS created_at  TIMESTAMPTZ DEFAULT NOW();

-- article_countries: add confidence + tagged_by + created_at
ALTER TABLE article_countries ADD COLUMN IF NOT EXISTS confidence  FLOAT DEFAULT 0.7;
ALTER TABLE article_countries ADD COLUMN IF NOT EXISTS tagged_by   TEXT;
ALTER TABLE article_countries ADD COLUMN IF NOT EXISTS created_at  TIMESTAMPTZ DEFAULT NOW();

-- finding_articles: add relevance_note + created_at
ALTER TABLE finding_articles ADD COLUMN IF NOT EXISTS relevance_note TEXT;
ALTER TABLE finding_articles ADD COLUMN IF NOT EXISTS created_at     TIMESTAMPTZ DEFAULT NOW();

-- finding_contacts: add relevance_note + created_at
ALTER TABLE finding_contacts ADD COLUMN IF NOT EXISTS relevance_note TEXT;
ALTER TABLE finding_contacts ADD COLUMN IF NOT EXISTS created_at     TIMESTAMPTZ DEFAULT NOW();
