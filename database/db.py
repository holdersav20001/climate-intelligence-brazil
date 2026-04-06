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

import json, sqlite3, uuid, sys, os
from datetime import datetime, date
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE_PATH",
    "/home/holder/.paperclip/instances/default/companies"
    "/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace"))
DB_PATH = WORKSPACE / "intelligence.db"
SCHEMA_PATH = WORKSPACE / "schema.sql"

def new_id(): return str(uuid.uuid4())
def now(): return datetime.now().isoformat()
def today(): return str(date.today())

class DB:
    def __init__(self, db_path=None):
        self.path = Path(db_path or DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema()

    def _ensure_schema(self):
        tables = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not tables and SCHEMA_PATH.exists():
            self.conn.executescript(SCHEMA_PATH.read_text())
            self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def insert_article(self, a):
        url = a.get("url") or a.get("source_url")
        if not url: return False
        try:
            self.conn.execute("""INSERT OR IGNORE INTO articles
                (id,url,title,summary,source_name,domain,topic,significance,verified,
                 sentiment_overall,sentiment_environmental,sentiment_economic,
                 sentiment_political,sentiment_social,sentiment_framing,
                 fetched_at,published_at,run_date,scout_run_id,analyst_run_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                a.get("id") or new_id(), url, a.get("title","Untitled"),
                a.get("summary") or a.get("description"),
                a.get("source_name") or a.get("source"),
                a.get("domain"), a.get("topic"), a.get("significance"),
                a.get("verified",0),
                a.get("sentiment_overall"), a.get("sentiment_environmental"),
                a.get("sentiment_economic"), a.get("sentiment_political"),
                a.get("sentiment_social"), a.get("sentiment_framing"),
                a.get("fetched_at") or now(), a.get("published_at"),
                a.get("run_date") or today(),
                a.get("scout_run_id"), a.get("analyst_run_id")))
            self.conn.commit()
            return self.conn.total_changes > 0
        except sqlite3.Error as e:
            print(f"DB error: {e}", file=sys.stderr)
            return False

    def upsert_contact(self, c):
        existing = self.conn.execute(
            "SELECT id FROM contacts WHERE name=? AND organisation=?",
            (c.get("name"), c.get("organisation"))).fetchone()
        row_id = existing["id"] if existing else (c.get("id") or new_id())
        self.conn.execute("""INSERT OR REPLACE INTO contacts
            (id,name,role,organisation,organisation_type,decision_power,ngo_access,
             influence_score,profile_url,contact_url,email,policies_owned,
             why_relevant,source_url,notes,last_updated)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, c.get("name","Unknown"),
            c.get("role") or c.get("title",""),
            c.get("organisation") or c.get("org",""),
            c.get("organisation_type","government"),
            c.get("decision_power") or c.get("power"),
            c.get("ngo_access",1),
            c.get("influence_score") or c.get("effective_score"),
            c.get("profile_url") or c.get("url"),
            c.get("contact_url"), c.get("email"),
            json.dumps(c.get("policies_owned") or c.get("policies",[])),
            c.get("why_relevant") or c.get("relevance"),
            c.get("source_url"), c.get("notes"), now()))
        self.conn.commit()
        return row_id

    def insert_finding(self, f):
        row_id = f.get("id") or new_id()
        self.conn.execute("""INSERT OR IGNORE INTO findings
            (id,paperclip_issue_id,agent,priority,category,title,body,
             source_url,source_name,action_required,deadline,
             coalition_opportunity,evidence_value,fetched_at,run_date)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, f.get("paperclip_issue_id") or f.get("issue_id"),
            f.get("agent","unknown"), f.get("priority","MEDIUM"),
            f.get("category"), f.get("title","Untitled"),
            f.get("body") or f.get("description",""),
            f.get("source_url"), f.get("source_name"),
            f.get("action_required") or f.get("action"),
            f.get("deadline"),
            1 if f.get("coalition_opportunity") else 0,
            f.get("evidence_value"),
            f.get("fetched_at") or now(),
            f.get("run_date") or today()))
        self.conn.commit()
        return row_id

    def upsert_policy(self, p):
        existing = self.conn.execute(
            "SELECT id FROM policies WHERE url=?", (p.get("url"),)).fetchone()
        row_id = existing["id"] if existing else (p.get("id") or new_id())
        self.conn.execute("""INSERT OR REPLACE INTO policies
            (id,title,body,url,owner,status,consultation_open,
             consultation_deadline,relevance,ngo_position,last_hash,last_checked)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, p.get("title","Untitled"),
            p.get("body") or p.get("description"),
            p.get("url"), p.get("owner") or p.get("body_name"),
            p.get("status"),
            1 if p.get("consultation_open") else 0,
            p.get("consultation_deadline") or p.get("deadline"),
            p.get("relevance"), p.get("ngo_position"),
            p.get("last_hash") or p.get("hash"),
            p.get("last_checked") or now()))
        self.conn.commit()
        return row_id

    def insert_ngo_intel(self, n):
        row_id = n.get("id") or new_id()
        self.conn.execute("""INSERT OR IGNORE INTO ngo_intel
            (id,organisation,organisation_category,type,title,summary,
             significance,coalition_opportunity,evidence_value,
             counter_argument_needed,url,fetched_at,run_date)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, n.get("organisation","Unknown"),
            n.get("organisation_category","allied"),
            n.get("type","report"), n.get("title","Untitled"),
            n.get("summary"), n.get("significance"),
            1 if n.get("coalition_opportunity") else 0,
            n.get("evidence_value"),
            1 if n.get("counter_argument_needed") else 0,
            n.get("url") or n.get("source_url"),
            n.get("fetched_at") or now(),
            n.get("run_date") or today()))
        self.conn.commit()
        return row_id

    def insert_finance_deal(self, d):
        row_id = d.get("id") or new_id()
        self.conn.execute("""INSERT OR IGNORE INTO finance_deals
            (id,institution,project_name,amount_usd,amount_brl,currency_note,
             deal_type,project_type,stage,intervention_window,priority,
             source_url,summary,recommended_action,fetched_at,run_date)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, d.get("institution","Unknown"), d.get("project_name"),
            d.get("amount_usd"), d.get("amount_brl"), d.get("currency_note"),
            d.get("deal_type","unknown"), d.get("project_type"),
            d.get("stage"), d.get("intervention_window"),
            d.get("priority","MEDIUM"), d.get("source_url"),
            d.get("summary"),
            d.get("recommended_action") or d.get("action"),
            d.get("fetched_at") or now(),
            d.get("run_date") or today()))
        self.conn.commit()
        return row_id

    def insert_report(self, r):
        row_id = r.get("id") or new_id()
        recipients = r.get("recipients",[])
        self.conn.execute("""INSERT OR IGNORE INTO reports
            (id,title,subject,body,report_type,run_date,sent_at,
             email_status,recipients,recipient_count,paperclip_issue)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
            row_id, r.get("title","Untitled"), r.get("subject"),
            r.get("body",""), r.get("report_type","daily_digest"),
            r.get("run_date") or today(), r.get("sent_at"),
            r.get("email_status","pending"),
            json.dumps(recipients), len(recipients),
            r.get("paperclip_issue")))
        self.conn.commit()
        return row_id

    def log_run(self, r):
        self.conn.execute("""INSERT OR REPLACE INTO run_log
            (id,agent_name,agent_id,status,started_at,finished_at,
             duration_sec,items_found,items_created,cost_usd,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
            r.get("id") or new_id(),
            r.get("agent_name","unknown"), r.get("agent_id"),
            r.get("status"), r.get("started_at"), r.get("finished_at"),
            r.get("duration_sec"),
            r.get("items_found",0), r.get("items_created",0),
            r.get("cost_usd"), r.get("notes")))
        self.conn.commit()

    def is_url_seen(self, url):
        return self.conn.execute(
            "SELECT 1 FROM seen_urls WHERE url=?", (url,)).fetchone() is not None

    def mark_url_seen(self, url, agent="unknown"):
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_urls (url,first_seen_by) VALUES(?,?)",
            (url, agent))
        self.conn.commit()

    def mark_urls_seen(self, urls, agent="unknown"):
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen_urls (url,first_seen_by) VALUES(?,?)",
            [(u, agent) for u in urls])
        self.conn.commit()

    def get_alert_hash(self, url):
        row = self.conn.execute(
            "SELECT hash FROM alert_hashes WHERE url=?", (url,)).fetchone()
        return row["hash"] if row else None

    def update_alert_hash(self, url, new_hash):
        self.conn.execute("""INSERT OR REPLACE INTO alert_hashes
            (url,hash,last_checked,check_count)
            VALUES(?,?,?,COALESCE((SELECT check_count FROM alert_hashes WHERE url=?),0)+1)
            """, (url, new_hash, now(), url))
        self.conn.commit()

    def stats(self):
        tables = ["articles","contacts","findings","policies",
                  "ngo_intel","finance_deals","reports","seen_urls","run_log"]
        return {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in tables}

    def query(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]


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
    elif cmd == "insert-report" and len(sys.argv) > 2:
        print(db.insert_report(json.loads(sys.argv[2])))
    elif cmd == "mark-url-seen" and len(sys.argv) > 2:
        db.mark_url_seen(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else "unknown")
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
