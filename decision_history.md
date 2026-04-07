# Climate Intelligence Platform
## How We Got Here — Decision History & Technology Rationale
**April 2026**

---

## Overview

This document records the full journey from a single-country NGO intelligence tool running on a local PC to the multi-tenant global SaaS platform defined in the product specification v1.2. Every major technology choice, architecture decision, and pivot is documented here with the reasoning behind it.

This is not a spec document. It is a record of thinking — why things were built the way they were, what was rejected and why, and what problems forced each design change.

---

## Where It Started

The project began as a practical tool to help a Brazilian NGO track energy policy intelligence. The initial brief was simple: monitor Brazil's energy sector, surface relevant policy developments, find contacts, and produce a daily briefing.

The starting point was a fresh Paperclip company — a blank slate with no agents, no data, no structure. The platform chosen was Paperclip because it provides a managed agent framework where Claude can run on a heartbeat schedule, maintain a task queue (issues), and coordinate across multiple specialised agents without requiring a full custom backend.

The first agent created was Scout — a single agent responsible for finding and fetching relevant stories from the Brazilian energy press.

---

## Phase 1: Building the Agent Team

### The Scout problem — one agent doing too much

The original Scout agent tried to do everything: discover new sources, fetch pages, filter content, score significance, and deduplicate. This worked initially but became the first major design problem identified during the session.

The decision was made early to eventually split Scout into two distinct agents with different cadences:

- **Scout Discovery** (daily) — finds new sources
- **Scout Retrieval** (hourly) — fetches known sources

This two-agent model is the industry standard approach used by professional intelligence platforms. Reuters and Factiva separate source discovery from content retrieval for the same reason: they require different logic, different failure modes, and different schedules. A source discovery run failing should not stop a content retrieval run, and vice versa.

### Growing the team to 14 agents

The team expanded through a series of capability gaps identified during the session. The question asked repeatedly was: "are there any other gaps?"

The decisions that drove each new agent:

**Translator** — added when it became clear that significant Brazilian energy coverage is published in Portuguese. Claude can read Portuguese but passing raw Portuguese text through the Analyst was inconsistent. A dedicated Translator agent normalises all content to English before analysis, making the Analyst's output more reliable.

**Analyst** — the core intelligence processing agent. Applies 6-dimension sentiment scoring (overall, environmental, economic, political, social, framing), extracts entities, assigns significance scores (0.0–1.0), and eventually auto-tags with country codes and topic slugs.

**Verifier** — added to address the evidence problem. NGO work requires citable, verifiable claims. Without a verification step, the platform could pass unverified or misrepresented claims through to the briefing. The Verifier checks that source URLs are real, accessible, and that the summary accurately reflects the source content. Any claim that cannot be verified is marked UNVERIFIED and never presented as fact.

**Policy Tracker** — added when it became clear that government consultation windows are a primary use case. NGOs need to know when a consultation is open, when the deadline is, and what the NGO's position should be. The Policy Tracker monitors government URLs, detects changes via hash comparison, and surfaces open consultation windows.

**Contact Mapper** — added after recognising that knowing who to influence is as important as knowing what to say. The Contact Mapper builds an influence network with decision_power scores (1–5) and ngo_access scores (1–5), linking contacts to the policies they own and the organisations they represent. All five verified key contacts (Silveira, Feitosa, Agostinho, Saboia, Tolmasquim) were discovered and scored via this agent.

**Reporter** — the output layer. Produces daily digests and on-demand briefs. The report style was a significant discussion point — the NGO's daughter needed a report she could read on her phone and act on immediately, not a wall of bullet points. The Reporter was given a specific REPORT_STYLE.md instruction file defining narrative prose, priority ordering, and action-oriented language.

**Alert** — added to address the breaking news gap. The hourly Scout Retrieval is too slow for truly urgent developments. The Alert agent monitors 5 priority URLs (government press offices, ANEEL, Petrobras) every 4 hours using hash comparison to detect page changes. When a change is detected, it creates a CRITICAL finding immediately regardless of the next scheduled Scout run.

**Parliamentary Monitor** — added after recognising that the Senado and Camara committees are where fossil fuel policy is actually made. Committee hearings, votes on licensing legislation, and budget amendments often move faster than press coverage.

**NGO Monitor** — a key addition driven by a specific question: "should the agents also search NGO sites in Brazil?" The answer was yes — for two reasons. First, allied NGOs (iCS, ARAYARA, Instituto Talanoa, IEMA) publish evidence and analysis that can be cited in policy submissions. Second, opposition bodies (IBP, ONIP) need to be monitored to anticipate their arguments. The NGO Monitor was configured with three tiers: allied organisations (weekly scan), international partners (weekly), and opposition bodies (every 7 runs).

**Finance Monitor** — added to track financing decisions, specifically fossil fuel deals where intervention windows exist. BNDES, IFC, IDB, and World Bank financing for fossil fuel projects often have consultation periods before board approval. Finding these windows early gives NGOs time to submit objections or organise investor pressure.

**COP30 Monitor** — Brazil is hosting COP30 in November 2026. This is the single most important climate policy event of the year for the NGO community. A dedicated agent monitors UNFCCC preparatory documents, voluntary coalition formation, and pre-COP30 conferences. The first CRITICAL finding from this agent (CLI-14) was the Colombia fossil fuel phase-out conference in April 2026 — something that needed immediate action.

**Consultation Writer** — added as a productivity multiplier. Instead of the NGO team writing policy submissions from scratch, this agent drafts them using the platform's accumulated intelligence — verified facts from Verifier, significance-scored articles from Analyst, evidence from NGO Monitor, and policy context from Policy Tracker. Human review and editing is always required before submission.

**Orchestrator** — the coordination layer. Ensures agents run in the right sequence (Scout → Translator → Analyst → Verifier), escalates unresolved critical findings, and maintains the overall pipeline health.

### Checking for additional sources

During agent development, a question arose: "should we check more websites — Reddit, Slack, etc.?"

This led to a broader sources audit. Reddit RSS feeds were added (r/energy, r/brasil, r/climate) because Reddit surfaces grassroots and technical discussions not covered by press. Nitter RSS feeds for official Twitter accounts (MME, ANEEL) were added for real-time government announcements. Slack was ruled out — there is no public RSS or API access to Slack workspaces.

---

## Phase 2: Data Storage — from JSON to SQLite

### The JSON problem

For the first phase, agents wrote their outputs to JSON and JSONL files in the workspace directory: `articles.jsonl`, `influence_model.json`, `tracked_policies.json`, `seen_urls.txt`.

This worked for a single agent running occasionally. It became a problem when raised as a production concern: "I was just thinking that we could build a React application to show the data and run filtering. Ever-growing JSON files don't seem the way forward — they could get huge and inaccessible."

This was correct. JSON files have no query capability, no deduplication enforcement, no concurrent write safety, and no way to filter or aggregate without loading everything into memory. For a platform that would eventually serve 1,000 subscribers seeing filtered views of millions of records, JSON was a dead end.

### Why SQLite first, not PostgreSQL

The question was directly raised: "what about the data — it's currently stored as JSON?" and then "should we go straight to Postgres?"

The decision to start with SQLite was deliberate:

- **Zero infrastructure** — SQLite is a single file. No server to install, no connection management, no network configuration.
- **Same Python API** — `sqlite3` is in Python's standard library. `db.py` uses the exact same interface whether the backend is SQLite or PostgreSQL. Migrating later required changing one import and the connection string.
- **Right for the current data volume** — at 24 articles, 11 findings, 57 runs, SQLite was not just adequate, it was the correct choice. Using PostgreSQL for a dataset this size would have been over-engineering.
- **Proof of concept before investment** — SQLite let us validate the schema design, test the db.py utility API, and confirm agents could write structured data correctly before committing to a proper database infrastructure.

The SQLite schema was designed with PostgreSQL migration in mind from day one — UUID primary keys, ISO timestamps, normalised tables, proper foreign key relationships. The migration to PostgreSQL in Phase 1 is a schema conversion and data migration, not a redesign.

### The db.py utility

Rather than having agents write SQL directly, a utility module was created that agents call via CLI:

```bash
python3 db.py insert-article '{"url": "...", "title": "...", ...}'
python3 db.py is-url-seen "https://..."
python3 db.py stats
```

This decision isolated database logic from agent instructions. If the database changes (SQLite → PostgreSQL → partitioned PostgreSQL), only `db.py` needs updating — not 14 sets of agent instructions. Agents call `db.py` as a black box.

### The sync script

Because agents were already writing to Paperclip issues (the task management system), a `sync_from_paperclip.py` script was written to backfill the database from existing Paperclip issues. This classified 56 issues into articles, findings, and reports by pattern-matching on title and description, then wrote them to the appropriate tables. The result: 24 articles, 11 findings, 17 reports, 57 run log entries populated on first run.

---

## Phase 3: Email Delivery

### The email question

The question was: "whenever I run it, I want to send the report to holdersav2000@gmail.com."

The decision was to build SMTP-based email delivery rather than an API-based service (SendGrid, Mailgun). Reasons:

- **Provider-agnostic** — SMTP works with Gmail, Outlook, Yahoo, or any business email server. No API key management, no third-party account, no cost per email.
- **Simple configuration** — `smtp_config.json` with host, port, user, password. Switching providers means changing 3 values.
- **Reliability** — SMTP is a 40-year-old protocol with essentially universal support. API-based services add a dependency that can fail or change pricing.

The Reporter was configured with a graceful degradation pattern: the report is always saved to `pending_review/` first, then email is attempted. If email fails (SMTP unavailable, credentials wrong), the run completes successfully — the report still exists in the workspace. The Reporter creates a Paperclip issue confirming completion regardless of email status.

A `mailing_list.json` file was created to manage recipients. Adding a new recipient means adding one entry to this file — no code changes.

---

## Phase 4: GitHub and Version Control

### Committing to GitHub

The question arose: "should we commit what we have done before we progress?"

A GitHub repository was created at `github.com/holdersav20001/climate-intelligence-brazil`. The commit included:

- All 14 agent AGENTS.md instruction files
- `REPORT_STYLE.md` and `EMAIL_DELIVERY.md` for Reporter
- `database/schema.sql`, `database/db.py`, `database/migrate.py`, `database/sync_from_paperclip.py`
- `scripts/send_email.py`, `scripts/smtp_config.json.example`
- `workspace-templates/mailing_list.json`
- Full Paperclip export (`.paperclip.yaml`)

`smtp_config.json` (with real credentials) was deliberately excluded from the commit. Only `smtp_config.json.example` was committed with blank values.

### Paperclip export

The question arose: "when I look at org in Paperclip it says 'export organisation' — should it export and move to GitHub?"

Yes. The `.paperclip.yaml` export captures all agent configurations, goals, heartbeat schedules, and workspace settings in a portable format. If Paperclip is reinstalled on a new machine or cloud VM, importing this file recreates the entire company configuration. This is the backup and portability mechanism for the agent layer.

---

## Phase 5: Productionisation Planning

### The productionisation question

The first explicit productionisation question was: "how do I productionise this? This is currently running on my local PC."

This opened a broad architectural discussion covering:

- Cloud hosting
- Database migration
- The React frontend
- Multi-tenancy
- Billing

### Why not Redis as the primary database

The question was raised: "I was thinking Redis would be better — what's your opinion?"

The honest answer was no, and the reasons were specific:

Redis is an in-memory key-value store. It is excellent at pub/sub messaging, caching, and job queuing. It is wrong for the primary use case here because the data is relational — articles have sentiment scores across 6 dimensions, contacts link to policies link to findings link to articles. Querying "show me all HIGH findings from the last 30 days where coalition_opportunity is true" is a 3-line SQL query in PostgreSQL and requires custom indexing in Redis. The platform would be rebuilding a relational database on top of a key-value store.

Redis was retained but in its correct role:
- **Pub/sub** for real-time alert delivery to the React frontend
- **Job queue** (via BullMQ) to prevent concurrent agent conflicts

### Shared infrastructure, tenant-specific views

The core multi-tenancy architectural decision: "my thought is that the agent layer + PostgreSQL + Redis is a core function shared by all. Using tags and filters they might just look at their country."

This is the correct model and was adopted without modification. One shared agent layer runs globally. One shared PostgreSQL instance holds all data. Subscribers are a read-time concern — the API applies their country and tag filters when they query. Adding 1,000 subscribers requires no changes to the agent layer.

The alternative — separate agents per subscriber — would mean 1,000 × 14 = 14,000 agent instances for a full subscriber base. That is operationally impossible and economically absurd.

---

## Phase 6: Database Architecture Decisions

### PostgreSQL over SQLite for production

With 1,000 subscribers in view, the SQLite limitations become hard blockers:

- **Concurrent writes** — SQLite allows one writer at a time. Multiple agents writing simultaneously would block. PostgreSQL handles thousands of concurrent connections.
- **Row-level security** — critical for multi-tenancy. PostgreSQL enforces per-row access control at the database layer. SQLite has no equivalent.
- **Full-text search** — PostgreSQL's `tsvector`/`tsquery` handles multilingual full-text search across millions of rows. Essential for searching Portuguese and Spanish content.
- **Partitioning** — monthly partitioning of time-series tables for the 3-month rolling window. Dropping a partition (dropping a month of data) is instantaneous with no performance impact.
- **pgvector** — semantic search in phase 2. This is a PostgreSQL extension — no separate vector database required.

### Why no graph database

The question was asked directly: "do we need a graph database to link information together?"

The cross-reference tables (finding_articles, finding_contacts, article_tags, contact_policies) are essentially a graph. PostgreSQL JOINs across these tables with proper indexes handle the 2–3 hop relationships needed here in milliseconds at this data volume.

A graph database (Neo4j, ArangoDB) is the right choice when traversals are 6+ hops deep and there are hundreds of millions of relationships. For "show me findings linked to articles tagged with petrobras where the finding is linked to a contact in government" — that is a 3-table JOIN. No graph database required.

### Why no separate vector database

The question was asked: "do we need a vector database for searching text?"

pgvector is a PostgreSQL extension. `ALTER TABLE articles ADD COLUMN embedding vector(1536)`. Semantic search requires no separate Pinecone, Weaviate, or Qdrant instance. The vector index lives in the same PostgreSQL database as everything else. This is simpler to operate, cheaper, and sufficient for this data volume.

pgvector was deferred to Phase 2. The priority for Phase 1 is getting keyword full-text search working. Semantic search is a phase 2 enhancement once the platform is stable.

### The 3-month rolling window

The concern raised: "I want to hold 3 months of data and then maybe archive — I am worried about PostgreSQL performance."

The correct response is that PostgreSQL performance with proper partitioning is not a concern at this data volume. Monthly table partitioning means the live 3-month window is at most 3 physical files. Queries filtered by date touch only the relevant partition. Dropping 3-month-old data means dropping a partition — one SQL statement, zero performance impact, instant execution.

Reference data (contacts, policies, sources, tenants, tags) never expires and is never archived. Only time-series data (articles, findings, run_log) rolls on the 3-month window.

---

## Phase 7: Sources Architecture

### The two-scout model and self-expanding sources

The insight: "I think we should have agents that discover useful sources — if a news feed comments and has links to other sources we should pull them in."

This is exactly the right architectural instinct. Static source lists are a competitive vulnerability. Any competitor can copy a static list. A self-expanding source network that automatically discovers new sources from link extraction is defensible — it improves continuously and surfaces obscure but credible sources no static list would find.

Scout Discovery extracts outbound links from every fetched article, scores domain credibility, checks against the sources table, and adds candidates for human approval. The `sources` tab in the React app shows the candidate queue with Approve/Reject buttons — human oversight is required before a new source is activated.

### The sources table

The key architectural change enabling global scale: sources are not hardcoded in agent instructions. They live in the `sources` table:

```sql
SELECT * FROM sources WHERE active=true AND country_code='BR' AND next_fetch <= NOW()
```

Adding Colombia means `INSERT INTO sources (country_code='CO', ...)`. Scout Retrieval picks it up on the next run. No agent code changes. No new agents. No redeployment.

### Yahoo Finance

The question: "doesn't Yahoo have a news RSS?"

Yes — two types confirmed working:
- `finance.yahoo.com/rss/` — general financial news
- `finance.yahoo.com/rss/headline?s=PBR` — ticker-specific news

Yahoo Finance ticker feeds are particularly useful for tracking energy companies. Every major energy company has a ticker. PBR for Petrobras, SHEL for Shell, TTE for TotalEnergies — news about these companies flows through automatically and reliably.

Yahoo News keyword search RSS (the equivalent of Google News search) no longer works as a free service. Google News RSS (`news.google.com/rss/search?q=...`) is the correct tool for keyword-based country-specific queries.

### GDELT

GDELT was identified as the most powerful global source layer — monitoring news in 100+ languages every 15 minutes, machine-translating 65 of them into English in real time, and providing a free query API. The GDELT DOC API covers thousands of global sources simultaneously with a single query. For the global expansion use case (50+ countries), GDELT provides coverage of local language press that no RSS list could match.

### Specialist renewable energy publications

A full audit of specialist renewable energy publications with confirmed RSS feeds was conducted, producing a curated list of 18 publications. The most important:

- **Recharge News** — world's leading wind and solar business intelligence
- **PV Magazine** — solar worldwide, with country editions including `pv-magazine.com.br` for Brazil in Portuguese
- **PV Tech** — solar project finance and manufacturing
- **Renewables Now** — all renewables, strong on deals
- **Windpower Monthly** — wind specifically
- **Energy Storage News** — storage and hydrogen
- **Carbon Brief** — most credible for policy analysis
- **Clean Energy Wire** — European energy transition in English and German
- **Energía Estratégica** — South America in Spanish

### Regional expansion — South America and Europe

The explicit requirement: "I want to include South America and Europe to the list."

The sources strategy was redesigned to be region-first rather than country-first:

**South America (Phase 2):** Colombia is the immediate priority — it is the site of the April 2026 fossil fuel phase-out conference and is actively forming the pre-COP30 voluntary coalition. Argentina (Vaca Muerta gas, growing solar), Chile (world-leading solar irradiance, lithium), and Peru (Amazon energy conflicts) follow.

**Europe (Phase 2):** Germany (Energiewende, world's most watched transition), UK (North Sea licensing wars), Spain (solar boom), France, Netherlands, Poland (coal phase-out under EU pressure).

**Asia (Phase 3):** Indonesia, India, Japan, South Korea.

**Africa (Phase 4):** South Africa, Nigeria, Kenya, Morocco.

---

## Phase 8: React Frontend Design

### The dashboard requirement

The question: "the dashboard should be simple and clean — I would like mocks before we progress."

A working interactive mockup was built with 6 tabs — Dashboard, World Map, Findings, Contacts, Sources, Reports — before any frontend code was written. The mockup established the visual language: flat design, tab navigation, significance badges, priority colour coding (red/amber/green), influence dot scoring for contacts, and the candidate approval queue for sources.

### The world map requirement

The most distinctive feature request: "one tab should have the world map that shows how many new stories, red/green/amber based on news, spiking up or down or neutral — I should be able to click on a country and it would show me the latest news."

This was designed in the mockup with:
- D3 GeoJSON for accurate country shapes
- Country circles sized by story count in the last 24 hours
- Colour encoding: red = negative sentiment, amber = mixed, green = positive, grey = no data
- Click handler showing a country popup with story count, top story, critical finding count, and a "View all" link
- Pulse animation for CRITICAL alerts via Redis WebSocket
- Subscriber filter: Starter plan subscribers see non-subscribed countries greyed out
- Time slider: drag back 30 days to see historical activity

### LinkedIn

The question was raised about LinkedIn as a source.

The honest answer: LinkedIn is valuable for monitoring energy ministers and executives but cannot be automated. LinkedIn's terms of service prohibit scraping and their API is heavily restricted. Automating LinkedIn monitoring risks account bans. The correct approach is to include LinkedIn profile URLs in contact records as manual check prompts — the Contact Mapper flags contacts with notable LinkedIn activity for human review, but never attempts automated fetching.

---

## Phase 9: Hermes Integration

### The Hermes question

The question: "many people use Hermes with Paperclip — should we incorporate now to reduce testing later?"

Hermes Agent (by Nous Research) solves the agent amnesia problem — every Paperclip heartbeat starts fresh with no memory of previous runs except what is written to files. Hermes provides persistent cross-session memory via FTS5 session search, user modelling (Honcho), and autonomous skill creation.

The decision was not to add Hermes immediately but to plan for it properly:

**Why not now:** Adding Hermes before the PostgreSQL migration and FastAPI backend are complete means debugging two new systems simultaneously. The agents that benefit most — Scout Discovery and Analyst — do not yet exist in their Phase 2 forms. Adding Hermes to agents that are about to be rewritten is wasted effort.

**The three agents that get Hermes in Phase 2:**

- **Scout Discovery** — remembers which domains were evaluated and rejected, which link patterns are noise, which source types work best per country. This is where Hermes memory changes output quality most directly.
- **Analyst** — remembers tagging accuracy feedback. Over weeks, it learns that certain source types tend to produce articles incorrectly tagged as coal_gas when they are actually renewables, and adjusts its confidence scores accordingly.
- **Contact Mapper** — remembers relationship context that does not fit neatly into database fields. The nuance of who is becoming more or less influential, who has been responsive to NGO outreach, which contacts are retiring or changing roles.

**The 11 agents that do not get Hermes:** All other agents have clear structured outputs that the database already captures. Reporter, Alert, Finance Monitor — these are task-driven with well-defined inputs and outputs. Hermes memory would add complexity without proportional benefit.

**Installation strategy:** Hermes is included in the Paperclip Dockerfile during Phase 0.5 but kept inactive. Activating it in Phase 2 is a configuration flag — no image rebuild required. Scout Discovery gets it first, runs for 2 weeks, measured against the baseline before Analyst and Contact Mapper are updated.

---

## Phase 10: Docker

### The Docker decision

The question: "I also believe we should start from the very beginning with a Dockerised version using Docker so it will be easy to deploy — what do you think?"

This was immediately agreed as the correct call, and the timing was identified as right — before the cloud VM is provisioned, before the PostgreSQL migration, before any new infrastructure is built.

The problems Docker solves for this specific project:

**The "works on my machine" problem.** The platform currently runs on a local WSL setup with specific Python versions, paths, and configurations. Moving to a Hetzner VM without Docker means manually replicating this environment. With Docker, the environment is the Dockerfile.

**Secrets management.** SMTP credentials are in `smtp_config.json`. The Claude API key is in the Paperclip configuration. Database passwords will exist soon. Docker Compose centralises all secrets in a `.env` file that is never committed to Git. One file, one place to update, enforced by `.gitignore`.

**Developer onboarding.** The eventual developer hired to build the FastAPI backend and React app should be able to run the full stack locally in under 5 minutes: `git clone` + `cp .env.example .env` + fill in API keys + `docker compose up`.

**Deployment repeatability.** Moving from Hetzner CX32 to a larger VM, or from Hetzner to DigitalOcean, means copying the `.env` file and running one command. No environment setup, no configuration drift.

**Service isolation.** PostgreSQL, Redis, Paperclip, FastAPI, React, and the worker scheduler each run in their own container. They communicate over a private Docker network. If the React frontend container crashes, the agents keep running. If Redis restarts, the database is unaffected.

### The Docker Compose structure

Six services were defined:

- `postgres` — PostgreSQL 16 with pgvector extension, schema auto-applied on first start via `docker-entrypoint-initdb.d`
- `redis` — Redis 7 with persistence
- `paperclip` — Paperclip with Hermes installed (inactive), workspace mounted as a named volume
- `api` — FastAPI backend
- `frontend` — React app served via nginx
- `worker` — BullMQ agent heartbeat scheduler

A `docker-compose.override.yml` provides local development overrides: hot reload for FastAPI and React, postgres port exposed for direct DB access with pgAdmin.

### Phase 0.5

Docker was inserted as Phase 0.5 — a distinct phase between the current state (Phase 0, done) and the PostgreSQL migration (Phase 1). The reasoning: get Docker working first against the existing SQLite database, confirm all services start and communicate correctly, then do the PostgreSQL migration inside the running Docker stack. This isolates two major changes.

---

## Summary of Key Technology Decisions

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Agent platform | Paperclip | Custom backend | Managed heartbeat scheduling, task queue, cost tracking out of the box |
| Agent model | Claude Haiku 4.5 | GPT-4, Gemini | Native tool use, instruction following, cost efficiency |
| Initial database | SQLite | PostgreSQL | Zero infrastructure, prove schema first, same API for migration |
| Production database | PostgreSQL 16 | Redis, MongoDB, DynamoDB | Relational queries, row-level security, partitioning, pgvector |
| Vector search | pgvector (phase 2) | Pinecone, Weaviate, Qdrant | PostgreSQL extension — no separate database |
| Graph queries | PostgreSQL JOINs | Neo4j, ArangoDB | 2-3 hop depth only — no graph DB needed at this volume |
| Real-time alerts | Redis pub/sub | Polling, WebSockets alone | Redis already in stack, sub-second delivery to frontend |
| Job queue | Redis + BullMQ | Celery, RQ | Already using Redis, Node-native, Paperclip is Node |
| Agent memory | Hermes (3 agents, phase 2) | No memory, custom memory | FTS5 session search + skill creation, official Paperclip adapter |
| Email delivery | SMTP | SendGrid, Mailgun, SES | Provider-agnostic, no API key dependency, works with any email server |
| Frontend | React + TypeScript | Vue, Angular, Svelte | Widest developer talent pool, strongest D3 integration for world map |
| Deployment | Docker Compose | Manual setup, Kubernetes, Heroku | Single-command deploy, environment reproducibility, appropriate complexity |
| Hosting | Hetzner CX32 | AWS, DigitalOcean, GCP | €3.79/month, Docker-ready Ubuntu, European data sovereignty |
| CI/CD | GitHub Actions | Jenkins, CircleCI | Free for public repos, native GitHub integration, simple YAML |
| Auth | Supabase Auth or Auth0 | Custom JWT | Managed service reduces auth complexity |
| Billing | Stripe | Paddle, Chargebee | Market standard, webhooks, subscription metering |
| Sources | Dynamic sources table | Hardcoded in AGENTS.md | New country = new DB rows, no code changes |
| Multi-tenancy | Shared DB, filtered views | Separate DB per tenant | 1,000 subscribers = 1,000 instances otherwise |
| LinkedIn | Manual only | Automated scraping | Terms of service prohibit automation |

---

## The Conversation That Shaped Each Decision

The project evolved through approximately 68 user interactions over two days. The decisions were not made from a pre-existing plan — they emerged from the practical problems encountered at each step:

1. Scout finding stories but no way to query them → JSON → SQLite → PostgreSQL plan
2. Reports arriving but unreadable on mobile → REPORT_STYLE.md for Reporter
3. Email working with Gmail only → SMTP refactor for provider-agnostic delivery
4. Agents not improving over time → Hermes (planned for Phase 2)
5. Local PC not scalable → Docker + cloud VM
6. JSON files growing without queryability → database-first architecture
7. Static source list → dynamic sources table + Scout Discovery
8. Single country scope → global architecture with tag-based filtering
9. No way to see data → React frontend with world map
10. Complex relationships between findings, contacts, articles → cross-reference junction tables

---

## What Has Been Built (April 2026)

- **14 Paperclip agents** — fully configured, tested, running on WSL
- **SQLite database** — 9 tables, 24 articles, 11 findings, 17 reports, 57 run logs
- **db.py utility** — CLI and library interface for all database operations
- **sync_from_paperclip.py** — backfills database from Paperclip issue history
- **send_email.py** — SMTP email delivery tested and working
- **GitHub repository** — all agent instructions, schema, scripts, Paperclip export committed
- **Product specification v1.2** — full spec covering all phases through launch
- **Interactive React mockup** — 6-tab dashboard prototype showing world map and all views

## What Comes Next

**Phase 0.5** (Late April / Early May 2026) — Docker Compose setup. The entire stack containerised, deployed to Hetzner VM, CI/CD via GitHub Actions. This is the first priority.

**Phase 1** (May 2026) — PostgreSQL migration, tag schema, FastAPI backend, JWT auth.

**Phase 2** (June 2026) — Scout split, Hermes activation (Scout Discovery first), auto-tagging, South America and Europe sources.

**Phase 3** (July–August 2026) — React frontend — all 6 tabs, world map, real-time alerts.

**Phase 4** (September 2026) — Stripe billing, onboarding, launch.

---

*Climate Intelligence Platform · Decision History v1.0 · April 2026*
*github.com/holdersav20001/climate-intelligence-brazil*
