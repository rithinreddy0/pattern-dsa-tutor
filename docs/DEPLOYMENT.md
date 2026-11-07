# Deployment guide

Target architecture: Vercel (React static frontend), Render (FastAPI service), Neon (persistent PostgreSQL with pgvector), Google Gemini (generation + embeddings).

## 1. Accounts and source

Push the project to your GitHub repository. The setup created [rithinreddy0/pattern-dsa-tutor](https://github.com/rithinreddy0/pattern-dsa-tutor). The owner explicitly approved publishing this new repository so Render can fetch it. Secret keys, local environment files, databases, and logs are excluded from the repository.

Use connected Neon and Vercel integrations when available. Otherwise use their dashboards. Account sign-in, terms, and billing steps may require the account owner. Keep credentials in platform secret storage, not chat or Git.

## 2. Neon

1. Create a new project and database named `pattern` in a region near the Render service (configured for Singapore).
2. Use the Neon SQL Editor to run `CREATE EXTENSION IF NOT EXISTS vector;`, or let the application do it with an appropriately authorized database role.
3. Put the TLS PostgreSQL connection URL into Render's secret `DATABASE_URL`. The application accepts `postgres://`, `postgresql://`, or `postgresql+psycopg://` URLs and uses Psycopg.
4. A pooled URL can be used by the application. Use Neon's direct URL if an administrative/indexing operation requires it.

## 3. Vercel project

Create a Vercel project for this repository with root directory **frontend** and framework **Vite**. Its build command is `npm run build`, output `dist`, and install command `npm ci`. Record the project's canonical production HTTPS URL for the backend CORS setting. Set `VITE_API_URL` to the verified Render HTTPS URL once the backend exists, then redeploy the frontend. Build-time variables require a new build.

The frontend intentionally reports connection errors if its backend is unavailable. It does not fabricate a working AI session.

## 4. Render backend

Use the supplied `render.yaml`, or create one Python web service with:

```text
Build: pip install -r backend/requirements.lock
Start: cd backend && python -m app.index && uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health check: /api/health
Region: Singapore
Plan: Free (subject to account availability; it sleeps when idle)
```

Set these environment variables through Render's secret settings:

- `DATABASE_URL`: Neon PostgreSQL URL with TLS.
- `GEMINI_API_KEY`: Google API key. Never prefix this with `VITE_`.
- `JWT_SECRET`: generated random string, at least 32 characters. The Blueprint generates one automatically.
- `CORS_ORIGINS`: the exact Vercel production HTTPS origin. Multiple approved origins can be comma-separated; no wildcard is allowed in production.
- `ENVIRONMENT=production`.
- `GEMINI_MODEL=gemini-2.5-flash` (configurable; check your account's model availability).
- `EMBEDDING_MODEL=gemini-embedding-001`.
- `PYTHON_VERSION=3.11.11`.

For an initial large index, run `python -m app.index` from a trusted local environment against Neon **before** deploying. The start command is resumable and subsequently skips current indexed passages. Quota limits can make the first embedding pass take several minutes; doing it before deployment keeps readiness quick. Do not run multiple initial indexers at once.

When the Render CLI is available, validate the Blueprint with `render blueprints validate render.yaml`. A local YAML parse is not a substitute for provider validation. A direct API deployment does not depend on the Blueprint having been applied.

## 5. Verify the actual launch

Wait for the specific Render deploy to reach `live`, then check:

1. `/api/health`: HTTP 200, `database=postgresql`, `ai=gemini`, `retrieval=pgvector`, and `indexed_chunks > 0`.
2. `/api/topics`: 16 populated topics and 53 taxonomy subtopics.
3. `/api/search?q=find%20a%20pair%20with%20a%20target%20sum`: reports `pgvector`.
4. A Hint request for Two Sum has citations and no implementation code.
5. Register a user, save a bookmark, mark a problem solved, and reload. The data should persist in Neon.
6. Create a tutor conversation and revisit it after signing in again. Another user must not access it.
7. Verify the deployed frontend uses the production backend, with no browser CORS errors or secret values in the JavaScript assets.

Record the verified Vercel URL, Render service URL, Neon project ID (not its connection secret), source commit, and deployment IDs. Do not call a queued build or an accepted API request a live deployment.

## Secret handling

The local Gemini key can live in Windows Credential Manager. Local `.env` files, database files, logs, and dependency directories are ignored. Production credentials belong in Render's environment secrets. Vercel only needs the public API URL. Tests disable local credential-vault discovery and use temporary databases and mock AI responses. Do not commit account credentials, real user records, or a copied production database.

## All-Render deployment

`render-managed.yaml` builds the React frontend and FastAPI backend into one web service and references the already-created `pattern-dsa-db` database privately. Render generates the signing secret and resolves the database URL without copying it to this repository. Only the Gemini key needs to be supplied during the initial Blueprint apply. This deployment uses the Folio Assignment workspace. The free database expires on December 7, 2026.
