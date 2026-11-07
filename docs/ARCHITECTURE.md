# Implementation notes

The React client calls the FastAPI JSON API. It sends an expiring bearer JWT only after login. Password hashes and signing keys never reach the client. Bookmarks, progress, and conversations are always filtered by the authenticated user, and conversation IDs from another account return 404.

A tutoring request validates its mode and question length, applies a basic scope/injection guard, and retrieves mode-appropriate chunks. Hint mode can retrieve only conceptual hint passages. Explanation includes notes without implementation chunks. Solution can retrieve implementations. Selected-problem sessions constrain retrieval to that problem. Authenticated follow-ups include bounded recent history.

In production, the backend embeds the query using the same 768-dimensional Gemini embedding model used by the indexer. PostgreSQL orders chunks by pgvector cosine distance, filtered by model and content mode; an HNSW index accelerates similarity search. The selected passages and untrusted question/history are serialized as data, separate from the system instruction, then sent to Gemini. Only stored, verified source metadata is returned as citation links, and nonexistent numerical citation references are stripped.

Without an indexed PostgreSQL database, development uses an explicit lexical ranking function. When no Gemini key is configured, answers are static reference notes for the best matching record. These fallbacks are labeled in health data and the UI and are not represented as semantic embeddings or personalized AI.

The indexer creates missing tables, seeds the pinned dataset, and embeds missing/current-model chunks in committed batches. A failure leaves completed batches intact. Startup must not use an ephemeral database in production. `render.yaml` supplies the required build, start, and health paths; Vercel serves the frontend with the Render API URL as a public build-time variable.

The source library intentionally preserves provenance and missing-data notices. It is a 389-record teaching collection, not a claim to reproduce the entire official A2Z sheet or certify every upstream answer. Original heap and greedy references fill two empty upstream topic folders.

The current rate limiter is local to one process; a shared Redis or database-backed quota is needed before horizontal scaling. Future production schema changes need migration tooling. Prompt defenses are layered constraints and heuristics, not a guarantee that a model will never hallucinate or follow a malicious instruction.
