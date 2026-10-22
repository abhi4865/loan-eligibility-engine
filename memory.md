# Project memory

## Status board
- Phase 1 — Local infrastructure and database: DONE (2026-10-22)
- Phase 2 — Ingestion code: NEXT

## Phase 1 results
- `docker-compose.yml` runs Postgres 16, n8n, MinIO, and a one-shot bucket initializer.
- `db/schema.sql` initializes the six tables: `upload_batches`, `users`, `loan_products`, `matches`, `llm_cache`, and `pipeline_stats`.
- `db/seed_products.sql` loads 18 fallback products across four fictional providers. Re-running the seed inserts zero duplicates; the count remains 18.
- MinIO bucket `loan-uploads` was created.
- n8n responds at `http://localhost:5678`.
- Postgres is mapped to host port 5433 because host port 5432 was already occupied by another running service. Inside Docker, it remains available at `postgres:5432`.
- MinIO is available at `http://localhost:9000` (S3 API) and `http://localhost:9001` (console).
- `.env` contains local generated credentials and is ignored by Git. `.env.example` is the shareable template.

## Explain-it
- Named volume `n8n_data` persists workflows and saved credentials when the n8n container is replaced.
- `UNIQUE (user_id, product_id)` prevents duplicate user/product matches when a workflow reruns.
- n8n connects to Postgres by the Compose service hostname `postgres` on port 5432. `localhost` inside n8n would refer to the n8n container itself.

## Local infrastructure adjustment
The supplied MinIO Docker Hub image references could not be pulled. The MinIO server and client are built from their published Go modules using `docker/minio/Dockerfile`.
