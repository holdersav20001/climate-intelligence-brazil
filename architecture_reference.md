# Climate Intelligence Platform — Architecture Reference
## For Claude Code / Developer Reference
**Version 1.2 · April 2026**

This document is the text equivalent of the architecture diagram. It describes every layer, every component, every connection, and every data flow in plain text so it can be read and actioned by Claude Code, developers, and CI tooling.

---

## Overview — 7 Layers

```
INGESTION     →  Sources table  →  AGENT LAYER  →  PROCESSING (Claude API)
     ↓
STORAGE (PostgreSQL + Redis + pgvector)
     ↓
API LAYER (FastAPI)
     ↓
FRONTEND (React)
     ↓
DELIVERY (Reports + Email)
     ↓
TENANTS (Stripe + Auth)
```

Everything from Storage downward runs inside a single **Docker Compose stack**.
Everything above Storage (ingestion sources) is external.

---

## Layer 1 — Ingestion (External Sources)

Five source types feed into the platform. All are free. All are fetched by Scout Retrieval from the `sources` table.

### 1.1 GDELT DOC API
- URL pattern: `https://api.gdeltproject.org/api/v2/doc/doc?query=brazil+energy&mode=artlist&maxrecords=25&format=json&timespan=24h`
- Frequency: every 15 minutes (most frequent source)
- Coverage: 100+ languages, machine-translated to English via `trans=googtrans`
- Value: single query covers thousands of global sources simultaneously
- Feeds into: Scout Retrieval → articles table

### 1.2 RSS Feeds (18 specialist publications)
Full list with confirmed RSS URLs:

| Publication | RSS URL | Sector | Region |
|---|---|---|---|
| Recharge News | services.rechargenews.com/app/rss | wind + solar | global |
| PV Magazine (global) | pv-magazine.com/feed | solar | global |
| PV Magazine Brasil | pv-magazine.com.br/feed | solar | Brazil (PT) |
| PV Tech | pvtech.org/feed | solar finance | global |
| Renewables Now | renewablesnow.com/feed | all renewables | global |
| Windpower Monthly | windpowermonthly.com/rss | wind | global |
| Energy Storage News | energy-storage.news/feed | storage / H2 | global |
| CleanTechnica | cleantechnica.com/feed | all clean energy | global |
| Carbon Brief | carbonbrief.org/feed | policy | global |
| Ember Energy | ember-energy.org/feed | electricity data | global |
| Clean Energy Wire | cleanenergywire.org/feed | transition | Europe |
| Euractiv Energy | euractiv.com/sections/energy/feed | EU policy | Europe |
| H2 View | h2-view.com/feed | hydrogen | global |
| Energía Estratégica | energiastrategica.com/feed | all renewables | South America (ES) |
| Energy Monitor | energymonitor.ai/feed | data-driven | global |
| RenewEconomy | reneweconomy.com.au/feed | all renewables | Asia-Pacific |
| China Dialogue Energy | dialogue.earth/en/energy/feed | transition | China |
| Renewable Energy World | renewableenergyworld.com/feed | all renewables | global |

- Frequency: hourly
- Feeds into: Scout Retrieval → articles table

### 1.3 Yahoo Finance RSS (Ticker feeds)
- URL pattern: `https://finance.yahoo.com/rss/headline?s={TICKER}`
- Key tickers: PBR (Petrobras), VALE, SHEL (Shell), TTE (TotalEnergies), BP, ENEL
- Energy sector feed: `https://finance.yahoo.com/sectors/energy/`
- Frequency: hourly
- Feeds into: Scout Retrieval → articles table

### 1.4 Google News RSS (Keyword search)
- URL pattern: `https://news.google.com/rss/search?q={QUERY}&hl={LANG}&gl={COUNTRY}&ceid={COUNTRY}:{LANG}`
- Examples:
  - `?q=brazil+energy&hl=en-US&gl=US` — English Brazil energy
  - `?q=energia+renovavel+brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419` — Portuguese Brazil renewables
  - `?q=energiewende&hl=de&gl=DE` — German Energiewende (for Europe expansion)
- Adding a new country: change `gl` and `hl` parameters only
- Frequency: hourly
- Feeds into: Scout Retrieval → articles table

### 1.5 Government Hash Monitor
- Method: fetch page HTML, compute SHA256 hash, compare to stored hash in `alert_hashes` table
- Priority URLs monitored (every 4 hours):
  - `https://www.gov.br/mme/pt-br/assuntos/noticias` (MME press office)
  - `https://www.aneel.gov.br/sala-de-imprensa` (ANEEL announcements)
  - `https://www.anp.gov.br/noticias` (ANP news)
  - `https://www.petrobras.com.br/fatos-e-dados` (Petrobras investor relations)
  - `https://www.ibama.gov.br/noticias` (IBAMA environmental)
- On change detected: Alert agent creates CRITICAL finding immediately
- Feeds into: alert_hashes table → Alert agent → findings table

### 1.6 Reddit RSS
- URLs:
  - `https://www.reddit.com/r/energy/.rss`
  - `https://www.reddit.com/r/brasil/.rss`
  - `https://www.reddit.com/r/climate/.rss`
  - `https://www.reddit.com/search.rss?q=brazil+energy&sort=new`
- Frequency: hourly
- Feeds into: Scout Retrieval → articles table

### 1.7 Nitter RSS (official accounts, X/Twitter)
- URL pattern: `https://nitter.privacydev.net/{ACCOUNT}/rss`
- Key accounts: mme_gov, aneel_gov, anp_gov (official Brazilian government)
- Frequency: hourly
- Note: Nitter instance availability varies — Scout Retrieval handles failures gracefully

---

## Layer 2 — Sources Table (PostgreSQL)

The central registry of all monitored sources. **Scout Retrieval reads from this table — no sources are hardcoded in agent instructions.**

```sql
CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    feed_url        TEXT,
    country_code    TEXT REFERENCES countries(code),
    sector          TEXT[],           -- ["solar", "wind"] etc
    source_type     TEXT,             -- "rss" | "gdelt" | "hash_monitor" | "social"
    language        TEXT DEFAULT 'en',
    fetch_frequency TEXT DEFAULT 'hourly', -- "realtime" | "hourly" | "daily" | "4hourly"
    active          BOOLEAN DEFAULT true,
    status          TEXT DEFAULT 'active', -- "active" | "candidate" | "rejected"
    reliability     FLOAT DEFAULT 0.8,  -- 0-1, updated by Verifier feedback
    last_fetched    TIMESTAMPTZ,
    last_successful TIMESTAMPTZ,
    fail_count      INTEGER DEFAULT 0,
    discovered_by   TEXT,             -- "scout_discovery" | "manual" | "link_extraction"
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**Adding a new country = INSERT rows into this table. No agent code changes required.**

---

## Layer 3 — Agent Layer (Paperclip + Claude Haiku 4.5)

14 agents running inside the `paperclip` Docker container. All write to PostgreSQL via `db.py`. All are country-agnostic — they tag everything and let tenant filters handle the subscriber view.

### Docker container: `paperclip`
- Base image: `node:20`
- Also installs: `hermes-paperclip-adapter` (inactive until Phase 2)
- Volume: `paperclip_workspace:/workspace`
- Environment vars: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `WORKSPACE_PATH`
- Exposes: port 3100

### Agent IDs and schedules

| Agent | Paperclip ID | Schedule | Hermes |
|---|---|---|---|
| Orchestrator | 026e19f1-d44c-49f9-85b1-94031444c71e | every 1h | No |
| Scout Discovery | (to be created in Phase 2) | daily | Yes — Phase 2 |
| Scout Retrieval | 3bb1d3f5-078d-426b-9b1b-4fd4687bba1d | every 1h | No |
| Translator | 5b947d5e-dd85-4b45-a6de-382cc7f259d7 | on demand | No |
| Analyst | 24694c2f-cdeb-4b24-a641-de88969666a0 | on demand | Yes — Phase 2 |
| Verifier | 512f07a7-9d19-4c54-9a12-a3fa198fc190 | on demand | No |
| Policy Tracker | 6698ab9e-4598-4d23-a947-44cdda66d9e6 | daily | No |
| Contact Mapper | 059d195f-59d0-4cf7-9676-1c019380e742 | every 1h | Yes — Phase 2 |
| Reporter | c6d80362-bfa6-44fa-acf0-ba853538463e | daily + on demand | No |
| Alert | 4e539647-7219-4382-bba5-649b46c6db40 | every 4h | No |
| Parliamentary Monitor | 4aed1e77-e280-4ffb-97f6-70a9f2a3d7ce | daily | No |
| NGO Monitor | 16f6833e-bb2b-4d5a-bfbf-fdca33d766ef | daily | No |
| Finance Monitor | 31672a00-637d-487a-b0ac-774ad7866a9c | daily | No |
| COP30 Monitor | 19e2eafc-f473-4f2f-a65a-6a58b3657690 | daily | No |
| Consultation Writer | bc3bbaf6-b290-4b0f-9ef3-befe87fd9d37 | on demand | No |

### Agent data flows

```
External sources
    ↓
Scout Retrieval (reads sources table, fetches feeds)
    → articles table (raw)
    → seen_urls table (dedup)
    ↓
Translator (Portuguese/Spanish → English)
    → articles table (updates body/title)
    ↓
Analyst (sentiment, entities, significance, tags)
    → articles table (updates all analysis fields)
    → article_tags table
    → article_countries table
    ↓
Verifier (checks source URL, confirms facts)
    → articles table (updates verified flag)

Scout Discovery (daily)
    → sources table (status='candidate')
    [human approves via React Sources tab]

Policy Tracker (daily)
    → policies table
    → findings table

Contact Mapper (hourly)
    → contacts table
    → contact_tags table
    → contact_countries table

Parliamentary Monitor (daily)
    → findings table

NGO Monitor (daily)
    → ngo_intel table
    → findings table

Finance Monitor (daily)
    → finance_deals table
    → findings table

COP30 Monitor (daily)
    → findings table

Alert (every 4h)
    → alert_hashes table
    → findings table (CRITICAL priority)
    → Redis pub/sub (immediate push to frontend)

Reporter (daily + on demand)
    → reports table
    → send_email.py (SMTP delivery)

Consultation Writer (on demand)
    → reports table (submission drafts)

Orchestrator (every 1h)
    → run_log table
    → coordinates all agent sequences
```

### Hermes integration (Phase 2)

Three agents get Hermes persistent memory via `hermes-paperclip-adapter`:

**Scout Discovery**
- What Hermes remembers: which domains were evaluated and rejected, why certain link patterns are noise, which source types work best per country
- Activation: Phase 2 start — run for 2 weeks, measure source quality vs baseline before expanding

**Analyst**
- What Hermes remembers: tagging accuracy feedback, which tag combinations proved wrong after Verifier checks, confidence score calibration
- Activation: Phase 2 end — only if Scout Discovery shows measurable improvement

**Contact Mapper**
- What Hermes remembers: relationship context, which contacts are becoming more/less active, nuanced influence signals beyond DB fields
- Activation: Phase 2 end

**All other agents: no Hermes.** Structured DB outputs already capture their relevant state.

### db.py — agent database interface

All agents interact with PostgreSQL via `db.py`. Never raw SQL in agent instructions.

```bash
# CLI usage (in agent instructions)
python3 $WORKSPACE/db.py insert-article '{"url":"...","title":"...","domain":"...","significance":0.8}'
python3 $WORKSPACE/db.py insert-finding '{"agent":"finance_monitor","priority":"HIGH","title":"...","body":"..."}'
python3 $WORKSPACE/db.py upsert-contact '{"name":"...","role":"...","organisation":"..."}'
python3 $WORKSPACE/db.py insert-ngo-intel '{"organisation":"iCS","title":"...","summary":"..."}'
python3 $WORKSPACE/db.py insert-finance-deal '{"institution":"BNDES","priority":"HIGH","summary":"..."}'
python3 $WORKSPACE/db.py insert-report '{"title":"...","body":"...","report_type":"daily_digest"}'
python3 $WORKSPACE/db.py mark-url-seen "https://..." "scout"
python3 $WORKSPACE/db.py is-url-seen "https://..."    # returns "true" or "false"
python3 $WORKSPACE/db.py log-run '{"agent_name":"scout","status":"succeeded","items_found":8}'
python3 $WORKSPACE/db.py stats                         # row counts for all tables
python3 $WORKSPACE/db.py query "SELECT * FROM articles ORDER BY run_date DESC LIMIT 5"
```

---

## Layer 4 — Processing (Claude API)

The Analyst agent calls the Claude API for every article that passes Scout Retrieval and Translator. This is the intelligence layer.

### What Claude does per article
1. **6-dimension sentiment scoring** — overall, environmental, economic, political, social, framing (each -1.0 to +1.0)
2. **Entity extraction** — companies, regions, projects, people mentioned
3. **Significance scoring** — 0.0 to 1.0 based on relevance to energy transition
4. **Country tagging** — which countries does this article relate to (array)
5. **Topic tagging** — which tag slugs from the taxonomy apply (array with confidence 0–1)
6. **Summary generation** — 2–3 sentence summary for the articles table

### Claude model
- Model: `claude-haiku-4-5` (cost-efficient for high-volume article processing)
- Called via: Paperclip heartbeat system (agent instructions call Claude automatically)
- API key: injected via `ANTHROPIC_API_KEY` environment variable in Docker

---

## Layer 5 — Storage (Docker services)

### 5.1 PostgreSQL 16
- Docker image: `pgvector/pgvector:pg16` (includes pgvector extension pre-installed)
- Docker service name: `postgres`
- Internal hostname: `postgres` (other containers connect via `postgres:5432`)
- Volume: `postgres_data:/var/lib/postgresql/data`
- Schema auto-applied: `./database/schema.sql` → `/docker-entrypoint-initdb.d/01_schema.sql`
- Seed data auto-applied: `./database/seed.sql` → `/docker-entrypoint-initdb.d/02_seed.sql`
- Partitioning: articles, findings, run_log, reports, ngo_intel, finance_deals partitioned by month
- Rolling window: 3 months live — old partitions dropped via scheduled job
- Reference tables (never archived): contacts, policies, sources, tenants, tags, countries

#### All 25 tables

**Time-series tables (partitioned by month):**
- `articles` — every story, 20+ fields including 6 sentiment dimensions
- `findings` — CRITICAL/HIGH/COALITION/EVIDENCE priority findings
- `ngo_intel` — NGO Monitor publications and reports
- `finance_deals` — fossil fuel and renewable financing deals
- `reports` — all Reporter outputs
- `run_log` — every agent heartbeat with duration and cost

**Reference tables (permanent):**
- `sources` — all monitored sources
- `tags` — tag taxonomy (sector, geography, actor_type, policy_stage, topic, urgency, company)
- `countries` — ISO country codes and regions
- `contacts` — global influence network
- `policies` — government policy documents with consultation windows
- `tenants` — subscriber accounts and plan details
- `alert_hashes` — URL hashes for change detection
- `seen_urls` — all URLs ever processed (deduplication)

**Junction tables:**
- `article_countries` — articles ↔ countries (many-to-many)
- `article_tags` — articles ↔ tags (with confidence score)
- `contact_countries` — contacts ↔ countries
- `contact_tags` — contacts ↔ topics/policies they own
- `finding_countries` — findings ↔ countries
- `finding_tags` — findings ↔ topics

**Cross-reference tables:**
- `finding_articles` — findings ↔ supporting articles (evidence links)
- `finding_contacts` — findings ↔ relevant contacts

**Tenant-specific tables:**
- `contact_access` — per-subscriber ngo_access scores
- `tenant_filters` — saved filter views per subscriber
- `tenant_article_status` — read/saved/actioned per article per subscriber

### 5.2 Redis 7
- Docker image: `redis:7-alpine`
- Docker service name: `redis`
- Internal hostname: `redis` (other containers connect via `redis:6379`)
- Volume: `redis_data:/data` (persistence enabled via `--appendonly yes`)
- Three uses only:
  1. **Alert pub/sub** — Alert agent publishes CRITICAL findings → React frontend subscribes via WebSocket → instant notification
  2. **BullMQ job queue** — worker container queues agent heartbeat jobs, prevents concurrent conflicts
  3. **Session cache** — subscriber filter preferences cached for fast dashboard load

### 5.3 pgvector (Phase 2)
- Not a separate service — it is an extension on the existing PostgreSQL container
- Enabled via: `pgvector/pgvector:pg16` Docker image (already includes it)
- Activation in Phase 2: `ALTER TABLE articles ADD COLUMN embedding vector(1536);`
- Embeddings generated: on article ingest via Claude embeddings API or OpenAI
- Query syntax: `SELECT * FROM articles ORDER BY embedding <=> $1 LIMIT 10`
- No Pinecone, Weaviate, or Qdrant required

---

## Layer 6 — API Layer (FastAPI)

### Docker container: `api`
- Base image: `python:3.12-slim`
- Docker service name: `api`
- Internal hostname: `api`
- External port: 8000
- Connects to: `postgres:5432`, `redis:6379`
- Environment vars: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ENVIRONMENT`

### Endpoints (Phase 1)

```
GET  /health                     Health check — returns {"status": "ok"}
POST /auth/login                 Returns JWT token
POST /auth/signup                Creates new tenant account

GET  /articles                   List articles (tenant filter applied)
GET  /articles/{id}              Single article with full sentiment data
GET  /findings                   List findings (priority filter, country filter)
GET  /findings/{id}              Single finding with linked articles + contacts
GET  /contacts                   List contacts (influence score sort)
GET  /contacts/{id}              Single contact with linked policies + findings
GET  /sources                    List sources (active + candidates)
POST /sources/{id}/approve       Approve candidate source
POST /sources/{id}/reject        Reject candidate source
GET  /reports                    List reports with delivery status
GET  /reports/{id}               Full report text
GET  /stats                      Dashboard metrics (row counts, today's activity)

WS   /ws/alerts                  WebSocket — Redis pub/sub stream for real-time alerts
```

### Tenant filtering (applied to ALL data endpoints)

Every request carries a JWT. The API extracts `tenant_id` from the JWT and applies:
```sql
JOIN article_countries ac ON a.id = ac.article_id
WHERE ac.country_code = ANY($tenant_countries)
  AND EXISTS (
    SELECT 1 FROM article_tags at
    WHERE at.article_id = a.id
    AND at.tag_slug = ANY($tenant_tags)  -- if tag filter set
  )
```

Tenants never see each other's data. Enforced at API layer, not at DB layer (Phase 1). Row-level security at DB layer in Phase 3.

### Rate limiting
- Starter: 100 requests/minute
- Pro: 500 requests/minute
- Enterprise: 2000 requests/minute + raw API key access

---

## Layer 7 — Frontend (React + TypeScript)

### Docker container: `frontend`
- Build: multi-stage — Node 20 build → nginx:alpine serve
- Docker service name: `frontend`
- External ports: 80 (HTTP), 443 (HTTPS via certbot)
- Environment vars: `VITE_API_URL`, `VITE_WS_URL`

### 6 tabs

**Tab 1: Dashboard**
- 4 metric cards: stories today, open findings, sentiment today, active sources
- Latest stories feed: title, source, significance badge, domain colour dot
- Top contacts: name, role, influence dots (1–5)
- All filterable by country and sector without page reload

**Tab 2: World Map**
- D3 GeoJSON — accurate country shapes
- Country circles: size = story count (last 24h), colour = sentiment
  - Red = negative trend (sentiment_overall < -0.2)
  - Amber = mixed (-0.2 to +0.2)
  - Green = positive (+0.2 and above)
  - Grey = no data in last 24h
- Click country: popup showing story count, top story title, sentiment, critical findings count, "View all" link
- Pulse animation: fires when Redis WebSocket delivers CRITICAL alert
- Time slider: drag to see any day in last 30 days
- Subscriber plan enforcement: Starter plan greys out non-subscribed countries

**Tab 3: Findings**
- Priority list with colour-coded left border
  - Red border = CRITICAL
  - Amber border = HIGH
  - Green border = COALITION
  - Blue border = EVIDENCE
- Filter bar: ALL / CRITICAL / HIGH / COALITION / EVIDENCE / FINANCE / COP30
- Click card: expands to full detail, source link, action button, related articles list
- Deadline countdown for time-sensitive findings

**Tab 4: Contacts**
- Split view: government contacts (left) + NGO alliance (right)
- Government contacts: sorted by influence score, decision_power dots
- NGO alliance: allied / monitor / opposition badges
- Click contact: full profile, linked policies, related findings
- ngo_access score: editable per subscriber (stored in contact_access table, tenant-specific)

**Tab 5: Sources**
- Active sources table: name, type, country, feed URL, reliability score, last_fetched, frequency
- Candidate queue: sources discovered by Scout Discovery, Approve/Reject buttons
- Add source form: manual entry
- Toggle active/inactive per source

**Tab 6: Reports**
- Archive list: title, type (daily_digest / brief / submission), date, email_status badge
- Click to read: full report rendered in markdown
- Resend button: re-triggers email delivery
- Download PDF: browser print to PDF
- Filter: All / Digests / Briefs / Submissions

### Real-time alerts
- WebSocket connection to `GET /ws/alerts`
- When Alert agent creates a CRITICAL finding, Redis pub/sub → WebSocket → React
- UI response: notification badge increments in header + toast popup with story title
- World map pulse animation fires for the relevant country circle

---

## Layer 8 — Delivery

### SMTP email
- Script: `workspace/send_email.py`
- Config: `workspace/smtp_config.json` (NOT in Git — real credentials in `.env`)
- Recipients: `workspace/mailing_list.json`
- Provider-agnostic: Gmail (`smtp.gmail.com:587`), Outlook (`smtp.office365.com:587`), any SMTP server
- Graceful degradation: report always saved to `pending_review/` first — email is best-effort
- Completion issue always created in Paperclip regardless of email status

### Report types
- `daily_digest` — auto-generated by Reporter every morning at 07:00
- `brief` — on-demand for specific stories or topics
- `submission` — policy consultation response drafted by Consultation Writer
- `compiled` — multi-finding summary for specific topic or event

---

## Layer 9 — Multi-Tenancy (Stripe + Auth)

### Authentication
- Provider: Supabase Auth or Auth0 (TBD in Phase 1)
- Method: JWT tokens, verified on every API request
- `tenant_id` extracted from JWT claims
- Applied to all data queries as filter

### Billing (Phase 4)
- Provider: Stripe
- Subscription plans:

| Plan | Price | country_limit | Features |
|---|---|---|---|
| Starter | £199/month | 1 | daily digest, 3-month data, email delivery |
| Pro | £499/month | 5 | + real-time alerts, contacts tab, findings tab |
| Enterprise | £1,499/month | unlimited | + API key access, raw data export, consultation writer |

- Plan limit enforcement: API layer checks `tenant.plan` and `tenant.country_limit` on every request
- Webhooks: Stripe → `/webhooks/stripe` → update `tenants.active` and `tenants.plan`

---

## Docker Compose — Service Summary

| Service | Image | Port | Connects to | Volume |
|---|---|---|---|---|
| `postgres` | pgvector/pgvector:pg16 | 5432 (internal) | — | postgres_data |
| `redis` | redis:7-alpine | 6379 (internal) | — | redis_data |
| `paperclip` | ./paperclip/Dockerfile | 3100 | postgres, redis | paperclip_workspace |
| `api` | ./api/Dockerfile | 8000 | postgres, redis | — |
| `frontend` | ./frontend/Dockerfile | 80, 443 | api | certbot_certs |
| `worker` | ./worker/Dockerfile | — | redis, postgres | — |

### Environment variables (all services read from `.env`)

```bash
POSTGRES_USER=climate_intel
POSTGRES_PASSWORD=<secret>
DATABASE_URL=postgresql://climate_intel:<secret>@postgres:5432/climate_intel
REDIS_URL=redis://redis:6379
CLAUDE_API_KEY=sk-ant-<secret>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASS=<app-password>
JWT_SECRET=<long-random-string>
STRIPE_SECRET_KEY=sk_live_<secret>
STRIPE_WEBHOOK_SECRET=whsec_<secret>
API_URL=https://api.yourdomain.com
WS_URL=wss://api.yourdomain.com
ENVIRONMENT=production
```

### Startup order (healthcheck-enforced)
1. `postgres` starts, healthcheck passes (`pg_isready`)
2. `redis` starts, healthcheck passes (`redis-cli ping`)
3. `paperclip` starts (depends on postgres + redis healthy)
4. `api` starts (depends on postgres healthy)
5. `worker` starts (depends on redis + postgres healthy)
6. `frontend` starts (depends on api)

---

## Repository Structure

```
climate-intelligence-brazil/
├── docker-compose.yml              # all 6 services
├── docker-compose.override.yml     # local dev: hot reload, expose postgres port
├── .env.example                    # committed — blank values
├── .env                            # NOT committed — real secrets
│
├── database/
│   ├── schema.sql                  # PostgreSQL schema (25 tables)
│   ├── seed.sql                    # tag taxonomy + country seed data
│   ├── db.py                       # database utility — agents use this
│   ├── migrate.py                  # SQLite → PostgreSQL migration
│   └── sync_from_paperclip.py     # backfill from Paperclip issue history
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app entry point
│       ├── auth.py                 # JWT verification middleware
│       ├── routes/
│       │   ├── articles.py
│       │   ├── findings.py
│       │   ├── contacts.py
│       │   ├── sources.py
│       │   ├── reports.py
│       │   └── stats.py
│       └── models/
│           └── schemas.py          # Pydantic models
│
├── frontend/
│   ├── Dockerfile                  # multi-stage: node build → nginx serve
│   ├── package.json
│   └── src/
│       ├── App.tsx                 # tab routing
│       ├── components/
│       │   ├── Dashboard.tsx
│       │   ├── WorldMap.tsx        # D3 GeoJSON
│       │   ├── Findings.tsx
│       │   ├── Contacts.tsx
│       │   ├── Sources.tsx
│       │   └── Reports.tsx
│       └── hooks/
│           └── useAlerts.ts        # Redis WebSocket hook
│
├── paperclip/
│   ├── Dockerfile                  # node:20, installs hermes-paperclip-adapter
│   └── workspace-templates/
│       ├── mailing_list.json
│       └── cop30_dates.json
│
├── worker/
│   ├── Dockerfile
│   └── queue.js                    # BullMQ heartbeat scheduler
│
├── nginx/
│   └── conf.d/
│       └── default.conf            # proxy: / → frontend, /api → api, /ws → api:8000/ws
│
├── agents/                         # all 14 agent instruction files
│   ├── orchestrator_AGENTS.md
│   ├── scout_discovery_AGENTS.md
│   ├── scout_retrieval_AGENTS.md
│   ├── translator_AGENTS.md
│   ├── analyst_AGENTS.md
│   ├── verifier_AGENTS.md
│   ├── policy_tracker_AGENTS.md
│   ├── contact_mapper_AGENTS.md
│   ├── reporter_AGENTS.md
│   ├── alert_AGENTS.md
│   ├── parliamentary_monitor_AGENTS.md
│   ├── ngo_monitor_AGENTS.md
│   ├── finance_monitor_AGENTS.md
│   ├── cop30_monitor_AGENTS.md
│   ├── consultation_writer_AGENTS.md
│   ├── REPORT_STYLE.md
│   └── EMAIL_DELIVERY.md
│
└── scripts/
    ├── send_email.py
    └── deploy.sh                   # SSH to VM + docker compose pull + up -d
```

---

## Key Data Flows for Claude Code

### Flow 1: New article ingested
```
Scout Retrieval fetches RSS feed
    → checks seen_urls table (is-url-seen)
    → if new: creates Paperclip issue
    → Translator runs (if non-English)
    → Analyst runs: sentiment + tags + significance
    → Verifier runs: confirms source URL is real
    → db.py insert-article (writes to articles table)
    → db.py mark-url-seen
    → article_tags + article_countries written
```

### Flow 2: Breaking alert fires
```
Alert agent fetches priority government URL
    → computes SHA256 hash
    → compares to alert_hashes table
    → if changed: db.py insert-finding (priority=CRITICAL)
    → Redis PUBLISH to "alerts" channel
    → React WebSocket subscriber receives message
    → Toast notification + world map pulse animation
    → Hash updated in alert_hashes table
```

### Flow 3: Subscriber views dashboard
```
React app loads → sends GET /articles?country=BR&limit=20
    → FastAPI extracts tenant_id from JWT
    → loads tenant from tenants table
    → applies country filter from tenant.countries[]
    → queries articles JOIN article_countries WHERE country_code IN (tenant countries)
    → returns paginated JSON
    → React renders story feed
```

### Flow 4: New source discovered
```
Scout Discovery scans outbound links in fetched articles
    → scores domain credibility (.gov/.edu/known publishers)
    → checks sources table: SELECT 1 FROM sources WHERE url=$1
    → if not found AND credible: INSERT INTO sources (status='candidate')
    → React Sources tab shows candidate in approval queue
    → Human clicks Approve → POST /sources/{id}/approve
    → status updated to 'active'
    → Scout Retrieval picks up on next hourly run
```

---

## Tag Taxonomy (for Analyst agent instructions)

```
sector:
  coal, gas, oil, solar, wind, hydrogen, hydro, nuclear, storage, biofuel, biomass

geography:
  brazil, colombia, argentina, chile, peru,
  germany, uk, spain, france, netherlands, poland,
  indonesia, india, japan, south_korea,
  south_africa, nigeria, kenya, morocco,
  south_america, europe, asia, africa, global

actor_type:
  government, ngo, industry, international, media, academic

policy_stage:
  proposed, consultation, enacted, repealed, under_review

topic:
  stranded_asset, just_transition, permitting, financing, cop30, ndc,
  auction, licensing, phase_out, green_hydrogen, offshore_wind

urgency:
  breaking, this_week, this_month, ongoing

company:
  petrobras, bndes, aneel, anp, mme, enel, total, shell, bp,
  equinor, world_bank, ifc, idb, vale, eletrobras
```

---

## Workspace File Locations (inside Docker volume)

All paths relative to `$WORKSPACE_PATH` (default: `/workspace` inside paperclip container)

```
/workspace/
├── intelligence.db             # SQLite (Phase 0 only — replaced by PostgreSQL)
├── schema.sql                  # applied to both SQLite and PostgreSQL
├── db.py                       # database utility
├── migrate.py                  # migration script
├── sync_from_paperclip.py     # Paperclip → DB sync
├── send_email.py               # SMTP delivery
├── smtp_config.json            # email credentials (from .env in Phase 0.5+)
├── mailing_list.json           # recipient list
├── alert_hashes.json           # migrated to alert_hashes table in Phase 1
├── seen_urls.txt               # migrated to seen_urls table in Phase 1
├── cop30_dates.json            # COP30 key deadlines
├── pending_review/             # reports saved here before email delivery
├── translations/               # Translator agent outputs
├── finance_deals/              # Finance Monitor markdown outputs
├── cop30_docs/                 # COP30 Monitor summaries
├── ngo_reports/                # NGO Monitor summaries
└── submissions/                # Consultation Writer drafts
```

---

*Climate Intelligence Platform · Architecture Reference v1.2 · April 2026*
*github.com/holdersav20001/climate-intelligence-brazil*
