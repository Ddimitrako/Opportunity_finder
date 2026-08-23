# Opportunity Finder

Full-stack platform for discovering Greek and EU public procurement opportunities that fit a solo or small full-stack software team.

It also includes a Buyer-Need & Software Market Radar that persists buyer signals, procurement lifecycle evidence, suppliers/integrators, software-brand mentions, market trends and lightweight follow-up tracking.

## Current production access

- URL: `https://srv1136832.hstgr.cloud`
- Username: `admin`
- Password: intentionally not stored in Git; keep it in the project owner's password manager. The VPS stores only its PBKDF2 hash in `/home/Opportunity_finder/.env` with permissions `600`.
- Nginx Proxy Manager upstream: `http://opportunity-finder-frontend:80` on the shared `voyag_network`.

To rotate the password, generate a new PBKDF2 hash with `app.auth.hash_password`, replace `AUTH_PASSWORD_HASH` in the protected VPS `.env`, and recreate the backend container. Never commit the password, its hash, or `AUTH_SECRET_KEY`.

## Stack

- Backend: FastAPI
- Frontend: React 19 + Vite + TypeScript
- Sources: ΚΗΜΔΗΣ OpenData API, TED Search API, local demo patterns
- Market sources: ΚΗΜΔΗΣ lifecycle, TED planning/competition/results, Διαύγεια for tracked buyers, optional Open Data ΓΕΜΗ and official company careers/news URLs
- AI: optional OpenAI enrichment when `OPENAI_API_KEY` is available

## Run Locally

With Docker Compose:

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python -c "from getpass import getpass; from app.auth import hash_password; print(hash_password(getpass('Login password: ')))"
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build
```

Put the generated password hash and secret in `.env` as `AUTH_PASSWORD_HASH` and `AUTH_SECRET_KEY`; single-quote the password hash so its `$` separators remain literal. Set `AUTH_USERNAME` as needed. Open `http://localhost:5173`. The frontend proxies `/api` internally, while the backend debug port is bound only to `127.0.0.1:8000`.

For an HTTPS deployment behind Nginx Proxy Manager, proxy the public hostname to the frontend on port `5173`, enable Force SSL, HTTP/2 and HSTS, then set `FRONTEND_ORIGIN=https://your-hostname` and `AUTH_COOKIE_SECURE=true`. Do not publish or proxy backend port `8000` directly.

Docker Compose also starts `market-worker`, which refreshes the radar daily at 07:00 Europe/Athens. A source failure is isolated and recorded in the refresh status.

Stop the stack:

```powershell
docker compose down
```

Without Docker:

Backend:

```powershell
.\\.venv\\Scripts\\python -m pip install -r backend\\requirements.txt
.\\.venv\\Scripts\\python -m uvicorn app.main:app --reload --app-dir backend --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`.

## Optional AI

The app works without an OpenAI key. Later, create `backend/.env.local` or `.env.local` and add:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
SOFTWARE_SCREENING_MODEL=gpt-4o-mini
SOFTWARE_SCREENING_DEEP_MODEL=gpt-4.1-mini
```

When the key exists, the API reports `ai_enabled: true` and AI enrichment can be enabled from the UI.

The opportunity drawer includes an AI Bid Decision Brief v2. It combines deterministic lifecycle/direct-award checks with a strict structured AI scorecard, page-level evidence citations, a 12-month buyer-history context, and `GO` / `CONDITIONAL GO` / `NO-GO` / `INSUFFICIENT DATA` decisions. Existing v1 briefs remain visible and can be regenerated on demand.

## Open-source product matchmaking

Search results are matched automatically against a local catalog of 63 open-source products. Runtime matching is deterministic and free of AI calls; the drawer can optionally rerank the eight strongest candidates with AI after an explicit click. The AI cannot introduce products outside that allow-list, and its result is cached in SQLite by opportunity, model, evidence IDs, and catalog version.

The `Software Match AI` page adds an explicit, persisted bulk-screening workflow for the current search results. It reuses strong deterministic matches, screens remaining titles in groups of up to 40, sends only ambiguous cases to a summary pass, and opens relevant document excerpts for at most five unresolved opportunities. The semantic model returns bounded category IDs and service types—not product slugs—so final product selection and hard exclusions remain deterministic. Saved results are reapplied automatically when the same opportunity is returned by a later search.

The editable source of truth is `backend/catalog/software_catalog.xlsx`. Runtime code reads only the generated `backend/app/data/software_catalog.json`; there is no runtime dependency or synchronization with the original `opensource-for-business` repository.

After editing the workbook, validate and regenerate the snapshot:

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python -m app.catalog_import
.\.venv\Scripts\python -m app.catalog_import --check
```

The workbook contains `Products`, `Departments`, `Categories`, `Licenses`, `Repository Health`, and `Data Dictionary` sheets. Multi-value cells use the visible delimiter ` | `.

## Market Radar configuration

The radar works immediately with procurement results loaded by the app. For private-company discovery through the official Open Data ΓΕΜΗ API, request a key and add:

```env
GEMI_API_KEY=your_gemi_api_key
MARKET_REFRESH_HOUR=7
```

Manual refresh:

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python -m app.worker --once --backfill-days 14
```

Use `--backfill-days 730` for the initial two-year procurement backfill. Company watch sources accept only public HTTPS careers/newsroom URLs and enforce DNS, response-size and content-type checks.
