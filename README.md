# 470 Brief

470 Brief helps small US IT vendors (E-Rate service providers) find and bid on school network requests. Schools and libraries post those requests as FCC Form 470s, which USAC publishes as open data.

Phase 1 is a free, automated pipeline:

- A nightly sync of certified Form 470s for the current funding year from USAC open data.
- Public static pages, one per state, listing the requests that are still open, plus a states index.
- Local-only CSV exports with contact details, for outreach.
- A local-only list of active E-Rate vendors per state, with review flags.

There is no LLM, no paid service and no backend server. The site is plain HTML on GitHub Pages.

## Setup

Requires Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional settings (environment variables or a `.env` file):

| Variable | Default | Purpose |
| --- | --- | --- |
| `FUNDING_YEAR` | `2027` | E-Rate funding year to sync |
| `SOCRATA_APP_TOKEN` | none | Free Socrata app token; raises rate limits. Works without it. |
| `WRITE_PRIVATE` | `true` | Write the contact snapshot to `data/private/`. CI sets it to `false`. |
| `GOOGLE_FORM_URL` | `REPLACE_WITH_GOOGLE_FORM_LINK` | Link used by the "Get a brief" buttons on state pages |
| `SITE_BASE_URL` | `https://abdulhafeez1724.github.io/470brief/` | Used for canonical links |

## CLI

```bash
brief470 sync [--state AZ] [--year 2027]   # fetch, dedupe, save snapshots
brief470 build-pages [--year 2027]          # write site/states/*.html
brief470 export --state AZ                   # data/private/exports/AZ_open_<date>.csv
brief470 vendors --state AZ                  # data/private/vendors/AZ.csv
brief470 all [--state AZ]                    # sync + build-pages
```

Add `-v` before the command for debug logs, e.g. `brief470 -v sync --state AZ`.

A state-scoped sync replaces only that state's records in the snapshots and keeps the rest.

## Where data goes

| Path | In git | Contents |
| --- | --- | --- |
| `data/public/form470_<year>.json` | yes | Entity, city, state, applicant type, dates, service requests and document URLs. No names, emails or phone numbers; emails and phone numbers in free-text descriptions are redacted. |
| `data/public/last_sync.json` | yes | Time of the last sync and its counts (total, open, open equipment, new since last sync). |
| `data/private/form470_<year>.json` | no | Full records including contacts. Only written on your machine. |
| `data/private/exports/`, `data/private/vendors/` | no | Outreach and vendor CSVs. |
| `site/` | yes | Landing page, shared CSS and generated state pages. |

"Open" means the allowable contract date is today or later. That is the earliest date the school may sign a contract. The real bid deadline is set inside each RFP and is often earlier.

## Architecture

```
src/brief470/
  domain/          entities, rules, ports (typing.Protocol). Pure Python.
  application/     use cases: SyncForm470, ListOpenRequests, BuildStatePages,
                   ExportOutreachCsv, ExportVendors
  infrastructure/  Socrata client and DTOs (pydantic), JSON repository, CSV writer,
                   settings, clock
  presentation/    Typer CLI (composition root), Jinja2 renderer and templates
```

`domain/brief.py` defines the Phase 2 ports `PdfTextReader` and `BriefSummarizer` and the `Brief` model. They are not implemented yet.

## Nightly job

`.github/workflows/nightly.yml` runs at 09:17 UTC every day and on manual dispatch. It installs the package, runs ruff and the tests, runs `brief470 all` for every state with `WRITE_PRIVATE=false`, commits any changes under `data/public/` and `site/` as `github-actions[bot]`, and deploys `site/` to GitHub Pages. A concurrency group keeps two runs from overlapping. Add a `SOCRATA_APP_TOKEN` repository secret if you have one.

## Development

```bash
ruff check . && ruff format --check .
pytest
```

Tests use respx and never touch the network.

## Data source and disclaimer

Data comes from USAC's public open data portal: FCC Form 470 tool ([jt8s-3q52](https://opendata.usac.org/resource/jt8s-3q52)) and the E-Rate service provider list ([xcy2-bdid](https://opendata.usac.org/resource/xcy2-bdid)). 470 Brief is independent and is not affiliated with USAC or the FCC. Always confirm details against the Form 470, the RFP and the USAC portal before bidding.
