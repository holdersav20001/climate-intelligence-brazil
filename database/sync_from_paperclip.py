#!/usr/bin/env python3
"""Sync Paperclip issues to SQLite. Usage: python3 sync_from_paperclip.py"""
import argparse, json, re, sys, urllib.request
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db import DB, new_id, now, today

PAPERCLIP_URL = "http://localhost:3100"
COMPANY_ID = "d54903c8-880c-48ed-ba9f-6fd2bb571aef"

AGENT_NAMES = {
    "026e19f1-d44c-49f9-85b1-94031444c71e": "orchestrator",
    "3bb1d3f5-078d-426b-9b1b-4fd4687bba1d": "scout",
    "24694c2f-cdeb-4b24-a641-de88969666a0": "analyst",
    "512f07a7-9d19-4c54-9a12-a3fa198fc190": "verifier",
    "6698ab9e-4598-4d23-a947-44cdda66d9e6": "policy_tracker",
    "059d195f-59d0-4cf7-9676-1c019380e742": "contact_mapper",
    "c6d80362-bfa6-44fa-acf0-ba853538463e": "reporter",
    "4e539647-7219-4382-bba5-649b46c6db40": "alert",
    "4aed1e77-e280-4ffb-97f6-70a9f2a3d7ce": "parliamentary_monitor",
    "16f6833e-bb2b-4d5a-bfbf-fdca33d766ef": "ngo_monitor",
    "31672a00-637d-487a-b0ac-774ad7866a9c": "finance_monitor",
    "19e2eafc-f473-4f2f-a65a-6a58b3657690": "cop30_monitor",
    "bc3bbaf6-b290-4b0f-9ef3-befe87fd9d37": "consultation_writer",
    "5b947d5e-dd85-4b45-a6de-382cc7f259d7": "translator",
}


def fetch_json(path):
    try:
        with urllib.request.urlopen(f"{PAPERCLIP_URL}{path}", timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  fetch error {path}: {e}", file=sys.stderr)
        return None

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def classify_issue(issue):
    title = issue.get("title","").lower()
    desc = issue.get("description","") or ""
    identifier = issue.get("identifier","")
    agent = AGENT_NAMES.get(issue.get("assigneeAgentId",""), "unknown")
    if identifier in ["CLI-1","CLI-2"]: return "skip", None
    if "scout:" in title and "monitor" in title: return "skip", None
    if agent == "reporter" or "daily digest" in title or "reporter:" in title: return "report", None
    if agent == "policy_tracker" or "policy tracker:" in title: return "finding", "policy_tracker"
    if agent == "finance_monitor" or "finance:" in title: return "finding", "finance_monitor"
    if agent == "cop30_monitor" or "cop30" in title or "colombia" in title: return "finding", "cop30_monitor"
    if agent == "ngo_monitor" or "coalition:" in title or "iema" in title or "talanoa" in title: return "finding", "ngo_monitor"
    if agent == "parliamentary_monitor" or "parliament:" in title: return "finding", "parliamentary_monitor"
    if "source url:" in desc.lower() or "fetch date:" in desc.lower(): return "article", None
    if "critical:" in title or "high:" in title or "evidence:" in title: return "finding", "unknown"
    return "article", None

def extract_source_url(desc):
    m = re.search(r"https?://[^\s\)]+", desc or "")
    return m.group(0).rstrip(".,)") if m else None

def extract_significance(text):
    m = re.search(r"significance[:\s]+([0-9.]+)", text or "", re.IGNORECASE)
    if m: return float(m.group(1))
    m = re.search(r"\b(0\.[6-9][0-9]|1\.0)\b", text or "")
    return float(m.group(0)) if m else None

def extract_domain(title, desc):
    text = (title + " " + (desc or "")).lower()
    if any(x in text for x in ["petrobras","pre-sal","fpso","gas","coal","fossil","lng","oil"]): return "coal_gas"
    if any(x in text for x in ["solar","wind","renewable","hydrogen","clean energy"]): return "renewables"
    if any(x in text for x in ["cop30","ndc","unfccc","climate","policy"]): return "policy"
    if any(x in text for x in ["bndes","ifc","financing","investment"]): return "finance"
    return "other"

def extract_priority(title):
    t = title.upper()
    if "CRITICAL" in t: return "CRITICAL"
    if "HIGH" in t: return "HIGH"
    if "COALITION" in t: return "COALITION"
    if "EVIDENCE" in t: return "EVIDENCE"
    return "MEDIUM"

def sync_issues(db, dry_run=False):
    log("Fetching issues...")
    data = fetch_json(f"/api/companies/{COMPANY_ID}/issues?limit=100")
    if not data: log("ERROR: could not fetch issues"); return 0,0,0
    issues = sorted(data, key=lambda x: x.get("identifier",""))
    a_count = f_count = r_count = 0
    for issue in issues:
        itype, agent = classify_issue(issue)
        title = issue.get("title","")
        desc = issue.get("description","") or ""
        identifier = issue.get("identifier","")
        created = issue.get("createdAt","")
        run_date = created[:10] if created else today()
        if itype == "skip": continue
        elif itype == "article":
            url = extract_source_url(desc) or f"paperclip://issue/{identifier}"
            a = {"id": issue.get("id") or new_id(), "url": url, "title": title,
                 "summary": desc[:500], "domain": extract_domain(title, desc),
                 "significance": extract_significance(title+" "+desc),
                 "verified": 1 if issue.get("status")=="done" else 0,
                 "fetched_at": created or now(), "run_date": run_date}
            m = re.search(r"https?://([^/\s]+)", desc, re.IGNORECASE)
            if m: a["source_name"] = m.group(1).replace("www.","")
            if not dry_run: db.insert_article(a)
            a_count += 1
        elif itype == "finding":
            m = re.search(r"action:?\s*(.+?)(?:\n|$)", desc, re.IGNORECASE)
            action = m.group(1).strip()[:200] if m else None
            f = {"id": issue.get("id") or new_id(), "paperclip_issue_id": identifier,
                 "agent": agent or "unknown", "priority": extract_priority(title),
                 "category": extract_domain(title, desc), "title": title, "body": desc,
                 "source_url": extract_source_url(desc), "action_required": action,
                 "coalition_opportunity": 1 if "coalition" in title.lower() else 0,
                 "evidence_value": "high" if "evidence:" in title.lower() else None,
                 "fetched_at": created or now(), "run_date": run_date,
                 "status": "open" if issue.get("status") in ["todo","in_progress","in_review"] else "actioned"}
            if not dry_run: db.insert_finding(f)
            f_count += 1
        elif itype == "report":
            r = {"id": issue.get("id") or new_id(), "title": title, "body": desc,
                 "report_type": "daily_digest" if "digest" in title.lower() else "brief",
                 "run_date": run_date, "email_status": "unknown", "paperclip_issue": identifier}
            if not dry_run: db.insert_report(r)
            r_count += 1
    return a_count, f_count, r_count

def sync_runs(db, dry_run=False):
    log("Fetching run logs...")
    total = 0
    for agent_id, agent_name in AGENT_NAMES.items():
        data = fetch_json(f"/api/companies/{COMPANY_ID}/heartbeat-runs?agentId={agent_id}&limit=20")
        if not data: continue
        for run in data:
            started, finished = run.get("startedAt"), run.get("finishedAt")
            duration = None
            if started and finished:
                try:
                    duration = int((datetime.fromisoformat(finished.replace("Z","")) -
                                    datetime.fromisoformat(started.replace("Z",""))).total_seconds())
                except: pass
            r = {"id": run.get("id") or new_id(), "agent_name": agent_name, "agent_id": agent_id,
                 "status": run.get("status"), "started_at": started, "finished_at": finished,
                 "duration_sec": duration,
                 "cost_usd": (run.get("resultJson") or {}).get("total_cost_usd")}
            if not dry_run: db.log_run(r)
            total += 1
    return total

def sync_seen_urls(db, dry_run=False):
    ws = Path("/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace")
    total = 0
    for fname, agent in [("seen_urls.txt","scout"),("ngo_seen.txt","ngo_monitor"),
                          ("finance_seen.txt","finance_monitor"),("cop30_seen.txt","cop30_monitor")]:
        fpath = ws / fname
        if not fpath.exists(): continue
        urls = [l.strip() for l in fpath.read_text().splitlines() if l.strip()]
        if not dry_run: db.mark_urls_seen(urls, agent)
        total += len(urls)
    return total

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    log("=== Paperclip to SQLite Sync ===")
    db = DB()
    a, fi, r = sync_issues(db, args.dry_run)
    runs = sync_runs(db, args.dry_run)
    urls = sync_seen_urls(db, args.dry_run)
    if not args.dry_run:
        s = db.stats()
        log("\n── Database after sync ─────────────────────")
        for k, v in s.items(): log(f"  {k:<20} {v:>6} rows")
        log("────────────────────────────────────────────")
    log(f"Synced: {a} articles  {fi} findings  {r} reports  {runs} runs  {urls} seen URLs")
    db.close()

if __name__ == "__main__":
    main()
