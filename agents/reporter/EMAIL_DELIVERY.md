# EMAIL_DELIVERY.md — Email Delivery Instructions

After completing every report, brief, or daily digest, send it by email
using the SMTP script. Email is best-effort — the report is always saved
locally first. A failed email never blocks or fails the run.

---

## STEP 1 — ALWAYS DO THIS FIRST

Save the completed report to:
/paperclip/agents/workspace/pending_review/[YYYY-MM-DD]_report.md

This happens unconditionally before any email attempt.

---

## STEP 2 — Send via SMTP script

Run this command to send the email:

python3 /paperclip/agents/workspace/send_email.py \
  --subject "Brazil Energy Intelligence — [date]" \
  --body-file /paperclip/agents/workspace/pending_review/[filename]

The script reads recipients from mailing_list.json and SMTP settings from
smtp_config.json — both in the workspace. No credentials are hardcoded.

### If the script succeeds (exit code 0):
Log: "Email sent to N recipients"
Continue to Step 3.

### If the script fails (any error or non-zero exit):
Log the error message.
Do not retry.
Continue to Step 3 — note the failure in the completion issue.
The report is already saved in Step 1, nothing is lost.

---

## STEP 3 — Always create a completion issue

Always create a Paperclip issue after every run:

If email succeeded:
  Title: Report delivered: Brazil Energy Intelligence [date]
  Status: done
  Body: Sent to N recipients. Report saved to [filename]. [Top finding in one line].

If email failed:
  Title: Report ready (email failed): Brazil Energy Intelligence [date]
  Status: in_review
  Body: Email failed — [error message]. Report saved to [filename]. Send manually.

If smtp_config.json missing:
  Title: Report ready (SMTP not configured): Brazil Energy Intelligence [date]
  Status: in_review
  Body: smtp_config.json not found. See workspace/smtp_config.json.example to configure.

---

## Rules
- Step 1 (save file) is mandatory. Never skipped.
- Step 3 (create issue) is mandatory. Never skipped.
- Step 2 (email) is best-effort. Failure handled gracefully.
- Never hardcode email addresses or credentials.
- Recipients come from mailing_list.json only.
- SMTP credentials come from smtp_config.json only.

## CRITICAL: Database writes
Use db.py to persist structured intelligence to PostgreSQL.
The database URL is read automatically from $CLIMATE_DATABASE_URL.

Write a finding:
  python3 /paperclip/agents/db.py insert-finding '{"agent":"reporter","priority":"HIGH","title":"...","body":"...","source_url":"..."}'

Write an article:
  python3 /paperclip/agents/db.py insert-article '{"url":"...","title":"...","summary":"...","source_name":"..."}'

Check if URL already seen (deduplication):
  python3 /paperclip/agents/db.py is-url-seen "https://..."

Mark URL seen after processing:
  python3 /paperclip/agents/db.py mark-url-seen "https://..." "reporter"

Log a completed run:
  python3 /paperclip/agents/db.py log-run '{"agent_name":"reporter","status":"succeeded","items_found":3}'

Do NOT reference intelligence.db. Do NOT use SQLite. All data goes to PostgreSQL via db.py.
