# Gridline

A daily scraper and dashboard for graduate finance, commercial and business roles at energy companies in the UK and Europe.

Every morning a GitHub Action checks each company's careers site, keeps the early-career roles that match your filters, and commits the results to `docs/data/jobs.json`. GitHub Pages serves the dashboard in `docs/`, which reads that file.

Your application tracker (status, deadline, notes) is saved in your browser only, never in the repo. Use **Export tracker** now and then to keep a backup or move it to another device.

## Set up (about 10 minutes)

1. **Create a public repository** on GitHub, for example `gridline`. GitHub Pages is free on public repos. The job data is public anyway; your tracker is not stored there.
2. **Upload the files.** The `.github` folder is hidden on macOS and Windows by default, and the web uploader skips it if you can't see it. The easiest route is [GitHub Desktop](https://desktop.github.com): clone the empty repo, copy everything from this folder into it (press Cmd+Shift+. on a Mac to show hidden files), commit, and push.
3. **Turn on Pages.** Settings → Pages → Build and deployment → Deploy from a branch → `main` and `/docs` → Save. Your dashboard will be at `https://<your-username>.github.io/gridline/`.
4. **Run the first scrape.** Actions tab → if asked, enable workflows → Scrape roles → Run workflow. It takes a few minutes. Then reload the dashboard.
5. If the commit step fails with a permission error: Settings → Actions → General → Workflow permissions → Read and write permissions.

After that it runs daily at 05:15 UTC.

## Add companies

Six employers are wired up and verified (Shell, bp, Equinor, Centrica, Trafigura, Gunvor). The rest of the watchlist in `config/companies.yaml` is `ats: manual`, which shows them on the dashboard as links to check yourself.

To convert one:

1. Actions → **Discover ATS** → Run workflow, with the company name and its careers or graduate page URL.
2. Open the finished run. The summary shows a snippet like:
   ```yaml
   - name: RWE
     sector: ?
     ats: workday
     tenant: rwe
     dc: wd3
     site: RWE_Careers
   ```
3. Set `sector` to `trader`, `major` or `utility`, replace the company's manual line in `config/companies.yaml`, and commit.

Gridline can read **Workday**, **Greenhouse**, **Lever** and **SmartRecruiters**. Companies on SAP SuccessFactors, Taleo, Oracle, or a custom site stay manual. You can also find Workday details yourself: open any job on the company's site and read them off the address, `https://<tenant>.<dc>.myworkdayjobs.com/en-US/<site>/job/...`.

## Tune the filters

Everything is in `config/filters.yaml`:

- `early_career` decides what counts as a graduate role (it already includes German, French, Italian and Spanish terms) and what to drop, such as internships and senior roles.
- `functions` sorts roles into commercial, finance and business. Titles with engineering or IT terms are dropped unless they also mention trading, commercial or finance. Generic titles like "Graduate Programme 2027 – UK" are kept as general programmes, because they often cover every stream.
- `regions` maps cities and countries to UK, EEA and Switzerland. Roles only outside Europe are dropped. Roles whose location is unclear (Workday often says "3 Locations") are kept and labelled.
- `work_rights` lists where you don't need sponsorship. Roles elsewhere get a sponsorship badge.

The tests in `tests/` run before every scrape. If you change a filter and a test fails, the scrape stops, so nothing half-broken gets published. Run them locally with `pip install -r requirements.txt && python -m pytest`.

## Run locally

```bash
pip install -r requirements.txt
python -m scraper.run --only Shell --verbose --dry-run   # see every title and why it was kept or dropped
python -m scraper.run                                    # full run, writes docs/data/jobs.json
cd docs && python -m http.server                         # dashboard at http://localhost:8000
```

## How it behaves

- **New roles** get an amber dot until your next visit. **New this week** filters by the date Gridline first saw the role, which is usually a day or two after the company posted it.
- **Closed roles** are ones that disappeared from the careers site. Tick **Show closed** to see them; they're removed from the file 45 days later.
- **Failed scrapers** show as a red dashed pill, with the error listed at the bottom of the page. Their roles stay as they were, so a broken site doesn't make everything look closed. A single failure is usually temporary. If it keeps failing, the company has probably changed its careers site: run Discover ATS again.
- **Deadlines** aren't reliably published in a form a scraper can read, so the deadline field is yours to fill in.

Scraping is polite by design: one run a day, a pause between requests, and only the public job-search endpoints each careers site already uses.
