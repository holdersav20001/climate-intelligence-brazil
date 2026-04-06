PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    summary TEXT, source_name TEXT, domain TEXT, topic TEXT,
    significance REAL, verified INTEGER DEFAULT 0,
    sentiment_overall REAL, sentiment_environmental REAL, sentiment_economic REAL,
    sentiment_political REAL, sentiment_social REAL, sentiment_framing REAL,
    fetched_at TEXT NOT NULL, published_at TEXT, run_date TEXT NOT NULL,
    scout_run_id TEXT, analyst_run_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_articles_run_date ON articles(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_domain ON articles(domain);
CREATE INDEX IF NOT EXISTS idx_articles_significance ON articles(significance DESC);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
    organisation TEXT NOT NULL, organisation_type TEXT,
    decision_power INTEGER, ngo_access INTEGER DEFAULT 1,
    influence_score REAL, profile_url TEXT, contact_url TEXT, email TEXT,
    policies_owned TEXT, why_relevant TEXT, source_url TEXT,
    first_seen TEXT DEFAULT (datetime('now')),
    last_updated TEXT DEFAULT (datetime('now')), notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_contacts_power ON contacts(decision_power DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_score ON contacts(influence_score DESC);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY, paperclip_issue_id TEXT, agent TEXT NOT NULL,
    priority TEXT NOT NULL, category TEXT, title TEXT NOT NULL, body TEXT NOT NULL,
    source_url TEXT, source_name TEXT, action_required TEXT, deadline TEXT,
    coalition_opportunity INTEGER DEFAULT 0, evidence_value TEXT,
    fetched_at TEXT NOT NULL, run_date TEXT NOT NULL,
    status TEXT DEFAULT 'open', created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_findings_priority ON findings(priority);
CREATE INDEX IF NOT EXISTS idx_findings_run_date ON findings(run_date DESC);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT, url TEXT UNIQUE,
    owner TEXT, status TEXT, consultation_open INTEGER DEFAULT 0,
    consultation_deadline TEXT, relevance TEXT, ngo_position TEXT,
    last_hash TEXT, last_checked TEXT,
    first_seen TEXT DEFAULT (datetime('now')), created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_policies_status ON policies(status);
CREATE INDEX IF NOT EXISTS idx_policies_consult ON policies(consultation_open, consultation_deadline);

CREATE TABLE IF NOT EXISTS ngo_intel (
    id TEXT PRIMARY KEY, organisation TEXT NOT NULL,
    organisation_category TEXT NOT NULL, type TEXT, title TEXT NOT NULL,
    summary TEXT, significance REAL, coalition_opportunity INTEGER DEFAULT 0,
    evidence_value TEXT, counter_argument_needed INTEGER DEFAULT 0,
    url TEXT, fetched_at TEXT NOT NULL, run_date TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ngo_intel_category ON ngo_intel(organisation_category);
CREATE INDEX IF NOT EXISTS idx_ngo_intel_run_date ON ngo_intel(run_date DESC);

CREATE TABLE IF NOT EXISTS finance_deals (
    id TEXT PRIMARY KEY, institution TEXT NOT NULL, project_name TEXT,
    amount_usd REAL, amount_brl REAL, currency_note TEXT,
    deal_type TEXT, project_type TEXT, stage TEXT,
    intervention_window TEXT, priority TEXT,
    source_url TEXT, summary TEXT, recommended_action TEXT,
    fetched_at TEXT NOT NULL, run_date TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_finance_type ON finance_deals(deal_type);
CREATE INDEX IF NOT EXISTS idx_finance_run_date ON finance_deals(run_date DESC);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, subject TEXT,
    body TEXT NOT NULL, report_type TEXT, run_date TEXT NOT NULL,
    sent_at TEXT, email_status TEXT DEFAULT 'pending',
    recipients TEXT, recipient_count INTEGER DEFAULT 0,
    paperclip_issue TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reports_run_date ON reports(run_date DESC);

CREATE TABLE IF NOT EXISTS alert_hashes (
    url TEXT PRIMARY KEY, hash TEXT, last_checked TEXT,
    last_changed TEXT, check_count INTEGER DEFAULT 0, alert_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS run_log (
    id TEXT PRIMARY KEY, agent_name TEXT NOT NULL, agent_id TEXT,
    status TEXT, started_at TEXT, finished_at TEXT, duration_sec INTEGER,
    items_found INTEGER DEFAULT 0, items_created INTEGER DEFAULT 0,
    cost_usd REAL, notes TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_run_log_agent ON run_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_run_log_started ON run_log(started_at DESC);

CREATE TABLE IF NOT EXISTS seen_urls (
    url TEXT PRIMARY KEY, first_seen_by TEXT,
    first_seen_at TEXT DEFAULT (datetime('now'))
);
