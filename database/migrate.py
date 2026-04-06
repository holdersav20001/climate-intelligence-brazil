#!/usr/bin/env python3
"""
Climate Intelligence Platform - migrate.py
Migrates existing workspace JSON/JSONL files to SQLite.
Usage: python3 migrate.py [--dry-run]
"""
import argparse, json, sys
from datetime import datetime, date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db import DB, new_id, now, today

WORKSPACE = Path("/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace")

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def migrate_articles(db, workspace, dry_run):
    path = workspace / "articles.jsonl"
    if not path.exists(): log("articles.jsonl not found"); return 0
    inserted = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: a = json.loads(line)
            except: continue
            if not dry_run and db.insert_article(a): inserted += 1
            elif dry_run: inserted += 1
    log(f"Articles: {inserted} rows")
    return inserted

def migrate_contacts(db, workspace, dry_run):
    path = workspace / "influence_model.json"
    if not path.exists(): log("influence_model.json not found"); return 0
    with open(path) as f: data = json.load(f)
    contacts = data if isinstance(data, list) else data.get("contacts", [])
    inserted = 0
    for c in contacts:
        if not dry_run: db.upsert_contact(c)
        inserted += 1
    log(f"Contacts: {inserted} rows")
    return inserted

def migrate_policies(db, workspace, dry_run):
    path = workspace / "tracked_policies.json"
    if not path.exists(): log("tracked_policies.json not found"); return 0
    with open(path) as f: data = json.load(f)
    policies = data if isinstance(data, list) else data.get("policies", [])
    inserted = 0
    for p in policies:
        if not dry_run: db.upsert_policy(p)
        inserted += 1
    log(f"Policies: {inserted} rows")
    return inserted

def migrate_alert_hashes(db, workspace, dry_run):
    path = workspace / "alert_hashes.json"
    if not path.exists(): log("alert_hashes.json not found"); return 0
    with open(path) as f: data = json.load(f)
    inserted = 0
    for url, info in data.items():
        if not dry_run:
            db.conn.execute(
                "INSERT OR REPLACE INTO alert_hashes (url, hash, last_checked) VALUES (?,?,?)",
                (url, info.get("hash"), info.get("last_checked")))
        inserted += 1
    if not dry_run: db.conn.commit()
    log(f"Alert hashes: {inserted} rows")
    return inserted

def migrate_seen_urls(db, workspace, dry_run):
    inserted = 0
    for filename, agent in [("seen_urls.txt","scout"),("ngo_seen.txt","ngo_monitor"),
                             ("finance_seen.txt","finance_monitor"),("cop30_seen.txt","cop30_monitor")]:
        path = workspace / filename
        if not path.exists(): continue
        urls = [l.strip() for l in open(path) if l.strip()]
        if not dry_run: db.mark_urls_seen(urls, agent)
        inserted += len(urls)
    log(f"Seen URLs: {inserted} rows")
    return inserted

def migrate_ngo_reports(db, workspace, dry_run):
    d = workspace / "ngo_reports"
    if not d.exists(): log("ngo_reports/ not found"); return 0
    inserted = 0
    for f in d.glob("*.md"):
        content = f.read_text()
        title = f.stem.replace("_"," ").replace("-"," ").title()
        for line in content.split("\n")[:5]:
            if line.startswith("# "): title = line[2:].strip()
        n = {"organisation":"Unknown","organisation_category":"allied",
             "type":"report","title":title,"summary":content[:500],
             "fetched_at":now(),"run_date":today()}
        if not dry_run: db.insert_ngo_intel(n)
        inserted += 1
    log(f"NGO reports: {inserted} rows")
    return inserted

def migrate_finance_deals(db, workspace, dry_run):
    d = workspace / "finance_deals"
    if not d.exists(): log("finance_deals/ not found"); return 0
    inserted = 0
    for f in d.glob("*.md"):
        content = f.read_text()
        title = f.stem.replace("_"," ").title()
        for line in content.split("\n")[:5]:
            if line.startswith("# "): title = line[2:].strip()
        deal = {"institution":"Unknown","project_name":title,"deal_type":"fossil_fuel",
                "stage":"announced","priority":"MEDIUM","summary":content[:500],
                "fetched_at":now(),"run_date":today()}
        if not dry_run: db.insert_finance_deal(deal)
        inserted += 1
    log(f"Finance deals: {inserted} rows")
    return inserted

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    log(f"Workspace: {WORKSPACE}")
    log(f"Dry run: {args.dry_run}")
    if not WORKSPACE.exists():
        log(f"ERROR: workspace not found"); sys.exit(1)
    db = DB()
    migrate_articles(db, WORKSPACE, args.dry_run)
    migrate_contacts(db, WORKSPACE, args.dry_run)
    migrate_policies(db, WORKSPACE, args.dry_run)
    migrate_alert_hashes(db, WORKSPACE, args.dry_run)
    migrate_seen_urls(db, WORKSPACE, args.dry_run)
    migrate_ngo_reports(db, WORKSPACE, args.dry_run)
    migrate_finance_deals(db, WORKSPACE, args.dry_run)
    if not args.dry_run:
        s = db.stats()
        log("\n── Database summary ─────────────────────────")
        for k,v in s.items(): log(f"  {k:<20} {v:>6} rows")
        log("─────────────────────────────────────────────")
    db.close()
    log("Done.")

if __name__ == "__main__":
    main()
