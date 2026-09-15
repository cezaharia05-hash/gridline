"""Workday career sites expose a JSON search endpoint used by their own front end:
POST https://<tenant>.<dc>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs"""

from __future__ import annotations

import time

from . import PAUSE, AdapterError, Posting, request_json, session

PAGE_SIZE = 20  # Workday rejects larger pages
MAX_PAGES = 10  # per search term


def fetch(company: dict, cfg: dict, s=None) -> list[Posting]:
    for key in ("tenant", "dc", "site"):
        if not company.get(key):
            raise AdapterError(f"workday entry is missing '{key}'")
    s = s or session()
    host = f"https://{company['tenant']}.{company['dc']}.myworkdayjobs.com"
    api = f"{host}/wday/cxs/{company['tenant']}/{company['site']}/jobs"
    terms = company.get("search_terms") or cfg.get("workday_search_terms") or ["graduate"]

    seen: dict[str, Posting] = {}
    for term in terms:
        offset, total = 0, None
        for _ in range(MAX_PAGES):
            payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": term}
            data = request_json(s, "POST", api, json=payload)
            postings = data.get("jobPostings") or []
            if total is None:
                total = data.get("total") or 0  # only reliable on the first page
            for p in postings:
                path = p.get("externalPath")
                if not path or not p.get("title"):
                    continue
                url = f"{host}/en-US/{company['site']}{path}"
                bullets = p.get("bulletFields") or []
                seen.setdefault(url, Posting(
                    title=p["title"].strip(),
                    url=url,
                    location=p.get("locationsText") or "",
                    posted=p.get("postedOn") or "",
                    ref=bullets[0] if bullets else "",
                ))
            offset += PAGE_SIZE
            if not postings or offset >= total:
                break
            time.sleep(PAUSE)
        time.sleep(PAUSE)
    return list(seen.values())
