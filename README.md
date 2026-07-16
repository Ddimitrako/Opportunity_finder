# Opportunity Finder

Full-stack platform for discovering Greek and EU public procurement opportunities that fit a solo or small full-stack software team.

It also includes a Buyer-Need & Software Market Radar that persists buyer signals, procurement lifecycle evidence, suppliers/integrators, software-brand mentions, market trends and lightweight follow-up tracking.

## Stack

- Backend: FastAPI
- Frontend: React 19 + Vite + TypeScript
- Sources: ΚΗΜΔΗΣ OpenData API, TED Search API, local demo patterns
- Market sources: ΚΗΜΔΗΣ lifecycle, TED planning/competition/results, Διαύγεια for tracked buyers, optional Open Data ΓΕΜΗ and official company careers/news URLs
- AI: optional OpenAI enrichment when `OPENAI_API_KEY` is available

## Run Locally

With Docker Compose:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. The API is exposed at `http://localhost:8000`.

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
```

When the key exists, the API reports `ai_enabled: true` and AI enrichment can be enabled from the UI.

The opportunity drawer includes an AI Bid Decision Brief v2. It combines deterministic lifecycle/direct-award checks with a strict structured AI scorecard, page-level evidence citations, a 12-month buyer-history context, and `GO` / `CONDITIONAL GO` / `NO-GO` / `INSUFFICIENT DATA` decisions. Existing v1 briefs remain visible and can be regenerated on demand.

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
