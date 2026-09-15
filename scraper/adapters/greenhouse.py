"""Greenhouse public job board API: GET boards-api.greenhouse.io/v1/boards/<token>/jobs"""

from __future__ import annotations

from . import AdapterError, Posting, request_json, session


def fetch(company: dict, cfg: dict, s=None) -> list[Posting]:
    token = company.get("token")
    if not token:
        raise AdapterError("greenhouse entry is missing 'token'")
    base = "https://boards-api.eu.greenhouse.io" if company.get("eu") else "https://boards-api.greenhouse.io"
    data = request_json(s or session(), "GET", f"{base}/v1/boards/{token}/jobs")
    out = []
    for j in data.get("jobs") or []:
        if not j.get("title") or not j.get("absolute_url"):
            continue
        out.append(Posting(
            title=j["title"].strip(),
            url=j["absolute_url"],
            location=(j.get("location") or {}).get("name") or "",
            posted=(j.get("updated_at") or "")[:10],
            ref=str(j.get("id") or ""),
        ))
    return out
