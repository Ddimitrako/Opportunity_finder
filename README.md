# Opportunity Finder

Full-stack platform for discovering Greek and EU public procurement opportunities that fit a solo or small full-stack software team.

## Stack

- Backend: FastAPI
- Frontend: React 19 + Vite + TypeScript
- Sources: ΚΗΜΔΗΣ OpenData API, TED Search API, local demo patterns
- AI: optional OpenAI enrichment when `OPENAI_API_KEY` is available

## Run Locally

With Docker Compose:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. The API is exposed at `http://localhost:8000`.

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
