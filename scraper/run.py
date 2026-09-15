"""Daily run: scrape every company on the watchlist, filter, merge, save.

    python -m scraper.run            # writes docs/data/jobs.json
    python -m scraper.run --only Shell --verbose
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from .adapters import get_adapter, session
from .filters import evaluate
from .store import job_id, load, merge, save

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data" / "jobs.json"


def read_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="scrape just this company (by name)")
    ap.add_argument("--verbose", action="store_true", help="print every posting and why it was kept or dropped")
    ap.add_argument("--dry-run", action="store_true", help="don't write the data file")
    args = ap.parse_args(argv)

    cfg = read_yaml("filters.yaml")
    companies = read_yaml("companies.yaml")["companies"]
    if args.only:
        companies = [c for c in companies if c["name"].lower() == args.only.lower()]
        if not companies:
            print(f"No company called {args.only!r} in companies.yaml")
            return 2

    s = session()
    found, statuses = [], []
    for c in companies:
        status = {"name": c["name"], "sector": c.get("sector", ""), "ats": c.get("ats", "manual")}
        adapter = get_adapter(c.get("ats", "manual"))
        if adapter is None:
            statuses.append({**status, "state": "manual", "url": c.get("url", "")})
            continue
        try:
            postings = adapter(c, cfg, s)
        except Exception as exc:  # one broken site must not stop the run
            print(f"[error] {c['name']}: {exc}")
            statuses.append({**status, "state": "error", "error": str(exc)[:300]})
            continue

        kept = 0
        for p in postings:
            v = evaluate(p.title, p.location, cfg)
            if args.verbose:
                print(f"  {'KEEP' if v.keep else 'drop'} {c['name']}: {p.title} | {p.location} {('- ' + v.reason) if v.reason else ''}")
            if not v.keep:
                continue
            kept += 1
            found.append({
                "id": job_id(c["name"], p.url),
                "company": c["name"],
                "sector": c.get("sector", ""),
                "title": p.title,
                "location": p.location,
                "regions": list(v.regions),
                "function": v.function,
                "posted": p.posted,
                "url": p.url,
            })
        print(f"[ok] {c['name']}: {len(postings)} postings scanned, {kept} kept")
        statuses.append({**status, "state": "ok", "scanned": len(postings), "kept": kept})

    previous = load(DATA)
    data = merge(previous, found, statuses, date.today(), cfg.get("keep_closed_days", 45))
    data["work_rights"] = cfg.get("work_rights", [])
    if args.only:
        # Partial run: keep other companies' statuses and jobs untouched.
        names = {c["name"] for c in companies}
        data["companies"] = [x for x in previous.get("companies", []) if x["name"] not in names] + statuses
        data["jobs"] = [j for j in previous.get("jobs", []) if j["company"] not in names] + [
            j for j in data["jobs"] if j["company"] in names
        ]
    if args.dry_run:
        print(f"Dry run: {sum(j['active'] for j in data['jobs'])} open roles, nothing written")
    else:
        save(DATA, data)
        print(f"Wrote {DATA.relative_to(ROOT)}: {sum(j['active'] for j in data['jobs'])} open roles")
    errors = sum(1 for x in statuses if x["state"] == "error")
    ok = sum(1 for x in statuses if x["state"] == "ok")
    return 1 if ok == 0 and errors else 0


if __name__ == "__main__":
    sys.exit(main())
