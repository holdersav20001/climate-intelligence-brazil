#!/usr/bin/env python3
"""
Sync agent instructions: copy each agent's external AGENTS.md into its
Paperclip-managed instructions path so the UI shows the correct content.

Also ensures instructionsBundleMode is set to "managed" (not "external")
so the Paperclip UI renders the file inline rather than treating it as
an opaque external reference.

Run at container startup (before the node process). Fails silently so it
never blocks the server from starting.
"""
import json
import os
import shutil
import sys
import time

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit(0)

# Wait up to 10s for postgres to be ready
for attempt in range(10):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    print("[sync-instructions] postgres not ready after 10s — skipping", flush=True)
    sys.exit(0)

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT id, name, company_id, adapter_config
    FROM public.agents
    WHERE adapter_config IS NOT NULL
""")
agents = cur.fetchall()

copied = 0
skipped = 0

for agent in agents:
    ac = agent["adapter_config"] or {}
    external_path = ac.get("instructionsFilePath")
    company_id = agent["company_id"]
    agent_id = agent["id"]
    name = agent["name"]

    if not external_path or not os.path.isfile(external_path):
        skipped += 1
        continue

    managed_dir = (
        f"/paperclip/instances/default/companies/{company_id}"
        f"/agents/{agent_id}/instructions"
    )
    managed_path = os.path.join(managed_dir, "AGENTS.md")

    if not os.path.isdir(managed_dir):
        skipped += 1
        continue

    # Copy if managed file is the generic placeholder or external file is newer
    managed_size = os.path.getsize(managed_path) if os.path.isfile(managed_path) else 0
    external_size = os.path.getsize(external_path)
    external_mtime = os.path.getmtime(external_path)
    managed_mtime = os.path.getmtime(managed_path) if os.path.isfile(managed_path) else 0

    needs_copy = managed_size <= 400 or external_mtime > managed_mtime

    # Ensure bundle mode is "managed" so the UI renders content inline
    needs_db_update = ac.get("instructionsBundleMode") != "managed"

    if needs_copy:
        # Read and normalise to CRLF — Paperclip UI's markdown/frontmatter parser
        # expects CRLF line endings; files from the Linux volume mount arrive as LF.
        with open(external_path, "rb") as f:
            content = f.read()
        content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        with open(managed_path, "wb") as f:
            f.write(content)
        # Preserve timestamps
        times = os.stat(external_path)
        os.utime(managed_path, (times.st_atime, times.st_mtime))
        print(f"[sync-instructions] {name}: synced {len(content)}b (CRLF)", flush=True)
        copied += 1

    if needs_db_update:
        ac["instructionsBundleMode"] = "managed"
        ac["instructionsRootPath"] = managed_dir
        update_cur = conn.cursor()
        update_cur.execute(
            "UPDATE public.agents SET adapter_config=%s, updated_at=NOW() WHERE id=%s",
            (json.dumps(ac), agent_id)
        )
        print(f"[sync-instructions] {name}: set bundleMode=managed", flush=True)

    if not needs_copy and not needs_db_update:
        skipped += 1

conn.commit()
conn.close()

print(f"[sync-instructions] done — {copied} synced, {skipped} skipped", flush=True)
