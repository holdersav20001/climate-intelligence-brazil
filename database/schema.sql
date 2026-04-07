-- database/schema.sql
-- PostgreSQL schema for Climate Intelligence Platform
-- All tables in the `climate` schema.
-- Applied automatically by docker-entrypoint-initdb.d on first `docker compose up`.

SET search_path TO climate;

-- ── Time-series tables ─────────────────────────────────────────────────────
-- Note: partitioning removed for MVP simplicity; can be added in Phase 4+

CREATE TABLE IF NOT EXISTS articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    summary         TEXT,
    source_name     TEXT,
    domain          TEXT,
    topic           TEXT,
    significance    FLOAT,
    verified        BOOLEAN DEFAULT false,
    sentiment_overall       FLOAT,
    sentiment_environmental FLOAT,
    sentiment_economic      FLOAT,
    sentiment_political     FLOAT,
    sentiment_social        FLOAT,
    sentiment_framing       FLOAT,
    country_codes   TEXT[] DEFAULT '{}',
    tag_slugs       TEXT[] DEFAULT '{}',
    language        TEXT DEFAULT 'en',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ,
    run_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    scout_run_id    UUID,
    analyst_run_id  UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_run_date     ON articles(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_domain       ON articles(domain);
CREATE INDEX IF NOT EXISTS idx_articles_significance ON articles(significance DESC);
CREATE INDEX IF NOT EXISTS idx_articles_country      ON articles USING GIN(country_codes);
CREATE INDEX IF NOT EXISTS idx_articles_tags         ON articles USING GIN(tag_slugs);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_articles_fts ON articles
    USING GIN(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(summary,'')));

CREATE TABLE IF NOT EXISTS findings (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paperclip_issue_id   TEXT,
    agent                TEXT NOT NULL,
    priority             TEXT NOT NULL CHECK (priority IN ('CRITICAL','HIGH','COALITION','EVIDENCE','MEDIUM','LOW')),
    category             TEXT,
    title                TEXT NOT NULL,
    body                 TEXT NOT NULL,
    source_url           TEXT,
    source_name          TEXT,
    action_required      TEXT,
    deadline             DATE,
    coalition_opportunity BOOLEAN DEFAULT false,
    evidence_value       TEXT,
    country_codes        TEXT[] DEFAULT '{}',
    tag_slugs            TEXT[] DEFAULT '{}',
    status               TEXT DEFAULT 'open',
    fetched_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_date             DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_priority ON findings(priority);
CREATE INDEX IF NOT EXISTS idx_findings_run_date ON findings(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_findings_country  ON findings USING GIN(country_codes);

CREATE TABLE IF NOT EXISTS ngo_intel (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation             TEXT NOT NULL,
    organisation_category    TEXT NOT NULL,
    type                     TEXT,
    title                    TEXT NOT NULL,
    summary                  TEXT,
    significance             FLOAT,
    coalition_opportunity    BOOLEAN DEFAULT false,
    evidence_value           TEXT,
    counter_argument_needed  BOOLEAN DEFAULT false,
    url                      TEXT,
    fetched_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_date                 DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ngo_intel_category ON ngo_intel(organisation_category);
CREATE INDEX IF NOT EXISTS idx_ngo_intel_run_date ON ngo_intel(run_date DESC);

CREATE TABLE IF NOT EXISTS finance_deals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution         TEXT NOT NULL,
    project_name        TEXT,
    amount_usd          FLOAT,
    amount_brl          FLOAT,
    currency_note       TEXT,
    deal_type           TEXT,
    project_type        TEXT,
    stage               TEXT,
    intervention_window TEXT,
    priority            TEXT,
    source_url          TEXT,
    summary             TEXT,
    recommended_action  TEXT,
    country_codes       TEXT[] DEFAULT '{}',
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_date            DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finance_type     ON finance_deals(deal_type);
CREATE INDEX IF NOT EXISTS idx_finance_run_date ON finance_deals(run_date DESC);

CREATE TABLE IF NOT EXISTS reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    subject         TEXT,
    body            TEXT NOT NULL,
    report_type     TEXT,
    run_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    sent_at         TIMESTAMPTZ,
    email_status    TEXT DEFAULT 'pending',
    recipients      JSONB DEFAULT '[]',
    recipient_count INTEGER DEFAULT 0,
    paperclip_issue TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_run_date ON reports(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_type     ON reports(report_type);

CREATE TABLE IF NOT EXISTS run_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name      TEXT NOT NULL,
    agent_id        UUID,
    status          TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_sec    INTEGER,
    items_found     INTEGER DEFAULT 0,
    items_created   INTEGER DEFAULT 0,
    cost_usd        FLOAT,
    notes           TEXT,
    run_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_log_agent   ON run_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_run_log_started ON run_log(started_at DESC);

-- ── Reference tables (permanent, never archived) ───────────────────────────

CREATE TABLE IF NOT EXISTS countries (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT,
    active      BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS tags (
    slug        TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    label       TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    feed_url        TEXT,
    country_code    TEXT REFERENCES countries(code),
    sector          TEXT[] DEFAULT '{}',
    source_type     TEXT,
    language        TEXT DEFAULT 'en',
    fetch_frequency TEXT DEFAULT 'hourly',
    active          BOOLEAN DEFAULT true,
    status          TEXT DEFAULT 'active',
    reliability     FLOAT DEFAULT 0.8,
    last_fetched    TIMESTAMPTZ,
    last_successful TIMESTAMPTZ,
    fail_count      INTEGER DEFAULT 0,
    discovered_by   TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sources_active  ON sources(active, status);
CREATE INDEX IF NOT EXISTS idx_sources_country ON sources(country_code);
CREATE INDEX IF NOT EXISTS idx_sources_fetch   ON sources(last_fetched);

CREATE TABLE IF NOT EXISTS contacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    role                TEXT NOT NULL,
    organisation        TEXT NOT NULL,
    organisation_type   TEXT,
    decision_power      INTEGER CHECK (decision_power BETWEEN 1 AND 5),
    ngo_access          INTEGER DEFAULT 1 CHECK (ngo_access BETWEEN 1 AND 5),
    influence_score     FLOAT,
    profile_url         TEXT,
    contact_url         TEXT,
    email               TEXT,
    policies_owned      JSONB DEFAULT '[]',
    why_relevant        TEXT,
    source_url          TEXT,
    notes               TEXT,
    first_seen          TIMESTAMPTZ DEFAULT NOW(),
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, organisation)
);

CREATE INDEX IF NOT EXISTS idx_contacts_power ON contacts(decision_power DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_score ON contacts(influence_score DESC);

CREATE TABLE IF NOT EXISTS policies (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                   TEXT NOT NULL,
    body                    TEXT,
    url                     TEXT UNIQUE,
    owner                   TEXT,
    status                  TEXT,
    consultation_open       BOOLEAN DEFAULT false,
    consultation_deadline   DATE,
    relevance               TEXT,
    ngo_position            TEXT,
    last_hash               TEXT,
    last_checked            TIMESTAMPTZ,
    first_seen              TIMESTAMPTZ DEFAULT NOW(),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_status  ON policies(status);
CREATE INDEX IF NOT EXISTS idx_policies_consult ON policies(consultation_open, consultation_deadline);

CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    plan            TEXT DEFAULT 'starter' CHECK (plan IN ('starter','pro','enterprise')),
    country_limit   INTEGER DEFAULT 1,
    countries       TEXT[] DEFAULT '{}',
    active          BOOLEAN DEFAULT true,
    stripe_customer TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_hashes (
    url             TEXT PRIMARY KEY,
    hash            TEXT,
    last_checked    TIMESTAMPTZ,
    last_changed    TIMESTAMPTZ,
    check_count     INTEGER DEFAULT 0,
    alert_count     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seen_urls (
    url             TEXT PRIMARY KEY,
    first_seen_by   TEXT,
    first_seen_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── Junction tables ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS article_countries (
    article_id   UUID REFERENCES articles(id) ON DELETE CASCADE,
    country_code TEXT REFERENCES countries(code),
    PRIMARY KEY (article_id, country_code)
);

CREATE TABLE IF NOT EXISTS article_tags (
    article_id  UUID REFERENCES articles(id) ON DELETE CASCADE,
    tag_slug    TEXT REFERENCES tags(slug),
    confidence  FLOAT DEFAULT 0.7,
    PRIMARY KEY (article_id, tag_slug)
);

CREATE TABLE IF NOT EXISTS contact_countries (
    contact_id   UUID REFERENCES contacts(id) ON DELETE CASCADE,
    country_code TEXT REFERENCES countries(code),
    PRIMARY KEY (contact_id, country_code)
);

CREATE TABLE IF NOT EXISTS contact_tags (
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    tag_slug   TEXT REFERENCES tags(slug),
    PRIMARY KEY (contact_id, tag_slug)
);

CREATE TABLE IF NOT EXISTS finding_countries (
    finding_id   UUID REFERENCES findings(id) ON DELETE CASCADE,
    country_code TEXT REFERENCES countries(code),
    PRIMARY KEY (finding_id, country_code)
);

CREATE TABLE IF NOT EXISTS finding_tags (
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    tag_slug   TEXT REFERENCES tags(slug),
    PRIMARY KEY (finding_id, tag_slug)
);

-- ── Cross-reference tables ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS finding_articles (
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    PRIMARY KEY (finding_id, article_id)
);

CREATE TABLE IF NOT EXISTS finding_contacts (
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    PRIMARY KEY (finding_id, contact_id)
);

-- ── Tenant-specific tables ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contact_access (
    tenant_id  UUID REFERENCES tenants(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    ngo_access INTEGER DEFAULT 1 CHECK (ngo_access BETWEEN 1 AND 5),
    notes      TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, contact_id)
);

CREATE TABLE IF NOT EXISTS tenant_filters (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    countries TEXT[] DEFAULT '{}',
    tags      TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tenant_article_status (
    tenant_id  UUID REFERENCES tenants(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    status     TEXT DEFAULT 'unread' CHECK (status IN ('unread','read','saved','actioned')),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, article_id)
);
