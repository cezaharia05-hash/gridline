from datetime import date

from scraper.adapters import greenhouse, lever, smartrecruiters, workday
from scraper.store import merge


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, pages):
        self.pages, self.calls = list(pages), []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return FakeResponse(self.pages.pop(0))


def test_workday_paginates_and_builds_urls(monkeypatch):
    monkeypatch.setattr(workday, "PAUSE", 0)
    page1 = {"total": 21, "jobPostings": [
        {"title": f"Graduate {i}", "externalPath": f"/job/London/G{i}_R{i}", "locationsText": "London", "postedOn": "Posted Today", "bulletFields": [f"R{i}"]}
        for i in range(20)]}
    page2 = {"total": 0, "jobPostings": [{"title": "Graduate 20", "externalPath": "/job/x/G20_R20", "locationsText": "Oslo"}]}
    s = FakeSession([page1, page2])
    out = workday.fetch({"tenant": "shell", "dc": "wd3", "site": "ShellCareers", "search_terms": ["graduate"]}, {}, s)
    assert len(out) == 21
    assert out[0].url == "https://shell.wd3.myworkdayjobs.com/en-US/ShellCareers/job/London/G0_R0"
    assert s.calls[0][1] == "https://shell.wd3.myworkdayjobs.com/wday/cxs/shell/ShellCareers/jobs"
    assert s.calls[1][2]["json"]["offset"] == 20


def test_greenhouse_lever_smartrecruiters_parse():
    gh = greenhouse.fetch({"token": "acme"}, {}, FakeSession([{"jobs": [
        {"id": 1, "title": "Graduate Analyst", "absolute_url": "https://x/1", "location": {"name": "London"}, "updated_at": "2026-09-01T00:00:00Z"}]}]))
    assert gh[0].location == "London" and gh[0].posted == "2026-09-01"

    lv = lever.fetch({"token": "acme"}, {}, FakeSession([[
        {"id": "a", "text": "Graduate Trader", "hostedUrl": "https://x/a", "categories": {"location": "Geneva"}, "createdAt": 1788000000000}]]))
    assert lv[0].location == "Geneva" and lv[0].posted.startswith("2026")

    sr = smartrecruiters.fetch({"token": "acme"}, {}, FakeSession([{"totalFound": 1, "content": [
        {"id": "9", "name": "Trainee Finance", "location": {"city": "Madrid", "country": "es"}, "releasedDate": "2026-09-10T00:00:00Z"}]}]))
    assert sr[0].location == "Madrid, Spain" and sr[0].url.endswith("/acme/9")


def job(jid, company="Shell"):
    return {"id": jid, "company": company, "title": jid, "url": jid}


def test_merge_tracks_first_seen_closed_and_failed_scrapes():
    d1 = merge({}, [job("a"), job("b", "Equinor")], [{"name": "Shell", "state": "ok"}, {"name": "Equinor", "state": "ok"}], date(2026, 9, 1))
    assert all(j["active"] and j["first_seen"] == "2026-09-01" for j in d1["jobs"])

    # Day 2: Shell drops 'a', adds 'c'. Equinor scrape fails, so 'b' must stay active.
    d2 = merge(d1, [job("c")], [{"name": "Shell", "state": "ok"}, {"name": "Equinor", "state": "error"}], date(2026, 9, 2))
    by = {j["id"]: j for j in d2["jobs"]}
    assert by["a"]["active"] is False and by["a"]["last_seen"] == "2026-09-01"
    assert by["b"]["active"] is True
    assert by["c"]["first_seen"] == "2026-09-02"

    # Long after: closed role pruned.
    d3 = merge(d2, [job("c")], [{"name": "Shell", "state": "ok"}, {"name": "Equinor", "state": "ok"}], date(2026, 12, 1), keep_closed_days=45)
    assert "a" not in {j["id"] for j in d3["jobs"]}
