# Project memory

## Status board
- Phase 1 — Local infrastructure and database: DONE (2026-10-22)
- Phase 2 — Ingestion (presign + parser): DONE (2026-10-22)
- Phase 3 — Workflow A: crawler: NEXT

## Current environment
- Local Postgres, n8n, and MinIO run with Docker Compose.
- Postgres host port is 5433 because another local service occupies 5432; Docker service address remains `postgres:5432`.
- Database: `loan_db`; S3 bucket: `loan-uploads`; n8n: `http://localhost:5678`.
- The real 10,000-row assignment CSV is at `data/users.csv`.
- Local Python dependencies are in `.venv`; `.env` is ignored by Git.

## Phase 2 implementation and verification
- `lambdas/common/db.py`: environment-based PostgreSQL connections and `run_query` helper.
- `lambdas/common/aws_clients.py`: S3-compatible boto3 client for MinIO or AWS.
- `lambdas/common/validators.py`: required row validation, cleanup, and employment normalization.
- `lambdas/presign/handler.py`: creates an upload batch and a 15-minute presigned PUT URL.
- `lambdas/parser/handler.py`: claims each batch once, streams CSV lines, checks headers, validates rows, upserts chunks of 1,000, and records processed/failed counters.
- `scripts/test_upload.py`: drives local presign, MinIO PUT, parser, and duplicate-event replay.
- `scripts/make_sample_csv.py` and `tests/test_validators.py`: create edge-case CSV and unit coverage.
- `requirements.txt`: runtime and development packages.
- The sample CSV processed 11 rows: 5 valid, 6 invalid, 4 unique users saved. Temporary sample users were removed after checking.
- The real file processed 10,000 rows: 10,000 valid, 0 invalid. A second upload left exactly 10,000 unique users. Employment counts: business 3,240; salaried 3,389; self-employed 3,371.
- Replaying the same S3 event returned `skipped`.
- A CSV missing columns was marked `failed` with `Missing columns: name, monthly_income, credit_score, employment_status, age`.
- Validator tests: 5 passed.
- The parser's n8n webhook returned 404 because the matching workflow is not implemented until Phase 4; this is expected and did not fail ingestion.

## Explain-it
- The presigned URL lets the browser send large files straight to S3, avoiding API Gateway and Lambda request-size limits.
- Batch inserts reduce database round trips while limiting memory and transaction size.
- The parser's atomic status claim skips duplicate S3 deliveries; the user upsert also makes repeat uploads safe.

## Decisions and known limits
- Local test upload simulates an S3 event because MinIO does not invoke the local Lambda automatically.
- CSV parsing is streamed; quoted field values containing embedded line breaks are not supported by the line-based reader.
- Workflow A remains next; the n8n callback is not active until the matching workflow is built.
- The Phase 1 MinIO images are built from Go modules because the supplied Docker Hub image references are unavailable.
