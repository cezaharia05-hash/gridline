"""Find which hiring platform a company uses and print a companies.yaml snippet.

    python -m scraper.discover "RWE" https://www.rwe.com
"""

from __future__ import annotations

import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .adapters import USER_AGENT

PATTERNS = [
    ("workday", re.compile(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.(eu\.)?greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.(eu\.)?lever\.co/([a-z0-9_-]+)")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)")),
    ("successfactors", re.compile(r"successfactors\.(?:com|eu)|jobs\.sap\.com|career\d*\.sapsf")),
    ("taleo", re.compile(r"taleo\.net")),
    ("oracle", re.compile(r"oraclecloud\.com/hcmUI/CandidateExperience")),
]
IGNORE_SLUGS = {"login", "job", "jobs", "wday", "embed", "en-us", "apply"}
LINK_HINTS = re.compile(r"career|job|karriere|carriere|carreira|lavora|graduate|early|vacanc|join", re.I)


def get(url: str) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25, allow_redirects=True)
        return r.text if r.ok else ""
    except requests.RequestException:
        return ""


def scan(html: str) -> list[tuple[str, tuple]]:
    hits: list[tuple[str, tuple]] = []
    for name, pat in PATTERNS:
        for m in pat.finditer(html):
            groups = m.groups()
            if name == "workday" and groups[2].lower() in IGNORE_SLUGS:
                continue
            if (name, groups) not in hits:
                hits.append((name, groups))
    return hits


def discover(start: str, max_pages: int = 15) -> list[tuple[str, tuple]]:
    visited, queue, results = set(), [start], []
    host = urlparse(start).netloc
    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        html = get(url)
        if not html:
            continue
        for hit in scan(html):
            if hit not in results:
                results.append(hit)
        if results and any(r[0] in ("workday", "greenhouse", "lever", "smartrecruiters") for r in results):
            break
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            text = f"{a.get_text(' ', strip=True)} {href}"
            if LINK_HINTS.search(text) and href.startswith("http") and href not in visited:
                # Stay on the company's site, but follow links out to known job hosts.
                if urlparse(href).netloc.endswith(host.replace("www.", "")) or any(p.search(href) for _, p in PATTERNS):
                    queue.append(href)
    return results


def snippet(name: str, hit: tuple[str, tuple]) -> str:
    ats, g = hit
    if ats == "workday":
        return f"  - name: {name}\n    sector: ?\n    ats: workday\n    tenant: {g[0]}\n    dc: {g[1]}\n    site: {g[2]}"
    if ats in ("greenhouse", "lever"):
        eu = "\n    eu: true" if g[0] else ""
        return f"  - name: {name}\n    sector: ?\n    ats: {ats}\n    token: {g[1]}{eu}"
    if ats == "smartrecruiters":
        return f"  - name: {name}\n    sector: ?\n    ats: smartrecruiters\n    token: {g[0]}"
    return f"  # {name} uses {ats}, which Gridline can't read yet. Keep it as ats: manual."


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    name, url = argv
    hits = discover(url)
    if not hits:
        print(f"No known hiring platform found for {name} starting from {url}.")
        print("Try the company's careers or graduate page URL directly, or keep it as ats: manual.")
        return 1
    print(f"Found for {name}:\n")
    for hit in hits[:5]:
        print(snippet(name, hit) + "\n")
    print("Replace ? with trader, major or utility, then paste into config/companies.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
