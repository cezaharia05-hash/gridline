"""Merge each day's scrape into the data file, remembering when roles first
appeared and when they disappeared."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def job_id(company: str, url: str) -> str:
    return hashlib.sha1(f"{company}|{url}".encode()).hexdigest()[:12]


def load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"jobs": [], "companies": []}


def merge(previous: dict, found: list[dict], statuses: list[dict], today: date, keep_closed_days: int = 45) -> dict:
    """found: jobs seen in this run. statuses: one entry per company with ok flag.
    Jobs from companies whose scrape failed keep their previous state, so a
    broken scraper doesn't make every role look closed."""
    today_s = today.isoformat()
    failed = {s["name"] for s in statuses if s.get("state") == "error"}
    old = {j["id"]: j for j in previous.get("jobs", [])}
    merged: dict[str, dict] = {}

    for job in found:
        prior = old.get(job["id"], {})
        merged[job["id"]] = {
            **job,
            "first_seen": prior.get("first_seen", today_s),
            "last_seen": today_s,
            "active": True,
        }

    cutoff = (today - timedelta(days=keep_closed_days)).isoformat()
    for jid, job in old.items():
        if jid in merged:
            continue
        if job["company"] in failed:
            merged[jid] = job
        elif job.get("last_seen", today_s) >= cutoff:
            merged[jid] = {**job, "active": False}

    # Open roles first, newest first, then alphabetical.
    jobs = sorted(
        merged.values(),
        key=lambda j: (not j["active"], -int(j["first_seen"].replace("-", "")), j["company"], j["title"]),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "companies": statuses,
        "jobs": jobs,
    }


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
