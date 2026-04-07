# Climate Intelligence Platform
## Product Specification & Engineering Roadmap
**Version 1.2 · April 2026 · Confidential**

---

## Table of Contents

1. [Vision and Product Overview](#1-vision-and-product-overview)
2. [Architecture](#2-architecture)
3. [Docker Compose Setup](#3-docker-compose-setup)
4. [Database Schema](#4-database-schema)
5. [Agent Architecture](#5-agent-architecture)
6. [Hermes Integration](#6-hermes-integration)
7. [Sources Strategy](#7-sources-strategy)
8. [React Frontend](#8-react-frontend)
9. [Engineering Tasks](#9-engineering-tasks)
10. [Roadmap](#10-roadmap)
11. [Immediate Next Steps](#11-immediate-next-steps)

---

## 1. Vision and Product Overview

Climate Intelligence Platform is a subscription SaaS product that delivers automated, evidence-based energy policy intelligence to NGOs, think tanks, journalists, researchers, and energy professionals worldwide.

The platform monitors government policy, news, NGO publications, parliamentary committees, financing deals, and COP30 developments across multiple countries — tagging, cross-referencing, and surfacing actionable intelligence to subscribers through a daily digest, real-time alerts, and a React web application.

### Mission

> Provide the world's most actionable, evidence-based energy transition intelligence — so every campaign, policy submission, and advocacy decision is grounded in verified facts.

### Business Model

| Tier | Price | Target | Features |
|---|---|---|---|
| **Starter** | £199/month | Single-country NGOs | 1 country, daily digest, 3-month data |
| **Pro** | £499/month | Regional NGOs, think tanks | 5 countries, alerts, contacts, submissions |
| **Enterprise** | £1,499/month | Foundations, law firms, media | Unlimited countries, API access, custom reports |

### Market Gap

No self-service SaaS exists at this price point for NGOs and smaller energy organisations. Closest competitors (Global Energy Monitor, ICIS, Bloomberg NEF) are manual, expensive, or enterprise-only. A self-serve platform at £200–500/month targeting NGOs, think tanks, and journalists covering the energy transition is a real and underserved gap.

---

## 2. Architecture

### Core Principle

**Shared infrastructure, tenant-specific views.** One shared agent layer, one shared PostgreSQL database, Redis for real-time alerts. Subscribers do not get their own agents — they get filtered views of shared data via country and tag filters. Adding a new country means adding rows to the `sources` table, not new agents.

**Everything runs in Docker.** The entire platform — PostgreSQL, Redis, Paperclip, FastAPI, React, worker — is defined in a single `docker-compose.yml`. Deployment to any environment (local laptop, cloud VM, CI) is one command: `docker compose up`.

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌─────────┐  │
│  │ frontend │  │   api    │  │ paperclip  │  │ worker  │  │
│  │  React   │  │ FastAPI  │  │ + Hermes   │  │ BullMQ  │  │
│  │  nginx   │  │  :8000   │  │  :3100     │  │ queues  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘  └────┬────┘  │
│       │             │               │               │       │
│  ─────┴─────────────┴───────────────┴───────────────┴────  │
│                    Docker private network                    │
│  ─────────────────────────┬─────────────────────────────── │
│                            │                                │
│              ┌─────────────┴──────────────┐                │
│              │                            │                │
│        ┌─────┴──────┐             ┌───────┴──────┐        │
│        │ PostgreSQL  │             │    Redis      │        │
│        │  :5432      │             │   :6379       │        │
│        │ (volume)    │             │  (volume)     │        │
│        └────────────┘             └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Container orchestration** | Docker Compose | Single-command deploy to any environment |
| **Agent layer** | Paperclip + Claude Haiku 4.5 | 14 agents, runs globally, writes to shared DB |
| **Agent memory** | Hermes Agent (Nous Research) | Persistent cross-session memory for 3 agents |
| **Primary database** | PostgreSQL 16 (partitioned by month) | All structured data |
| **Search phase 1** | PostgreSQL tsvector | Keyword search across articles |
| **Search phase 2** | pgvector extension | Semantic search — no separate database needed |
| **Real-time** | Redis pub/sub + WebSocket | Breaking alerts pushed to dashboard instantly |
| **Job queue** | Redis + BullMQ | Agent run scheduling, prevents concurrent conflicts |
| **API** | FastAPI (Python) | REST endpoints, tenant auth, rate limiting |
| **Frontend** | React + TypeScript + nginx | Dashboard, world map, findings, contacts, sources |
| **Auth** | Supabase Auth or Auth0 | JWT tokens, subscriber management |
| **Billing** | Stripe | Subscription management, usage metering |
| **Hosting** | Hetzner CX32 (~£12/month) | Ubuntu 24, Docker installed, always-on |
| **CI/CD** | GitHub Actions | Build images → push to GHCR → deploy to VM |

### Why Docker from the Start

Without Docker, every environment change means manually re-installing Python, PostgreSQL, Redis, Paperclip, Node, nginx, certbot, configuring paths, and managing environment variables — then repeating this for every new developer, every new VM, and every deployment. That is days of work each time.

With Docker:

- `docker compose up` starts the entire platform identically on any machine
- Moving to a new cloud provider is copy `.env` + run one command
- Developer onboarding is `git clone` + `docker compose up` — no setup call needed
- PostgreSQL migration from SQLite can be tested safely against a throwaway container
- Environment variables and secrets are centralised in one `.env` file that never enters Git
- If a container crashes, Docker restarts it automatically
- Each service can be updated independently without touching the others

---

## 3. Docker Compose Setup

### Service Definitions

```yaml
# docker-compose.yml (abbreviated — full file in repository)

services:

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: climate_intel
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
      - ./database/seed.sql:/docker-entrypoint-initdb.d/02_seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  paperclip:
    build: ./paperclip
    environment:
      ANTHROPIC_API_KEY: ${CLAUDE_API_KEY}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/climate_intel
      REDIS_URL: redis://redis:6379
      WORKSPACE_PATH: /workspace
    volumes:
      - paperclip_workspace:/workspace
      - ./agents:/app/agents:ro
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    ports:
      - "3100:3100"

  api:
    build: ./api
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/climate_intel
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
      ENVIRONMENT: ${ENVIRONMENT}
    depends_on:
      postgres: { condition: service_healthy }
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    environment:
      VITE_API_URL: ${API_URL}
      VITE_WS_URL: ${WS_URL}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - api

  worker:
    build: ./worker
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/climate_intel
    depends_on:
      - redis
      - postgres

volumes:
  postgres_data:
  redis_data:
  paperclip_workspace:
  certbot_certs:
```

### Environment Variables

All secrets and configuration live in `.env`. This file is never committed to Git — only `.env.example` (with blank values) is committed.

```bash
# .env.example — copy to .env and fill in values

# Database
POSTGRES_USER=climate_intel
POSTGRES_PASSWORD=change_me_in_production
DATABASE_URL=postgresql://climate_intel:change_me@postgres:5432/climate_intel

# Redis
REDIS_URL=redis://redis:6379

# Claude / Paperclip
CLAUDE_API_KEY=sk-ant-...

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password

# Authentication
JWT_SECRET=generate-a-long-random-string-here

# Stripe (Phase 4)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# URLs
API_URL=https://api.yourdomain.com
WS_URL=wss://api.yourdomain.com

# Environment
ENVIRONMENT=production
```

### Local Development Override

```yaml
# docker-compose.override.yml — applied automatically in local dev

services:
  api:
    volumes:
      - ./api:/app          # hot reload
    environment:
      ENVIRONMENT: development

  frontend:
    volumes:
      - ./frontend:/app     # hot reload via Vite dev server
    ports:
      - "5173:5173"         # Vite dev port instead of nginx

  postgres:
    ports:
      - "5432:5432"         # expose for direct DB access with pgAdmin or DBeaver
```

### Repository Structure

```
climate-intelligence-brazil/
├── docker-compose.yml
├── docker-compose.override.yml    # local dev overrides
├── .env.example                   # committed — blank values only
├── .env                           # NOT committed — real secrets
│
├── database/
│   ├── schema.sql                 # PostgreSQL schema
│   ├── seed.sql                   # tag taxonomy + country seed data
│   ├── migrate.py                 # SQLite → PostgreSQL migration
│   ├── db.py                      # database utility for agents
│   └── sync_from_paperclip.py    # Paperclip → DB sync
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── routes/
│       └── models/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│
├── paperclip/
│   ├── Dockerfile
│   └── workspace-templates/
│
├── worker/
│   ├── Dockerfile
│   └── queue.js
│
├── nginx/
│   └── conf.d/
│       └── default.conf
│
├── agents/                        # all 14 agent AGENTS.md files
│   ├── scout_discovery_AGENTS.md
│   ├── scout_retrieval_AGENTS.md
│   └── ...
│
└── scripts/
    ├── send_email.py
    └── deploy.sh                  # SSH to VM + docker compose pull + up
```

### Deployment to Hetzner VM

```bash
# On Hetzner VM — first time setup (5 minutes)
apt update && apt install -y docker.io docker-compose-plugin
git clone https://github.com/holdersav20001/climate-intelligence-brazil
cd climate-intelligence-brazil
cp .env.example .env
nano .env                    # fill in real values
docker compose up -d
docker compose logs -f       # watch startup
```

After this, every future deployment is automated via GitHub Actions — push to `main`, images build, VM pulls and restarts. Zero manual SSH required after initial setup.

---

## 4. Database Schema

### Design Decisions

- PostgreSQL 16 with pgvector extension (installed via `pgvector/pgvector:pg16` Docker image)
- Partitioned by month for all time-series tables — old partitions dropped instantly, no performance impact
- **No separate graph database** — PostgreSQL JOINs handle 2–3 hop cross-references at this volume
- **No separate vector database** — pgvector is a PostgreSQL extension, added in phase 2 as `ALTER TABLE articles ADD COLUMN embedding vector(1536)`
- All content tagged with country codes and tag slugs — the primary subscriber filter axes
- Tenant-specific data in separate tables, never mixed with shared content

### Tables

| Table | Type | Purpose |
|---|---|---|
| `articles` | time-series (partitioned) | Every story found by Scout. Tagged with countries and topics. |
| `article_countries` | junction | Many-to-many: articles ↔ countries |
| `article_tags` | junction | Many-to-many: articles ↔ tags. Includes confidence score (0–1). |
| `contacts` | reference (permanent) | Global influence network. Decision power + NGO access scores. |
| `contact_countries` | junction | Which countries each contact operates in |
| `contact_tags` | junction | Which topics/policies each contact owns or influences |
| `contact_access` | tenant-specific | Per-subscriber ngo_access scores — only the tenant can update |
| `findings` | time-series (partitioned) | High-value outputs from Finance, COP30, NGO Monitor agents |
| `finding_countries` | junction | Which countries each finding relates to |
| `finding_tags` | junction | Topic tags for each finding |
| `finding_articles` | cross-reference | Evidence links: findings ↔ supporting articles |
| `finding_contacts` | cross-reference | Relevance links: findings ↔ relevant contacts |
| `policies` | reference (permanent) | Government policy documents with consultation windows |
| `ngo_intel` | time-series (partitioned) | NGO Monitor publications and research |
| `finance_deals` | time-series (partitioned) | Fossil fuel and renewable financing intelligence |
| `reports` | time-series (partitioned) | Every report the Reporter agent produces |
| `sources` | reference (permanent) | All monitored sources. Scout Retrieval reads from this table. |
| `tags` | reference (permanent) | Tag taxonomy: sector, topic, actor_type, urgency, policy_stage |
| `countries` | reference (permanent) | ISO country codes, regions, active status |
| `tenants` | reference (permanent) | Subscriber accounts, plans, billing status |
| `tenant_filters` | per-tenant | Saved filter views (e.g. "My Brazil View") |
| `tenant_article_status` | per-tenant | Read/saved/actioned status per article per subscriber |
| `run_log` | time-series (partitioned) | Every agent heartbeat run with duration and cost |
| `seen_urls` | dedup | All URLs ever processed — replaces seen_urls.txt files |
| `alert_hashes` | reference | URL hashes for change detection by Alert agent |

### Tag Taxonomy

Every article, contact, finding, and policy is tagged against this taxonomy on ingest by the Analyst agent.

| Category | Example slugs |
|---|---|
| `sector` | coal, gas, oil, solar, wind, hydrogen, hydro, nuclear, storage, biofuel, biomass |
| `geography` | brazil, colombia, argentina, chile, germany, uk, spain, france, indonesia, south_america, europe, global |
| `actor_type` | government, ngo, industry, international, media, academic |
| `policy_stage` | proposed, consultation, enacted, repealed, under_review |
| `topic` | stranded_asset, just_transition, permitting, financing, cop30, ndc, auction, licensing |
| `urgency` | breaking, this_week, this_month, ongoing |
| `company` | petrobras, bndes, aneel, anp, mme, enel, total, shell, bp, equinor |

---

## 5. Agent Architecture

### Design Principle

Agents run globally and are **country-agnostic**. They write to the shared PostgreSQL database via `db.py`, tagging everything with country codes and tag slugs on ingest. Tenants are a read-time concern only — agents never need to know which subscribers exist.

Inside Docker, agents communicate with PostgreSQL and Redis using internal Docker network hostnames (`postgres:5432`, `redis:6379`). The `DATABASE_URL` and `REDIS_URL` environment variables are injected from `.env`.

### Current Agents (14)

| Agent | Schedule | Function | Writes to |
|---|---|---|---|
| **Orchestrator** | every 1h | Coordinates pipeline, escalates to board | run_log |
| **Scout Discovery** | daily | Finds new sources via GDELT, Google News, link extraction | sources (candidates) |
| **Scout Retrieval** | every 1h | Fetches all active sources from sources table | articles, seen_urls |
| **Translator** | on demand | Portuguese/Spanish → English before analysis | articles (updates) |
| **Analyst** | on demand | Sentiment (6 dims), entities, significance, country + topic tags | articles (updates) |
| **Verifier** | on demand | Checks source URLs, confirms facts match summary | articles (verified flag) |
| **Policy Tracker** | daily | Monitors government policy docs and consultation windows | policies, findings |
| **Contact Mapper** | every 1h | Builds influence network, scores contacts | contacts, contact_tags |
| **Reporter** | daily + demand | Writes daily digest and story briefs, sends email | reports |
| **Alert** | every 4h | Hash-monitors 5 priority URLs for breaking news | findings (CRITICAL) |
| **Parliamentary Monitor** | daily | Watches Senado/Camara committees for hearings | findings |
| **NGO Monitor** | daily | Monitors allied NGOs, international partners, opposition | ngo_intel, findings |
| **Finance Monitor** | daily | Tracks fossil fuel and renewable financing deals | finance_deals, findings |
| **COP30 Monitor** | daily | Tracks COP30 preparatory documents and opportunities | findings |
| **Consultation Writer** | on demand | Drafts formal policy submissions from platform intelligence | reports (submissions) |

### Two-Scout Model

**Scout Discovery (daily)** uses GDELT DOC API, Google News RSS, and link extraction from already-fetched articles to discover new sources. Adds candidates with `status = 'candidate'` for human approval via the React Sources tab. Creates a self-expanding source network over time.

**Scout Retrieval (hourly)** reads from the `sources` table: `SELECT * FROM sources WHERE active=true AND next_fetch <= NOW()`. Deduplicates against `seen_urls`. Passes new articles to the Analyst queue via Redis. **Adding a new country = adding rows to the sources table. No agent code changes required.**

---

## 6. Hermes Integration

### What Hermes Solves

Every Paperclip agent heartbeat currently starts fresh — the only memory available is what is written in `AGENTS.md` and readable from the workspace. Agents cannot improve over time.

Hermes Agent (by Nous Research) provides three persistent memory mechanisms:
- **FTS5 session search** — searchable database of all past interactions with LLM summarisation
- **Honcho user modelling** — persistent model of working patterns and domain knowledge that evolves across sessions
- **Autonomous skill creation** — solutions are abstracted into reusable skills that improve future runs

The `hermes-paperclip-adapter` (also by Nous Research) runs Hermes inside Paperclip via the `--resume` flag, picking up exactly where the last heartbeat ended.

Inside Docker, Hermes runs as a sidecar process inside the `paperclip` container. Its session database is stored in the `paperclip_workspace` named volume — persisting across container restarts and redeployments.

### Which Agents Get Hermes

| Agent | Hermes benefit | What it remembers |
|---|---|---|
| **Scout Discovery** | High — add Phase 2 | Which domains were rejected and why, which source types work best per country, link pattern noise |
| **Analyst** | High — add Phase 2 | Tagging accuracy feedback, which tag combinations proved wrong after verification |
| **Contact Mapper** | Medium — add Phase 2 | Relationship context, influence signal nuances beyond what the DB captures |
| All others | Low — not added | Structured DB outputs already capture the relevant state |

### When to Add It

| Phase | Action |
|---|---|
| Phase 0.5 | Include Hermes in the Paperclip Dockerfile — installed but not activated |
| Phase 1 | Build and test without Hermes enabled |
| Phase 2 start | Activate Hermes on Scout Discovery only. Run for 2 weeks. Measure source quality vs baseline. |
| Phase 2 end | If Scout Discovery improves, activate on Analyst and Contact Mapper |

Installing Hermes in the Docker image during Phase 0.5 (even before activating it) means no code changes or image rebuilds are needed to enable it later — just a config flag.

---

## 7. Sources Strategy

### Five Source Types

| Type | Example URL | Frequency | Cost |
|---|---|---|---|
| GDELT DOC API | api.gdeltproject.org | 15 min | Free |
| Google News RSS | news.google.com/rss/search?q=brazil+energy&hl=pt-BR&gl=BR | Hourly | Free |
| Specialist RSS | pv-magazine.com.br/feed | Hourly | Free |
| Yahoo Finance ticker | finance.yahoo.com/rss/headline?s=PBR | Hourly | Free |
| Government hash monitor | gov.br/mme/pt-br/assuntos/noticias | 4-hourly | Free |
| Reddit RSS | reddit.com/r/energy/.rss | Hourly | Free |
| Nitter RSS | nitter.privacydev.net/mme_gov/rss | Hourly | Free |

### Specialist Renewable Energy Publications

| Publication | RSS URL | Focus |
|---|---|---|
| Recharge News | services.rechargenews.com/app/rss | Global wind + solar — world's leading specialist |
| PV Magazine (global) | pv-magazine.com/feed | Solar worldwide |
| PV Magazine Brasil | pv-magazine.com.br/feed | Brazil solar in Portuguese |
| PV Tech | pvtech.org/feed | Solar project finance and manufacturing |
| Renewables Now | renewablesnow.com/feed | All renewables — business intelligence since 2009 |
| Windpower Monthly | windpowermonthly.com/rss | Wind — strong on offshore and Latin America |
| Energy Storage News | energy-storage.news/feed | Storage, battery, hydrogen |
| CleanTechnica | cleantechnica.com/feed | All clean energy — high volume, trend signals |
| Carbon Brief | carbonbrief.org/feed | Climate and energy policy — most credible |
| Ember Energy | ember-energy.org/feed | Electricity data and analysis |
| Clean Energy Wire | cleanenergywire.org/feed | European energy transition |
| Euractiv Energy | euractiv.com/sections/energy/feed | EU energy policy |
| H2 View | h2-view.com/feed | Hydrogen specifically |
| Energía Estratégica | energiastrategica.com/feed | South America renewables in Spanish |
| Energy Monitor | energymonitor.ai/feed | Data-driven transition analysis |
| RenewEconomy | reneweconomy.com.au/feed | Asia-Pacific |
| China Dialogue Energy | dialogue.earth/en/energy/feed | China energy transition |
| Renewable Energy World | renewableenergyworld.com/feed | All renewables — established 1999 |

### Regional Coverage Plan

| Region | Phase | Countries | Key sources to add |
|---|---|---|---|
| **South America** | Phase 2 | Brazil (live), Colombia, Argentina, Chile, Peru | Energía Estratégica, BNAmericas Latin America, local govt feeds |
| **Europe** | Phase 2 | Germany, UK, Spain, France, Netherlands, Poland | Clean Energy Wire, Euractiv Energy, national energy ministries |
| **Asia** | Phase 3 | Indonesia, India, Japan, South Korea | Local energy press, IEA Asia desk, China Dialogue |
| **Africa** | Phase 4 | South Africa, Nigeria, Kenya, Morocco | ESI Africa, IRENA Africa, national utility feeds |

**Scaling rule:** Adding a new country = new rows in the `sources` table + Google News RSS queries for that country's language and geography. No agent code changes.

---

## 8. React Frontend

### Design Principles

- Clean and simple — flat design, generous whitespace, no gradients
- Fun to use — world map as centrepiece, real-time feel with alert animations
- Tab navigation — all views reachable in one click
- Global country/sector filter bar applies across all tabs without page reload
- Mobile-responsive from day one

### Tabs

| Tab | Key components | Core interaction |
|---|---|---|
| **Dashboard** | 4 metric cards, latest stories feed, top contacts | Filter by country, date range, sector |
| **World Map** | D3 GeoJSON map, country circles, real-time alerts | Click country → popup. Pulse for breaking news. Time slider 30 days. |
| **Findings** | Priority list with colour-coded badges, filter bar | CRITICAL / HIGH / COALITION / EVIDENCE filters. Click → full detail + action. |
| **Contacts** | Government contacts + NGO alliance split view | Sort by influence. Click → profile, linked policies, related findings. |
| **Sources** | Active sources table + candidate approval queue | Approve/reject discovery candidates. Toggle active/inactive. |
| **Reports** | Archive with delivery status | Click to read. Resend. Download PDF. Filter by type. |

### World Map

- D3 GeoJSON for accurate country shapes
- Country circles: **size** = story count (last 24h), **colour** = sentiment (red / amber / green / grey)
- Click country → popup: story count, top story, sentiment, critical findings, "View all" link
- Pulse animation on CRITICAL alert via Redis WebSocket
- Starter plan subscribers see non-subscribed countries greyed out
- Time slider: drag back 30 days to see historical activity

### Search

**Phase 1:** PostgreSQL full-text search (tsvector) — keyword search across article titles and summaries, filterable by date, country, sector, significance.

**Phase 2:** pgvector semantic search — find articles by meaning. "Energy sector job losses" returns coal worker redundancy stories without exact keyword match.

---

## 9. Engineering Tasks

Priority: **P0** = blocking · **P1** = required before launch · **P2** = required before scale

---

### Phase 0 — Foundation ✅ Complete

| ID | Task | Detail | Status |
|---|---|---|---|
| T-001 | 14 Paperclip agents operational | All agents created, AGENTS.md written, tested | ✅ Done |
| T-002 | SQLite database with schema | 9 tables, db.py utility, migrate.py | ✅ Done |
| T-003 | Paperclip sync script | sync_from_paperclip.py — 56 issues, 42 runs synced | ✅ Done |
| T-004 | SMTP email delivery | send_email.py, provider-agnostic, tested | ✅ Done |
| T-005 | GitHub repository | github.com/holdersav20001/climate-intelligence-brazil | ✅ Done |

---

### Phase 0.5 — Dockerise 🔧 Next

| ID | Pri | Task | Detail | Effort |
|---|---|---|---|---|
| T-050 | P0 | Write docker-compose.yml | Define 6 services: postgres, redis, paperclip, api, frontend, worker. Named volumes for postgres data and paperclip workspace. Private Docker network. healthcheck on all services. | 4h |
| T-051 | P0 | Dockerfile — FastAPI | Python 3.12-slim base. Install requirements.txt. Non-root user. Expose port 8000. Health endpoint at /health. | 2h |
| T-052 | P0 | Dockerfile — React | Multi-stage: Node 20 build stage + nginx:alpine serve stage. Keeps final image small (~25MB). | 2h |
| T-053 | P0 | Dockerfile — Paperclip | Node 20 base. Install Paperclip and hermes-paperclip-adapter (inactive by default). Mount workspace as volume so data survives container restarts. Pass CLAUDE_API_KEY via env. | 3h |
| T-054 | P0 | Dockerfile — Worker | Node 20-slim. Install BullMQ. Agent heartbeat scheduler reads from sources table, enqueues jobs. | 2h |
| T-055 | P0 | .env.example | All required variables with descriptions and blank values. Committed to Git. Real .env never committed. | 1h |
| T-056 | P0 | docker-compose.override.yml | Local dev overrides: hot reload for API and frontend, expose postgres:5432 for direct DB access. | 1h |
| T-057 | P0 | Migrate workspace config to env vars | Replace hardcoded paths in db.py, send_email.py, agent instructions with environment variable references. All secrets move to .env. | 4h |
| T-058 | P0 | Test full stack locally | `docker compose up` — all 6 services start, Paperclip agents run, postgres migration applies, API /health returns 200, frontend loads. | 4h |
| T-059 | P1 | nginx config + SSL | nginx reverse proxy: port 80/443 → frontend, /api/* → FastAPI, /ws/* → WebSocket. certbot for Let's Encrypt SSL on domain. | 2h |
| T-060 | P1 | Deploy to Hetzner VM | Install Docker on VM. Clone repo. Set .env. `docker compose up -d`. Verify all services healthy. | 2h |
| T-061 | P1 | GitHub Actions CI/CD | On push to main: build images, push to GitHub Container Registry, SSH to VM, pull new images, `docker compose up -d`. Zero-downtime rolling restart. | 4h |

---

### Phase 1 — Production Infrastructure

| ID | Pri | Task | Detail | Effort |
|---|---|---|---|---|
| T-101 | P0 | PostgreSQL schema (Docker) | Convert schema.sql to PostgreSQL syntax. Add monthly partitioning. Add uuid_generate_v4() defaults. Schema auto-applies on first `docker compose up` via docker-entrypoint-initdb.d. | 1 day |
| T-102 | P0 | Tag tables and taxonomy | Create tags, countries, article_tags, article_countries, finding_tags, finding_countries, contact_tags, contact_countries. Seed via seed.sql. | 1 day |
| T-103 | P0 | Tenant tables | Create tenants, tenant_filters, tenant_article_status, contact_access. Add tenant_id enforcement at API layer. | 1 day |
| T-104 | P0 | Sources table | Create sources table. Seed with all 38 current sources plus new specialist publications from section 7. | 1 day |
| T-105 | P0 | Migrate SQLite → PostgreSQL | Run migrate.py against live PostgreSQL container. Verify row counts match. Smoke test key queries. | 4h |
| T-106 | P0 | Update db.py for PostgreSQL | Replace sqlite3 with psycopg2. Read DATABASE_URL from environment. All insert/upsert/query methods unchanged — agents need no updates. | 4h |
| T-107 | P0 | Update agent instructions for Docker | Update absolute paths in AGENTS.md files to match Docker volume mount points. Test each agent writes correctly with tags. | 1 day |
| T-108 | P1 | Redis job queue | BullMQ in worker container. Scout Retrieval enqueues fetch jobs. Analyst/Verifier consume from queue. Prevents concurrent conflicts. | 4h |
| T-109 | P0 | FastAPI backend | FastAPI app in api container. CORS, auth middleware, rate limiting. Endpoints: GET /articles, /findings, /contacts, /sources, /reports, /stats. Tenant filter on all queries. | 2 days |
| T-110 | P0 | JWT authentication | Integrate Supabase Auth or Auth0. /auth/login, /auth/signup. Verify JWT on all protected endpoints. Create first test subscriber. | 1 day |

---

### Phase 2 — Agent Improvements

| ID | Pri | Task | Detail | Effort |
|---|---|---|---|---|
| T-201 | P0 | Split Scout into Discovery + Retrieval | Scout Discovery (daily, GDELT + Google News + link extraction). Scout Retrieval (hourly, reads sources table). Update Orchestrator. | 2 days |
| T-202 | P1 | Source Discovery — link extraction | Extract outbound links from fetched articles. Score domain credibility. Add candidates to sources table. Human approval via Sources tab. | 1 day |
| T-203 | P0 | Auto-tagging in Analyst | Tag each article with country_codes[] and tag_slugs[] from taxonomy. Write to article_tags and article_countries. Confidence score 0.7 for auto-tags. | 1 day |
| T-204 | P1 | Cross-reference linking | Finance Monitor and COP30 Monitor write finding_articles and finding_contacts when creating findings. | 1 day |
| T-205 | P1 | South America sources | Add Colombian, Argentine, Chilean energy sources. Google News RSS per country. Energía Estratégica RSS. | 4h |
| T-206 | P1 | Europe sources | Add German, UK, Spanish, French energy sources. Clean Energy Wire, Euractiv Energy. National energy ministry feeds. | 4h |
| T-207 | P1 | Reporter writes to DB | Reporter calls `db.py insert-report` after every report. email_status, recipient_count, run_date included. | 2h |
| T-208 | P1 | Contact Mapper uses DB | Contact Mapper reads/writes contacts via `db.py upsert-contact`. country_codes and tag_slugs included. | 4h |
| T-209 | P1 | **Hermes on Scout Discovery** | Activate hermes-paperclip-adapter on Scout Discovery. Configure --resume flag. Run 2 weeks. Measure source quality vs pre-Hermes baseline. | 1 day |
| T-210 | P2 | **Hermes on Analyst** | Activate Hermes on Analyst. Remembers tagging accuracy feedback. Deploy only if T-209 shows measurable improvement. | 1 day |
| T-211 | P2 | **Hermes on Contact Mapper** | Activate Hermes on Contact Mapper. Remembers relationship context and influence nuances. | 1 day |

---

### Phase 3 — React Frontend

| ID | Pri | Task | Detail | Effort |
|---|---|---|---|---|
| T-301 | P0 | React app scaffold | Vite + TypeScript. axios, react-query, d3, recharts, tailwindcss. Routing. Auth context. API base URL from VITE_API_URL env var. | 4h |
| T-302 | P0 | Tab navigation and layout | Top tabs: Dashboard, World Map, Findings, Contacts, Sources, Reports. Global country/tag filter. Header with subscriber name, plan badge, alert count. | 1 day |
| T-303 | P0 | Dashboard tab | 4 metric cards, latest stories feed with significance badges, top contacts with influence dots. | 1 day |
| T-304 | P1 | World map tab | D3 GeoJSON map. Country circles by story count and sentiment. Click → popup. Pulse animation via Redis WebSocket. 30-day time slider. | 3 days |
| T-305 | P0 | Findings tab | Priority list with colour-coded left border. Filter bar: ALL / CRITICAL / HIGH / COALITION / EVIDENCE + sector. Click expands to full detail. | 2 days |
| T-306 | P1 | Contacts tab | Split view: government + NGO alliance. Influence dots. Click → profile, linked policies, related findings. Editable ngo_access score. | 2 days |
| T-307 | P1 | Sources tab | Active sources table. Candidate approval queue with Approve/Reject. Add source form. Reliability score visible. | 1 day |
| T-308 | P1 | Reports tab | Archive list with delivery status badges. Read, resend, download PDF. Filter by type. | 1 day |
| T-309 | P1 | Real-time alerts via WebSocket | Redis pub/sub → WebSocket. CRITICAL findings push immediately to React. Notification badge + toast popup. | 1 day |
| T-310 | P1 | Full-text search | PostgreSQL tsvector search across titles and summaries. Results page with relevance ranking. Date, country, sector filters. | 1 day |

---

### Phase 4 — Business

| ID | Pri | Task | Detail | Effort |
|---|---|---|---|---|
| T-401 | P0 | Stripe billing | 3 tiers. Webhook for subscription status. Plan limits enforced at API layer. | 2 days |
| T-402 | P0 | Onboarding flow | Sign-up → plan → Stripe checkout → account → country/sector setup → first digest scheduled. | 2 days |
| T-403 | P1 | Subscriber settings | Filter preferences, mailing list, SMTP config, plan management, API key (Enterprise). | 1 day |
| T-404 | P1 | Usage metering | API calls per tenant per month. Rate limits. Usage visible in settings. Alert at 80% of plan limit. | 1 day |
| T-405 | P1 | Production monitoring | Grafana or Datadog. Agent run success rates, API latency, DB query time, Redis queue depth. Alert if Scout fails 3 consecutive runs. | 1 day |
| T-406 | P2 | pgvector semantic search | Add vector(1536) column to articles. Generate embeddings on ingest. Semantic search endpoint. Replace keyword search in React. | 3 days |

---

## 10. Roadmap

| Phase | Deliverable | Key tasks | Timeline |
|---|---|---|---|
| **Phase 0** ✅ | 14 agents live, SQLite DB, sync script, email, GitHub | T-001–T-005 | April 2026 |
| **Phase 0.5** 🔧 | Docker Compose — full stack containerised, deployed to VM, CI/CD | T-050–T-061 | Late April / early May 2026 |
| **Phase 1** | PostgreSQL, tag schema, FastAPI backend, JWT auth | T-101–T-110 | May 2026 |
| **Phase 2** | Scout split, Hermes (Discovery first), auto-tagging, cross-reference, SA+EU sources | T-201–T-211 | June 2026 |
| **Phase 3** | Full React app — all 6 tabs, world map, real-time alerts, search | T-301–T-310 | July–Aug 2026 |
| **Phase 4** | Stripe billing, onboarding, monitoring, semantic search | T-401–T-406 | Sept 2026 |
| **Phase 5** | Asia-Pacific sources, mobile app, API access tier, white-label | TBD | Q1 2027 |

### Total Engineering Effort Estimate

| Phase | Estimated effort |
|---|---|
| Phase 0.5 — Docker | 2–3 days |
| Phase 1 — Infrastructure | 8–10 days |
| Phase 2 — Agent improvements | 8–10 days |
| Phase 3 — React frontend | 15–18 days |
| Phase 4 — Business | 8–10 days |
| **Total to launch** | **~45 developer-days** |

At 5 days/week for one developer, that is approximately 9 weeks from Phase 0.5 start to launch — **target launch: September 2026.**

### Open Questions Before Phase 0.5 Starts

1. **Cloud provider:** Hetzner CX32 (€3.79/month, cheapest) vs DigitalOcean (simpler UI) vs AWS (most scalable)?
2. **Domain and brand name:** Climate Intel, Pulse, Sinal, Radar? Register domain before Phase 3.
3. **Auth provider:** Supabase Auth (includes managed DB) vs Auth0 (cleaner API)?
4. **Stripe pricing:** Monthly only, or annual discount (2 months free)?
5. **First subscribers:** Outreach to Brazilian NGOs first, or global soft launch?

---

## 11. Immediate Next Steps

| # | Action | Who | When |
|---|---|---|---|
| 1 | **Register for Colombia fossil fuel phase-out conference (CLI-14) — CRITICAL** | Your daughter | **Urgent — April 2026** |
| 2 | Contact Instituto Talanoa about co-signing MME letter on fossil fuel phase-out timeline | Your daughter's team | This week |
| 3 | Enable Scout, Reporter, and Alert heartbeats in Paperclip | You | This week |
| 4 | Update ngo_access scores for contacts your daughter's NGO already knows | Your daughter's team | This week |
| 5 | Decide cloud provider and create account (Hetzner recommended) | You | Before Phase 0.5 |
| 6 | Decide brand name and register domain | You + your daughter | Before Phase 3 |
| 7 | Begin Phase 0.5 — write docker-compose.yml and Dockerfiles | Developer | Now |
| 8 | Test `docker compose up` locally — all 6 services healthy | Developer | End of Phase 0.5 |
| 9 | Deploy Docker stack to Hetzner VM | Developer | End of Phase 0.5 |
| 10 | Sign first 3 paying subscribers to validate pricing before full launch | You | Before Phase 4 |

---

*Climate Intelligence Platform · Version 1.2 · April 2026*
*Built on Paperclip + Claude + Hermes · Docker Compose deployment*
*github.com/holdersav20001/climate-intelligence-brazil*
