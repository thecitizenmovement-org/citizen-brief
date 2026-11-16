#!/usr/bin/env python3
"""Citizen Brief auto-poster.

Delivers today's brief rows (Shasta + Tehama) from Supabase to Telegram
(@thecitizenbrief) and the Facebook Page (The United Citizen), then writes
the message/post ids back to the row.

Dependency-free: urllib only. Env (GitHub Secrets in the Action):
  SUPABASE_URL, SUPABASE_SERVICE_KEY, BRIEF_BOT_TOKEN,
  FB_PAGE_TOKEN, FB_PAGE_ID

If a destination token is missing/empty, that destination is SKIPPED with a
clear log line and the script still exits 0. Nothing here fails the run for
a missing token. If there is no brief row for today, logs 'no brief today'
and exits 0.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

COUNTIES = ["Shasta", "Tehama"]
CHANNEL = "@thecitizenbrief"
STORE_URL = "thecitizenmovement.store"


def log(msg):
    print(f"[brief] {msg}", flush=True)


def today_pt():
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


def supabase_headers():
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_get(path, params):
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    url = f"{base}/rest/v1/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=supabase_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log(f"Supabase GET {path} failed: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        return None
    except urllib.error.URLError as e:
        log(f"Supabase GET {path} failed: {e.reason}")
        return None


def supabase_patch_brief(row_id, fields):
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    url = f"{base}/rest/v1/briefs?id=eq.{row_id}"
    headers = dict(supabase_headers())
    headers["Prefer"] = "return=minimal"
    req = urllib.request.Request(
        url, data=json.dumps(fields).encode("utf-8"), headers=headers, method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            log(f"wrote back {fields} to brief {row_id} (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        log(f"Supabase PATCH brief {row_id} failed: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        return False
    except urllib.error.URLError as e:
        log(f"Supabase PATCH brief {row_id} failed: {e.reason}")
        return False


def get_briefs(date_str):
    rows = []
    for county in COUNTIES:
        data = supabase_get("briefs", {"select": "*", "date": f"eq.{date_str}", "county": f"eq.{county}"})
        if not data:
            log(f"no brief row for {county} on {date_str}")
            continue
        rows.append(data[0])
        log(f"found brief for {county} on {date_str}: {data[0].get('headline', '')[:80]}")
    return rows


def get_sponsor_footer():
    data = supabase_get(
        "sponsors",
        {"select": "name", "active": "eq.true", "tier": "eq.sponsor",
         "order": "created_at.asc", "limit": "1"},
    )
    if data:
        name = data[0].get("name") or "a supporter"
        log(f"active sponsor: {name}")
        return (f"Today's Brief is supported by {name} — thank you. "
                f"Want your business here? $50/mo: {STORE_URL}")
    log("no active sponsor")
    return f"Today's Brief has no sponsor yet — put your business here $50/mo"


def build_message(row, footer):
    parts = []
    if row.get("headline"):
        parts.append(row["headline"])
    if row.get("body"):
        parts.append(row["body"])
    if row.get("sources"):
        parts.append(f"Sources: {row['sources']}")
    parts.append(footer)
    return "\n\n".join(parts)


def post_telegram(token, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": CHANNEL, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        msg_id = body.get("result", {}).get("message_id")
        log(f"Telegram: posted to {CHANNEL}, message_id={msg_id}")
        return str(msg_id) if msg_id is not None else None
    except urllib.error.HTTPError as e:
        log(f"Telegram: FAILED HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        return None
    except urllib.error.URLError as e:
        log(f"Telegram: FAILED {e.reason}")
        return None


def post_facebook(token, page_id, text):
    url = f"https://graph.facebook.com/v21.0/{page_id}/feed"
    payload = urllib.parse.urlencode({"message": text, "access_token": token}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        post_id = body.get("id")
        log(f"Facebook: posted to page {page_id}, post_id={post_id}")
        return post_id
    except urllib.error.HTTPError as e:
        log(f"Facebook: FAILED HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        return None
    except urllib.error.URLError as e:
        log(f"Facebook: FAILED {e.reason}")
        return None


def main():
    date_str = today_pt()
    log(f"running for {date_str} (America/Los_Angeles)")

    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_KEY"):
        log("SUPABASE_URL / SUPABASE_SERVICE_KEY missing — cannot fetch briefs. Exiting 0.")
        return 0

    rows = get_briefs(date_str)
    if not rows:
        log("no brief today")
        return 0

    footer = get_sponsor_footer()
    tg_token = os.environ.get("BRIEF_BOT_TOKEN", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()

    if not tg_token:
        log("BRIEF_BOT_TOKEN missing — SKIPPING Telegram")
    if not fb_token or not fb_page_id:
        log("FB_PAGE_TOKEN / FB_PAGE_ID missing — SKIPPING Facebook")

    for row in rows:
        county = row.get("county", "?")
        text = build_message(row, footer)
        updates = {}
        if tg_token:
            msg_id = post_telegram(tg_token, text)
            if msg_id:
                updates["tg_msg_id"] = msg_id
        if fb_token and fb_page_id:
            post_id = post_facebook(fb_token, fb_page_id, text)
            if post_id:
                updates["fb_post_id"] = post_id
        if updates:
            supabase_patch_brief(row["id"], updates)
        else:
            log(f"{county}: nothing posted (no destinations available), row untouched")

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
