# Phase 1 — Production Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Phase 0.5 stub services into a working backend — full FastAPI REST API, JWT auth, real BullMQ job queue, and agent instructions updated for the Docker environment.

**Architecture:** FastAPI serves tenant-filtered data from the climate schema. BullMQ in the worker container manages the Scout → Analyst → Verifier pipeline. Supabase Auth issues JWTs that the API verifies on every request. Agent AGENTS.md files are updated to use Docker volume paths.

**Tech Stack:** FastAPI + psycopg2, Supabase Auth, BullMQ + Redis, Docker Compose

---

## Prerequisites

- Phase 0.5 complete: `docker compose up` starts all 6 services cleanly
- `GET /health` returns `{"status":"ok"}`
- PostgreSQL `climate` schema has 25 tables
- `db.py` uses psycopg2 and reads `CLIMATE_DATABASE_URL`
- `.env` file is populated with real values

---

## T-107: Update Agent Instructions for Docker

**Why:** Every agent AGENTS.md still references the old local absolute path `/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace/` and the SQLite file `intelligence.db`. Inside Docker, the Paperclip container mounts the workspace at `/paperclip/agents/`. The agents also need to know to use `db.py` via `CLIMATE_DATABASE_URL` instead of any SQLite path.

**Affected files — confirmed by grep:**
- `agents/cop30-monitor/AGENTS.md` — 3 absolute paths (workspace, cop30_docs/, cop30_seen.txt)
- `agents/finance-monitor/AGENTS.md` — 3 absolute paths (workspace, finance_deals/, finance_seen.txt)
- `agents/ngo-monitor/AGENTS.md` — 3 absolute paths (workspace, ngo_reports/, ngo_seen.txt)
- `agents/reporter/EMAIL_DELIVERY.md` — 3 absolute paths (pending_review/, send_email.py, pending_review/[file])
- `agents/translator/AGENTS.md` — 1 workspace/ relative path (translations/)
- `agents/contact-mapper/AGENTS.md` — 1 workspace/ relative path (influence_model.json)
- `agents/alert/AGENTS.md` — 1 workspace/ relative path (alert_hashes.json)
- `agents/orchestrator/AGENTS.md` — 1 workspace/ relative path (influence_model.json)
- `agents/parliamentary-monitor/AGENTS.md` — 1 workspace/ relative path (parliament_seen.txt)
- `agents/consultation-writer/AGENTS.md` — 5 workspace/ relative paths
- `agents/policy-tracker/AGENTS.md` — 1 workspace/ relative path (influence_model.json)
- `agents/scout/AGENTS.md` — no path references (no change needed)
- `agents/analyst/AGENTS.md` — no path references (no change needed)
- `agents/verifier/AGENTS.md` — no path references (no change needed)

**Step 1: Open each agent file and read it fully before editing**

Read these four files that contain the hardcoded absolute paths:
- `agents/cop30-monitor/AGENTS.md`
- `agents/finance-monitor/AGENTS.md`
- `agents/ngo-monitor/AGENTS.md`
- `agents/reporter/EMAIL_DELIVERY.md`

**Step 2: Update `agents/cop30-monitor/AGENTS.md`**

Find the `## CRITICAL: File paths` block at the bottom and replace it:

```
## CRITICAL: File paths
Workspace: /home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace
Save docs to: /home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace/cop30_docs/
Dedup: /home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace/cop30_seen.txt
```

Replace with:

```
## CRITICAL: File paths
Workspace: /paperclip/agents/workspace
Save docs to: /paperclip/agents/workspace/cop30_docs/
Dedup: /paperclip/agents/workspace/cop30_seen.txt
```

Also update the inline JSON blob inside the file — find every occurrence of:
`/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace`

Replace all with: `/paperclip/agents/workspace`

**Step 3: Update `agents/finance-monitor/AGENTS.md`**

Replace all occurrences of:
`/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace`

With: `/paperclip/agents/workspace`

This covers both the inline JSON blob and the `## CRITICAL: File paths` block at the bottom.

**Step 4: Update `agents/ngo-monitor/AGENTS.md`**

Replace all occurrences of:
`/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace`

With: `/paperclip/agents/workspace`

**Step 5: Update `agents/reporter/EMAIL_DELIVERY.md`**

Replace all occurrences of:
`/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace`

With: `/paperclip/agents/workspace`

The script invocation line should end up as:
```
python3 /paperclip/agents/workspace/send_email.py \
  --subject "Brazil Energy Intelligence — [date]" \
  --body-file /paperclip/agents/workspace/pending_review/[filename]
```

**Step 6: Add db.py usage note to agents that write structured data**

For agents that produce structured output (cop30-monitor, finance-monitor, ngo-monitor, reporter), append a new section after `## CRITICAL: File paths`:

```markdown
## CRITICAL: Database writes
Use db.py to persist structured intelligence to PostgreSQL.
The database URL is read automatically from $CLIMATE_DATABASE_URL.

Write a finding:
  python3 /paperclip/agents/db.py insert-finding '{"agent":"cop30_monitor","priority":"HIGH","title":"...","body":"...","source_url":"..."}'

Write an article:
  python3 /paperclip/agents/db.py insert-article '{"url":"...","title":"...","summary":"...","source_name":"..."}'

Check if URL already seen (deduplication):
  python3 /paperclip/agents/db.py is-url-seen "https://..."

Mark URL seen after processing:
  python3 /paperclip/agents/db.py mark-url-seen "https://..." "cop30_monitor"

Log a completed run:
  python3 /paperclip/agents/db.py log-run '{"agent_name":"cop30_monitor","status":"succeeded","items_found":3}'

Do NOT reference intelligence.db. Do NOT use SQLite. All data goes to PostgreSQL via db.py.
```

Adjust `"agent":"cop30_monitor"` to the correct agent name for each file.

**Step 7: Verify the workspace/ relative paths in the remaining agents**

The agents below use `workspace/` relative paths without the absolute prefix. These are fine — Paperclip resolves them relative to the company workspace. No changes needed:
- `agents/translator/AGENTS.md` — `workspace/translations/`
- `agents/contact-mapper/AGENTS.md` — `workspace/influence_model.json`
- `agents/alert/AGENTS.md` — `workspace/alert_hashes.json`
- `agents/orchestrator/AGENTS.md` — `workspace/influence_model.json`
- `agents/parliamentary-monitor/AGENTS.md` — `workspace/parliament_seen.txt`
- `agents/consultation-writer/AGENTS.md` — `workspace/articles.jsonl` etc.
- `agents/policy-tracker/AGENTS.md` — `workspace/influence_model.json`

**Step 8: Test**

```bash
# Confirm no old absolute paths remain in any agent file
grep -r "d54903c8" agents/
# Expected: no output

grep -r "intelligence.db" agents/
# Expected: no output

grep -r "/home/holder" agents/
# Expected: no output
```

**Step 9: Commit**

```bash
git add agents/
git commit -m "fix(agents): update all agent file paths for Docker volume mounts"
```

---

## T-108: Redis Job Queue — Real BullMQ Implementation

**Why:** The current `worker/queue.js` is a stub. Scout needs to enqueue fetch jobs when it finds new articles. Analyst and Verifier must consume from the queue, and only one Analyst should run at a time to prevent concurrent conflicts.

**Files to create/modify:**
- Create: `worker/src/queues.js`
- Create: `worker/src/workers.js`
- Create: `worker/src/index.js`
- Modify: `worker/package.json` (add bullmq dependency)
- Replace: `worker/queue.js` (old stub → re-export from src/)

**Step 1: Update `worker/package.json`**

Read the current file first, then ensure it contains:

```json
{
  "name": "climate-intel-worker",
  "version": "1.0.0",
  "type": "module",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js"
  },
  "dependencies": {
    "bullmq": "^5.4.2",
    "ioredis": "^5.3.2"
  }
}
```

**Step 2: Create `worker/src/queues.js`**

This module defines the three queues and exports them. All workers share one Redis connection.

```javascript
// worker/src/queues.js
import { Queue } from 'bullmq';

const redisConnection = {
  host: process.env.REDIS_HOST || 'redis',
  port: parseInt(process.env.REDIS_PORT || '6379'),
};

// article-fetch: Scout enqueues when it finds a new URL
export const articleFetchQueue = new Queue('article-fetch', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

// article-analysis: enqueued after successful fetch
export const articleAnalysisQueue = new Queue('article-analysis', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: 'fixed', delay: 10000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

// article-verify: enqueued after Analyst completes
export const articleVerifyQueue = new Queue('article-verify', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: 'fixed', delay: 5000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

// Helper: enqueue a URL for fetching (called by Scout via HTTP or directly)
export async function enqueueFetch(url, metadata = {}) {
  const job = await articleFetchQueue.add(
    'fetch',
    { url, metadata, enqueuedAt: new Date().toISOString() },
    { jobId: `fetch:${Buffer.from(url).toString('base64url').slice(0, 40)}` }
  );
  return job.id;
}

// Helper: enqueue an article for analysis
export async function enqueueAnalysis(articleId, url, scoutRunId) {
  const job = await articleAnalysisQueue.add(
    'analyse',
    { articleId, url, scoutRunId, enqueuedAt: new Date().toISOString() }
  );
  return job.id;
}

// Helper: enqueue an article for verification
export async function enqueueVerify(articleId, url, analystRunId) {
  const job = await articleVerifyQueue.add(
    'verify',
    { articleId, url, analystRunId, enqueuedAt: new Date().toISOString() }
  );
  return job.id;
}
```

**Step 3: Create `worker/src/workers.js`**

This defines the three Worker processors. The Analyst worker uses `concurrency: 1` to prevent concurrent runs.

```javascript
// worker/src/workers.js
import { Worker } from 'bullmq';
import { enqueueAnalysis, enqueueVerify } from './queues.js';

const redisConnection = {
  host: process.env.REDIS_HOST || 'redis',
  port: parseInt(process.env.REDIS_PORT || '6379'),
};

// ── Fetch Worker ─────────────────────────────────────────────────────────────
// Processes article-fetch jobs. Marks the URL as seen in PostgreSQL,
// then enqueues for analysis.
export function startFetchWorker() {
  const worker = new Worker(
    'article-fetch',
    async (job) => {
      const { url, metadata } = job.data;
      console.log(`[fetch] Processing: ${url}`);

      // Mark URL seen via db.py (exec in paperclip container is unavailable here,
      // so we POST to the internal API instead — see api/app/internal.py)
      // For Phase 1: log the job and pass straight to analysis queue.
      const articleId = metadata.articleId || null;

      if (articleId) {
        const analysisJobId = await enqueueAnalysis(articleId, url, metadata.scoutRunId);
        console.log(`[fetch] Enqueued analysis job ${analysisJobId} for article ${articleId}`);
      } else {
        console.log(`[fetch] No articleId in metadata — article not yet in DB, skipping analysis enqueue`);
      }

      return { url, articleId, processedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 5, // fetch can run in parallel
    }
  );

  worker.on('completed', (job) => {
    console.log(`[fetch] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[fetch] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}

// ── Analysis Worker ──────────────────────────────────────────────────────────
// Processes article-analysis jobs. concurrency: 1 ensures only one
// Analyst runs at a time — prevents concurrent Claude API conflicts.
export function startAnalysisWorker() {
  const worker = new Worker(
    'article-analysis',
    async (job) => {
      const { articleId, url, scoutRunId } = job.data;
      console.log(`[analysis] Processing article ${articleId}: ${url}`);

      // In Phase 1, signal the Paperclip Analyst agent via an internal
      // HTTP call or by writing a trigger record to PostgreSQL.
      // The actual analysis is done by the Paperclip agent; this worker
      // manages sequencing and prevents concurrency.

      // Phase 1 placeholder: log and enqueue verification
      // When Paperclip Analyst integration is wired (Phase 2), this
      // will await the agent completion webhook before enqueueing verify.
      const analystRunId = `worker-${Date.now()}`;
      const verifyJobId = await enqueueVerify(articleId, url, analystRunId);
      console.log(`[analysis] Enqueued verify job ${verifyJobId} for article ${articleId}`);

      return { articleId, url, analystRunId, processedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 1, // CRITICAL: only one Analyst at a time
    }
  );

  worker.on('completed', (job) => {
    console.log(`[analysis] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[analysis] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}

// ── Verify Worker ────────────────────────────────────────────────────────────
// Processes article-verify jobs. Signals the Verifier agent.
export function startVerifyWorker() {
  const worker = new Worker(
    'article-verify',
    async (job) => {
      const { articleId, url, analystRunId } = job.data;
      console.log(`[verify] Processing article ${articleId}: ${url}`);

      // Phase 1 placeholder: log the verification request.
      // Phase 2 will trigger the Paperclip Verifier agent here.

      return { articleId, url, verifiedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 3,
    }
  );

  worker.on('completed', (job) => {
    console.log(`[verify] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[verify] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}
```

**Step 4: Create `worker/src/index.js`**

```javascript
// worker/src/index.js
import { startFetchWorker, startAnalysisWorker, startVerifyWorker } from './workers.js';
import { articleFetchQueue, articleAnalysisQueue, articleVerifyQueue } from './queues.js';

console.log('Climate Intelligence Worker starting...');
console.log(`Redis: ${process.env.REDIS_HOST || 'redis'}:${process.env.REDIS_PORT || '6379'}`);

const fetchWorker = startFetchWorker();
const analysisWorker = startAnalysisWorker();
const verifyWorker = startVerifyWorker();

console.log('Workers started:');
console.log('  article-fetch    (concurrency: 5)');
console.log('  article-analysis (concurrency: 1)');
console.log('  article-verify   (concurrency: 3)');

// Graceful shutdown
async function shutdown() {
  console.log('Shutting down workers...');
  await Promise.all([
    fetchWorker.close(),
    analysisWorker.close(),
    verifyWorker.close(),
    articleFetchQueue.close(),
    articleAnalysisQueue.close(),
    articleVerifyQueue.close(),
  ]);
  console.log('Workers stopped cleanly');
  process.exit(0);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
```

**Step 5: Replace `worker/queue.js` stub**

Read the current stub, then replace its contents with a re-export for backward compatibility:

```javascript
// worker/queue.js
// Re-exports from src/queues.js for backward compatibility.
// New code should import from worker/src/queues.js directly.
export { enqueueFetch, enqueueAnalysis, enqueueVerify } from './src/queues.js';
```

**Step 6: Test the queue**

```bash
# Run the worker container
docker compose up worker -d

# Check it started without errors
docker compose logs worker --tail=30
# Expected: "Climate Intelligence Worker starting..." and "Workers started:"

# Drop into a Node shell in the worker container and enqueue a test job
docker compose exec worker node -e "
  import('./src/queues.js').then(async ({ enqueueFetch }) => {
    const id = await enqueueFetch('https://example.com/test-article', { articleId: 'test-123' });
    console.log('Job enqueued:', id);
    process.exit(0);
  });
"

# Check the worker log again
docker compose logs worker --tail=20
# Expected: "[fetch] Processing: https://example.com/test-article"
# Expected: "[fetch] Job <id> completed"

# Verify job moved through to verify queue (check Redis directly)
docker compose exec redis redis-cli LRANGE "bull:article-verify:wait" 0 -1
```

**Step 7: Commit**

```bash
git add worker/
git commit -m "feat(worker): implement real BullMQ queues — article-fetch, article-analysis, article-verify"
```

---

## T-109: FastAPI Backend — Full REST Endpoints

**Why:** `api/app/main.py` currently returns only `GET /health → {"status":"ok"}`. We need full REST endpoints for the React frontend and external consumers.

**Files to create/modify:**
- Modify: `api/app/main.py` — replace stub with full FastAPI app
- Create: `api/app/models.py` — Pydantic response models
- Create: `api/app/db.py` — database connection helper
- Create: `api/app/routes/articles.py`
- Create: `api/app/routes/findings.py`
- Create: `api/app/routes/contacts.py`
- Create: `api/app/routes/sources.py`
- Create: `api/app/routes/reports.py`
- Create: `api/app/routes/stats.py`
- Create: `api/app/routes/ws.py` — WebSocket alerts
- Modify: `api/requirements.txt` — add dependencies

**Step 1: Update `api/requirements.txt`**

Read the current file, then ensure it contains:

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
psycopg2-binary==2.9.10
pydantic==2.9.2
python-jose[cryptography]==3.3.0
httpx==0.27.2
redis==5.2.0
slowapi==0.1.9
```

**Step 2: Create `api/app/db.py`**

```python
# api/app/db.py
"""
PostgreSQL connection pool for FastAPI.
Reads CLIMATE_DATABASE_URL which already sets search_path=climate.
"""
import os
import psycopg2
import psycopg2.pool
from contextlib import contextmanager

DATABASE_URL = os.environ.get(
    "CLIMATE_DATABASE_URL",
    "postgresql://climate_intel:password@postgres:5432/climate_intel?options=-csearch_path%3Dclimate"
)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL,
        )
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute(sql: str, params: tuple = ()) -> int:
    """Returns rowcount."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
```

**Step 3: Create `api/app/models.py`**

```python
# api/app/models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class ArticleOut(BaseModel):
    id: str
    url: str
    title: str
    summary: Optional[str] = None
    source_name: Optional[str] = None
    domain: Optional[str] = None
    topic: Optional[str] = None
    significance: Optional[float] = None
    verified: bool = False
    sentiment_overall: Optional[float] = None
    sentiment_environmental: Optional[float] = None
    sentiment_economic: Optional[float] = None
    sentiment_political: Optional[float] = None
    sentiment_social: Optional[float] = None
    sentiment_framing: Optional[float] = None
    country_codes: list[str] = []
    tag_slugs: list[str] = []
    language: str = "en"
    fetched_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    run_date: Optional[date] = None


class FindingOut(BaseModel):
    id: str
    agent: str
    priority: str
    category: Optional[str] = None
    title: str
    body: str
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    action_required: Optional[str] = None
    deadline: Optional[date] = None
    coalition_opportunity: bool = False
    evidence_value: Optional[str] = None
    country_codes: list[str] = []
    tag_slugs: list[str] = []
    status: str = "open"
    run_date: Optional[date] = None
    created_at: Optional[datetime] = None


class ContactOut(BaseModel):
    id: str
    name: str
    role: str
    organisation: str
    organisation_type: Optional[str] = None
    decision_power: Optional[int] = None
    ngo_access: int = 1
    influence_score: Optional[float] = None
    profile_url: Optional[str] = None
    email: Optional[str] = None
    why_relevant: Optional[str] = None
    country_code: Optional[str] = None
    last_updated: Optional[datetime] = None


class SourceOut(BaseModel):
    id: str
    name: str
    url: str
    feed_url: Optional[str] = None
    source_type: Optional[str] = None
    country_code: Optional[str] = None
    language: str = "en"
    active: bool = True
    approved: bool = False
    last_fetched: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ReportOut(BaseModel):
    id: str
    title: str
    subject: Optional[str] = None
    body: str
    report_type: Optional[str] = None
    run_date: Optional[date] = None
    sent_at: Optional[datetime] = None
    email_status: str = "pending"
    recipient_count: int = 0
    created_at: Optional[datetime] = None


class StatsOut(BaseModel):
    articles: int
    findings: int
    contacts: int
    sources: int
    reports: int
    run_log: int
    as_of: datetime


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    has_more: bool
```

**Step 4: Create `api/app/routes/articles.py`**

```python
# api/app/routes/articles.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import ArticleOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/articles", tags=["articles"])

DEV_TENANT_COUNTRIES = ["BR"]  # Phase 1: hardcoded dev tenant


@router.get("", response_model=PaginatedResponse)
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    domain: Optional[str] = None,
    min_significance: Optional[float] = None,
    topic: Optional[str] = None,
    verified: Optional[bool] = None,
    run_date: Optional[str] = None,
):
    """
    List articles filtered to the tenant's countries.
    Ordered by significance DESC, fetched_at DESC.
    """
    filters = ["country_codes && %s::text[]"]
    params: list = [DEV_TENANT_COUNTRIES]

    if domain:
        filters.append("domain = %s")
        params.append(domain)
    if min_significance is not None:
        filters.append("significance >= %s")
        params.append(min_significance)
    if topic:
        filters.append("topic = %s")
        params.append(topic)
    if verified is not None:
        filters.append("verified = %s")
        params.append(verified)
    if run_date:
        filters.append("run_date = %s")
        params.append(run_date)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM articles WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, url, title, summary, source_name, domain, topic,
               significance, verified,
               sentiment_overall, sentiment_environmental, sentiment_economic,
               sentiment_political, sentiment_social, sentiment_framing,
               country_codes, tag_slugs, language,
               fetched_at, published_at, run_date
        FROM articles
        WHERE {where}
        ORDER BY significance DESC NULLS LAST, fetched_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ArticleOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: str):
    rows = query(
        """
        SELECT id::text, url, title, summary, source_name, domain, topic,
               significance, verified,
               sentiment_overall, sentiment_environmental, sentiment_economic,
               sentiment_political, sentiment_social, sentiment_framing,
               country_codes, tag_slugs, language,
               fetched_at, published_at, run_date
        FROM articles WHERE id = %s AND country_codes && %s::text[]
        """,
        (article_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut(**rows[0])
```

**Step 5: Create `api/app/routes/findings.py`**

```python
# api/app/routes/findings.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import FindingOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/findings", tags=["findings"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=PaginatedResponse)
def list_findings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    priority: Optional[str] = None,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    coalition_opportunity: Optional[bool] = None,
):
    filters = ["country_codes && %s::text[]"]
    params: list = [DEV_TENANT_COUNTRIES]

    if priority:
        filters.append("priority = %s")
        params.append(priority.upper())
    if agent:
        filters.append("agent = %s")
        params.append(agent)
    if status:
        filters.append("status = %s")
        params.append(status)
    if coalition_opportunity is not None:
        filters.append("coalition_opportunity = %s")
        params.append(coalition_opportunity)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM findings WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, agent, priority, category, title, body,
               source_url, source_name, action_required, deadline,
               coalition_opportunity, evidence_value,
               country_codes, tag_slugs, status, run_date, created_at
        FROM findings
        WHERE {where}
        ORDER BY
          CASE priority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'COALITION' THEN 3
            WHEN 'EVIDENCE' THEN 4
            WHEN 'MEDIUM' THEN 5
            WHEN 'LOW' THEN 6
            ELSE 7
          END,
          created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[FindingOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
```

**Step 6: Create `api/app/routes/contacts.py`**

```python
# api/app/routes/contacts.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import ContactOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/contacts", tags=["contacts"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=PaginatedResponse)
def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organisation_type: Optional[str] = None,
    min_influence: Optional[float] = None,
):
    filters = ["country_code = ANY(%s::text[])"]
    params: list = [DEV_TENANT_COUNTRIES]

    if organisation_type:
        filters.append("organisation_type = %s")
        params.append(organisation_type)
    if min_influence is not None:
        filters.append("influence_score >= %s")
        params.append(min_influence)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM contacts WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, name, role, organisation, organisation_type,
               decision_power, ngo_access, influence_score,
               profile_url, email, why_relevant, country_code, last_updated
        FROM contacts
        WHERE {where}
        ORDER BY influence_score DESC NULLS LAST, decision_power DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ContactOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
```

**Step 7: Create `api/app/routes/sources.py`**

```python
# api/app/routes/sources.py
from fastapi import APIRouter, HTTPException
from ..models import SourceOut, PaginatedResponse
from ..db import query, execute

router = APIRouter(prefix="/sources", tags=["sources"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=PaginatedResponse)
def list_sources(page: int = 1, page_size: int = 50):
    filters = ["country_code = ANY(%s::text[])"]
    params: list = [DEV_TENANT_COUNTRIES]
    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM sources WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, name, url, feed_url, source_type, country_code,
               language, active, approved, last_fetched, created_at
        FROM sources WHERE {where}
        ORDER BY name ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[SourceOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.post("/{source_id}/approve", status_code=200)
def approve_source(source_id: str):
    rows = query(
        "SELECT id FROM sources WHERE id = %s AND country_code = ANY(%s::text[])",
        (source_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")

    execute(
        "UPDATE sources SET approved = true, active = true WHERE id = %s",
        (source_id,),
    )
    return {"id": source_id, "approved": True}


@router.post("/{source_id}/reject", status_code=200)
def reject_source(source_id: str):
    rows = query(
        "SELECT id FROM sources WHERE id = %s AND country_code = ANY(%s::text[])",
        (source_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")

    execute(
        "UPDATE sources SET approved = false, active = false WHERE id = %s",
        (source_id,),
    )
    return {"id": source_id, "approved": False, "active": False}
```

**Step 8: Create `api/app/routes/reports.py`**

```python
# api/app/routes/reports.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import ReportOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/reports", tags=["reports"])

DEV_TENANT_ID = "dev-tenant-br"  # Phase 1 hardcoded — replaced by JWT in T-110


@router.get("", response_model=PaginatedResponse)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = None,
):
    filters = ["tenant_id = %s"]
    params: list = [DEV_TENANT_ID]

    if report_type:
        filters.append("report_type = %s")
        params.append(report_type)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM reports WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, title, subject, body, report_type, run_date,
               sent_at, email_status, recipient_count, created_at
        FROM reports WHERE {where}
        ORDER BY run_date DESC, created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ReportOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
```

**Step 9: Create `api/app/routes/stats.py`**

```python
# api/app/routes/stats.py
from fastapi import APIRouter
from datetime import datetime
from ..models import StatsOut
from ..db import query

router = APIRouter(prefix="/stats", tags=["stats"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=StatsOut)
def get_stats():
    def count(table: str, where: str = "TRUE", params: tuple = ()) -> int:
        rows = query(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", params)
        return rows[0]["n"] if rows else 0

    return StatsOut(
        articles=count("articles", "country_codes && %s::text[]", (DEV_TENANT_COUNTRIES,)),
        findings=count("findings", "country_codes && %s::text[]", (DEV_TENANT_COUNTRIES,)),
        contacts=count("contacts", "country_code = ANY(%s::text[])", (DEV_TENANT_COUNTRIES,)),
        sources=count("sources", "country_code = ANY(%s::text[])", (DEV_TENANT_COUNTRIES,)),
        reports=count("reports"),
        run_log=count("run_log"),
        as_of=datetime.utcnow(),
    )
```

**Step 10: Create `api/app/routes/ws.py`**

```python
# api/app/routes/ws.py
"""
WebSocket endpoint: GET /ws/alerts
Subscribes to Redis pub/sub channel "alerts" and pushes messages to
connected clients in real time.
"""
import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

router = APIRouter(tags=["websocket"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("alerts")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    data = {"text": message["data"]}
                await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("alerts")
        await r.aclose()
```

**Step 11: Replace `api/app/main.py`**

Read the current stub, then replace with:

```python
# api/app/main.py
"""
Climate Intelligence Platform — FastAPI application
Phase 1: Full REST endpoints with tenant filtering.
JWT auth (T-110) adds real tenant_id extraction from bearer tokens.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import articles, findings, contacts, sources, reports, stats, ws

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Climate Intelligence Platform API",
    version="1.0.0",
    description="Tenant-filtered energy intelligence for NGOs, think tanks, journalists.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow React frontend (dev and prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "https://app.climateintel.br",  # Production frontend (future)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register routers
app.include_router(articles.router)
app.include_router(findings.router)
app.include_router(contacts.router)
app.include_router(sources.router)
app.include_router(reports.router)
app.include_router(stats.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "Climate Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }
```

**Step 12: Create `api/app/routes/__init__.py`**

Create an empty `__init__.py` in `api/app/routes/` if it does not already exist:

```python
# api/app/routes/__init__.py
```

**Step 13: Test every endpoint**

```bash
# Restart the API container
docker compose restart api

# Wait for startup
sleep 3
docker compose logs api --tail=20
# Expected: "Application startup complete"

# Health check
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "ok", "version": "1.0.0"}

# Stats (will show 0 rows if no data yet — that is correct)
curl -s http://localhost:8000/stats | python3 -m json.tool
# Expected: {"articles": 0, "findings": 0, ...}

# Articles (empty list — correct)
curl -s "http://localhost:8000/articles?page=1&page_size=5" | python3 -m json.tool
# Expected: {"items": [], "total": 0, "page": 1, "page_size": 5, "has_more": false}

# Findings
curl -s "http://localhost:8000/findings?priority=HIGH" | python3 -m json.tool

# Sources
curl -s "http://localhost:8000/sources" | python3 -m json.tool

# Approve a source (replace <id> with a real UUID from the sources table)
# psql -c "SELECT id FROM climate.sources LIMIT 1"
curl -s -X POST "http://localhost:8000/sources/<id>/approve" | python3 -m json.tool
# Expected: {"id": "<id>", "approved": true}

# OpenAPI docs (open in browser)
# http://localhost:8000/docs

# WebSocket test (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/ws/alerts
# Then in another terminal, publish a test alert:
docker compose exec redis redis-cli PUBLISH alerts '{"type":"test","message":"hello"}'
# Expected: wscat receives {"type":"test","message":"hello"}
```

**Step 14: Commit**

```bash
git add api/
git commit -m "feat(api): implement full FastAPI REST endpoints — articles, findings, contacts, sources, reports, stats, WebSocket"
```

---

## T-110: JWT Authentication

**Why:** Every data endpoint must be scoped to a tenant. Supabase Auth issues JWTs; the API verifies the token on every request and extracts `tenant_id` from the claims. This replaces the hardcoded `DEV_TENANT_COUNTRIES = ["BR"]` with real per-tenant country filtering.

**Decision:** Supabase Auth over Auth0 — see `decision_history.md`. Supabase is self-hostable, has a Python JWT library, and the `tenant_id` custom claim fits naturally in the JWT payload.

**Files to create/modify:**
- Create: `api/app/auth.py` — JWT verification middleware + dependency
- Create: `api/app/routes/auth.py` — `/auth/login`, `/auth/signup` endpoints
- Modify: `api/app/main.py` — add auth router, remove hardcoded tenant
- Modify: `api/app/routes/articles.py` — replace hardcoded `DEV_TENANT_COUNTRIES` with `current_user` dependency
- Modify: `api/app/routes/findings.py` — same
- Modify: `api/app/routes/contacts.py` — same
- Modify: `api/app/routes/sources.py` — same
- Modify: `api/app/routes/stats.py` — same
- Add: database migration for first test subscriber (SQL command below)
- Modify: `.env.example` — add Supabase variables

**Step 1: Add Supabase variables to `.env.example`**

Read the current `.env.example` then append:

```bash
# ── Supabase Auth ────────────────────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
# Get JWT secret from: Supabase dashboard → Settings → API → JWT Secret
```

**Step 2: Add `supabase` to `api/requirements.txt`**

```
supabase==2.9.1
```

**Step 3: Create `api/app/auth.py`**

```python
# api/app/auth.py
"""
JWT authentication for the Climate Intelligence Platform API.

Token flow:
1. Client calls POST /auth/login with email + password
2. Supabase returns a JWT with custom claims: { tenant_id, countries }
3. Client sends: Authorization: Bearer <token>
4. Every protected endpoint calls Depends(get_current_user)
5. get_current_user verifies the JWT, extracts tenant_countries,
   and returns a CurrentUser object used for data filtering.

Phase 1 dev shortcut: if ENVIRONMENT=development and no token is
provided, a default dev user is returned (BR tenant, no auth required).
This is removed before any real deployment.
"""
import os
import json
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[str] = None
    tenant_id: str
    tenant_countries: list[str]
    is_dev: bool = False


# Phase 1 dev fallback — no token required in development
DEV_USER = CurrentUser(
    user_id="dev-user",
    email="dev@climateintel.br",
    tenant_id="dev-tenant-br",
    tenant_countries=["BR"],
    is_dev=True,
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    # Development shortcut: no token needed
    if ENVIRONMENT == "development" and not credentials:
        return DEV_USER

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if not SUPABASE_JWT_SECRET:
        # If no JWT secret is configured in development, accept the dev user
        if ENVIRONMENT == "development":
            return DEV_USER
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},  # Supabase uses custom aud
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract standard Supabase claims
    user_id = payload.get("sub")
    email = payload.get("email")

    # Extract custom claims (set in Supabase Auth hooks)
    app_metadata = payload.get("app_metadata", {})
    user_metadata = payload.get("user_metadata", {})

    tenant_id = app_metadata.get("tenant_id") or user_metadata.get("tenant_id")
    tenant_countries = app_metadata.get("countries") or user_metadata.get("countries", ["BR"])

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant_id in token claims. Contact support.",
        )

    return CurrentUser(
        user_id=user_id,
        email=email,
        tenant_id=tenant_id,
        tenant_countries=tenant_countries if isinstance(tenant_countries, list) else [tenant_countries],
    )
```

**Step 4: Create `api/app/routes/auth.py`**

```python
# api/app/routes/auth.py
"""
Auth endpoints — thin wrapper around Supabase Auth.
The API itself does not store passwords. Supabase handles credentials.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"email": body.email, "password": body.password},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        token_type="bearer",
        expires_in=data.get("expires_in", 3600),
        refresh_token=data.get("refresh_token", ""),
    )


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={
                "email": body.email,
                "password": body.password,
                "data": {"full_name": body.full_name},
            },
            timeout=10,
        )

    if resp.status_code not in (200, 201):
        detail = resp.json().get("msg", "Signup failed")
        raise HTTPException(status_code=400, detail=detail)

    return {"message": "Account created. Check your email to confirm."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"refresh_token": refresh_token},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        token_type="bearer",
        expires_in=data.get("expires_in", 3600),
        refresh_token=data.get("refresh_token", ""),
    )
```

**Step 5: Update `api/app/routes/articles.py` to use JWT tenant**

Replace the hardcoded `DEV_TENANT_COUNTRIES = ["BR"]` and add `Depends(get_current_user)`:

```python
# At the top of api/app/routes/articles.py, replace the DEV_TENANT_COUNTRIES line:
from fastapi import APIRouter, Query, Depends
from ..auth import get_current_user, CurrentUser

# Remove: DEV_TENANT_COUNTRIES = ["BR"]

# In list_articles signature, add:
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    domain: Optional[str] = None,
    min_significance: Optional[float] = None,
    topic: Optional[str] = None,
    verified: Optional[bool] = None,
    run_date: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    # Replace all references to DEV_TENANT_COUNTRIES with current_user.tenant_countries
    filters = ["country_codes && %s::text[]"]
    params: list = [current_user.tenant_countries]
    # ... rest unchanged
```

Apply the same `Depends(get_current_user)` pattern to `get_article()`.

**Step 6: Apply the same tenant injection to all other route files**

For each of these files, add `Depends(get_current_user)` to every endpoint function and replace `DEV_TENANT_COUNTRIES` / `DEV_TENANT_ID` with `current_user.tenant_countries` or `current_user.tenant_id`:

- `api/app/routes/findings.py`
- `api/app/routes/contacts.py`
- `api/app/routes/sources.py`
- `api/app/routes/reports.py`
- `api/app/routes/stats.py`

**Step 7: Update `api/app/main.py` to register the auth router**

Add to the router registrations in `main.py`:

```python
from .routes import auth as auth_routes
app.include_router(auth_routes.router)
```

**Step 8: Create the first test subscriber in PostgreSQL**

Run this SQL to create a dev tenant and a test subscriber. This seeds data used by the dev shortcut in `auth.py`:

```sql
-- Run via: docker compose exec postgres psql -U climate_intel -d climate_intel

SET search_path TO climate;

-- Insert dev tenant
INSERT INTO tenants (id, name, slug, plan, country_codes, active)
VALUES (
    gen_random_uuid(),
    'Climate Intelligence Dev',
    'dev-tenant-br',
    'trial',
    ARRAY['BR'],
    true
)
ON CONFLICT (slug) DO NOTHING;

-- Insert test subscriber contact (for email delivery testing)
INSERT INTO contacts (id, name, role, organisation, country_code, email, ngo_access)
VALUES (
    gen_random_uuid(),
    'Dev Subscriber',
    'Platform Tester',
    'Climate Intelligence Brazil',
    'BR',
    'dev@climateintel.br',
    1
)
ON CONFLICT DO NOTHING;

SELECT id, name, slug, country_codes FROM tenants WHERE slug = 'dev-tenant-br';
```

**Step 9: Test JWT auth**

```bash
# Restart the API
docker compose restart api
docker compose logs api --tail=20

# Development mode: no token needed (ENVIRONMENT=development)
curl -s http://localhost:8000/articles | python3 -m json.tool
# Expected: articles list (scoped to BR) — works without a token in dev mode

# Test the health endpoint (no auth required)
curl -s http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

# Test login (requires Supabase to be configured — skip if not yet set up)
# If SUPABASE_URL is set:
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@climateintel.br","password":"testpassword123"}' \
  | python3 -m json.tool
# Expected: {"access_token":"eyJ...","token_type":"bearer","expires_in":3600,...}

# Test authenticated request with a real token
TOKEN="eyJ..."  # from the login response above
curl -s http://localhost:8000/articles \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
# Expected: articles filtered to the token's tenant_countries

# Test rejected request with an invalid token
curl -s http://localhost:8000/articles \
  -H "Authorization: Bearer invalid-token" \
  | python3 -m json.tool
# Expected: {"detail":"Invalid token: ..."}

# Verify the OpenAPI schema shows the security requirement
curl -s http://localhost:8000/openapi.json | python3 -m json.tool | grep -A5 '"security"'
```

**Step 10: Commit**

```bash
git add api/ .env.example
git commit -m "feat(auth): add Supabase JWT authentication — login, signup, tenant-filtered endpoints"
```

---

## End-to-End Smoke Test

Run this after all four tasks are complete to verify the full stack.

```bash
# 1. Start everything
docker compose up -d
sleep 10

# 2. Verify all services are healthy
docker compose ps
# Expected: 6 services Up (postgres, redis, paperclip, api, frontend, worker)

# 3. Health check
curl -s http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

# 4. Stats (will be zero — that is correct at this point)
curl -s http://localhost:8000/stats | python3 -m json.tool

# 5. Seed one test article directly into PostgreSQL
docker compose exec postgres psql -U climate_intel -d climate_intel -c "
  INSERT INTO climate.articles (url, title, summary, source_name, domain,
    significance, country_codes, run_date, fetched_at)
  VALUES (
    'https://www.gov.br/mme/pt-br/test-article',
    'MME Announces New Renewable Energy Targets',
    'Brazil MME sets 2030 renewable targets at 80% of grid capacity.',
    'MME',
    'policy',
    0.85,
    ARRAY['BR'],
    CURRENT_DATE,
    NOW()
  );
"

# 6. Verify article appears in API
curl -s "http://localhost:8000/articles" | python3 -m json.tool
# Expected: items array with 1 article, significance 0.85

# 7. Verify stats updated
curl -s "http://localhost:8000/stats" | python3 -m json.tool
# Expected: {"articles": 1, ...}

# 8. Enqueue a test job to the worker
docker compose exec worker node -e "
  import('./src/queues.js').then(async ({ enqueueFetch }) => {
    const id = await enqueueFetch('https://www.aneel.gov.br/test', { articleId: 'smoke-test' });
    console.log('Job ID:', id);
    process.exit(0);
  });
"
docker compose logs worker --tail=10
# Expected: "[fetch] Processing: https://www.aneel.gov.br/test"

# 9. Confirm agent file paths are updated
grep -r "d54903c8" agents/
# Expected: no output

grep -r "intelligence.db" agents/
# Expected: no output
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `api` container exits with `ModuleNotFoundError: No module named 'slowapi'` | `api/requirements.txt` not updated or image not rebuilt | `docker compose build api && docker compose up -d api` |
| `GET /articles` returns 500 with `psycopg2.OperationalError` | `CLIMATE_DATABASE_URL` not set or postgres not ready | Check `.env` has `CLIMATE_DATABASE_URL`; run `docker compose logs postgres` |
| `GET /articles` returns 500 with `relation "articles" does not exist` | Schema not applied or search_path wrong | Check `?options=-csearch_path%3Dclimate` in URL; run `docker compose exec postgres psql -U climate_intel -d climate_intel -c "\dt climate.*"` |
| Worker starts but `[fetch]` line never appears in logs | BullMQ can't connect to Redis | Check `REDIS_HOST=redis` is reachable; `docker compose exec worker ping redis` |
| Worker exits immediately with `Cannot find package 'bullmq'` | npm install not run after package.json change | `docker compose build worker && docker compose up -d worker` |
| `POST /auth/login` returns 503 `Auth service not configured` | `SUPABASE_URL` or `SUPABASE_ANON_KEY` not in `.env` | Add Supabase credentials to `.env`; they are not required in development mode |
| `GET /articles` returns 401 in production but 200 in dev | `ENVIRONMENT` env var not set to `development` | Add `ENVIRONMENT=development` to `.env` for local dev; remove for production |
| JWT decode fails with `Signature verification failed` | Wrong `SUPABASE_JWT_SECRET` | Copy the exact secret from Supabase dashboard → Settings → API → JWT Secret |
| WebSocket disconnects immediately | Redis pub/sub connection fails | Check Redis is running: `docker compose exec redis redis-cli ping` → `PONG` |
| `POST /sources/<id>/approve` returns 404 | No sources in the `sources` table yet | Seed a source: `docker compose exec postgres psql -U climate_intel -d climate_intel -c "INSERT INTO climate.sources (name, url, country_code) VALUES ('Test', 'https://test.com', 'BR');"` |
| `agents/cop30-monitor/AGENTS.md` still contains old path after edit | String not unique in file — Edit tool failed | Use `replace_all: true` in the Edit tool call |
| `docker compose up` fails with `port 8000 already in use` | Something else is running on 8000 | `lsof -i :8000` (WSL) or change port in `docker-compose.yml` |
