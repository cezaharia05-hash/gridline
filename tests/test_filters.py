from pathlib import Path

import yaml

from scraper.filters import evaluate

CFG = yaml.safe_load((Path(__file__).parent.parent / "config" / "filters.yaml").read_text())


def keep(title, loc=""):
    return evaluate(title, loc, CFG)


def test_generic_uk_programme_kept_as_general():
    v = keep("Shell Graduate Programme 2026 - United Kingdom", "London")
    assert v.keep and v.function == "general" and v.regions == ("UK",)


def test_trading_programme_in_title_location():
    v = keep("Geneva Commercial Graduate Programme", "")
    assert v.keep and v.function == "commercial" and v.regions == ("CH",)


def test_non_europe_dropped():
    assert not keep("Houston Commercial Graduate Programme", "Houston, Texas").keep
    assert not keep("Shell Graduate Program 2027 - United States", "Texas, United States of America").keep


def test_technical_dropped_unless_commercial():
    assert not keep("Graduate Program 2027 - Mechanical Engineer", "London").keep
    assert keep("Graduate Trading Engineer", "London").keep  # commercial wins


def test_internships_and_senior_dropped():
    assert not keep("Graduate Summer Internship - Trading", "London").keep
    assert not keep("Senior Trader", "London").keep


def test_multilingual_and_accents():
    v = keep("Traineeprogramm Finanzen (m/w/d)", "Essen, Deutschland")
    assert v.keep and v.function == "finance" and v.regions == ("EEA",)
    assert keep("Programme Jeunes Diplômés – Trading", "Paris La Défense").keep


def test_unknown_location_kept_for_review():
    v = keep("Graduate Commodity Trading Analyst", "3 Locations")
    assert v.keep and v.regions == ("UNKNOWN",)


def test_multi_region():
    v = keep("Graduate Commodity Trading Analyst", "Greater London; Aalborg")
    assert v.keep and set(v.regions) == {"UK", "EEA"}


def test_word_boundaries():
    assert not keep("Undergraduate Ambassador", "London").keep  # 'graduate' inside a word
    assert not keep("IT Graduate Scheme", "London").keep
