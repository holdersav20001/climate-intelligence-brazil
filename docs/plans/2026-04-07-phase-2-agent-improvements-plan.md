# Phase 2 — Agent Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve agent intelligence — split Scout, add auto-tagging, enable cross-references, expand sources to South America and Europe, activate Hermes memory on Scout Discovery.

**Architecture:** Scout splits into daily Discovery (finds new sources) and hourly Retrieval (fetches known sources). Analyst tags articles with country_codes[] and tag_slugs[] arrays. Finance and COP30 monitors write cross-reference links. Hermes gives Scout Discovery persistent memory across heartbeats.

**Tech Stack:** Paperclip + Claude Haiku 4.5, PostgreSQL (climate schema), db.py CLI, hermes-paperclip-adapter

---

## Prerequisites

Before any task begins:

- Phase 1 is complete and `docker compose up` starts cleanly
- All 14 agents have valid `AGENTS.md` files in `./agents/<name>/AGENTS.md`
- `database/db.py` is the single CLI utility all agents use
- `database/schema.sql` is the SQLite schema (used for local dev; PostgreSQL via psycopg2 for prod)
- The `seen_urls` table exists and `db.py is-url-seen` / `mark-url-seen` work
- `hermes-paperclip-adapter` is installed in the Paperclip container but currently inactive

**Verify the baseline before starting:**
```bash
python3 database/db.py stats
python3 database/db.py is-url-seen "https://test.example.com"
```

---

## Task T-201: Split Scout into Discovery + Retrieval

**Why:** The current Scout does too much in one run — it finds new sources AND fetches them AND deduplicates. Splitting separates concerns: Discovery runs once daily and populates a candidates queue; Retrieval runs hourly and processes it. This also makes it possible to apply Hermes memory selectively to Discovery (T-209).

### Step 1: Add `sources` table to schema

The `sources` table is referenced by both Scout agents but does not yet exist in `database/schema.sql`.

**File to modify:** `database/schema.sql`

Append the following to the end of the file:

```sql
-- Sources: feed URLs that Scout Discovery finds and Scout Retrieval fetches
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    feed_type TEXT,          -- rss | atom | gdelt | google_news | html
    status TEXT DEFAULT 'candidate',  -- candidate | active | paused | rejected
    country_code TEXT,
    language TEXT DEFAULT 'en',
    discovered_by TEXT,      -- link_extraction | gdelt | google_news_rss | manual
    credibility_tier TEXT,   -- high | medium | low
    last_fetched TIMESTAMPTZ,
    fetch_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_last_fetched ON sources(last_fetched);
CREATE INDEX IF NOT EXISTS idx_sources_country ON sources(country_code);
```

**Verify:**
```bash
python3 database/db.py query "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"
```
Expected: `[{"name": "sources"}]`

### Step 2: Add `insert-source` command to `db.py`

**File to modify:** `database/db.py`

**2a.** Add the `insert_source` method to the `DB` class, after the `insert_ngo_intel` method:

```python
def insert_source(self, s):
    row_id = s.get("id") or new_id()
    try:
        self.conn.execute("""INSERT OR IGNORE INTO sources
            (id,url,name,feed_type,status,country_code,language,
             discovered_by,credibility_tier,notes,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, s.get("url"), s.get("name"),
            s.get("feed_type","rss"),
            s.get("status","candidate"),
            s.get("country_code"), s.get("language","en"),
            s.get("discovered_by","manual"),
            s.get("credibility_tier","medium"),
            s.get("notes"), now(), now()))
        self.conn.commit()
        return row_id if self.conn.total_changes > 0 else None
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return None
```

**2b.** Add the CLI handler in the `cli()` function, after the `insert-finance-deal` handler:

```python
elif cmd == "insert-source" and len(sys.argv) > 2:
    result = db.insert_source(json.loads(sys.argv[2]))
    print(result if result else "exists")
```

**Verify:**
```bash
python3 database/db.py insert-source '{"url":"https://test-source.example.com/feed","name":"Test Source","status":"candidate","credibility_tier":"high"}'
python3 database/db.py query "SELECT url, status, credibility_tier FROM sources LIMIT 1"
```

### Step 3: Create Scout Discovery agent

**File to create:** `agents/scout-discovery/AGENTS.md`

```markdown
---
name: "Scout Discovery"
title: "Source Discovery Agent"
reportsTo: "orchestrator"
heartbeat: daily
model: claude-haiku-4-5
---

# Scout Discovery — Daily Source Discovery

You are Scout Discovery for the Climate Intelligence Platform.
You run once per day. Your only job is to find new source URLs and
add them as candidates to the sources table. You do NOT fetch article
content — that is Scout Retrieval's job.

## Mission
Discover new RSS feeds, API endpoints, and web sources about Brazil
energy policy. Score each for credibility. Add unknown credible sources
as candidates in the database.

## Coverage — Brazil focus, South America and Europe secondary
- Brazil: MME, ANEEL, ANP, EPE, IBAMA, Petrobras, BNDES, Agência Brasil
- South America: Colombia, Argentina, Chile energy ministries
- Europe: Germany (BMWK), UK (DESNZ), Spain, France energy policy
- International: IEA, IRENA, UNFCCC, World Bank energy

## Discovery methods (run all three each day)

### Method 1 — GDELT DOC API
Query the GDELT Document API for recent Brazil energy stories.
Extract all unique source domains from results.
Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc?query=brazil+energy+policy&mode=artlist&maxrecords=250&format=json`
For each domain found: check credibility tier, check if already known.

### Method 2 — Google News RSS
Fetch these RSS feeds and extract source domains from item links:
- `https://news.google.com/rss/search?q=brazil+energy+policy&hl=en&gl=BR&ceid=BR:en`
- `https://news.google.com/rss/search?q=energia+brasil+politica&hl=pt-BR&gl=BR&ceid=BR:pt-419`
- `https://news.google.com/rss/search?q=energia+colombia&hl=es&gl=CO&ceid=CO:es`
- `https://news.google.com/rss/search?q=energia+argentina&hl=es&gl=AR&ceid=AR:es`
- `https://news.google.com/rss/search?q=energiewende&hl=de&gl=DE&ceid=DE:de`
- `https://news.google.com/rss/search?q=uk+energy+policy&hl=en-GB&gl=GB&ceid=GB:en`

### Method 3 — Link extraction from recent articles
Query the database for articles fetched in the last 7 days:
`python3 db.py query "SELECT url FROM articles WHERE fetched_at > datetime('now','-7 days') ORDER BY significance DESC LIMIT 50"`
For each article URL: fetch the page and extract all outbound links (href attributes).
Filter to links that look like news articles or feeds (contain /feed, /rss, .xml, or are from news domains).

## Credibility scoring
Score each discovered domain before inserting:
- HIGH: .gov, .gov.br, .gov.co, .gov.ar, .gov.cl, .gov.uk, .bmwk.de, known publishers
  (agenciabrasil.ebc.gov.br, valor.globo.com, brazilenergyinsight.com, cleanenergywire.org,
  euractiv.com, iea.org, irena.org, unfccc.int, bndes.gov.br, petrobras.com.br)
- MEDIUM: established news organisations, industry publications, think tanks
- LOW: blogs, social media aggregators, unknown domains, domains with ads-heavy patterns

## Deduplication before inserting
For each candidate URL, check if it is already known:
```
python3 db.py query "SELECT 1 FROM sources WHERE url='<url>' LIMIT 1"
```
If result is non-empty: skip. Do not insert duplicates.

## Inserting new candidates
Only insert if: credibility_tier is HIGH or MEDIUM.
Do NOT insert LOW credibility sources — log them in your run notes instead.

```
python3 db.py insert-source '{"url":"<feed_url>","name":"<publication_name>","feed_type":"rss","status":"candidate","country_code":"BR","discovered_by":"link_extraction","credibility_tier":"high"}'
```

Valid values for `discovered_by`: `gdelt`, `google_news_rss`, `link_extraction`, `manual`
Valid values for `feed_type`: `rss`, `atom`, `gdelt`, `google_news`, `html`
Valid values for `country_code`: ISO 3166-1 alpha-2 (BR, CO, AR, CL, DE, GB, ES, FR)

## End of run
Log your run with items_found = number of new candidates inserted:
```
python3 db.py log-run '{"agent_name":"scout_discovery","status":"succeeded","items_found":<N>,"notes":"<summary of what was found>"}'
```

## What you do NOT do
- Do NOT fetch article content
- Do NOT create findings or reports
- Do NOT contact other agents directly
- Do NOT insert LOW credibility sources
- Do NOT re-insert known sources
```

### Step 4: Create Scout Retrieval agent

**File to create:** `agents/scout-retrieval/AGENTS.md`

```markdown
---
name: "Scout Retrieval"
title: "Source Fetching Agent"
reportsTo: "orchestrator"
heartbeat: hourly
model: claude-haiku-4-5
---

# Scout Retrieval — Hourly Source Fetcher

You are Scout Retrieval for the Climate Intelligence Platform.
You run every hour. Your job is to fetch content from active sources
and hand new articles to the Analyst queue via Redis.

## Mission
Read active sources from the database, fetch their feeds, deduplicate
against seen_urls, and write new article records to the database.
Pass each new article to the Analyst as a task.

## Step 1: Load active sources
```
python3 db.py query "SELECT id, url, name, feed_type, country_code FROM sources WHERE status='active' AND (last_fetched IS NULL OR last_fetched < datetime('now','-1 hour')) ORDER BY last_fetched ASC LIMIT 20"
```
Process up to 20 sources per run to stay within time budget.

## Step 2: For each source, fetch and parse
- If `feed_type` is `rss` or `atom`: parse as XML feed, extract items
- If `feed_type` is `html`: fetch page, extract article links and headlines
- If `feed_type` is `google_news`: parse as RSS (Google News feeds are RSS)

For each item/article found: extract URL, title, published_at, summary.

## Step 3: Deduplicate
Before doing anything with an article URL:
```
python3 db.py is-url-seen "<article_url>"
```
If result is `true`: skip entirely.
If result is `false`: proceed.

## Step 4: Write new articles to DB
For each new (unseen) article:
```
python3 db.py insert-article '{"url":"<url>","title":"<title>","summary":"<summary>","source_name":"<name>","domain":"<domain>","fetched_at":"<ISO datetime>","published_at":"<ISO datetime or null>"}'
```
Then mark as seen:
```
python3 db.py mark-url-seen "<url>" "scout_retrieval"
```

## Step 5: Create Analyst task
For each new article inserted, create a Paperclip task for the Analyst agent:
- Task title: `Analyse: <article title>`
- Task body: article URL, source name, fetched_at, country_code
- Assign to: Analyst agent

## Step 6: Update source last_fetched
After processing each source, update its last_fetched timestamp:
```
python3 db.py query "UPDATE sources SET last_fetched=NOW(), fetch_count=fetch_count+1 WHERE id='<source_id>'"
```

## Step 7: Log run
```
python3 db.py log-run '{"agent_name":"scout_retrieval","status":"succeeded","items_found":<new_articles>,"notes":"Fetched <N> sources, <M> new articles"}'
```

## Error handling
If a source fails to fetch (network error, parse error):
```
python3 db.py query "UPDATE sources SET error_count=error_count+1 WHERE id='<source_id>'"
```
If error_count reaches 5: set status='paused' and note in your log.

## What you do NOT do
- Do NOT discover new sources — that is Scout Discovery's job
- Do NOT analyse article content
- Do NOT score significance or sentiment
- Do NOT write findings
```

### Step 5: Retire the original Scout agent

**File to modify:** `agents/scout/AGENTS.md`

Add a deprecation notice at the very top of the file (before the frontmatter `---`):

```markdown
> **DEPRECATED as of Phase 2.** This agent has been split into Scout Discovery (daily)
> and Scout Retrieval (hourly). Do not run this agent. See agents/scout-discovery/ and
> agents/scout-retrieval/.
```

### Step 6: Update Orchestrator

**File to modify:** `agents/orchestrator/AGENTS.md`

Replace the Scout line in the agent team section:

**Old:**
```
Scout — runs hourly. Finds Brazil energy stories. After each Scout run,
Contact Mapper should also run to check for new people named in stories.
```

**New:**
```
Scout Discovery — runs daily. Finds new source URLs via GDELT, Google News RSS,
and link extraction from recent articles. Adds candidates to sources table.
Uses Hermes memory to remember rejected domains and noise patterns (see T-209).

Scout Retrieval — runs hourly. Reads active sources from the database.
Fetches feeds. Deduplicates via seen_urls. Writes new articles to DB.
Creates Analyst tasks for each new article.
After each Scout Retrieval run, Contact Mapper should also run.
```

Also update the intelligence cycle section. Replace step 1:

**Old:**
```
1. Scout finds stories
```

**New:**
```
1. Scout Discovery (daily) finds new source candidates
   Scout Retrieval (hourly) fetches active sources and finds new articles
```

### Verify T-201

```bash
# Check both new agent files exist
ls agents/scout-discovery/AGENTS.md
ls agents/scout-retrieval/AGENTS.md

# Check sources table in schema
python3 database/db.py query "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"

# Check insert-source command works
python3 database/db.py insert-source '{"url":"https://agenciabrasil.ebc.gov.br/energia/feed/atom","name":"Agencia Brasil Energy","feed_type":"atom","status":"active","country_code":"BR","credibility_tier":"high"}'
python3 database/db.py query "SELECT url, status, credibility_tier FROM sources"
```

### Commit T-201
```bash
git add agents/scout-discovery/AGENTS.md agents/scout-retrieval/AGENTS.md agents/scout/AGENTS.md agents/orchestrator/AGENTS.md database/schema.sql database/db.py
git commit -m "feat(T-201): split Scout into Discovery (daily) and Retrieval (hourly)"
```

---

## Task T-202: Source Discovery — Link Extraction

**Why:** RSS feeds and GDELT only surface sources that are already well-known. Link extraction finds cited sources within articles — often government documents, niche publications, and evidence URLs that would never appear in a search index.

**This task extends Scout Discovery** (created in T-201). The link extraction logic is specified in Scout Discovery's AGENTS.md Method 3, but T-202 adds the credibility scoring detail and the `insert-source` plumbing.

### Step 1: Verify `insert-source` is working (prerequisite from T-201)

```bash
python3 database/db.py query "SELECT COUNT(*) as c FROM sources"
```

### Step 2: Define credibility scoring rules (reference document)

No code change needed — the credibility rules are embedded in Scout Discovery's AGENTS.md (HIGH/MEDIUM/LOW tiers). This step is a documentation checkpoint.

HIGH tier domains (hard-coded list Scout Discovery should recognise):
```
.gov, .gov.br, .gov.co, .gov.ar, .gov.cl, .gov.uk, .bmwk.de, .gouv.fr
agenciabrasil.ebc.gov.br, valor.globo.com, brazilenergyinsight.com,
cleanenergywire.org, euractiv.com, iea.org, irena.org, unfccc.int,
bndes.gov.br, petrobras.com.br, aneel.gov.br, anp.gov.br, epe.gov.br,
mme.gov.br, ibama.gov.br, cop30.gov.br, banktrack.org, urgewald.org
```

### Step 3: Add `sources` to `db.py stats()` output

**File to modify:** `database/db.py`

In the `stats()` method, add `"sources"` to the tables list:

```python
def stats(self):
    tables = ["articles","contacts","findings","policies",
              "ngo_intel","finance_deals","reports","seen_urls","run_log","sources"]
    return {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables}
```

### Verify T-202

```bash
# Insert a test candidate via link extraction discovery
python3 database/db.py insert-source '{"url":"https://www.poder360.com.br/feed","name":"Poder360","feed_type":"rss","status":"candidate","country_code":"BR","discovered_by":"link_extraction","credibility_tier":"medium"}'

# Confirm stats shows sources table
python3 database/db.py stats

# Confirm duplicate is rejected
python3 database/db.py insert-source '{"url":"https://www.poder360.com.br/feed","name":"Poder360 duplicate"}'
# Expected output: "exists"
```

### Commit T-202
```bash
git add database/db.py
git commit -m "feat(T-202): add sources to db.py stats; credibility tier rules in Scout Discovery"
```

---

## Task T-203: Auto-tagging in Analyst

**Why:** Articles currently have no machine-readable country or topic tags. Without tags, you cannot filter by country, run country-specific reports, or measure coverage gaps. This task makes every article queryable by `country_code` and `tag_slug`.

### Step 1: Add junction tables to schema

**File to modify:** `database/schema.sql`

Append to the end of the file:

```sql
-- Tags taxonomy: topic labels applied to articles
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,  -- e.g. coal, solar, cop30, bndes, offshore-wind
    label TEXT NOT NULL,
    category TEXT,              -- sector | policy | actor | geography | event
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Countries reference table
CREATE TABLE IF NOT EXISTS countries (
    code TEXT PRIMARY KEY,      -- ISO 3166-1 alpha-2 (BR, CO, AR, etc.)
    name TEXT NOT NULL,
    region TEXT                 -- south_america | europe | north_america | etc.
);

-- Article-to-tag junction
CREATE TABLE IF NOT EXISTS article_tags (
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    tag_slug TEXT NOT NULL REFERENCES tags(slug) ON DELETE CASCADE,
    confidence REAL DEFAULT 0.7,
    tagged_by TEXT DEFAULT 'analyst',  -- analyst | human
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (article_id, tag_slug)
);
CREATE INDEX IF NOT EXISTS idx_article_tags_slug ON article_tags(tag_slug);

-- Article-to-country junction
CREATE TABLE IF NOT EXISTS article_countries (
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    country_code TEXT NOT NULL REFERENCES countries(code) ON DELETE CASCADE,
    confidence REAL DEFAULT 0.7,
    tagged_by TEXT DEFAULT 'analyst',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (article_id, country_code)
);
CREATE INDEX IF NOT EXISTS idx_article_countries_code ON article_countries(country_code);
```

### Step 2: Add `insert-article-tag` and `insert-article-country` commands to `db.py`

**File to modify:** `database/db.py`

**2a.** Add two methods to the `DB` class, after the `insert_source` method:

```python
def insert_article_tag(self, article_id, tag_slug, confidence=0.7, tagged_by="analyst"):
    try:
        self.conn.execute("""INSERT OR IGNORE INTO article_tags
            (article_id, tag_slug, confidence, tagged_by, created_at)
            VALUES(?,?,?,?,?)""",
            (article_id, tag_slug, confidence, tagged_by, now()))
        self.conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return False

def insert_article_country(self, article_id, country_code, confidence=0.7, tagged_by="analyst"):
    try:
        self.conn.execute("""INSERT OR IGNORE INTO article_countries
            (article_id, country_code, confidence, tagged_by, created_at)
            VALUES(?,?,?,?,?)""",
            (article_id, country_code, confidence, tagged_by, now()))
        self.conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return False
```

**2b.** Add CLI handlers in the `cli()` function, after the `insert-source` handler:

```python
elif cmd == "insert-article-tag" and len(sys.argv) > 3:
    data = json.loads(sys.argv[2]) if sys.argv[2].startswith('{') else None
    if data:
        ok = db.insert_article_tag(data["article_id"], data["tag_slug"],
                                    data.get("confidence",0.7), data.get("tagged_by","analyst"))
    else:
        ok = db.insert_article_tag(sys.argv[2], sys.argv[3],
                                    float(sys.argv[4]) if len(sys.argv)>4 else 0.7)
    print("inserted" if ok else "exists")
elif cmd == "insert-article-country" and len(sys.argv) > 3:
    data = json.loads(sys.argv[2]) if sys.argv[2].startswith('{') else None
    if data:
        ok = db.insert_article_country(data["article_id"], data["country_code"],
                                        data.get("confidence",0.7), data.get("tagged_by","analyst"))
    else:
        ok = db.insert_article_country(sys.argv[2], sys.argv[3],
                                        float(sys.argv[4]) if len(sys.argv)>4 else 0.7)
    print("inserted" if ok else "exists")
```

### Step 3: Seed the tags taxonomy

**File to create:** `database/seed_tags.sql`

```sql
-- Core tag taxonomy for Climate Intelligence Platform
-- Run once after schema creation: python3 database/db.py query "$(cat database/seed_tags.sql)"
-- Or apply via sqlite3 directly

INSERT OR IGNORE INTO tags (id, slug, label, category) VALUES
  -- Fossil fuel sectors
  ('tag-coal',       'coal',          'Coal',                'sector'),
  ('tag-gas',        'gas',           'Natural Gas',         'sector'),
  ('tag-oil',        'oil',           'Oil / Petroleum',     'sector'),
  ('tag-lng',        'lng',           'LNG',                 'sector'),
  ('tag-presal',     'pre-sal',       'Pre-Sal',             'sector'),
  -- Renewable sectors
  ('tag-solar',      'solar',         'Solar Energy',        'sector'),
  ('tag-wind',       'wind',          'Wind Energy',         'sector'),
  ('tag-hydro',      'hydro',         'Hydropower',          'sector'),
  ('tag-hydrogen',   'hydrogen',      'Green Hydrogen',      'sector'),
  ('tag-biomass',    'biomass',       'Biomass / Ethanol',   'sector'),
  ('tag-storage',    'storage',       'Energy Storage',      'sector'),
  ('tag-offshore',   'offshore-wind', 'Offshore Wind',       'sector'),
  -- Policy & governance
  ('tag-ndc',        'ndc',           'NDC / Climate Target','policy'),
  ('tag-regulation', 'regulation',    'Regulation',          'policy'),
  ('tag-auction',    'auction',       'Energy Auction',      'policy'),
  ('tag-license',    'licensing',     'Licensing',           'policy'),
  ('tag-finance',    'climate-finance','Climate Finance',    'policy'),
  ('tag-transition', 'transition',    'Energy Transition',   'policy'),
  -- Key events
  ('tag-cop30',      'cop30',         'COP30 Belem',         'event'),
  ('tag-cop29',      'cop29',         'COP29',               'event'),
  -- Key actors
  ('tag-petrobras',  'petrobras',     'Petrobras',           'actor'),
  ('tag-bndes',      'bndes',         'BNDES',               'actor'),
  ('tag-aneel',      'aneel',         'ANEEL',               'actor'),
  ('tag-anp',        'anp',           'ANP',                 'actor'),
  ('tag-mme',        'mme',           'MME',                 'actor'),
  ('tag-ibama',      'ibama',         'IBAMA',               'actor'),
  -- Indigenous / social
  ('tag-indigenous', 'indigenous',    'Indigenous Territory','policy'),
  ('tag-amazon',     'amazon',        'Amazon / Amazonia',   'geography');

-- Core countries
INSERT OR IGNORE INTO countries (code, name, region) VALUES
  ('BR', 'Brazil',          'south_america'),
  ('CO', 'Colombia',        'south_america'),
  ('AR', 'Argentina',       'south_america'),
  ('CL', 'Chile',           'south_america'),
  ('DE', 'Germany',         'europe'),
  ('GB', 'United Kingdom',  'europe'),
  ('ES', 'Spain',           'europe'),
  ('FR', 'France',          'europe'),
  ('US', 'United States',   'north_america'),
  ('CN', 'China',           'asia');
```

**Apply the seed:**
```bash
sqlite3 $WORKSPACE_PATH/intelligence.db < database/seed_tags.sql
# Or using db.py for individual inserts during testing
python3 database/db.py query "SELECT slug, label, category FROM tags ORDER BY category, slug"
```

### Step 4: Update Analyst AGENTS.md

**File to modify:** `agents/analyst/AGENTS.md`

Add the following section after the `## Significance scoring (Brazil context)` section:

```markdown
## Auto-tagging — REQUIRED for every article

After scoring significance and sentiment, you MUST assign tags.
Use the taxonomy from the `tags` table. Query available tags first:
```
python3 db.py query "SELECT slug, label FROM tags ORDER BY slug"
```

### Assign country codes
Identify all countries the article is primarily about.
Brazil should be tagged if the article mentions Brazilian entities, policy, or geography.
Use confidence 0.7 for auto-assignments.

For the article you just analysed (article_id from insert-article output):
```
python3 db.py insert-article-country '{"article_id":"<id>","country_code":"BR","confidence":0.7,"tagged_by":"analyst"}'
```
Add additional country codes if article covers multiple countries (e.g. Colombia + Brazil).

### Assign topic tags
Select 2-5 tags from the taxonomy that best describe the article.
Match to `slug` values in the tags table (e.g. "coal", "pre-sal", "cop30").
Do not invent tags — only use slugs from the tags table.

```
python3 db.py insert-article-tag '{"article_id":"<id>","tag_slug":"<slug>","confidence":0.7,"tagged_by":"analyst"}'
```

Call insert-article-tag once per tag. If an article covers pre-sal gas and COP30 negotiations,
insert two tags: `pre-sal` and `cop30`.

### Confidence rules
- 0.9: Explicitly named in headline or first paragraph
- 0.7: Clearly implied by content (default for auto-tagging)
- 0.5: Mentioned but not primary focus — consider skipping
Do not insert tags with confidence below 0.5.
```

### Verify T-203

```bash
# Check tables were created
python3 database/db.py query "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('tags','countries','article_tags','article_countries')"

# Check seed data
python3 database/db.py query "SELECT COUNT(*) as tag_count FROM tags"
python3 database/db.py query "SELECT COUNT(*) as country_count FROM countries"

# Test a round-trip: insert article, tag it, query tags
ARTICLE_ID=$(python3 database/db.py insert-article '{"url":"https://test-tagging.example.com/article1","title":"Petrobras announces pre-sal expansion","domain":"test","fetched_at":"2026-04-07T10:00:00","run_date":"2026-04-07"}' 2>&1 | grep -v exists || echo "test-article-001")
python3 database/db.py query "SELECT id FROM articles WHERE url='https://test-tagging.example.com/article1'" | python3 -c "import json,sys; rows=json.load(sys.stdin); print(rows[0]['id'] if rows else 'not found')"
# Use the returned ID in the commands below:
python3 database/db.py insert-article-tag '{"article_id":"<ID>","tag_slug":"pre-sal","confidence":0.9,"tagged_by":"analyst"}'
python3 database/db.py insert-article-country '{"article_id":"<ID>","country_code":"BR","confidence":0.9,"tagged_by":"analyst"}'
python3 database/db.py query "SELECT at.tag_slug, at.confidence FROM article_tags at WHERE at.article_id='<ID>'"
```

### Commit T-203
```bash
git add database/schema.sql database/db.py database/seed_tags.sql agents/analyst/AGENTS.md
git commit -m "feat(T-203): auto-tagging in Analyst — article_tags and article_countries junction tables"
```

---

## Task T-204: Cross-reference Linking

**Why:** Finance Monitor and COP30 Monitor currently write findings in isolation. Cross-references let analysts ask "which articles support this finding?" and "which contacts are relevant to this deal?". These links are the connective tissue of the intelligence database.

### Step 1: Add cross-reference tables to schema

**File to modify:** `database/schema.sql`

Append to the end of the file:

```sql
-- Finding-to-article links (which articles support a finding)
CREATE TABLE IF NOT EXISTS finding_articles (
    finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    relevance_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (finding_id, article_id)
);
CREATE INDEX IF NOT EXISTS idx_finding_articles_finding ON finding_articles(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_articles_article ON finding_articles(article_id);

-- Finding-to-contact links (which contacts are relevant to a finding)
CREATE TABLE IF NOT EXISTS finding_contacts (
    finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    relevance_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (finding_id, contact_id)
);
CREATE INDEX IF NOT EXISTS idx_finding_contacts_finding ON finding_contacts(finding_id);
```

### Step 2: Add `link-finding-article` and `link-finding-contact` commands to `db.py`

**File to modify:** `database/db.py`

**2a.** Add two methods to the `DB` class, after the `insert_article_country` method:

```python
def link_finding_article(self, finding_id, article_id, relevance_note=None):
    try:
        self.conn.execute("""INSERT OR IGNORE INTO finding_articles
            (finding_id, article_id, relevance_note, created_at)
            VALUES(?,?,?,?)""", (finding_id, article_id, relevance_note, now()))
        self.conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return False

def link_finding_contact(self, finding_id, contact_id, relevance_note=None):
    try:
        self.conn.execute("""INSERT OR IGNORE INTO finding_contacts
            (finding_id, contact_id, relevance_note, created_at)
            VALUES(?,?,?,?)""", (finding_id, contact_id, relevance_note, now()))
        self.conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return False
```

**2b.** Add CLI handlers in the `cli()` function, after the `insert-article-country` handler:

```python
elif cmd == "link-finding-article" and len(sys.argv) > 3:
    data = json.loads(sys.argv[2]) if sys.argv[2].startswith('{') else None
    if data:
        ok = db.link_finding_article(data["finding_id"], data["article_id"], data.get("relevance_note"))
    else:
        ok = db.link_finding_article(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv)>4 else None)
    print("linked" if ok else "exists")
elif cmd == "link-finding-contact" and len(sys.argv) > 3:
    data = json.loads(sys.argv[2]) if sys.argv[2].startswith('{') else None
    if data:
        ok = db.link_finding_contact(data["finding_id"], data["contact_id"], data.get("relevance_note"))
    else:
        ok = db.link_finding_contact(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv)>4 else None)
    print("linked" if ok else "exists")
```

### Step 3: Update Finance Monitor AGENTS.md

**File to modify:** `agents/finance-monitor/AGENTS.md`

Add the following section after the `## Output format` section:

```markdown
## Cross-reference linking — REQUIRED for every finding

After creating a finding with `db.py insert-finding`, you MUST link it
to the articles that support it and to relevant contacts.

### Link supporting articles
Query recent articles related to the deal:
```
python3 db.py query "SELECT id, url, title FROM articles WHERE (title LIKE '%<institution>%' OR title LIKE '%<project_name>%') AND run_date > date('now','-30 days') ORDER BY significance DESC LIMIT 10"
```
For each article that is genuine evidence for this finding:
```
python3 db.py link-finding-article '{"finding_id":"<finding_id>","article_id":"<article_id>","relevance_note":"<one sentence on why this article supports the finding>"}'
```

### Link relevant contacts
Query contacts at the institution or relevant decision-makers:
```
python3 db.py query "SELECT id, name, organisation FROM contacts WHERE organisation LIKE '%<institution>%' OR organisation LIKE '%BNDES%' ORDER BY decision_power DESC LIMIT 5"
```
For each contact who is directly relevant to this deal:
```
python3 db.py link-finding-contact '{"finding_id":"<finding_id>","contact_id":"<contact_id>","relevance_note":"<role in this deal>"}'
```

Only link contacts you have evidence for. Do not guess.
```

### Step 4: Update COP30 Monitor AGENTS.md

**File to modify:** `agents/cop30-monitor/AGENTS.md`

Add the same cross-reference section after the `## Output format` section:

```markdown
## Cross-reference linking — REQUIRED for every finding

After creating a finding with `db.py insert-finding`, link it to supporting
articles and relevant contacts — especially NGO contacts and civil society
actors who could act on this intelligence.

### Link supporting articles
```
python3 db.py query "SELECT id, url, title FROM articles WHERE (title LIKE '%COP30%' OR title LIKE '%UNFCCC%' OR title LIKE '%NDC%') AND run_date > date('now','-14 days') ORDER BY fetched_at DESC LIMIT 10"
```
```
python3 db.py link-finding-article '{"finding_id":"<finding_id>","article_id":"<article_id>","relevance_note":"<why relevant>"}'
```

### Link relevant contacts
```
python3 db.py query "SELECT id, name, organisation FROM contacts WHERE why_relevant LIKE '%COP%' OR why_relevant LIKE '%climate%' ORDER BY influence_score DESC LIMIT 5"
```
```
python3 db.py link-finding-contact '{"finding_id":"<finding_id>","contact_id":"<contact_id>","relevance_note":"<COP30 role>"}'
```
```

### Verify T-204

```bash
# Check tables exist
python3 database/db.py query "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('finding_articles','finding_contacts')"

# Test link commands (requires an existing finding_id and article_id)
# Insert test finding first
FINDING_ID=$(python3 database/db.py insert-finding '{"agent":"finance_monitor","priority":"HIGH","title":"Test BNDES deal","body":"Test body","source_url":"https://test.example.com","run_date":"2026-04-07"}')
ARTICLE_ID=$(python3 database/db.py query "SELECT id FROM articles LIMIT 1" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r[0]['id'] if r else '')")
echo "Finding: $FINDING_ID, Article: $ARTICLE_ID"
python3 database/db.py link-finding-article "{\"finding_id\":\"$FINDING_ID\",\"article_id\":\"$ARTICLE_ID\",\"relevance_note\":\"Test link\"}"
python3 database/db.py query "SELECT finding_id, article_id, relevance_note FROM finding_articles LIMIT 5"
```

### Commit T-204
```bash
git add database/schema.sql database/db.py agents/finance-monitor/AGENTS.md agents/cop30-monitor/AGENTS.md
git commit -m "feat(T-204): cross-reference linking for findings — finding_articles and finding_contacts"
```

---

## Task T-205: South America Sources

**Why:** Colombia, Argentina, and Chile are the most active energy transition markets in South America outside Brazil. Their policies directly affect Brazil's competitive position and COP30 negotiating dynamics. Expanding coverage to these three countries completes South America coverage.

### Step 1: Add South American sources to seed data

**File to create:** `database/seed_south_america_sources.sql`

```sql
-- South America energy sources — Colombia, Argentina, Chile
-- Run: sqlite3 $WORKSPACE_PATH/intelligence.db < database/seed_south_america_sources.sql

INSERT OR IGNORE INTO sources (id, url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Colombia
('src-co-minenergia',     'https://www.minenergia.gov.co/noticias', 'MinEnergia Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('src-co-upme',           'https://www1.upme.gov.co/Noticias', 'UPME Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('src-co-energia-gnews',  'https://news.google.com/rss/search?q=energia+colombia&hl=es&gl=CO&ceid=CO:es', 'Google News — Energia Colombia', 'google_news', 'active', 'CO', 'es', 'manual', 'medium'),
('src-co-estrategica',    'https://www.energiaestrategica.com/feed/', 'Energía Estratégica', 'rss', 'active', 'CO', 'es', 'manual', 'high'),

-- Argentina
('src-ar-secenergia',     'https://www.argentina.gob.ar/noticias/secretaria-de-energia', 'Secretaría de Energía Argentina', 'html', 'active', 'AR', 'es', 'manual', 'high'),
('src-ar-energia-gnews',  'https://news.google.com/rss/search?q=energia+argentina&hl=es&gl=AR&ceid=AR:es', 'Google News — Energia Argentina', 'google_news', 'active', 'AR', 'es', 'manual', 'medium'),
('src-ar-iapg',           'https://www.iapg.org.ar/noticias', 'IAPG Argentina', 'html', 'candidate', 'AR', 'es', 'manual', 'medium'),
('src-ar-estrategica',    'https://www.energiaestrategica.com/feed/', 'Energía Estratégica (AR)', 'rss', 'active', 'AR', 'es', 'manual', 'high'),

-- Chile
('src-cl-minenergia',     'https://www.energia.gob.cl/noticias', 'Ministerio de Energía Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('src-cl-cne',            'https://www.cne.cl/noticias/', 'CNE Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('src-cl-energia-gnews',  'https://news.google.com/rss/search?q=energia+chile&hl=es&gl=CL&ceid=CL:es', 'Google News — Energia Chile', 'google_news', 'active', 'CL', 'es', 'manual', 'medium'),
('src-cl-estrategica',    'https://www.energiaestrategica.com/feed/', 'Energía Estratégica (CL)', 'rss', 'active', 'CL', 'es', 'manual', 'high'),

-- BNAmericas — Latin America (covers BR, CO, AR, CL, PE)
('src-latam-bnamericas',  'https://www.bnamericas.com/en/rss', 'BNAmericas Latin America', 'rss', 'active', NULL, 'en', 'manual', 'high');
```

Note: `src-co-estrategica`, `src-ar-estrategica`, `src-cl-estrategica` all point to the same Energía Estratégica RSS — this is intentional. The agent will deduplicate article URLs via `seen_urls`. Using three separate source records allows country-level tracking of the same feed.

### Step 2: Apply the seed

```bash
# Check the sources table exists first (from T-201)
python3 database/db.py query "SELECT COUNT(*) as c FROM sources"

# Apply seed
sqlite3 $WORKSPACE_PATH/intelligence.db < database/seed_south_america_sources.sql

# Verify
python3 database/db.py query "SELECT url, name, country_code, status FROM sources WHERE country_code IN ('CO','AR','CL') ORDER BY country_code"
```

### Step 3: Ensure CO, AR, CL exist in countries table (from T-203 seed)

```bash
python3 database/db.py query "SELECT code, name FROM countries WHERE code IN ('CO','AR','CL')"
```

If empty (seed_tags.sql from T-203 not yet applied), insert manually:
```bash
python3 database/db.py query "INSERT OR IGNORE INTO countries (code, name, region) VALUES ('CO','Colombia','south_america'), ('AR','Argentina','south_america'), ('CL','Chile','south_america')"
```

### Verify T-205

```bash
python3 database/db.py query "SELECT country_code, COUNT(*) as source_count FROM sources WHERE country_code IN ('CO','AR','CL') GROUP BY country_code"
# Expected: CO=4, AR=4, CL=4 (approximately, depending on dedupe of estrategica)
```

### Commit T-205
```bash
git add database/seed_south_america_sources.sql
git commit -m "feat(T-205): add Colombia, Argentina, Chile energy sources to seed data"
```

---

## Task T-206: Europe Sources

**Why:** COP30 is the core event of 2026. Germany, UK, France, and Spain are the largest European voices on fossil fuel phase-out. Tracking their energy policy gives the NGO context for negotiating bloc positions and lets the platform flag when European policy shifts could be cited as precedent at COP30.

### Step 1: Add European sources to seed data

**File to create:** `database/seed_europe_sources.sql`

```sql
-- Europe energy sources — Germany, UK, Spain, France
-- Run: sqlite3 $WORKSPACE_PATH/intelligence.db < database/seed_europe_sources.sql

INSERT OR IGNORE INTO sources (id, url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Germany
('src-de-bmwk',           'https://www.bmwk.de/SiteGlobals/Forms/Webs/BMWK/Suche/EN/Solr/sitesearch_formular.html?resourceId=9bc7fc0c-3d3d-4c63-bc3b-fd22064a1044&input_=&pageLocale=en&facets=type_facet%3APressemitteilung', 'BMWK Germany Press Releases', 'html', 'active', 'DE', 'de', 'manual', 'high'),
('src-de-bmwk-en',        'https://www.bmwk.de/Navigation/EN/Press/press-releases.html', 'BMWK Germany (English)', 'html', 'active', 'DE', 'en', 'manual', 'high'),
('src-de-cleanenergy',    'https://www.cleanenergywire.org/rss.xml', 'Clean Energy Wire', 'rss', 'active', 'DE', 'en', 'manual', 'high'),
('src-de-energiewende',   'https://news.google.com/rss/search?q=energiewende&hl=de&gl=DE&ceid=DE:de', 'Google News — Energiewende', 'google_news', 'active', 'DE', 'de', 'manual', 'medium'),
('src-de-policy-gnews',   'https://news.google.com/rss/search?q=german+energy+policy&hl=en&gl=DE&ceid=DE:en', 'Google News — German Energy Policy', 'google_news', 'active', 'DE', 'en', 'manual', 'medium'),

-- United Kingdom
('src-gb-desnz',          'https://www.gov.uk/government/organisations/department-for-energy-security-and-net-zero.atom', 'UK DESNZ (Dept for Energy Security and Net Zero)', 'atom', 'active', 'GB', 'en', 'manual', 'high'),
('src-gb-policy-gnews',   'https://news.google.com/rss/search?q=uk+energy+policy&hl=en-GB&gl=GB&ceid=GB:en', 'Google News — UK Energy Policy', 'google_news', 'active', 'GB', 'en', 'manual', 'medium'),
('src-gb-carbon-brief',   'https://www.carbonbrief.org/feed/', 'Carbon Brief', 'rss', 'active', 'GB', 'en', 'manual', 'high'),

-- Spain
('src-es-miteco',         'https://www.miteco.gob.es/es/prensa/notas-de-prensa/', 'MITECO Spain', 'html', 'active', 'ES', 'es', 'manual', 'high'),
('src-es-energia-gnews',  'https://news.google.com/rss/search?q=politica+energetica+espana&hl=es&gl=ES&ceid=ES:es', 'Google News — Política Energética España', 'google_news', 'active', 'ES', 'es', 'manual', 'medium'),

-- France
('src-fr-mte',            'https://www.ecologie.gouv.fr/actualites', 'Ministère Transition Écologique France', 'html', 'active', 'FR', 'fr', 'manual', 'high'),
('src-fr-energia-gnews',  'https://news.google.com/rss/search?q=politique+energetique+france&hl=fr&gl=FR&ceid=FR:fr', 'Google News — Politique Énergétique France', 'google_news', 'active', 'FR', 'fr', 'manual', 'medium'),

-- EU-wide
('src-eu-euractiv',       'https://www.euractiv.com/sections/energy/feed/', 'Euractiv Energy', 'rss', 'active', NULL, 'en', 'manual', 'high'),
('src-eu-iea',            'https://www.iea.org/news/feed/', 'IEA News', 'rss', 'active', NULL, 'en', 'manual', 'high');
```

Note on `src-gb-desnz`: the `.atom` URL is the official GOV.UK Atom feed for the department's publications. If the Atom URL returns a 404 at runtime, fall back to fetching `https://www.gov.uk/search/news-and-communications?organisations[]=department-for-energy-security-and-net-zero` as HTML.

### Step 2: Apply the seed

```bash
sqlite3 $WORKSPACE_PATH/intelligence.db < database/seed_europe_sources.sql

# Verify
python3 database/db.py query "SELECT url, name, country_code, status FROM sources WHERE country_code IN ('DE','GB','ES','FR') OR (country_code IS NULL AND name LIKE '%Euractiv%' OR name LIKE '%IEA%') ORDER BY country_code"
```

### Step 3: Ensure DE, GB, ES, FR exist in countries table

```bash
python3 database/db.py query "SELECT code, name FROM countries WHERE code IN ('DE','GB','ES','FR')"
```

If empty:
```bash
python3 database/db.py query "INSERT OR IGNORE INTO countries (code, name, region) VALUES ('DE','Germany','europe'), ('GB','United Kingdom','europe'), ('ES','Spain','europe'), ('FR','France','europe')"
```

### Verify T-206

```bash
python3 database/db.py query "SELECT country_code, COUNT(*) as source_count FROM sources WHERE country_code IN ('DE','GB','ES','FR') GROUP BY country_code"
# Expected: DE=5, GB=3, ES=2, FR=2
python3 database/db.py query "SELECT COUNT(*) as total FROM sources"
```

### Commit T-206
```bash
git add database/seed_europe_sources.sql
git commit -m "feat(T-206): add Germany, UK, Spain, France energy sources to seed data"
```

---

## Task T-207: Reporter Writes to DB

**Why:** Reporter currently saves reports to workspace files only. Files are ephemeral — they get lost when the container restarts. Writing to the `reports` table makes every report queryable and persistent. The `db.py insert-report` command already exists; this task just wires Reporter to use it.

### Step 1: Update Reporter AGENTS.md

**File to modify:** `agents/reporter/AGENTS.md`

The current file has nested JSON/markdown. Find the section that says:

```
## All output goes to human review queue
Never distribute directly. Always create a review task for the board.
```

Add the following section immediately after that:

```markdown
## MANDATORY: Write every report to the database

After writing any report or digest, you MUST call:
```
python3 db.py insert-report '{"title":"<headline>","subject":"<email subject>","body":"<full report body>","report_type":"<type>","run_date":"<YYYY-MM-DD>"}'
```

Valid `report_type` values:
- `daily_digest` — daily summary of all new stories
- `brief` — single-story intelligence brief
- `alert` — time-critical alert for immediate action
- `weekly_summary` — weekly digest

The `body` field must contain the full report text.
The `subject` field is the email subject line (max 78 characters).

After inserting the report, log your run:
```
python3 db.py log-run '{"agent_name":"reporter","status":"succeeded","items_created":1,"notes":"Report: <title>"}'
```

If you write multiple briefs in one run, call insert-report once per brief
and increment items_created in log-run accordingly.
```

Also remove (or comment out) the line:
```
Save output to workspace/pending_review/ and create board review task.
```
Replace it with:
```
Save output to the database via insert-report (above) AND create a board review task in Paperclip.
The workspace/pending_review/ directory is no longer the primary storage — the DB is.
```

### Verify T-207

```bash
# Simulate a Reporter run
python3 database/db.py insert-report '{"title":"Test Daily Digest 2026-04-07","subject":"Climate Intel Daily — 7 April 2026","body":"Test body — Petrobras announces offshore wind partnership.","report_type":"daily_digest","run_date":"2026-04-07"}'

python3 database/db.py query "SELECT title, report_type, run_date, email_status FROM reports ORDER BY run_date DESC LIMIT 5"
# Expected: row with title "Test Daily Digest 2026-04-07"

python3 database/db.py log-run '{"agent_name":"reporter","status":"succeeded","items_created":1,"notes":"Test run"}'
python3 database/db.py query "SELECT agent_name, status, items_created FROM run_log WHERE agent_name='reporter' ORDER BY created_at DESC LIMIT 3"
```

### Commit T-207
```bash
git add agents/reporter/AGENTS.md
git commit -m "feat(T-207): Reporter writes reports and run logs to database via db.py"
```

---

## Task T-208: Contact Mapper Uses DB

**Why:** Contact Mapper currently writes to `workspace/influence_model.json`. This file is a single JSON blob — it cannot be queried, it has no deduplication, and it is lost on container restart. Writing contacts to the `contacts` table makes them queryable, persistent, and linkable to findings (T-204).

### Step 1: Update Contact Mapper AGENTS.md

**File to modify:** `agents/contact-mapper/AGENTS.md`

Replace the entire `## Manual run mode` section with:

```markdown
## Writing contacts to the database — REQUIRED

Use `db.py upsert-contact` for all contact writes. Do NOT write to
workspace/influence_model.json for new contacts — the DB is authoritative.

### For each new contact discovered:
```
python3 db.py upsert-contact '{"name":"<Full Name>","role":"<Job Title>","organisation":"<Organisation Name>","organisation_type":"<government|ngo|industry|academic>","decision_power":<1-5>,"ngo_access":1,"why_relevant":"<one sentence>","source_url":"<evidence URL>","policies_owned":["<policy slug>"]}'
```

Fields:
- `name`: Full name as found in the source
- `role`: Job title as found in the source — do NOT guess
- `organisation`: Organisation name — do NOT abbreviate unless the source does
- `organisation_type`: one of: government, ngo, industry, academic, international
- `decision_power`: 1-5 scale (5 = minister/CEO, 3 = senior official, 1 = staff)
- `ngo_access`: always 1 for new contacts — only humans can change this
- `why_relevant`: one sentence citing specific policy or moment
- `source_url`: verifiable URL where this person was mentioned — REQUIRED
- `policies_owned`: list of policy slugs this person owns/influences

### Country and tag assignment
After upserting a contact, note their country codes and relevant tag slugs
in the `notes` field:
```
python3 db.py upsert-contact '{"name":"<name>","organisation":"<org>","notes":"country_codes:[BR] tags:[mme,regulation,transition]"}'
```

### Updating existing contacts
`upsert-contact` uses name + organisation as the unique key.
Running the same command again with updated fields will update the record.
Use this to update `influence_score` after recalculation.

### Querying contacts
```
python3 db.py query "SELECT name, role, organisation, influence_score, decision_power FROM contacts ORDER BY influence_score DESC LIMIT 20"
```
```
python3 db.py query "SELECT name, organisation FROM contacts WHERE why_relevant LIKE '%MME%'"
```

### workspace/influence_model.json — transition note
The JSON file may still exist for legacy reasons. Do NOT update it during
Phase 2 runs. The database is the single source of truth from Phase 2 onwards.

## Run logging
At the end of every Contact Mapper run:
```
python3 db.py log-run '{"agent_name":"contact_mapper","status":"succeeded","items_found":<new_contacts_discovered>,"items_created":<contacts_upserted>,"notes":"<summary>"}'
```
```

### Verify T-208

```bash
# Test upsert-contact
python3 database/db.py upsert-contact '{"name":"Alexandre Silveira","role":"Minister of Mines and Energy","organisation":"MME","organisation_type":"government","decision_power":5,"ngo_access":1,"why_relevant":"Heads MME — primary decision-maker for Brazilian energy policy","source_url":"https://www.gov.br/mme/pt-br","policies_owned":["energy-transition","pre-sal","renewables"]}'

python3 database/db.py query "SELECT name, role, organisation, decision_power FROM contacts WHERE organisation='MME'"

# Test update (re-run same contact with new notes)
python3 database/db.py upsert-contact '{"name":"Alexandre Silveira","organisation":"MME","notes":"country_codes:[BR] tags:[mme,transition,pre-sal]"}'
python3 database/db.py query "SELECT name, notes FROM contacts WHERE name='Alexandre Silveira'"
```

### Commit T-208
```bash
git add agents/contact-mapper/AGENTS.md
git commit -m "feat(T-208): Contact Mapper writes to database via db.py upsert-contact"
```

---

## Task T-209: Hermes on Scout Discovery

**Why:** Scout Discovery runs daily and evaluates hundreds of domains. Without memory, it re-evaluates the same rejected domains every day, wastes tokens scoring noise patterns, and rediscovers sources it already rejected. Hermes gives it cross-session memory so it learns which domains are noise and which produce signal.

**Prerequisite:** T-201 must be complete. Scout Discovery agent must be running and producing quality metrics (see Step 1).

### Step 1: Establish baseline quality metrics BEFORE activating Hermes

Run Scout Discovery for 5 consecutive days without Hermes. Record these metrics each day:

```bash
# After each daily run, capture:
python3 database/db.py query "SELECT COUNT(*) as total_candidates FROM sources WHERE status='candidate' AND DATE(created_at)=DATE('now')"
python3 database/db.py query "SELECT credibility_tier, COUNT(*) as c FROM sources WHERE DATE(created_at)=DATE('now') GROUP BY credibility_tier"
python3 database/db.py query "SELECT agent_name, items_found, notes FROM run_log WHERE agent_name='scout_discovery' ORDER BY created_at DESC LIMIT 5"
```

Record results in `docs/metrics/scout-discovery-baseline.md` (create this file manually after 5 days of runs).

Target baseline metrics:
- Daily new candidates: expected 5-20
- HIGH credibility ratio: target > 40% of inserts
- Duplicate rejections: count how many domains are checked but already known

### Step 2: Configure Hermes on Scout Discovery

**What Hermes provides:**
- FTS5-indexed cross-session memory stored in the Paperclip workspace
- `--resume` flag makes the agent load its previous session memory on each start
- Skill creation: Scout Discovery can save reusable patterns (e.g. "domains ending in .blogspot.com are LOW credibility")

**File to modify:** `agents/scout-discovery/AGENTS.md`

Add the following section at the top of the AGENTS.md file, after the frontmatter `---`:

```markdown
## Hermes memory — active

You have persistent cross-session memory via hermes-paperclip-adapter.
Your memories persist across daily runs. Use them to avoid re-evaluating
known noise and to recall why you rejected specific domains.

### What to remember

**After rejecting a domain as LOW credibility:**
Save a memory note:
> Rejected domain: <domain> — reason: <one sentence>. Do not re-evaluate.

**After discovering a HIGH value source:**
Save a memory note:
> High-value source confirmed: <domain> — covers <topic>. Inserts good articles.

**After identifying a noise pattern:**
Save a memory note:
> Noise pattern: <pattern description> (e.g. "aggregator sites with /news/press-release in path have no original content")

### How to use memories at run start
At the start of each daily run, search your memory for:
- Previously rejected domains in today's candidate list
- Known noise patterns to filter before scoring
- High-value sources to prioritise

Use memories to skip re-evaluation — if a domain was previously rejected,
skip it immediately without scoring. Log: "Skipped (known noise): <domain>".
```

**Paperclip configuration change:**

The `--resume` flag is set in the Paperclip agent configuration, not in AGENTS.md. The exact mechanism depends on the version of `hermes-paperclip-adapter` installed. Check the installed version:

```bash
# Inside the Paperclip container:
docker exec -it <paperclip-container> bash -c "hermes --version 2>/dev/null || paperclip-agent --help 2>&1 | grep resume"
```

If `--resume` is a supported flag, add it to the Scout Discovery agent's startup command in the Paperclip UI agent settings (Settings → Agents → Scout Discovery → Advanced → Additional flags: `--resume`).

If using a `.paperclip.yaml` config file, add to the scout-discovery agent entry:
```yaml
agents:
  scout-discovery:
    flags:
      - --resume
```

### Step 3: Run Hermes-enabled Scout Discovery for 2 weeks

Run for 14 consecutive days. Capture the same metrics as the baseline:

```bash
python3 database/db.py query "SELECT COUNT(*) as total_candidates FROM sources WHERE status='candidate' AND DATE(created_at)=DATE('now')"
python3 database/db.py query "SELECT credibility_tier, COUNT(*) as c FROM sources WHERE DATE(created_at)=DATE('now') GROUP BY credibility_tier"
python3 database/db.py query "SELECT agent_name, items_found, notes FROM run_log WHERE agent_name='scout_discovery' ORDER BY created_at DESC LIMIT 14"
```

### Step 4: Decision gate — evaluate before expanding to T-210/T-211

After 2 weeks, compare Hermes-on metrics to baseline.

**Proceed to T-210/T-211 if ALL of the following are true:**
1. HIGH credibility ratio improved by ≥ 10 percentage points
2. Daily token cost for Scout Discovery decreased (fewer domains re-evaluated)
3. Duplicate rejection count decreased (Hermes skipping known domains)
4. No false negatives observed (no known HIGH-value domains incorrectly skipped)

**Do NOT proceed to T-210/T-211 if:**
- HIGH credibility ratio did not improve
- Hermes is causing Scout Discovery to skip valid new sources
- Memory is producing false positives (rejecting good domains based on stale memories)

Document the decision in `docs/metrics/hermes-t209-evaluation.md`.

### Verify T-209

```bash
# Confirm hermes-paperclip-adapter is installed
docker exec -it <paperclip-container> bash -c "pip show hermes-paperclip-adapter 2>/dev/null || echo 'not found'"

# Confirm Scout Discovery has --resume in its config
# (Check Paperclip UI or .paperclip.yaml)

# After first Hermes-enabled run, check logs
python3 database/db.py query "SELECT agent_name, notes, items_found FROM run_log WHERE agent_name='scout_discovery' ORDER BY created_at DESC LIMIT 3"
```

### Commit T-209
```bash
git add agents/scout-discovery/AGENTS.md
git commit -m "feat(T-209): activate Hermes memory on Scout Discovery with baseline measurement protocol"
```

---

## Task T-210: Hermes on Analyst

**Conditional on T-209 showing measurable improvement.**

**Do not implement T-210 unless T-209's decision gate passed.**

**Why:** If Hermes improves Scout Discovery, the same mechanism should help Analyst remember recurring entities (known companies, known regulators), previously scored significance patterns, and which domains reliably produce high-significance articles.

### Prerequisite gate
Before implementing T-210:
1. T-209 evaluation complete and decision gate passed
2. Document in `docs/metrics/hermes-t209-evaluation.md`: "T-209 gate: PASSED. Proceeding to T-210."

### Step 1: Define what Analyst should remember

**File to modify:** `agents/analyst/AGENTS.md`

Add a Hermes memory section at the top after frontmatter:

```markdown
## Hermes memory — active (after T-209 gate)

Use persistent memory to improve consistency across runs.

### What to remember

**Recurring entities:**
> Entity confirmed: <organisation name> — always tag with <tag_slug>. Significance baseline: <0.X>.

**Domain quality:**
> Domain <domain> reliably produces significance > 0.75 articles on <topic>.

**False positive patterns:**
> Pattern: articles from <domain> about <topic> are consistently significance < 0.4.
> Reason: commentary/opinion only, no new policy developments.

### How to use at run start
At the start of each run, check memory for:
- The source domain of the article you're about to analyse
- Any entity names in the title that have been previously scored
Use memories to calibrate your starting significance estimate, but always
verify against the actual article content.
```

Enable `--resume` flag for Analyst agent in Paperclip config (same as T-209 Step 2).

### Commit T-210
```bash
git add agents/analyst/AGENTS.md
git commit -m "feat(T-210): activate Hermes memory on Analyst (conditional on T-209 gate)"
```

---

## Task T-211: Hermes on Contact Mapper

**Conditional on T-209 showing measurable improvement.**

**Do not implement T-211 unless T-209's decision gate passed.**

**Why:** Contact Mapper discovers the same actors over and over — ministers rarely change. Without memory, Contact Mapper spends tokens re-verifying contacts it already knows. Hermes lets it remember confirmed contacts and their current roles, so it can detect genuine changes (new appointment, departure) rather than re-verifying known facts.

### Prerequisite gate
Before implementing T-211:
1. T-209 evaluation complete and decision gate passed
2. T-211 can run in parallel with T-210 — they are independent

### Step 1: Define what Contact Mapper should remember

**File to modify:** `agents/contact-mapper/AGENTS.md`

Add a Hermes memory section at the top after frontmatter:

```markdown
## Hermes memory — active (after T-209 gate)

Use persistent memory to avoid re-verifying known contacts.

### What to remember

**Confirmed contacts:**
> Confirmed: <Name>, <Role>, <Organisation>. Verified via <source_url> on <date>.
> Only re-verify if a new article mentions a role change or departure.

**Rejected actors:**
> Rejected: <Name> from <source> — reason: <unverifiable / out of jurisdiction / wrong sector>.
> Do not re-process.

**Role change detections:**
> Role change detected: <Name> moved from <old role> to <new role> on <date>.
> DB record updated via upsert-contact.

### How to use at run start
Before processing any actor name from a new article:
1. Search memory for that person's name
2. If confirmed in memory: only re-verify if article implies a role change
3. If rejected in memory: skip immediately
4. If unknown: proceed with full verification workflow
```

Enable `--resume` flag for Contact Mapper agent in Paperclip config (same as T-209 Step 2).

### Commit T-211
```bash
git add agents/contact-mapper/AGENTS.md
git commit -m "feat(T-211): activate Hermes memory on Contact Mapper (conditional on T-209 gate)"
```

---

## Full Phase 2 Verification Checklist

Run these checks after all non-conditional tasks (T-201 through T-208) are complete:

```bash
# 1. Schema — all new tables exist
python3 database/db.py query "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
# Expected: articles, article_countries, article_tags, contacts, finance_deals,
#           finding_articles, finding_contacts, findings, ngo_intel, policies,
#           reports, run_log, seen_urls, sources, tags, countries, alert_hashes

# 2. db.py — all new commands work
python3 database/db.py insert-source '{"url":"https://verify-phase2.example.com","name":"Phase 2 Verify","status":"candidate","credibility_tier":"low"}' || echo "ok"
python3 database/db.py insert-article-tag '{"article_id":"nonexistent","tag_slug":"coal","confidence":0.7}' 2>&1 || echo "ok (FK error expected for nonexistent article)"
python3 database/db.py link-finding-article '{"finding_id":"nonexistent","article_id":"nonexistent"}' 2>&1 || echo "ok (FK error expected)"
python3 database/db.py link-finding-contact '{"finding_id":"nonexistent","contact_id":"nonexistent"}' 2>&1 || echo "ok (FK error expected)"

# 3. Seed data
python3 database/db.py query "SELECT COUNT(*) as tags FROM tags"
# Expected: ≥ 27

python3 database/db.py query "SELECT COUNT(*) as countries FROM countries"
# Expected: ≥ 10

python3 database/db.py query "SELECT country_code, COUNT(*) as c FROM sources GROUP BY country_code ORDER BY c DESC"
# Expected: BR highest, CO/AR/CL/DE/GB/ES/FR all present

# 4. Agent files exist
ls agents/scout-discovery/AGENTS.md
ls agents/scout-retrieval/AGENTS.md

# 5. Stats
python3 database/db.py stats
# Expected: sources row appears in output
```

---

## Summary of all files changed in Phase 2

| Task | Files Modified | Files Created |
|------|---------------|---------------|
| T-201 | `database/schema.sql`, `database/db.py`, `agents/scout/AGENTS.md`, `agents/orchestrator/AGENTS.md` | `agents/scout-discovery/AGENTS.md`, `agents/scout-retrieval/AGENTS.md` |
| T-202 | `database/db.py` | — |
| T-203 | `database/schema.sql`, `database/db.py`, `agents/analyst/AGENTS.md` | `database/seed_tags.sql` |
| T-204 | `database/schema.sql`, `database/db.py`, `agents/finance-monitor/AGENTS.md`, `agents/cop30-monitor/AGENTS.md` | — |
| T-205 | — | `database/seed_south_america_sources.sql` |
| T-206 | — | `database/seed_europe_sources.sql` |
| T-207 | `agents/reporter/AGENTS.md` | — |
| T-208 | `agents/contact-mapper/AGENTS.md` | — |
| T-209 | `agents/scout-discovery/AGENTS.md` | — |
| T-210* | `agents/analyst/AGENTS.md` | — |
| T-211* | `agents/contact-mapper/AGENTS.md` | — |

*Conditional on T-209 gate passing.
