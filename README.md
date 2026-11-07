# Pattern — AI-powered DSA tutor

A working React + FastAPI learning app with a problem library, progressive tutoring, source citations, JWT authentication, saved conversations, bookmarks, and problem progress. Production retrieval uses Gemini embeddings and PostgreSQL/pgvector; development also supports an explicitly labeled keyword-based reference mode.

The interface opens directly into a restrained black-and-white chat workspace, with a subtle paper texture and light/dark themes. Your theme preference is saved locally. The problem library and progress counts come from the database.

## What is included

- React 19, TypeScript, Vite, responsive layouts, Markdown/code rendering, and keyboard search (`Ctrl/Cmd K`).
- FastAPI, SQLAlchemy, Argon2 password hashing, signed expiring JWTs, per-user authorization, bounded inputs, strict CORS, and basic per-process rate limiting.
- **389 learning problems:** 381 usable C++ files imported from a pinned MIT-licensed community repository and 8 original, explained heap/greedy references.
- **16 populated topics and 53 taxonomy subtopics.** Some subtopics have no imported problem. This is **not the complete 455-question Striver sheet**. Difficulty is inferred from upstream folders, not an official rating.
- Hint / Explanation / Solution modes with separate retrieval passages. Hint context excludes full solutions. Responses cite verified source metadata.
- A resumable embedding indexer, 768-dimensional vectors, cosine similarity, and an HNSW index.
- Vercel frontend configuration, Render backend configuration, optional local pgvector via Docker, and GitHub Actions checks.

The upstream collection is a community reference, not an independently verified answer bank. Where it omits a statement, editorial, or complexity analysis, the app says so. The app is not affiliated with Striver or takeUforward.

## Run locally on Windows

From the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
# Optional: Windows Credential Manager integration for a local Gemini key
.venv/Scripts/python.exe -m pip install -r backend/requirements-windows.txt
Copy-Item backend/.env.example backend/.env
```

Replace `JWT_SECRET` in the ignored `backend/.env` with a random value of at least 32 characters. When created by the setup workflow, this file already has a generated secret. Keep all secrets outside version control. The shipped dataset is ready to use; no scraper or import command is needed to launch.

In one terminal:

```powershell
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open [localhost:5173](http://localhost:5173). API docs are at [localhost:8000/docs](http://localhost:8000/docs). The default SQLite database and keyword retrieval make the app usable without a cloud account. SQLite is for local development, not production persistence.

### Local Gemini key storage

```powershell
.venv/Scripts/python.exe scripts/store_gemini_key.py
```

The hidden prompt saves the key in Windows Credential Manager under service `pattern-dsa-tutor`, account `gemini-api-key`. It verifies access against Google's models endpoint and prints no key. On Windows the backend reads this credential if `GEMINI_API_KEY` is empty. `USE_OS_KEYRING=false` disables this behavior. Linux/Render reads the platform's secret environment variable. No key is sent to the frontend or stored in the repository.

With SQLite, Gemini can generate source-grounded responses while retrieval remains explicitly labeled as keyword matching. Full semantic RAG requires PostgreSQL and a completed embedding index.

### PostgreSQL / pgvector

Create a Neon project and copy its PostgreSQL connection string into `DATABASE_URL` in the ignored local environment file, or use a secret environment variable. Include Neon's recommended TLS settings. Alternatively, run the supplied Docker Compose service and use:

```text
postgresql://pattern:local-development-only@localhost:5432/pattern
```

The application creates the `vector` extension, tables, and HNSW index at startup. The connection's role needs permission to create the extension. Run the indexer from `backend` with the same database and Gemini credentials:

```powershell
../.venv/Scripts/python.exe -m app.index
```

Indexing sends the attributed curriculum passages to Google's embedding API. It may consume API quota. Completed batches are committed, so rerunning resumes missing chunks. Retrieval only compares embeddings from the configured embedding model. A model change requires reindexing.

## Deploy: Vercel + Render + Neon

An all-Render option is available in `render-managed.yaml`: the same FastAPI service serves the built React frontend and `/api` routes, and connects privately to the existing `pattern-dsa-db` Postgres instance in the same workspace. This keeps database credentials inside Render references. The initial free database expires on December 7, 2026; upgrade or migrate before expiry. The Vercel/Neon configuration below remains available for that hosting split.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the exact order and environment variables. Do not set production to SQLite. Production startup rejects missing database credentials, a missing Gemini key, weak signing secrets, and wildcard/non-HTTPS CORS origins.

Production must be verified separately: a successful local build does not prove a cloud deployment or a populated pgvector index. `/api/health` reports the active database, AI provider, retrieval method, and indexed chunk count without exposing credentials.

## Validation

```powershell
cd backend
../.venv/Scripts/python.exe -m pytest -q
cd ../frontend
npm run build
```

The integration suite checks authentication, malformed tokens, user isolation, saved progress, bookmarks, chat ownership/deletion, rate limiting, search/pagination, source citations, and mode-separated retrieval. Gemini request construction is tested with a mocked response; live Google and PostgreSQL checks require real account access. The frontend build includes TypeScript checking. Windows may require local socket access for Python's test client/event loop.

## Data provenance and updates

Source: [Kartavya728/Data-Structure-and-Algorithms-Sheet](https://github.com/Kartavya728/Data-Structure-and-Algorithms-Sheet), pinned to `1ef6eec5cb6a103246ce2f54fe0977b6dd9ff2c8`. The MIT copyright notice is preserved in `third_party/KARTAVYA_LICENSE.txt`, the data manifest, and the app's attribution view. Original notes are in `backend/data/originals.json` and `scripts/original_curriculum.py`.

To reproduce the import, clone the source into the ignored `third_party/upstream` directory at the pinned commit, then run `python scripts/import_curriculum.py`. The importer checks the commit and license and never executes downloaded code. It excludes tiny unusable files and reports actual imported counts. Reusing public GitHub material without a license is deliberately avoided.

The seed operation inserts new records without overwriting existing ones. To change existing curriculum records in a deployed database, use an explicit reviewed migration and invalidate/rebuild their chunks. Do not silently overwrite indexed content.

## Project layout

```text
backend/app/          API, auth, database models, retrieval, Gemini, seed/index commands
backend/data/         Pinned curriculum, taxonomy, provenance, original references
backend/tests/        API integration and retrieval contract tests
frontend/src/         React application and responsive styles
scripts/             Import, secure key setup, local launch, GitHub repository setup
docs/                Deployment and architecture notes
render.yaml          Render backend Blueprint
frontend/vercel.json Vercel frontend build configuration
```

## Current limits

Prompt-injection checks and mode-specific evidence reduce risk; they are not a proof against every adversarial prompt or model error. There is no untrusted-code execution, password-reset email, social login, refresh-token rotation, or multi-instance distributed rate limiter. JWTs expire after 8 hours by default; signing out removes the browser's session token. Tokens use session storage, so keep the application's XSS protections intact. Schema initialization uses `create_all`; future production schema changes should use versioned migrations. Source implementations should be tested before being used as authoritative solutions.
