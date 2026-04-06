#!/usr/bin/env python3
import argparse, json, smtplib, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

WORKSPACE = Path("/home/holder/.paperclip/instances/default/companies/d54903c8-880c-48ed-ba9f-6fd2bb571aef/workspace")

def load_json(path, label):
    if not path.exists():
        print(f"ERROR: {label} not found at {path}", file=sys.stderr)
        sys.exit(2)
    with open(path) as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args()

    body_path = Path(args.body_file)
    if not body_path.exists():
        print(f"ERROR: body file not found: {body_path}", file=sys.stderr)
        sys.exit(2)

    body = body_path.read_text()
    config = load_json(WORKSPACE / "smtp_config.json", "smtp_config.json")
    mailing = load_json(WORKSPACE / "mailing_list.json", "mailing_list.json")

    recipients = mailing.get("recipients", [])
    if not recipients:
        print("ERROR: no recipients in mailing_list.json", file=sys.stderr)
        sys.exit(2)

    smtp_host = config["host"]
    smtp_port = int(config.get("port", 587))
    smtp_user = config["username"]
    smtp_pass = config["password"]
    from_addr = config.get("from_address", smtp_user)
    from_name = config.get("from_name", "Climate Intelligence Platform")

    errors = []
    sent = []

    for r in recipients:
        to_addr = r["email"]
        to_name = r.get("name", to_addr)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = args.subject
            msg["From"] = f"{from_name} <{from_addr}>"
            msg["To"] = f"{to_name} <{to_addr}>"
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_addr], msg.as_string())

            sent.append(to_addr)
            print(f"Sent to {to_addr}")
        except Exception as e:
            errors.append(f"{to_addr}: {e}")
            print(f"FAILED {to_addr}: {e}", file=sys.stderr)

    print(f"Sent: {len(sent)}, Failed: {len(errors)}")
    if errors and not sent:
        sys.exit(1)

if __name__ == "__main__":
    main()
