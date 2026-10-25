# memory.md — Live project state (update after every phase)

> This file is the shared brain between LLM sessions. Keep it short and factual.
> Always paste it together with `project.md` into a new LLM.
> Last updated: 2026-10-25. Local phases 1–4 were exercised against an earlier running Docker/n8n session; Phase 5 email delivery failed; Phase 6's real browser upload was not verified. Docker is currently inaccessible from this Codex session.

## 0. How to update this file (do this at the end of every phase)

1. Change the phase status in the table (section 1): `DONE`, and mark the following phase `NEXT`.
2. Add one entry to the Results log (section 4) using the template there.
3. Add any changed decision to section 3, with the reason.
4. Add new blockers to section 5, and remove solved ones.
5. Update section 2 if any file, port or value changed.
6. Ask the LLM: "Give me the exact text to paste into memory.md." Then paste it here.

Rule: a phase is `DONE` only after the developer ran its acceptance checklist and ticked the boxes. Code that was written but not yet run is `IN PROGRESS`.

## 1. Phase status

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | Repo and skeleton | IN PROGRESS | Folder layout, `.gitignore`, `.env.example` created (placeholders). Still open: SES verification, collaborator invites, real `users.csv` in `data/` |
| 1 | Local infra and database | IN PROGRESS | Earlier run found 6 public tables and healthy services; products totaled 30 after seed plus Workflow A. Could not independently recheck Docker in current session (Docker named-pipe access denied). Phase acceptance checklist is not fully verified. |
| 2 | Ingestion (presign + parser) | IN PROGRESS | Earlier local presign → MinIO PUT → parser run processed `data/users.csv`: 10,000 valid, 0 invalid, batch `d36e65da-f86d-4aa0-b48c-6397bdb8814f`. Did not verify repeat-upload, replay, bad-header, or pytest cases this run. |
| 3 | Workflow A: crawler | IN PROGRESS | Earlier n8n manual runs A16 and A17 succeeded against mock server; product count stayed 30. Stopped-server fallback and workflow export/commit checklist not verified. |
| 4 | Workflow B: matching + treasure hunt | IN PROGRESS | Parser triggered Workflow B for the batch. Funnel in `docs/treasure_hunt.md`; wrong secret returned 401. `llm_calls=0` was recorded although LLM_API_KEY was present in the container; do not assert the key was unset or that no external attempt occurred. |
| 5 | Workflow C: notification | IN PROGRESS | Earlier n8n execution 15 routed five items through email failure; zero batch matches marked notified. No email delivery verified; SES identity verification and wrong-secret/second-run checks remain. |
| 6 | Minimal UI | IN PROGRESS | Browser upload of `data/users.csv` not verified. A repeat could trigger Workflow B and transmit financial attributes to the configured external LLM provider; no further run performed. |
| 7 | serverless.yml | IN PROGRESS | Merged supplied Phase 7 files; `npm run package` succeeded with temporary dummy values. ZIP and CloudFormation template verified; no AWS deployment. |
| 8 | README and diagram | NEXT | Needs the real funnel numbers from Workflow B (section 6) |
| 9 | Demo video | TODO | |

Status values: `TODO`, `NEXT`, `IN PROGRESS`, `DONE`, `BLOCKED`.

## 2. Current environment facts

- Repo: private GitHub repo `loan-eligibility-engine`; local path `C:/Users/DELL/Desktop/loan-eligibility-engine` (Windows, so use PowerShell commands)
- Collaborators invited: no (do in GitHub: Settings → Collaborators, before submitting)
- Local mode in use: Postgres in Docker, MinIO for S3, n8n in Docker
- Docker containers: `loan_postgres`, `loan_n8n`, `loan_minio` (plus a one-time `minio-init` that creates the bucket)
- n8n URL: http://localhost:5678 (owner account is created on first open). Postgres credential in n8n uses host `postgres`, not `localhost`. In Workflows A and B the Postgres credential must be selected in each Postgres node after import (A: 1 node, B: 7 nodes)
- Postgres: db `loan_db`, user `loan_user`, port 5432. Host is `localhost` for scripts on the laptop and `postgres` inside Docker
- S3 (MinIO): bucket `loan-uploads`, API http://localhost:9000, console http://localhost:9001, region `ap-south-1` (if a region error appears, set `AWS_REGION=us-east-1`)
- Webhook to n8n: `N8N_WEBHOOK_URL=http://localhost:5678/webhook/users-processed`, header `X-Webhook-Secret` = `N8N_WEBHOOK_SECRET`. Returns 404 until Workflow B is imported AND set Active (test URL `/webhook-test/...` works only while "Execute workflow" is listening). The parser only logs a warning on failure
- n8n container env needed by Workflow B: `N8N_WEBHOOK_SECRET`, `LLM_API_KEY`, `LLM_MODEL`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`. Check `docker-compose.yml` has all four (the Phase 1 file may lack `LLM_API_KEY` and `LLM_MODEL`); recreate with `docker compose up -d n8n`
- SES sender verified: no. Test aliases verified: no (needed for phase 5, start now because approval takes time)
- Authenticated AWS access: not set up (only needed to DEPLOY in phase 7; `serverless package` needs none)
- LLM for Workflow B: OpenAI-compatible chat endpoint. Default `llmUrl` is Google's (`https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`), set in the `Settings` node. Model name (`LLM_MODEL`) and key: not chosen yet by the developer
- Sites for crawler (Workflow A): two local test pages `data/mock_sites/bank_a.html` (provider `QuickCredit Bank`) and `bank_b.html` (provider `FinEasy Lenders`), 6 products each, served with `cd data/mock_sites && python -m http.server 8080` and fetched at `http://host.docker.internal:8080/...`. Real sites: not chosen (optional)
- Real CSV header: `user_id,name,email,monthly_income,credit_score,employment_status,age`
- Real CSV: 10,000 rows plus header, Windows line endings (`\r\n`), read with `utf-8-sig`
- CSV data profile: income 25,000-150,000; credit score 650-800; age 22-50; employment counts business 3,240 / salaried 3,389 / self-employed 3,371; no blanks or bad emails; user_id all unique UUIDs; only 2,632 unique emails (about 3.8 users per email)
- `data/users.csv`: 10,000 user rows plus header (verified 2026-10-25)
- Seed data: 18 products from 4 fictional lenders (Alpha Bank 4, Beta Finance 5, Gamma Credit 4, Delta NBFC 5), `source_url = 'seed'`. Four have text-only rules for the LLM stage: Beta Business Boost, Beta Salary Advance, Gamma Self-Made Loan, Alpha Business Growth Loan. `Delta Open Door Loan` matches everyone, `Delta Mega Loan` almost nobody
- Expected `loan_products` after Workflow A: 18 seed + 12 crawled = 30 rows (so about 300,000 user × product pairs for 10,000 users). To be confirmed by the developer
- Python packages (requirements.txt): boto3, psycopg2-binary, python-dotenv, pytest
- Workflow C (`n8n/workflows/C_user_notification.json`, 10 nodes): webhook `POST /webhook/matching-complete` with `{batch_id}` and header `X-Webhook-Secret`. Credentials to select after import: Postgres in `Pick matches` and `Mark notified`, AWS in `Send with SES`
- n8n container env needed by Workflow C (add to the `n8n` service, then `docker compose up -d n8n`): `N8N_WEBHOOK_SECRET`, `SES_SENDER_EMAIL`, `TEST_EMAIL_1`, `TEST_EMAIL_2`, `MAX_DEMO_EMAILS`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- Reset for a new email demo: `UPDATE matches SET notified = false;`
- UI (phase 6): start `python scripts/local_server.py` (127.0.0.1:8000, run from the repo root), open http://localhost:8000. The page uses `GET /presign`, `PUT` to MinIO, `POST /process` (local mode) and `GET /status`. The local server needs `.env` and the handler functions named `lambda_handler` or `handler` in `lambdas/presign/handler.py` and `lambdas/parser/handler.py`
- MinIO CORS: default allows all origins. To restrict, add `MINIO_API_CORS_ALLOW_ORIGIN=http://localhost:8000` to the `minio` service. For real S3 run `python scripts/set_bucket_cors.py`
- AWS deploy (phase 7): Serverless Framework v3 via `npm install` then `npm run package` / `npm run deploy`. Deploy values are read from `.env.dev`; keep real AWS values separate from MinIO `.env` values and use a globally unique `S3_BUCKET`. Packaging selects manylinux x86_64 Python 3.11 wheels directly and does not require Docker. RDS is documented, not created

## 3. Decisions log

Only record decisions that differ from project.md, or choices project.md left open.

| # | Decision | Reason | Phase |
|---|----------|--------|-------|
| 1 | Build local-first, AWS deploy only as bonus | Assignment allows local deployment; about 4 hour budget | 0 |
| 2 | Added `name` column to `users` table | Real CSV has a `name` column; used in the email greeting | 1 |
| 3 | `email` is NOT unique and never used as a key | Only 2,632 unique emails across 10,000 users | 1 |
| 4 | Employment stored lowercase: `salaried`, `self-employed`, `business` | CSV has `Salaried`, `Self-Employed`, `Business`; one format avoids SQL mismatches | 2 |
| 5 | Seed products tuned to data range (income 25k-150k, score 650-800, age 22-50) | Otherwise the funnel is trivial (everyone or nobody matches) | 1 |
| 6 | Email run capped by `MAX_DEMO_EMAILS` (default 5) | 10,000 users would produce thousands of matches and emails; SES sandbox limits | 5 |
| 7 | Added `lambdas/common/aws_clients.py` and `__init__.py` files; imports are `from lambdas.common.x import y` | One shared S3 client for MinIO and AWS; package-style imports work locally and when deployed from the repo root | 2 |
| 8 | Locally the parser is called directly by `scripts/test_upload.py` with a fake S3 event | MinIO on a laptop cannot trigger a Lambda; real S3 sends the same event shape on AWS | 2 |
| 9 | Presigned PUT URL (not presigned POST); Content-Type must be `text/csv` | Simpler for the browser; trade-off: file size cannot be capped (a presigned POST could) | 2 |
| 10 | Parser claims the batch with `UPDATE ... WHERE status IN ('uploaded','failed') RETURNING` | Duplicate S3 events are skipped; failed batches can be retried | 2 |
| 11 | A failed n8n webhook call does NOT fail the batch (only a warning) | The users are already saved; Workflow B does not exist until phase 4 | 2 |
| 12 | n8n image `n8nio/n8n:latest`, with `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` | Workflows can read `$env` values (webhook secret, test emails, email cap) | 1 |
| 13 | DB init SQL files run only when the Postgres volume is first created | After editing `schema.sql` or `seed_products.sql`, reset with `docker compose down -v` (deletes data) | 1 |
| 14 | Seed lenders are fictional; crawler upserts on `(provider, product_name)` | Crawled products are added next to the seed rows. OPEN QUESTION: keep seed rows in matching, or drop them once the crawler works (currently kept) | 1 |
| 15 | Added index `idx_matches_batch_notified` on `matches(batch_id, notified)` | Workflow C looks up un-emailed matches per batch | 1 |
| 16 | Workflow A reads two local test pages (`data/mock_sites/`) served by `python -m http.server 8080` | Deterministic demo that does not depend on a real site; real sites need only new selectors and URLs | 3 |
| 17 | `raw_hash` = `md5(eligibility_text)` computed in Postgres inside the upsert, not in the Code node | The n8n Code node cannot use `crypto` without an extra env var | 3 |
| 18 | Crawler upsert uses `COALESCE(new, old)` for thresholds, `allowed_employment`, rate, text and hash | A failed parse never wipes good data | 3 |
| 19 | Employment words found in rule text become `allowed_employment`; no employment word means NULL (any) | Simple parsing; the raw text still goes to the LLM stage | 3 |
| 20 | Workflow B Stage 1 uses `ON CONFLICT (user_id, product_id) DO UPDATE SET batch_id, stage='sql'` (project.md showed `DO NOTHING`) | After a second upload users get a new `batch_id`; with DO NOTHING old matches would keep the old batch id and later stages would miss them. `notified` is not touched | 4 |
| 21 | Stage 2 rules are built in the `Settings` Code node and run as ONE SQL statement: EMI on ₹300,000 over 36 months must be at most 40% of income; loans with rate ≤ 10% need income ≥ 40,000 | Moving 15,000+ rows into n8n memory would be slow; numbers stay tunable in one place | 4 |
| 22 | `llm_cache.rule_hash` = `md5(raw_hash|income|score|age|employment)`, `result` = `{"eligible": true|false}` | The LLM answer depends on the rule text and the user profile, not on `user_id` | 4 |
| 23 | Borderline = within 5% above an income or score limit, or `eligibility_text` matches the hidden-criteria regex (years old, experience, tax, turnover, ...). Max 100 NEW pairs per run (`llmMaxPairs`), 20 users per call, one call every 2.5 s | Keeps the demo cheap and inside free-tier limits; cached answers cost nothing on reruns | 4 |
| 24 | If the LLM call fails or returns bad JSON, the pair stays matched and nothing is cached | Benefit of the doubt; the next run asks again | 4 |
| 25 | Workflow B answers 202 at once and then continues; wrong or empty secret returns 401 | The parser Lambda must not wait for the whole run | 4 |
| 26 | Workflow B calls Workflow C with `POST http://localhost:5678/webhook/matching-complete`, body `{batch_id}`, header `X-Webhook-Secret` (HTTP node continues on error) | Phase 4 passes before C exists | 4 |
| 27 | Added `scripts/trigger_workflow_b.py` (`--test`, `--wrong-secret`) | Test B without uploading a CSV again | 4 |
| 28 | Workflow C starts only from `POST /webhook/matching-complete` (secret checked like in B, 202 at once); no Execute Workflow Trigger | B already calls it by HTTP; one entry point is simpler | 5 |
| 29 | `MAX_DEMO_EMAILS` (default 5, hard limit 50) is a cap PER BATCH: allowed users = cap − users already `notified` in that batch (refines decision 6) | project.md needs "running C again sends nothing new"; a per-run cap would email the next 5 users each time | 5 |
| 30 | Pick SQL never selects `users.email`; recipients are `TEST_EMAIL_1` / `TEST_EMAIL_2` round-robin | A real CSV address can never reach a send | 5 |
| 31 | `Send with SES` continues on error; only users whose email had no error are marked `notified`; one email per user (grouped) | A failed user stays un-notified and is retried on the next run | 5 |
| 32 | Added `scripts/trigger_workflow_c.py` (`--test`, `--wrong-secret`) | Test C alone | 5 |
| 33 | Added `scripts/local_server.py`: serves the page, `GET /presign`, `POST /process?batch_id=` (parser in a background thread with a fake S3 event, key `uploads/<batch_id>/users.csv`), `GET /status?batch_id=`. Binds 127.0.0.1:8000, CORS allow-all | MinIO cannot start a Lambda and there is no API Gateway locally | 6 |
| 34 | UI has a "Local mode" checkbox (on for localhost). Off on AWS, where the S3 event starts the parser. Without `/status` the page says to watch n8n | One page for laptop and AWS | 6 |
| 35 | Added `scripts/set_bucket_cors.py` for real S3; MinIO uses its own server CORS setting | MinIO ignores bucket CORS | 6 |
| 36 | Serverless Framework v3 (`frameworkVersion: '3'`) + `serverless-python-requirements`; `package.json` at repo root | v3 needs no login | 7 |
| 37 | Deploy values come from `.env.dev`, not `.env`; `.env.*` git-ignored | v3 reads `.env.{stage}` instead of `.env`; keeps real AWS keys apart from the MinIO keys | 7 |
| 38 | `requirements-lambda.txt` (psycopg2-binary 2.9.9, python-dotenv 1.0.1) for the zip; pip selects manylinux x86_64 wheels for Python 3.11 without Docker | boto3 and pytest are not needed in the zip; psycopg2 must be a Linux build | 7 |
| 39 | Bucket, CORS, `uploads/` S3 event, 30-day lifecycle and the Lambda permission are in `resources` (not the `s3` event shortcut); bucket `DependsOn` the permission | Everything in one place; S3 needs permission before saving the event | 7 |
| 40 | Lambda env uses the same names as `.env`, without `AWS_*`, with `S3_ENDPOINT_URL` empty; IAM limited to `uploads/*` of one bucket plus SES send (not used by the Lambdas) | Least privilege; the spec lists SES in the role | 7 |
| 41 | RDS is NOT provisioned (documented in `instruction7.md`); Lambdas not in a VPC by default, `USE_VPC=on` switches it on | Time budget; Lambdas need internet access for S3 and the n8n webhook | 7 |
| 42 | Serverless handler references use `.handler` for both functions | Both Phase 2 modules define `handler(event, context)` | 7 |
| 43 | Optional deploy env names: `PYTHON_BIN`, `USE_VPC`, `VPC_SECURITY_GROUP_ID`, `VPC_SUBNET_ID_1`, `VPC_SUBNET_ID_2` | Python executable override and optional VPC settings in `serverless.yml` | 7 |

## 4. Results log

Newest entry at the bottom. Copy the template for each phase.

```
### Phase N — name — DONE (date)
Files created/changed:
- path: one line on what it does
How to run:
- command(s)
Acceptance test result:
- what I ran, what I saw (counts, screenshots taken, errors fixed)
Explain-it answers I can give:
- Q1 -> short answer
- Q2 -> short answer
- Q3 -> short answer
Things I changed myself in the code (so I know I understand it):
- example: changed credit score minimum from 300 to 350
Open issues left:
- none / list
```

### Phase 0 — Repo and skeleton — IN PROGRESS
Files created/changed:
- Folder layout from project.md section 3, `.gitignore`, `.env.example`: created by another tool; project implementation is now present and `data/users.csv` contains the real sample dataset
Still open:
- [ ] Start SES verification (sender + two Gmail `+alias` test addresses)
- [ ] Invite the 4 collaborators in GitHub

### Phase 1 — Local infrastructure and database — PARTIALLY VERIFIED
Files created/changed:
- docker-compose.yml: postgres 16, n8n, minio and a one-time bucket creator; data in named volumes
- db/schema.sql: 6 tables (upload_batches, users, loan_products, matches, llm_cache, pipeline_stats) plus indexes
- db/seed_products.sql: 18 made-up products tuned to the CSV ranges; 4 have text-only rules for the LLM stage
- .env.example, .gitignore, instruction1.md
How to run:
- copy `.env.example` to `.env` (fill values), then `docker compose up -d`; follow instruction1.md
Observed in the earlier run: 6 public tables; 30 products after seed plus the successful two Workflow A runs; container services reported healthy and n8n credentials were present. Git tracking checks in this session confirm `.env` and `.env.dev` are untracked/ignored and `.env.example` is tracked. Seed-only idempotency (18 rows), MinIO console, and a fresh credential test were not independently verified here.
Acceptance checklist:
- [x] Database has 6 tables
- [x] `.env` not tracked by Git
- [ ] `docker compose ps` freshly verified: postgres healthy, n8n and minio running
- [ ] seed-only count is 18, unchanged after re-running the seed
- [ ] MinIO console shows bucket `loan-uploads`
- [ ] n8n Postgres credential test freshly verified
Explain-it answers I can give:
- Named volume -> keeps n8n workflows/credentials after container removal
- UNIQUE(user_id, product_id) -> reruns cannot create duplicate matches
- n8n reaches Postgres by service name `postgres`, not localhost
Things I changed myself in the code (so I know I understand it):
- (developer to fill in)
Open issues left:
- Fresh Docker/container state could not be checked in the current session because the Docker named pipe denied access.

### Phase 2 — Ingestion (presign + parser) — PARTIALLY VERIFIED
Files created/changed:
- lambdas/common/db.py, aws_clients.py, validators.py: shared connection, S3 client, row validation
- lambdas/presign/handler.py: creates batch row + presigned PUT URL (valid 15 minutes, .csv only)
- lambdas/parser/handler.py: claims batch, streams CSV, validates, upserts in chunks of 1000, marks processed/failed, calls n8n
- scripts/test_upload.py (also `--replay <batch_id>`), scripts/make_sample_csv.py, tests/test_validators.py, requirements.txt, instruction2.md
- data/sample_small.csv: 11 rows, 6 bad, with BOM and CRLF
How to run:
- `pip install -r requirements.txt`, then `python scripts/test_upload.py` (or pass another CSV path); follow instruction2.md
Testing already done by the LLM (with stand-ins for Postgres and S3, NOT the real services):
- unit tests: 5 passed; real file: 10,000 valid / 0 invalid in 10 chunks of 1,000; small file: 11 total / 5 valid / 6 invalid / 4 unique users; replay -> skipped; bad header -> failed with clear error
Acceptance checklist:
- [x] real file upload: 10,000 valid, 0 invalid, parser completed
- [ ] `python -m pytest tests -q` -> 5 passed in the current environment
- [ ] small file integration case and cleanup
- [ ] employment-category totals verified against database
- [ ] repeat upload, replay, and bad-header cases
Explain-it answers I can give:
- Presigned URL -> file goes straight to S3, bypassing API Gateway/Lambda size/time limits
- Claim UPDATE ... RETURNING -> duplicate S3 events are skipped
- Chunked execute_values upsert -> fast and safe to re-run; a dict per chunk avoids duplicate user_id inside one INSERT
Things I changed myself in the code (so I know I understand it):
- (developer to fill in, for example an income cap rule plus its own unit test)
Open issues left:
- Not run against the real Postgres and MinIO yet
- n8n webhook returns 404 until phase 4 (expected, only a warning)

### Phase 3 — Workflow A: loan product discovery — PARTIALLY VERIFIED
Files created/changed:
- n8n/workflows/A_loan_product_discovery.json: 10 nodes. Manual Trigger + Daily Schedule (02:00) → Config sources (Code) → Fetch page (HTTP, continue on error) → Extract HTML (`.loan-name`, `.loan-rate`, `.loan-rules`) → Normalize (Code, builds one multi-row SQL upsert) → Upsert loan_products (Postgres) → Summary; Normalize also → Any site empty? (IF) → Log empty sites
- data/mock_sites/bank_a.html, bank_b.html: fake lender pages, 6 products each, some with text-only rules (business age, filed taxes)
- instruction3.md
How to run:
- `cd data/mock_sites && python -m http.server 8080` (keep running), import the JSON in n8n, select the Postgres credential in `Upsert loan_products`, click Execute workflow; follow instruction3.md
Testing already done by the LLM (NOT in n8n):
- JSON validated; the Normalize code run on both pages: 12 products parsed, a third dead site was reported as empty; generated SQL inspected
Acceptance checklist:
- [x] two n8n manual runs succeeded and product count remained 30
- [ ] summary explicitly shows `products_upserted: 12`
- [ ] with the Python server stopped, workflow logs empty sites and ends successfully
- [ ] workflow exported and committed
Explain-it answers I can give:
- Why upsert -> daily runs refresh rates and rules without duplicates (`ON CONFLICT (provider, product_name)`), updates `last_seen_at`
- Layout change -> selectors return nothing, log shows `0 products`, seed and old rows stay safe, fix the selectors
- Why static pages first -> plain HTTP request; JavaScript pages need a headless browser, which is slower and fragile
Things I changed myself in the code (so I know I understand it):
- (developer to fill in)
Open issues left:
- Stopped-server fallback and export/commit were not verified.
- The three extracted arrays are matched by position; a card with a missing rule text would shift the rest (limitation)
- Both sites use the same CSS selectors; real sites with different layouts need one Extract HTML node each

### Phase 4 — Workflow B: matching and the Treasure Hunt — PARTIALLY VERIFIED
Files created/changed:
- n8n/workflows/B_user_loan_matching.json: 17 nodes. Webhook → Check secret (401) → Respond 202 → Settings (Code: batch_id check, all numbers, Stage 2 and 3 SQL) → Stage 0 all pairs → Stage 1 SQL filter → Stage 2 rules → Find borderline → Plan LLM batches → Nothing to ask? → Call LLM → Parse LLM answers → Save llm_cache → Apply LLM decisions → Record llm_calls and final → Trigger Workflow C
- scripts/trigger_workflow_b.py: sends the webhook like the parser does (`--test`, `--wrong-secret`)
- docs/treasure_hunt.md: updated with the current local run's recorded funnel numbers
- instruction4.md
How to run:
- add `N8N_WEBHOOK_SECRET`, `LLM_API_KEY`, `LLM_MODEL` and `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` to the n8n service, `docker compose up -d n8n`, import the JSON, select the Postgres credential in 7 nodes, then `python scripts/trigger_workflow_b.py <batch_id> --test` (after clicking Execute workflow) or without `--test` when the workflow is Active; follow instruction4.md
Testing already done by the LLM (local Postgres with the real `users.csv` and only 4 made-up products, fake LLM answers, NOT n8n, NOT the real seed data):
- Stage 0/1/2: 40,000 → 15,132 → 15,051 pairs; with fake LLM answers final = 15,030; bad JSON and a failed call were skipped; second run left the same match count (no duplicates); empty-LLM path returns harmless SQL
- These numbers are NOT the real funnel. Do not use them in the README
Acceptance checklist:
- [x] parser-triggered batch has 104,294 match rows
- [x] recorded stats are monotonic: 300,000 > 105,339 >= 104,294 >= 104,294
- [x] wrong secret returns 401
- [x] `docs/treasure_hunt.md` filled from recorded real local stats
- [ ] distinct second authenticated run proved idempotent for this batch
- [ ] workflow exported and committed
Explain-it answers I can give:
- Why SQL first -> comparisons are what a database does best; one set-based query removes most pairs for free, so the paid LLM sees few
- Borderline -> within 5% above an income or score limit, or text-only criteria the columns cannot hold
- Cache by hash and bad JSON -> the same rule and profile share one answer; a bad answer is skipped, pairs stay matched, nothing cached, next run asks again
Things I changed myself in the code (so I know I understand it):
- (developer to fill in, for example the 40% EMI share or the 5% margin in `Settings`)
Open issues left:
- The LLM key/model were present, but `llm_calls` recorded zero; whether the endpoint was contacted is unknown. Avoid another run until external data sharing is approved.
- `Trigger Workflow C` shows an error until phase 5 creates the webhook (expected)
- The CSV has no business age, so the LLM is told to assume text-only criteria are met when the data is missing
- Only 100 new pairs per run reach the LLM; the rest stay matched until later runs judge them

### Phase 5 — Workflow C: notification — EMAIL DELIVERY FAILED
Files created/changed:
- n8n/workflows/C_user_notification.json: 10 nodes. Webhook (`matching-complete`) → Check secret (401) → Respond 202 → Settings (Code: batch_id check, test inboxes, sender, cap, pick SQL) → Pick matches (Postgres) → Build emails (Code: one email per user, test alias round-robin) → Send with SES (continue on error) → Collect sent (Code) → Mark notified (Postgres)
- scripts/trigger_workflow_c.py: sends the webhook (`--test`, `--wrong-secret`)
- instruction5.md
How to run:
- add the 6 env lines to the `n8n` service, `docker compose up -d n8n`, create an AWS credential in n8n, import the JSON, select credentials in 3 nodes, then `python scripts/trigger_workflow_c.py <batch_id> --test` (after clicking Execute workflow); follow instruction5.md
Earlier unit/integration simulation (local Postgres with fake SES, not real email):
- 5 users picked, 5 emails alternating between two aliases, subject "Name, you matched with N loan offer(s)"; with one fake SES failure only 4 users (6 matches) were marked; run 2 picked only the failed user; run 3 picked nobody
Observed n8n run: execution 15 routed five items to the email-failure branch; zero users were marked notified. No email arrival was verified.
Acceptance checklist:
- [ ] a test email arrives and lists the right products
- [ ] successful email count is at most `MAX_DEMO_EMAILS`
- [ ] running C again sends nothing new after successful delivery
- [ ] wrong secret returns 401
- [ ] full pipeline completes with email delivery
- [ ] workflow exported and committed
Explain-it answers I can give:
- Why mark `notified` -> the same user is never emailed twice; marked only after SES accepts, so failures are retried
- Why group per user -> one person can match many products; one email with a table
- Why replace the address -> CSV addresses belong to other people; only own verified aliases are used, the pick query never reads the CSV email
Things I changed myself in the code (so I know I understand it):
- (developer to fill in)
Open issues left:
- Not run in n8n; SES sender and aliases not verified; the n8n AWS SES node field names may differ by n8n version (see instruction5.md troubleshooting)
- Cap is per batch: reset with `UPDATE matches SET notified = false;` before each demo

### Phase 6 — Minimal UI — BROWSER CHECK NOT RUN
Files created/changed:
- ui/index.html: one file, plain HTML and JS. Presign → `PUT` to the presigned URL (`Content-Type: text/csv`, progress bar) → (local mode) `POST /process` → polls `GET /status` every 2 s. Settings: API URL and Local mode
- scripts/local_server.py: local helper (page, `/presign`, `/process`, `/status`), 127.0.0.1:8000
- scripts/set_bucket_cors.py: sets bucket CORS on real S3 (MinIO only prints an explanation)
- instruction6.md
How to run:
- from the repo root `python scripts/local_server.py`, open http://localhost:8000, choose `data/users.csv`, click Upload; follow instruction6.md
Testing already done by the LLM (stand-in Lambda handlers, local Postgres, NO real MinIO, NO real browser):
- local server: index, presign (200 and 400), status (found and 404), process (batch moved to `processed`), bad batch id (400), CORS preflight (204)
- page logic in jsdom with a fake storage `PUT`: no file and `.txt` errors, full success flow ending with `Status: processed (rows 3, valid 2, invalid 1)`
Acceptance checklist:
- [ ] browser upload shows "Uploaded, batch id: ..."
- [ ] page ends with `Status: processed (rows 10000, valid 10000, invalid 0)`
- [ ] `users` has 10,000 rows
- [ ] n8n Executions show B then C and the email arrives (workflows Active)
- [ ] error cases behave as in instruction6.md Step 6
Explain-it answers I can give:
- Why CORS -> page and storage are different origins; the browser needs storage to allow `PUT` in the preflight
- Why PUT bypasses Lambda -> presigned URL lets the browser talk to S3 directly: no API Gateway/Lambda limits, lower cost
- Why a local server -> on AWS API Gateway and the S3 event do those jobs; locally this small server does them with the same Lambda code
Things I changed myself in the code (so I know I understand it):
- (developer to fill in)
Open issues left:
- Not tried through a manual real-browser session; the HTTP upload, parser and status flow was exercised with PowerShell against MinIO
- Presign has no login; file size cannot be capped (presigned PUT)

### Phase 7 — AWS deployment config (serverless.yml) — PACKAGE VERIFIED, DEPLOY NOT TRIED
Files created/changed:
- serverless.yml: python3.11; presign Lambda (HTTP API `GET /presign`, CORS), parser Lambda (300 s, 512 MB); resources: bucket with public-access block, CORS, `uploads/` event, 30-day lifecycle, Lambda permission; IAM limited to `uploads/*` plus SES send; env vars like `.env`; outputs `PresignUrl`, `UploadBucketName`; optional VPC
- package.json (serverless ^3, serverless-python-requirements), requirements-lambda.txt, instruction7.md
How to run:
- `npm install`, create `.env.dev`, check handler names, `npx serverless package` (Docker running); bonus `npx serverless deploy`; follow instruction7.md
Testing run in this workspace (2026-10-25):
- `npm run package` → `✔ Service packaged (37s)` using temporary dummy environment values; no AWS deployment.
- ZIP contains both Lambda handlers, `psycopg2` built for Linux x86_64 Python 3.11, and `dotenv`; no `.pytest_cache`, `.venv`, tests, `node_modules`, or `.git` entries.
- CloudFormation template contains `UploadBucket`, `ParserS3Permission`, `PresignLambdaFunction`, and `ParserLambdaFunction`.
- Initial validation exposed invalid empty VPC config from the supplied file; corrected `off` mode to explicit empty `securityGroupIds` and `subnetIds` arrays.
- The supplied Dockerized pip build stalled without pulling a build image. Config now selects the manylinux x86_64 Python 3.11 wheels directly, which packaged successfully on Windows.
Expected acceptance result (developer must confirm and tick):
- [x] `npm run package` ends with `✔ Service packaged` for the merged supplied config
- [x] `.serverless/cloudformation-template-update-stack.json` has `UploadBucket`, `ParserS3Permission`, both Lambda functions
- [ ] files committed; `.gitignore` has `node_modules/`, `.serverless/`, `.env.*`
- [ ] bonus: deploy works and a browser upload reaches RDS
Explain-it answers I can give:
- S3 Lambda permission -> S3 is another service calling the function; the permission names `s3.amazonaws.com` and one bucket
- IAM limited to `uploads/*` -> least privilege, a leak only reaches one prefix of one bucket
- No VPC by default / RDS -> Lambdas need internet for S3 and n8n; a private RDS needs the VPC switch plus NAT
Things I changed myself in the code (so I know I understand it):
- (developer to fill in)
Open issues left:
- Not deployed; RDS not created. `.env.dev` is absent; provide deployment values before deploy.
- For a real deploy the n8n URL must be public and n8n's Postgres credential must point to the same RDS

## 5. Blockers and open issues

- SES sender and the two test aliases must be verified (needed in phase 5; approval can take time). Status: not started. Done by the developer in the AWS console.
- Collaborator invites (`ujjwalkala-clickpe`, `HarshSrivastav-Dailype`, `ManishBiswal-clickpe`, `tushar-clickpe`): not done. Done by the developer in GitHub, needed before submission.
- Authenticated AWS access: not set up. Only needed to DEPLOY (phase 7 bonus); `serverless package` works without it.
- `data/users.csv` is present with 10,000 rows; the 2026-10-24 integration check used `data/sample_small.csv`.
- Remaining phase 1–7 checklist items are listed in section 4; local phases 1–4 have partial verification, phase 5 email delivery failed, and phase 6 browser upload remains unverified.
- Workflow B's n8n container had an LLM key and model configured. The recorded `llm_calls` count is zero; endpoint contact is not established from that counter.
- n8n container needs the Workflow B and C env values (secret, LLM, SES sender, test emails, cap); check `docker-compose.yml`.
- Both deployed handlers are named `handler`; `serverless.yml` points to `lambdas.presign.handler.handler` and `lambdas.parser.handler.handler`.
- AWS deploy (bonus) needs: AWS access, a unique S3 bucket name, an RDS (or any reachable Postgres), and a public n8n URL.
- Open question: keep the 18 seed products in matching once the crawler works? (decision 14, currently kept)

Known limitations to mention honestly in the README:
- Presigned PUT cannot cap the file size (a presigned POST could).
- The presign endpoint has no login.
- A quoted CSV field containing a line break is not supported.
- The n8n call from the parser is not retried.
- `serverless.yml` / RDS / SES on real AWS may stay untested if there is no AWS access.
- Crawler: only static pages; fields are matched by position, so a missing field shifts the rest.
- The CSV has no business age, so text-only rules like "business at least 2 years old" cannot truly be checked; the LLM assumes they are met.
- At most 100 new pairs per run go to the LLM (cost and free-tier limits); undecided pairs stay matched.
- Emails: at most `MAX_DEMO_EMAILS` users per batch, only to test inboxes; the demo needs a reset of `notified` to repeat.
- `local_server.py` is a demo helper (no login, allows any origin); it is not part of the AWS deployment.
- On AWS the page has no status endpoint (only two Lambdas), so it tells the user to watch n8n.
- `serverless.yml` stores secrets as Lambda environment variables (SSM would be stricter); RDS is documented, not created; Lambdas run outside a VPC by default.

## 6. Funnel numbers for the README (recorded local Workflow B run)

These are the real local stats recorded for the batch below, not the earlier four-product simulation. `llm_calls=0` is only the workflow's recorded count; since an API key was present, do not assume this proves the provider was never contacted.

| Stage | Pairs |
|-------|-------|
| All pairs (users × products) | 300,000 |
| After SQL pre-filter | 105,339 |
| After Code-node rules | 104,294 |
| LLM calls recorded (batched) | 0 |
| Final matches | 104,294 |

## 7. Next action for the next LLM

1. Finish remaining Phase 1–6 acceptance boxes and diagnose why all five Workflow C sends failed.
2. Do not re-run Workflow B or repeat the full UI upload with an LLM key enabled until the developer approves sending loan eligibility attributes to the configured external provider.
3. Phase 8 can now use the recorded real funnel values in section 6 and `docs/treasure_hunt.md`. Write `README.md` and `docs/architecture.md` per project.md Phase 8, and state clearly that RDS is documented, not created.
4. Phase 9 is the demo video. Reset `notified` before recording (`UPDATE matches SET notified = false;`) only after confirming the test inbox setup.
5. Follow project.md section 1 and preserve project names/schema/validators/seed data.
