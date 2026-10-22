# Project memory

## Status board
- Phase 1 — Local infrastructure and database: DONE (2026-10-22)
- Phase 2 — Ingestion (presign + parser): DONE (2026-10-22)
- Phase 3 — Workflow A: crawler: DONE (2026-10-22)
- Phase 4 — Workflow B: matching and the Treasure Hunt: DONE (2026-10-22)
- Phase 5 — Workflow C: notifications: NEXT

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

## Phase 3 — Workflow A: loan product discovery
- Workflow: `n8n/workflows/A_loan_product_discovery.json` (10 nodes), imported into n8n, linked to the `Postgres account` credential, and published with its daily schedule enabled.
- Test pages: `data/mock_sites/bank_a.html` and `bank_b.html`, served on port 8080 at `host.docker.internal:8080`.
- Manual run saved 12 products: 6 from QuickCredit Bank and 6 from FinEasy Lenders. With the 18 seed products, `loan_products` contains 30 rows.
- A second manual run did not change the counts. With the test server stopped, the workflow still completed and routed one item through `Any site empty?` to `Log empty sites`; existing rows remained at 30. The test server was restarted afterward.
- Normalization parses interest rate, minimum income, score and age thresholds, and employment types from the eligibility text. `raw_hash` is computed in SQL as `md5(eligibility_text)`; `COALESCE` on conflict preserves stored values when parsing returns NULL.
- n8n automatically associated the existing `Postgres account` credential during import.
- NEXT: Phase 4 — Workflow B (matching and the Treasure Hunt).

## Decisions and known limits
- Local test upload simulates an S3 event because MinIO does not invoke the local Lambda automatically.
- CSV parsing is streamed; quoted field values containing embedded line breaks are not supported by the line-based reader.
- The two lender pages are local static test fixtures; replace or supplement their URLs and CSS selectors when moving to approved live static pages.
- The Phase 1 MinIO images are built from Go modules because the supplied Docker Hub image references are unavailable.

## Phase 4 — Workflow B: matching and the Treasure Hunt
- Workflow: `n8n/workflows/B_user_loan_matching.json` (17 nodes), published with production webhook `POST /webhook/users-processed` and linked to the existing Postgres credential.
- Added `scripts/trigger_workflow_b.py` for normal, test, and wrong-secret calls.
- Batch `cd58f598-f784-43e4-ab7f-9775259d339c` had 10,000 users and 30 products: `all_pairs=300000`, `after_sql=105339`, `after_rules=104294`, `llm_calls=0`, `final=104294`.
- Wrong secret returned 401; valid secret returned 202. Two valid runs finished with 104,294 matches and no duplicate pairs.
- Borderline candidate count was 40,986. No `LLM_API_KEY`/`LLM_MODEL` is configured, so the workflow safely skipped LLM requests and kept undecided borderline pairs matched. `docs/treasure_hunt.md` records the actual funnel and this limitation.
- Compose passes optional `LLM_API_KEY` and `LLM_MODEL` to n8n; with no key, the workflow records zero calls. `Trigger Workflow C` continues on error until Phase 5 creates its webhook.
- NEXT: Phase 5 — Workflow C (user notifications).
