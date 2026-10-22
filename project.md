# project.md — Loan Eligibility Engine (master spec)

> **How to use this file.** Paste `project.md` and `memory.md` into any LLM at the start of a session.
> Tell it: "Continue from the phase marked NEXT in memory.md. Follow the rules in section 1."
> After each phase, update `memory.md` (see its section 0) before switching LLMs.

---

## 0. Goal in one paragraph

Build an automated pipeline: a user uploads a CSV of people (income, credit score, etc.) through a small web page. The file goes straight to S3, a Lambda parses it into PostgreSQL, then tells a self-hosted n8n instance. n8n has three workflows: **A** crawls loan products daily, **B** matches users to products using a multi-stage filter (the "Optimization Treasure Hunt"), **C** emails each matched user through AWS SES (to test inboxes only). Deliverables: private GitHub repo, `serverless.yml`, `docker-compose.yml`, three workflow JSON files, README with diagram, and a 5-10 minute demo video.

Time budget: **about 4 hours of build** plus 45-60 min for the video. Local deployment is accepted by the assignment; AWS deployment is a bonus.

## 1. Rules every LLM must follow (read this first)

1. **Work one phase at a time.** Do not start a phase that memory.md does not mark NEXT.
2. **Never change names, tables, columns, env vars, paths or payloads** defined in sections 3-5 without writing the change into `memory.md` under "Decisions". Other LLMs depend on them.
3. **Comments in simple English.** Every function gets a 1-3 line comment saying *what* it does and *why*. Inline comments only where the logic is not obvious. Short sentences, no jargon.
4. **After every code block, add a "What this does" paragraph** in easy English (3-6 lines): the flow, the key decision, and one thing that could go wrong. This is for the developer to learn from.
5. **Small steps.** Output one file at a time. Keep each file under about 150 lines. If a file would be longer, split it.
6. **No secrets in code.** Read everything from environment variables (section 5). Provide `.env.example` only.
7. **End every phase with:** (a) how to run it, (b) the acceptance test from that phase, (c) 3 "explain it" questions an evaluator might ask, (d) the exact text to paste into `memory.md`.
8. **If something is unclear, make the simplest choice, state it, and log it in memory.md.** Do not ask more than one question at a time.
9. **Do not email addresses from the sample CSV.** Notification emails go only to the developer's own test inbox aliases (section 5, `TEST_EMAIL_*`).

## 2. Architecture

```
Browser (ui/index.html)
   │ 1. GET /presign?filename=users.csv
   ▼
Lambda "presign"  ──▶ returns presigned S3 PUT URL + batch_id (row in upload_batches, status=uploaded)
   │
Browser PUTs the CSV directly to S3  (no API Gateway size/timeout limits)
   │ 2. S3 ObjectCreated event
   ▼
Lambda "parser"  ──▶ streams CSV, validates rows, bulk-upserts into Postgres `users`
   │                  updates upload_batches (processed, counts)
   │ 3. POST /webhook/users-processed  {batch_id, valid_rows, s3_key}   (header X-Webhook-Secret)
   ▼
n8n Workflow B (matching)  ◀── reads users (by batch_id) + loan_products from Postgres
   │   Stage 1 SQL pre-filter → Stage 2 Code-node rules → Stage 3 LLM on borderline only
   │   writes `matches` and `pipeline_stats`
   │ 4. Execute Workflow / POST /webhook/matching-complete {batch_id}
   ▼
n8n Workflow C (notify) ──▶ groups matches per user ──▶ AWS SES ──▶ test inbox

n8n Workflow A (crawler): Cron daily → HTTP Request → HTML Extract → normalize → upsert `loan_products`
```

Local mode: S3 = MinIO or LocalStack, Postgres = Docker container, Lambdas run via `serverless-offline` or a small local runner. AWS mode: real S3, Lambda, RDS (or documented fallback), SES.

## 3. Repository layout (fixed)

```
loan-eligibility-engine/
├── project.md
├── memory.md
├── README.md                      # final docs (phase 8)
├── docker-compose.yml             # n8n + postgres (+ minio/localstack)
├── serverless.yml                 # AWS resources
├── .env.example
├── .gitignore
├── db/
│   ├── schema.sql                 # all tables (section 4)
│   └── seed_products.sql          # 15-20 fallback loan products
├── lambdas/
│   ├── __init__.py                # every folder under lambdas/ has an __init__.py (imports look like: from lambdas.common.db import ...)
│   ├── common/
│   │   ├── db.py                  # get_connection(), shared helpers
│   │   ├── aws_clients.py         # get_s3_client() (MinIO locally, real S3 on AWS)
│   │   └── validators.py          # row validation rules
│   ├── presign/handler.py
│   └── parser/handler.py
├── n8n/workflows/
│   ├── A_loan_product_discovery.json
│   ├── B_user_loan_matching.json
│   └── C_user_notification.json
├── ui/index.html
├── requirements.txt               # boto3, psycopg2-binary, python-dotenv, pytest
├── tests/
│   └── test_validators.py         # unit tests, no database needed
├── scripts/
│   ├── make_sample_csv.py         # tiny CSV for quick tests
│   └── test_upload.py             # uploads a CSV without the UI
├── data/users.csv                 # the sample file from the assignment
└── docs/
    ├── architecture.md            # Mermaid diagram
    └── treasure_hunt.md           # funnel numbers and reasoning
```

## 4. Database contract (fixed — copy exactly into `db/schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS upload_batches (
  batch_id      UUID PRIMARY KEY,
  s3_key        TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'uploaded',  -- uploaded | processing | processed | failed
  total_rows    INT DEFAULT 0,
  valid_rows    INT DEFAULT 0,
  invalid_rows  INT DEFAULT 0,
  error         TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  processed_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS users (
  user_id            TEXT PRIMARY KEY,      -- the CSV gives UUID strings; TEXT keeps parsing simple
  name               TEXT,
  email              TEXT NOT NULL,         -- NOT unique: many users share an email in the sample file
  monthly_income     NUMERIC NOT NULL,
  credit_score       INT NOT NULL,
  employment_status  TEXT NOT NULL,
  age                INT NOT NULL,
  batch_id           UUID REFERENCES upload_batches(batch_id),
  created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_batch ON users(batch_id);

CREATE TABLE IF NOT EXISTS loan_products (
  product_id           SERIAL PRIMARY KEY,
  provider             TEXT NOT NULL,
  product_name         TEXT NOT NULL,
  source_url           TEXT,
  interest_rate        NUMERIC,                 -- yearly percent, e.g. 10.99
  min_monthly_income   NUMERIC,
  min_credit_score     INT,
  max_credit_score     INT,
  min_age              INT,
  max_age              INT,
  allowed_employment   TEXT[],                  -- e.g. {salaried,self-employed}
  eligibility_text     TEXT,                    -- raw criteria text, used for LLM stage
  raw_hash             TEXT,                    -- hash of eligibility_text, for caching
  last_seen_at         TIMESTAMPTZ DEFAULT now(),
  UNIQUE (provider, product_name)
);

CREATE TABLE IF NOT EXISTS matches (
  match_id    SERIAL PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(user_id),
  product_id  INT  NOT NULL REFERENCES loan_products(product_id),
  batch_id    UUID,
  stage       TEXT NOT NULL,                    -- sql | rules | llm
  notified    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, product_id)                  -- makes reruns safe (idempotent)
);

CREATE TABLE IF NOT EXISTS llm_cache (
  rule_hash   TEXT PRIMARY KEY,
  result      JSONB NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_stats (
  id          SERIAL PRIMARY KEY,
  batch_id    UUID,
  stage       TEXT NOT NULL,                    -- all_pairs | after_sql | after_rules | llm_calls | final
  pairs       INT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

**CSV columns (checked against the real `users.csv`):**
`user_id, name, email, monthly_income, credit_score, employment_status, age`

**Sample data profile (measured from the real file):**

| Fact | Value |
|------|-------|
| Rows | 10,000 (plus 1 header line) |
| `user_id` | all unique, UUID strings |
| `email` | only 2,632 unique values, so about 3.8 users share one email. Do **not** make email unique, and do not use it as a key |
| `monthly_income` | whole numbers, 25,000 to 150,000 |
| `credit_score` | 650 to 800 |
| `age` | 22 to 50 |
| `employment_status` | exactly 3 values: `Salaried` (3,389), `Self-Employed` (3,371), `Business` (3,240) |
| Blanks / bad emails | none in the sample, but the validator must still handle them |
| File format | Windows line endings (`\r\n`), possible BOM. Open with `utf-8-sig` and use the `csv` module |

Normalization rule used everywhere (parser, seed data, crawler, SQL): employment is stored **lowercase and trimmed**: `salaried`, `self-employed`, `business`.

## 5. Contracts and configuration (fixed)

**Environment variables** (all in `.env.example`):

```
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
S3_BUCKET, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
S3_ENDPOINT_URL            # only for MinIO/LocalStack, empty on real AWS
N8N_WEBHOOK_URL            # e.g. http://host.docker.internal:5678/webhook/users-processed
N8N_WEBHOOK_SECRET         # shared secret sent in header X-Webhook-Secret
SES_SENDER_EMAIL           # verified sender
TEST_EMAIL_1, TEST_EMAIL_2 # your own Gmail aliases, e.g. name+one@gmail.com
MAX_DEMO_EMAILS            # hard cap on emails per run, default 5 (the CSV has 10,000 users)
LLM_API_KEY, LLM_MODEL     # any free-tier model is fine
```

**Presign Lambda**
- Request: `GET /presign?filename=users.csv`
- Response: `{ "batch_id": "<uuid>", "upload_url": "<presigned PUT url>", "s3_key": "uploads/<batch_id>/users.csv" }`
- Side effect: inserts `upload_batches` row with status `uploaded`.

**Parser Lambda**
- Trigger: S3 `ObjectCreated` on prefix `uploads/`. The `batch_id` is the second path segment of the key.
- Must: set status `processing`, stream the file line by line, validate, upsert in batches of 1000 using `execute_values`, set counts and status `processed`, then POST the webhook.
- Webhook body: `{ "batch_id": "...", "valid_rows": 0, "s3_key": "..." }` with header `X-Webhook-Secret`.
- On failure: status `failed` plus `error` text. Never call the webhook on failure.

**n8n webhooks**
- `POST /webhook/users-processed` → starts Workflow B. First node checks the secret header.
- Workflow B ends by triggering Workflow C with `{ "batch_id": "..." }`.

## 6. Phases

Time boxes add up to about 4 hours. Each phase is independent enough to hand to a new LLM using only `project.md` + `memory.md`.

---

### Phase 0 — Repo and skeleton (0:00-0:20)

**Do**
- Create a private GitHub repo `loan-eligibility-engine`. Invite collaborators: `ujjwalkala-clickpe`, `HarshSrivastav-Dailype`, `ManishBiswal-clickpe`, `tushar-clickpe`.
- Create the folder layout from section 3, `.gitignore` (include `.env`), and `.env.example`.
- **Start the SES verification now** for the sender and both test aliases (it can take time).

**Accept when:** repo exists with the structure, collaborators invited, SES verification emails sent.

**Explain-it questions:** Why is `.env` git-ignored? Why verify SES addresses first?

---

### Phase 1 — Local infrastructure and database (0:20-0:50)

**Build**
- `docker-compose.yml` with services: `postgres` (volume, port 5432), `n8n` (port 5678, volume `n8n_data`, env for basic auth and webhook URL, `extra_hosts: host.docker.internal:host-gateway`), and `minio` (ports 9000/9001) for local S3.
- `db/schema.sql` exactly as section 4. Mount it into Postgres `docker-entrypoint-initdb.d`.
- `db/seed_products.sql`: 15-20 realistic products across 3-4 providers. This is the crawler fallback. Tune thresholds to the **real data range** so the funnel is interesting (users have income 25k-150k, score 650-800, age 22-50):
  - `min_monthly_income` spread across 20000, 25000, 30000, 40000, 50000, 75000, 100000
  - `min_credit_score` spread across 650, 680, 700, 720, 750, 780 (a few with a `max_credit_score`)
  - `min_age` 21-25 and `max_age` 45-60 on some products
  - `allowed_employment` using only `salaried`, `self-employed`, `business` (some salaried-only, some all three, some NULL = any)
  - at least 3 products with an `eligibility_text` containing a rule the columns can't express (for example "Business must be at least 2 years old"), so the LLM stage has real work
  - a few products with thresholds so low that everyone matches, and a few so high that almost nobody does

**Accept when:** `docker compose up -d` works, n8n opens at `localhost:5678`, `\dt` in Postgres shows all 6 tables, seed loads.

**Explain-it:** Why a named volume for n8n? Why does `UNIQUE (user_id, product_id)` matter? How does n8n reach Postgres from inside Docker?

---

### Phase 2 — Ingestion (0:50-1:40)

**Build**
- `lambdas/common/db.py`: connection from env vars, one helper to run a query.
- `lambdas/common/validators.py`: validate one row. Required columns: `user_id, name, email, monthly_income, credit_score, employment_status, age`. Rules: `user_id` not empty, email format, income > 0, credit score 300-900, age 18-100, employment lowercased/trimmed and in `{salaried, self-employed, business}`. `name` may be empty (store NULL). Return `(clean_row, error_or_None)`.
- Parser file handling: decode with `utf-8-sig` (removes a BOM), let `csv.DictReader` handle `\r\n`, and fail the whole batch early with a clear error if a required column is missing from the header. Expect 10,000 rows, so 10 insert batches of 1,000.
- `lambdas/presign/handler.py` per section 5.
- `lambdas/parser/handler.py` per section 5. Stream with `iter_lines`/`csv.DictReader` over the S3 body, never load the whole file. Upsert `ON CONFLICT (user_id) DO UPDATE`. Count valid and invalid rows.
- `scripts/test_upload.py`: calls presign handler (or endpoint), PUTs the CSV, so the pipeline can be tested without the UI.

**Accept when:** uploading `data/users.csv` fills `users`, `upload_batches` shows `processed` with correct counts, uploading the same file twice does not duplicate rows, a bad row is counted as invalid and skipped.

**Explain-it:** Why presigned URL instead of sending the file through API Gateway? Why batch inserts? What happens if S3 delivers the event twice?

---

### Phase 3 — Workflow A: Loan product discovery (1:40-2:10)

**Build in n8n** (export to `n8n/workflows/A_loan_product_discovery.json`)
1. Schedule Trigger (daily) plus a Manual Trigger for demos.
2. Split into 2-3 source sites (static pages only). Use one HTTP Request per site, or one node looping a list of URLs.
3. HTML Extract node (CSS selectors) for product name, rate, and eligibility text.
4. Code node: normalize to the `loan_products` columns (parse "10.5% p.a." to 10.5, "₹25,000" to 25000, map text to `allowed_employment`), compute `raw_hash`.
5. Postgres node: `INSERT ... ON CONFLICT (provider, product_name) DO UPDATE`.
6. If a site fails or returns nothing, the workflow still succeeds because `seed_products.sql` data exists. Add an IF node that logs "0 products from site X".

**Time rule:** if a site fights you for more than 15 minutes, drop it and rely on the seed data plus the other site.

**Accept when:** running the workflow manually leaves at least 10 rows in `loan_products`; running twice does not duplicate.

**Explain-it:** Why upsert? What would you do if a site changes its layout? Why static pages first?

---

### Phase 4 — Workflow B: Matching and the Treasure Hunt (2:10-3:00)

**Build in n8n** (export to `B_user_loan_matching.json`)
1. Webhook node (`users-processed`, POST). IF node checks header `X-Webhook-Secret`; otherwise respond 401.
2. **Stage 0 stats:** Postgres query counting `users(batch) × loan_products` → insert `pipeline_stats(all_pairs)`.
3. **Stage 1 — SQL pre-filter** (one set-based query, no loops):
   ```sql
   INSERT INTO matches (user_id, product_id, batch_id, stage)
   SELECT u.user_id, p.product_id, u.batch_id, 'sql'
   FROM users u
   JOIN loan_products p
     ON u.monthly_income >= COALESCE(p.min_monthly_income, 0)
    AND u.credit_score  >= COALESCE(p.min_credit_score, 0)
    AND u.credit_score  <= COALESCE(p.max_credit_score, 900)
    AND u.age BETWEEN COALESCE(p.min_age, 18) AND COALESCE(p.max_age, 100)
    AND (p.allowed_employment IS NULL OR lower(u.employment_status) = ANY(p.allowed_employment))
   WHERE u.batch_id = $1
   ON CONFLICT (user_id, product_id) DO NOTHING
   RETURNING user_id, product_id;
   ```
   Record `after_sql`.
4. **Stage 2 — Code node rules** that SQL expresses badly: for example, estimated EMI must be at most 40% of income (use a simple EMI formula with a fixed 3-year tenure and a standard amount), and exclude users with too-low income for the product's rate bracket. Remove failing pairs from `matches`. Record `after_rules`.
5. **Stage 3 — LLM for borderline only.** Borderline = pairs within about 5% of a threshold, or products whose `eligibility_text` has criteria not captured in columns. Steps: group by `raw_hash`, check `llm_cache`, batch up to ~20 users per call, ask for strict JSON (`user_id` → eligible true/false), parse safely, store in `llm_cache`, delete rejected pairs. Record `llm_calls`.
6. Record `final`, then trigger Workflow C with `{batch_id}`.

**Accept when:** after an upload, `matches` has rows, `pipeline_stats` shows a shrinking funnel (all_pairs > after_sql >= after_rules >= final), a second run adds no duplicates, a wrong secret gets 401.

**Scale to expect:** 10,000 users × about 20 products = about 200,000 pairs. Stage 1 should cut this by a large factor (since all users have income at least 25k and score at least 650, low-threshold products match nearly everyone and high-threshold ones match few). The numbers vary with your seed data, so record the real ones, do not guess.

**Write `docs/treasure_hunt.md`:** the funnel numbers from a real run, why each stage exists, and the cost saved compared with calling an LLM for every pair.

**Explain-it:** Why SQL first? What makes a pair "borderline"? Why cache by hash? What if the LLM returns invalid JSON?

---

### Phase 5 — Workflow C: Notification (3:00-3:25)

**Build in n8n** (export to `C_user_notification.json`)
1. Trigger: Execute Workflow Trigger (called by B) or Webhook `matching-complete`.
2. Postgres: select `matches` where `notified = false` and `batch_id = $1`, joined with users and products.
3. Code node: group by user, build subject and body (HTML) listing product name, interest rate, provider.
4. **Safety step:** replace the real `email` with a test alias (round-robin `TEST_EMAIL_1`, `TEST_EMAIL_2`). Never send to CSV addresses. The sample file has 10,000 users and most will have matches, so **cap the run at `MAX_DEMO_EMAILS` (default 5)** users, using a `LIMIT` in the SQL. Without the cap you would try to send thousands of emails, which breaks the SES sandbox limits. Use the user's `name` in the greeting ("Hi Dhruv"). Mark `notified = true` only for the users actually emailed.
5. AWS SES node sends the mail.
6. Postgres: mark those matches `notified = true`.

**Accept when:** an email arrives in your Gmail alias inbox listing the right products; running C again sends nothing new.

**Explain-it:** Why mark `notified`? Why group per user? Why must the address be replaced in this assignment?

---

### Phase 6 — Minimal UI (3:25-3:45)

**Build** `ui/index.html`: one file, plain HTML and JS. A file input and an Upload button. On click: call the presign endpoint, PUT the file to `upload_url` with `Content-Type: text/csv`, show "Uploaded, batch id: ...". Optionally poll a status endpoint or just tell the user to watch n8n. Configure CORS on the S3 bucket (and MinIO) to allow PUT from the page.

**Accept when:** choosing `users.csv` in the browser triggers the whole pipeline.

**Explain-it:** Why does the browser need CORS? Why does the PUT bypass Lambda?

---

### Phase 7 — AWS deployment config (3:45-4:00, or after the 4 hours if time is short)

**Build** `serverless.yml`: provider `aws` python3.11, S3 bucket with CORS and an event to the parser Lambda, two Lambda functions, IAM role (S3 read/write on the bucket, RDS network access, SES send), env vars from SSM or `.env`, optional `httpApi` for presign. RDS can be documented rather than created if time is short; state that clearly in the README.

**Accept when:** `serverless package` succeeds (full deploy is a bonus).

---

### Phase 8 — Documentation (about 20-30 min, after the build)

**Build** `README.md` with: overview, Mermaid architecture diagram (from section 2), prerequisites, step-by-step setup (Docker, schema, n8n credentials for Postgres, AWS/SES, importing the three workflow JSONs), how to run a demo, design decisions (event-driven upload, idempotency, treasure hunt funnel with real numbers, crawling strategy and fallback), limitations, and what you would improve.

---

### Phase 9 — Demo video (about 45-60 min)

Script (5-10 minutes): 1) architecture in 1 minute using the diagram, 2) walk through each workflow node by node, 3) live run: upload CSV in the UI, show DB rows, show the n8n execution, show `pipeline_stats`, 4) show the received email, 5) short wrap-up. Rehearse once. Record in one take.

---

## 7. Handoff prompt (copy into a new LLM)

```
You are continuing a project. Read project.md and memory.md fully.
Do only the phase marked NEXT in memory.md.
Follow section 1 rules: simple English comments, a "What this does" paragraph after every
code block, one file at a time, no renaming of anything defined in project.md.
At the end give me: how to run, the acceptance test, 3 explain-it questions,
and the exact text to paste into memory.md.
```

## 8. Final checklist before submitting

- [ ] Private repo with all 4 collaborators invited
- [ ] `serverless.yml`, `docker-compose.yml`, 3 workflow JSONs committed
- [ ] README with diagram, setup, design decisions, treasure hunt numbers
- [ ] Video shows workflows, live run, and a received email
- [ ] No secrets committed, no emails sent to CSV addresses
- [ ] You can explain every node and every file without reading it
