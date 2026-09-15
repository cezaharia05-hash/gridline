"""SmartRecruiters public postings API: GET api.smartrecruiters.com/v1/companies/<token>/postings"""

from __future__ import annotations

import time

from . import PAUSE, AdapterError, Posting, request_json, session

# SmartRecruiters gives ISO country codes; spell out the European ones so the
# region filter recognises them.
COUNTRIES = {
    "gb": "United Kingdom", "uk": "United Kingdom", "ch": "Switzerland", "at": "Austria",
    "be": "Belgium", "bg": "Bulgaria", "hr": "Croatia", "cy": "Cyprus", "cz": "Czechia",
    "dk": "Denmark", "ee": "Estonia", "fi": "Finland", "fr": "France", "de": "Germany",
    "gr": "Greece", "hu": "Hungary", "ie": "Ireland", "it": "Italy", "lv": "Latvia",
    "lt": "Lithuania", "lu": "Luxembourg", "mt": "Malta", "nl": "Netherlands", "pl": "Poland",
    "pt": "Portugal", "ro": "Romania", "sk": "Slovakia", "si": "Slovenia", "es": "Spain",
    "se": "Sweden", "no": "Norway", "is": "Iceland", "li": "Liechtenstein", "us": "United States",
}

PAGE_SIZE = 100
MAX_PAGES = 10


def fetch(company: dict, cfg: dict, s=None) -> list[Posting]:
    token = company.get("token")
    if not token:
        raise AdapterError("smartrecruiters entry is missing 'token'")
    s = s or session()
    api = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
    out, offset = [], 0
    for _ in range(MAX_PAGES):
        data = request_json(s, "GET", api, params={"limit": PAGE_SIZE, "offset": offset})
        content = data.get("content") or []
        for j in content:
            if not j.get("name") or not j.get("id"):
                continue
            loc = j.get("location") or {}
            out.append(Posting(
                title=j["name"].strip(),
                url=f"https://jobs.smartrecruiters.com/{token}/{j['id']}",
                location=", ".join(x for x in (
                    loc.get("city"),
                    COUNTRIES.get((loc.get("country") or "").lower(), loc.get("country")),
                ) if x),
                posted=(j.get("releasedDate") or "")[:10],
                ref=j.get("refNumber") or "",
            ))
        offset += PAGE_SIZE
        if not content or offset >= (data.get("totalFound") or 0):
            break
        time.sleep(PAUSE)
    return out
