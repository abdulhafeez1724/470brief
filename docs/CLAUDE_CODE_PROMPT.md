# Prompt for Claude Code: 470 Brief, Phase 1

Fill in the 5 values in "My details", put `index.html` (the landing page) in the repo root, then paste everything below the line into Claude Code.

---

Build Phase 1 of "470 Brief" in this repo, end to end, in one go. Read this whole brief before writing code, write a short plan, then implement it without stopping to ask unless something below is contradictory.

## My details

- GitHub username: `FILL_ME`
- Repo name: `470brief`
- Google Form link (free sample request): `FILL_ME`
- Contact email shown on the site: `FILL_ME`
- Name shown in the footer: `FILL_ME`

## What the product is

470 Brief helps small US IT vendors (E-Rate service providers) find and bid on school network requests. Schools post requests as FCC Form 470s in USAC's public open data. Phase 1 is a free, automated data pipeline plus public state pages. No LLM, no paid services, no backend server yet.

## Phase 1 scope

1. Nightly sync of Form 470 requests from USAC open data for the current bidding season.
2. Dedupe and normalize them into domain entities.
3. Generate a static public page per state listing open requests, plus a states index page.
4. Local-only CSV exports with contact details, for my outreach.
5. Local-only vendor list export from USAC's service provider dataset.
6. A GitHub Actions workflow that runs the sync nightly, commits the public snapshot, and deploys `site/` to GitHub Pages.

Out of scope: RFP PDF summarization, LLM calls, FastAPI, database server, auth, payments, email sending. Define the ports for brief generation (below) but do not implement them.

## Stack and code rules

- Python 3.12, `pyproject.toml` (hatchling), package `brief470` under `src/`.
- Clean Architecture: `domain` → `application` → `infrastructure` → `presentation`.
- Domain layer is pure Python: dataclasses and enums only, zero framework imports.
- Ports in the domain are `typing.Protocol`s. Infrastructure implements them; use cases receive them through constructors.
- Async by default (`httpx.AsyncClient`).
- Pydantic v2 only in infrastructure (API DTOs) and for settings (`pydantic-settings`): `model_config`, `field_validator`, never `@validator`.
- Type hints on everything. `logging`, never `print`.
- CLI with Typer. Templates with Jinja2. Tests with pytest, pytest-asyncio and respx (no real network in tests).
- Ruff for lint and format. Keep dependencies minimal.

## Data source 1: Form 470 requests

- Endpoint: `https://opendata.usac.org/resource/jt8s-3q52.json` (Socrata SoQL: `$select`, `$where`, `$order`, `$limit`, `$offset`).
- Page with `$limit=5000` and `$offset` until a page returns fewer rows. Send a descriptive `User-Agent`. Support an optional free Socrata app token from env `SOCRATA_APP_TOKEN` via header `X-App-Token`; work without it.
- Filter: `funding_year='<FUNDING_YEAR>'` and `fcc_form_470_status='Certified'`. `FUNDING_YEAR` is a setting, default `2027`. Optional state filter on `billed_entity_state`.
- Fields to use: `application_number`, `service_request_id`, `form_version`, `funding_year`, `fcc_form_470_status`, `allowable_contract_date`, `certified_date_time`, `last_modified_date_time`, `billed_entity_number`, `billed_entity_name`, `applicant_type`, `billed_entity_city`, `billed_entity_state`, `website_url`, `contact_name`, `contact_email`, `contact_phone`, `technical_contact_name`, `technical_contact_email`, `consulting_firm_data`, `service_category`, `service_type`, `function`, `quantity`, `unit`, `manufacturer`, `category_two_description`, `form_pdf` (object with `url`), `rfp_documents` (object with `url`), `rfp_upload_date`.
- Any field can be missing. Dates come as ISO strings like `2026-12-04T00:00:00.000`.

Important data quirk: the dataset has one row per RFP attachment, so the same service request repeats. Dedupe by `(application_number, service_request_id)` and collect all `rfp_documents.url` values for that request into a unique, ordered list. A Form 470 (application) has many service requests.

Domain model (suggested):

- `Form470` (application): number, entity name, applicant type, city, state, website, contacts, consultant flag, form PDF url, RFP doc urls, certified at, allowable contract date, service requests.
- `ServiceRequest`: id, category (enum: C1, C2), service type, function, quantity, unit, manufacturer, description.
- `is_open(today)`: allowable contract date is today or later. Note in code comments that this is the earliest date the applicant may sign; the real bid deadline is inside each RFP.
- `has_equipment`: any Category 2 service request.

## Data source 2: service providers (vendors, local only)

- Endpoint: `https://opendata.usac.org/resource/xcy2-bdid.json`.
- Fields: `spin`, `service_provider_name`, `status`, `general_contact_name`, `general_contact_email`, `phone_number`, `physical_city`, `physical_state`, `fcc_form_499_filer`, `fcc_form_473_spac_filed` (comma-separated years, e.g. `2024,2025,2026`).
- Vendor filter: `status='Active'`, given state, `fcc_form_499_filer='No'`, and the current calendar year present in `fcc_form_473_spac_filed`.
- Add a `needs_review` flag for names that look like non-vendors (contain: County, City of, Town of, School, District, University, Board of, Regents, Consortium, Utilities, Electric Association). Also flag generic emails (`usac@`, `erate@`, `sales@`, `info@`, `compliance@`) and free-mail domains (gmail, yahoo, juno).

## Storage

- Repository port in the domain; JSON-file implementation in infrastructure.
- Public snapshot committed to git: `data/public/form470_<FUNDING_YEAR>.json`. It must NOT contain any person's name, email or phone. Keep entity, city, state, type, dates, service requests, and document URLs.
- Contact data stays local: `data/private/` is in `.gitignore`. The sync writes the full records there when run locally.
- Keep `data/public/last_sync.json` with timestamp and counts, and compute "new since last sync" by application number.

## Use cases (application layer)

- `SyncForm470(source, repo, clock)`: fetch, dedupe, save public and private snapshots, return counts (total, open, open equipment, new).
- `ListOpenRequests(repo, clock)`: by state, optional category filter, sorted by allowable contract date then name.
- `BuildStatePages(repo, renderer, clock)`: write `site/states/<xx>.html` for every state with requests, and `site/states/index.html` with counts per state.
- `ExportOutreachCsv(repo, clock)`: `data/private/exports/<STATE>_open_<YYYY-MM-DD>.csv` with entity, city, category, service types, allowable contract date, contact name and email, technical contact name and email, consultant flag, Form 470 number, form PDF URL, RFP URLs.
- `ExportVendors(source)`: `data/private/vendors/<STATE>.csv` with the vendor fields above plus `needs_review` and reason.

Brief generation ports (define only, do not implement): `PdfTextReader` and `BriefSummarizer` Protocols, and a `Brief` dataclass with: scope summary, line items (item, model, quantity), bid deadline text, submission method, contact, contract term, scoring criteria (name, points), required attachments, disqualifiers, source URLs.

## CLI

`brief470 sync [--state AZ] [--year 2027]`, `brief470 build-pages`, `brief470 export --state AZ`, `brief470 vendors --state AZ`, and `brief470 all` (sync + build-pages). Log a one-line summary per command.

## Site

- Move the existing `index.html` from the repo root to `site/index.html`. Replace `REPLACE_WITH_GOOGLE_FORM_LINK`, `REPLACE_WITH_YOUR_EMAIL` and `[YOUR NAME]` with my details. Keep its design.
- Add a "Browse open requests by state" link on the landing page pointing to `states/index.html`.
- State pages reuse the landing page's look (same fonts, colors, header and footer). Extract shared CSS into `site/assets/style.css` only if it does not break the landing page.
- State page content: H1 "<State name>: open E-Rate requests, funding year 2027", "updated <date>", counts (filed, open, open equipment), then a table of open requests: entity, city, request type (service types), "can sign a contract from" date, link to the Form 470 PDF. Equipment requests first. A CTA to the Google Form ("Get a one-page brief for any of these"). Footer note: data is from public USAC records; 470 Brief is independent and not affiliated with USAC or the FCC.
- No personal names, emails or phone numbers on any public page.
- Each page needs a proper `<title>` and meta description for search.
- Accessible: real tables with `<th scope>`, visible focus, readable at 390px width (table scrolls horizontally).

## GitHub Actions

`.github/workflows/nightly.yml`:

- Triggers: cron daily at `17 9 * * *` (UTC) and `workflow_dispatch`.
- Steps: checkout, set up Python 3.12, install the package, run tests, run `brief470 all`, commit `data/public/` and `site/` changes as `github-actions[bot]` only if something changed, then deploy `site/` with `actions/upload-pages-artifact` and `actions/deploy-pages`.
- Permissions: `contents: write`, `pages: write`, `id-token: write`. Use a `concurrency` group so two runs never overlap.
- `SOCRATA_APP_TOKEN` read from repo secrets if present.

## Tests (minimum)

- Dedupe: 4 raw rows for 2 service requests with different RFP URLs become 2 service requests with merged URLs.
- Missing fields do not crash parsing.
- `is_open` boundary: a request whose allowable contract date is today counts as open.
- Public snapshot contains no `contact_*`, `technical_contact_*` or email-like strings.
- Vendor filter and `needs_review` flags.
- Pagination stops correctly (respx mock).
- State page renders and contains no `@`.

## Repo hygiene

- `README.md` in English: what it is, setup, CLI commands, how the nightly job works, data source and disclaimer.
- `.gitignore` covers `data/private/`, virtualenvs, caches.
- No secrets in code.

## Definition of done

1. `ruff check` and `pytest` pass.
2. Run a real `brief470 sync --state AZ` and `brief470 build-pages` once, and show me the counts (total, open, open equipment) and the generated file list. For reference, on 2026-11-11 Arizona had 132 certified FY2027 applications, 85 open and 30 open with equipment; small differences are expected because the data updates daily.
3. Run `brief470 vendors --state AZ` and show how many vendors and how many are flagged.
4. Tell me exactly which GitHub settings I must change (Pages source = GitHub Actions; Actions workflow permissions) and the commands to commit and push.
5. Summarize what you built and anything you could not do.
