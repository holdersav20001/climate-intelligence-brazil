#!/usr/bin/env python3
"""
Climate Intelligence Platform - db.py
Database writer utility for all agents.

CLI usage:
    python3 db.py stats
    python3 db.py insert-article '{"url":"...","title":"..."}'
    python3 db.py insert-finding '{"agent":"finance_monitor","priority":"HIGH","title":"...","body":"..."}'
    python3 db.py insert-contact '{"name":"...","role":"...","organisation":"..."}'
    python3 db.py insert-ngo-intel '{"organisation":"iCS","title":"...","summary":"..."}'
    python3 db.py insert-finance-deal '{"institution":"BNDES","project_name":"...","priority":"HIGH"}'
    python3 db.py insert-report '{"title":"...","body":"...","report_type":"daily_digest"}'
    python3 db.py mark-url-seen "https://..." "scout"
    python3 db.py is-url-seen "https://..."
    python3 db.py log-run '{"agent_name":"scout","status":"succeeded","items_found":8}'
    python3 db.py query "SELECT * FROM articles ORDER BY run_date DESC LIMIT 5"
"""

import json, uuid, sys, os
import psycopg2
import psycopg2.extras
from datetime import datetime, date

def new_id(): return str(uuid.uuid4())
def now(): return datetime.now().isoformat()
def today(): return str(date.today())


class DB:
    def __init__(self):
        dsn = os.environ.get("CLIMATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("CLIMATE_DATABASE_URL environment variable not set")
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = False
        # Ensure we're in the climate schema
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO climate, public")

    def close(self):
        self.conn.commit()
        self.conn.close()

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def _execute(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
        self.conn.commit()

    def _fetchone(self, sql, params=()):
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def _fetchall(self, sql, params=()):
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def insert_article(self, a):
        url = a.get("url") or a.get("source_url")
        if not url: return False
        try:
            self._execute("""
                INSERT INTO articles
                    (url, title, summary, source_name, domain, topic, significance, verified,
                     sentiment_overall, sentiment_environmental, sentiment_economic,
                     sentiment_political, sentiment_social, sentiment_framing,
                     country_codes, tag_slugs, language,
                     fetched_at, published_at, run_date, scout_run_id, analyst_run_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (url) DO NOTHING
            """, (
                url, a.get("title", "Untitled"),
                a.get("summary") or a.get("description"),
                a.get("source_name") or a.get("source"),
                a.get("domain"), a.get("topic"),
                a.get("significance"), a.get("verified", False),
                a.get("sentiment_overall"), a.get("sentiment_environmental"),
                a.get("sentiment_economic"), a.get("sentiment_political"),
                a.get("sentiment_social"), a.get("sentiment_framing"),
                a.get("country_codes", []), a.get("tag_slugs", []),
                a.get("language", "en"),
                a.get("fetched_at") or now(), a.get("published_at"),
                a.get("run_date") or today(),
                a.get("scout_run_id"), a.get("analyst_run_id"),
            ))
            return True
        except psycopg2.Error as e:
            print(f"DB error: {e}", file=sys.stderr)
            self.conn.rollback()
            return False

    def upsert_contact(self, c):
        existing = self._fetchone(
            "SELECT id FROM contacts WHERE name=%s AND organisation=%s",
            (c.get("name"), c.get("organisation")))
        row_id = existing["id"] if existing else (c.get("id") or new_id())
        self._execute("""
            INSERT INTO contacts
                (id, name, role, organisation, organisation_type, decision_power, ngo_access,
                 influence_score, profile_url, contact_url, email, policies_owned,
                 why_relevant, source_url, notes, last_updated)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (name, organisation) DO UPDATE SET
                role=EXCLUDED.role, decision_power=EXCLUDED.decision_power,
                influence_score=EXCLUDED.influence_score, last_updated=NOW()
        """, (
            row_id, c.get("name", "Unknown"),
            c.get("role") or c.get("title", ""),
            c.get("organisation") or c.get("org", ""),
            c.get("organisation_type", "government"),
            c.get("decision_power") or c.get("power"),
            c.get("ngo_access", 1),
            c.get("influence_score") or c.get("effective_score"),
            c.get("profile_url") or c.get("url"),
            c.get("contact_url"), c.get("email"),
            json.dumps(c.get("policies_owned") or c.get("policies", [])),
            c.get("why_relevant") or c.get("relevance"),
            c.get("source_url"), c.get("notes"), now(),
        ))
        return row_id

    def insert_finding(self, f):
        row_id = f.get("id") or new_id()
        self._execute("""
            INSERT INTO findings
                (id, paperclip_issue_id, agent, priority, category, title, body,
                 source_url, source_name, action_required, deadline,
                 coalition_opportunity, evidence_value,
                 country_codes, tag_slugs, fetched_at, run_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            row_id, f.get("paperclip_issue_id") or f.get("issue_id"),
            f.get("agent", "unknown"), f.get("priority", "MEDIUM"),
            f.get("category"), f.get("title", "Untitled"),
            f.get("body") or f.get("description", ""),
            f.get("source_url"), f.get("source_name"),
            f.get("action_required") or f.get("action"),
            f.get("deadline"),
            bool(f.get("coalition_opportunity")),
            f.get("evidence_value"),
            f.get("country_codes", []), f.get("tag_slugs", []),
            f.get("fetched_at") or now(),
            f.get("run_date") or today(),
        ))
        return row_id

    def upsert_policy(self, p):
        self._execute("""
            INSERT INTO policies
                (title, body, url, owner, status, consultation_open,
                 consultation_deadline, relevance, ngo_position, last_hash, last_checked)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (url) DO UPDATE SET
                title=EXCLUDED.title, status=EXCLUDED.status,
                consultation_open=EXCLUDED.consultation_open,
                consultation_deadline=EXCLUDED.consultation_deadline,
                last_hash=EXCLUDED.last_hash, last_checked=EXCLUDED.last_checked
        """, (
            p.get("title", "Untitled"),
            p.get("body") or p.get("description"),
            p.get("url"), p.get("owner") or p.get("body_name"),
            p.get("status"),
            bool(p.get("consultation_open")),
            p.get("consultation_deadline") or p.get("deadline"),
            p.get("relevance"), p.get("ngo_position"),
            p.get("last_hash") or p.get("hash"),
            p.get("last_checked") or now(),
        ))

    def insert_ngo_intel(self, n):
        row_id = n.get("id") or new_id()
        self._execute("""
            INSERT INTO ngo_intel
                (id, organisation, organisation_category, type, title, summary,
                 significance, coalition_opportunity, evidence_value,
                 counter_argument_needed, url, fetched_at, run_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            row_id, n.get("organisation", "Unknown"),
            n.get("organisation_category", "allied"),
            n.get("type", "report"), n.get("title", "Untitled"),
            n.get("summary"), n.get("significance"),
            bool(n.get("coalition_opportunity")),
            n.get("evidence_value"),
            bool(n.get("counter_argument_needed")),
            n.get("url") or n.get("source_url"),
            n.get("fetched_at") or now(),
            n.get("run_date") or today(),
        ))
        return row_id

    def insert_finance_deal(self, d):
        row_id = d.get("id") or new_id()
        self._execute("""
            INSERT INTO finance_deals
                (id, institution, project_name, amount_usd, amount_brl, currency_note,
                 deal_type, project_type, stage, intervention_window, priority,
                 source_url, summary, recommended_action, country_codes, fetched_at, run_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            row_id, d.get("institution", "Unknown"), d.get("project_name"),
            d.get("amount_usd"), d.get("amount_brl"), d.get("currency_note"),
            d.get("deal_type", "unknown"), d.get("project_type"),
            d.get("stage"), d.get("intervention_window"),
            d.get("priority", "MEDIUM"), d.get("source_url"),
            d.get("summary"),
            d.get("recommended_action") or d.get("action"),
            d.get("country_codes", []),
            d.get("fetched_at") or now(),
            d.get("run_date") or today(),
        ))
        return row_id

    def insert_source(self, s):
        """Insert a source candidate. Returns the id if inserted, None if already exists."""
        row_id = s.get("id") or str(__import__('uuid').uuid4())
        try:
            with self.conn.cursor() as cur:
                cur.execute("""INSERT INTO sources
                    (id, url, name, feed_type, status, country_code, language,
                     discovered_by, credibility_tier, notes, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    ON CONFLICT (url) DO NOTHING""", (
                    row_id, s.get("url"), s.get("name"),
                    s.get("feed_type", "rss"),
                    s.get("status", "candidate"),
                    s.get("country_code"), s.get("language", "en"),
                    s.get("discovered_by", "manual"),
                    s.get("credibility_tier", "medium"),
                    s.get("notes")))
                inserted = cur.rowcount > 0
            self.conn.commit()
            return row_id if inserted else None
        except Exception as e:
            self.conn.rollback()
            print(f"DB error: {e}", file=sys.stderr)
            return None

    def insert_report(self, r):
        row_id = r.get("id") or new_id()
        recipients = r.get("recipients", [])
        self._execute("""
            INSERT INTO reports
                (id, title, subject, body, report_type, run_date, sent_at,
                 email_status, recipients, recipient_count, paperclip_issue)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            row_id, r.get("title", "Untitled"), r.get("subject"),
            r.get("body", ""), r.get("report_type", "daily_digest"),
            r.get("run_date") or today(), r.get("sent_at"),
            r.get("email_status", "pending"),
            json.dumps(recipients), len(recipients),
            r.get("paperclip_issue"),
        ))
        return row_id

    def log_run(self, r):
        self._execute("""
            INSERT INTO run_log
                (agent_name, agent_id, status, started_at, finished_at,
                 duration_sec, items_found, items_created, cost_usd, notes, run_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            r.get("agent_name", "unknown"), r.get("agent_id"),
            r.get("status"), r.get("started_at"), r.get("finished_at"),
            r.get("duration_sec"),
            r.get("items_found", 0), r.get("items_created", 0),
            r.get("cost_usd"), r.get("notes"),
            r.get("run_date") or today(),
        ))

    def is_url_seen(self, url):
        return self._fetchone("SELECT 1 FROM seen_urls WHERE url=%s", (url,)) is not None

    def mark_url_seen(self, url, agent="unknown"):
        self._execute(
            "INSERT INTO seen_urls (url, first_seen_by) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (url, agent))

    def mark_urls_seen(self, urls, agent="unknown"):
        with self.conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                "INSERT INTO seen_urls (url, first_seen_by) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                [(u, agent) for u in urls])
        self.conn.commit()

    def get_alert_hash(self, url):
        row = self._fetchone("SELECT hash FROM alert_hashes WHERE url=%s", (url,))
        return row["hash"] if row else None

    def update_alert_hash(self, url, new_hash):
        self._execute("""
            INSERT INTO alert_hashes (url, hash, last_checked, check_count)
            VALUES (%s,%s,NOW(),1)
            ON CONFLICT (url) DO UPDATE SET
                hash=EXCLUDED.hash, last_checked=NOW(),
                check_count=alert_hashes.check_count+1
        """, (url, new_hash))

    def stats(self):
        tables = ["articles","contacts","findings","policies",
                  "ngo_intel","finance_deals","reports","seen_urls","run_log"]
        result = {}
        for t in tables:
            row = self._fetchone(f"SELECT COUNT(*) AS n FROM {t}")
            result[t] = row["n"] if row else 0
        return result

    def query(self, sql, params=()):
        return [dict(r) for r in self._fetchall(sql, params)]


def cli():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    db = DB()
    if cmd == "stats":
        s = db.stats()
        print("\n── Intelligence Database ──────────────────────")
        for k, v in s.items():
            print(f"  {k:<20} {v:>6} rows")
        print("───────────────────────────────────────────────")
    elif cmd == "insert-article" and len(sys.argv) > 2:
        print("inserted" if db.insert_article(json.loads(sys.argv[2])) else "exists")
    elif cmd == "insert-finding" and len(sys.argv) > 2:
        print(db.insert_finding(json.loads(sys.argv[2])))
    elif cmd == "insert-contact" and len(sys.argv) > 2:
        print(db.upsert_contact(json.loads(sys.argv[2])))
    elif cmd == "insert-ngo-intel" and len(sys.argv) > 2:
        print(db.insert_ngo_intel(json.loads(sys.argv[2])))
    elif cmd == "insert-finance-deal" and len(sys.argv) > 2:
        print(db.insert_finance_deal(json.loads(sys.argv[2])))
    elif cmd == "insert-source" and len(sys.argv) > 2:
        result = db.insert_source(json.loads(sys.argv[2]))
        print(result if result else "exists")
    elif cmd == "insert-report" and len(sys.argv) > 2:
        print(db.insert_report(json.loads(sys.argv[2])))
    elif cmd == "mark-url-seen" and len(sys.argv) > 2:
        db.mark_url_seen(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "unknown")
        print(f"marked: {sys.argv[2]}")
    elif cmd == "is-url-seen" and len(sys.argv) > 2:
        print("true" if db.is_url_seen(sys.argv[2]) else "false")
    elif cmd == "log-run" and len(sys.argv) > 2:
        db.log_run(json.loads(sys.argv[2]))
        print("logged")
    elif cmd == "query" and len(sys.argv) > 2:
        print(json.dumps(db.query(sys.argv[2]), indent=2, default=str))
    else:
        print(f"Unknown command: {cmd}")
    db.close()


if __name__ == "__main__":
    cli()
