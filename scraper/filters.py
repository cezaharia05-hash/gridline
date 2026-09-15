"""Decide whether a posting is an early-career finance/commercial/business role
in the UK or Europe, and tag it."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

EUROPE = ("UK", "CH", "EEA")

# Workday sites often write locations as "IN: Patna" or "GB - London".
EEA_CODES = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
             "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "NO", "IS", "LI"}
CODE_PREFIX = re.compile(r"^\s*([A-Z]{2})\s*[:\-]\s")


def region_from_code(location: str) -> str | None:
    m = CODE_PREFIX.match(location or "")
    if not m:
        return None
    code = m.group(1)
    if code in ("GB", "UK"):
        return "UK"
    if code == "CH":
        return "CH"
    return "EEA" if code in EEA_CODES else "OTHER"


def normalise(text: str | None) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=None)
def _pattern(terms: tuple[str, ...]) -> re.Pattern:
    parts = sorted((re.escape(normalise(t)) for t in terms if t), key=len, reverse=True)
    # Word boundaries that also work for terms ending in punctuation ("v.i.e", "fp&a").
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


def matches(text: str, terms) -> bool:
    if not terms:
        return False
    return bool(_pattern(tuple(terms)).search(normalise(text)))


@dataclass
class Verdict:
    keep: bool
    reason: str = ""
    function: str = ""
    regions: tuple[str, ...] = ()


def classify_function(title: str, cfg: dict) -> str | None:
    """Return finance | commercial | business | general, or None to drop."""
    fn = cfg["functions"]
    hits = [name for name in ("commercial", "finance") if matches(title, fn.get(name))]
    if hits:
        return hits[0]
    if matches(title, cfg.get("technical_exclude")):
        return None
    if matches(title, fn.get("business")):
        return "business"
    return "general"


def classify_regions(location: str, title: str, cfg: dict) -> tuple[str, ...] | None:
    """Return the European regions a role is in, ("UNKNOWN",) if unclear,
    or None if it is only outside Europe."""
    coded = region_from_code(location)
    if coded == "OTHER":
        return None
    text = f"{location} {title}"
    regions_cfg = cfg["regions"]
    found = tuple(r for r in EUROPE if matches(text, regions_cfg.get(r)))
    if coded and coded not in found:
        found = found + (coded,)
    if found:
        return found
    if matches(text, regions_cfg.get("OTHER")):
        return None
    return ("UNKNOWN",)


def evaluate(title: str, location: str, cfg: dict) -> Verdict:
    ec = cfg["early_career"]
    if not matches(title, ec["include"]):
        return Verdict(False, "not early career")
    if matches(title, ec.get("exclude")):
        return Verdict(False, "excluded term")
    function = classify_function(title, cfg)
    if function is None:
        return Verdict(False, "technical role")
    regions = classify_regions(location, title, cfg)
    if regions is None:
        return Verdict(False, "outside Europe")
    return Verdict(True, "", function, regions)
