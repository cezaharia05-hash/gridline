"""One adapter per hiring platform. Each returns a list of raw Posting objects."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

USER_AGENT = "Gridline/1.0 (personal graduate job tracker; runs once a day)"
TIMEOUT = 30
PAUSE = 1.0  # seconds between requests to the same site


@dataclass
class Posting:
    title: str
    url: str
    location: str = ""
    posted: str = ""
    ref: str = ""


class AdapterError(RuntimeError):
    pass


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Language": "en-GB,en;q=0.8"})
    return s


def request_json(s: requests.Session, method: str, url: str, retries: int = 2, **kwargs):
    last = None
    for attempt in range(retries + 1):
        try:
            r = s.request(method, url, timeout=TIMEOUT, **kwargs)
            if r.status_code == 429 or r.status_code >= 500:
                raise AdapterError(f"HTTP {r.status_code} from {url}")
            if r.status_code in (401, 403):
                raise AdapterError(f"HTTP {r.status_code} from {url} (site refused the request; it may block automated access)")
            if r.status_code >= 400:
                # Won't fix itself on retry: usually a wrong tenant/site/token.
                raise AdapterError(f"HTTP {r.status_code} from {url} (check the config values)")
            return r.json()
        except (requests.RequestException, ValueError, AdapterError) as exc:
            last = exc
            if isinstance(exc, AdapterError) and ("check the config" in str(exc) or "refused" in str(exc)):
                break
            time.sleep(PAUSE * (attempt + 2))
    raise AdapterError(str(last))


def get_adapter(ats: str):
    from . import greenhouse, lever, smartrecruiters, workday

    return {
        "workday": workday.fetch,
        "greenhouse": greenhouse.fetch,
        "lever": lever.fetch,
        "smartrecruiters": smartrecruiters.fetch,
    }.get(ats)
