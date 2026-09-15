"""Lever public postings API: GET api.lever.co/v0/postings/<token>?mode=json"""

from __future__ import annotations

from datetime import datetime, timezone

from . import AdapterError, Posting, request_json, session


def fetch(company: dict, cfg: dict, s=None) -> list[Posting]:
    token = company.get("token")
    if not token:
        raise AdapterError("lever entry is missing 'token'")
    base = "https://api.eu.lever.co" if company.get("eu") else "https://api.lever.co"
    data = request_json(s or session(), "GET", f"{base}/v0/postings/{token}", params={"mode": "json"})
    out = []
    for j in data if isinstance(data, list) else []:
        if not j.get("text") or not j.get("hostedUrl"):
            continue
        cats = j.get("categories") or {}
        created = j.get("createdAt")
        posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).date().isoformat() if created else ""
        out.append(Posting(
            title=j["text"].strip(),
            url=j["hostedUrl"],
            location=cats.get("location") or ", ".join(cats.get("allLocations") or []),
            posted=posted,
            ref=j.get("id") or "",
        ))
    return out
