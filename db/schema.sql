-- db/schema.sql
-- Creates all the tables for the Loan Eligibility Engine.
-- Postgres runs this file automatically the first time the database starts.
-- "IF NOT EXISTS" means running it again will not break anything.


-- 1) upload_batches
-- One row per CSV upload. It tells us where the upload is in its journey:
-- uploaded -> processing -> processed (or failed).
CREATE TABLE IF NOT EXISTS upload_batches (
  batch_id      UUID PRIMARY KEY,
  s3_key        TEXT NOT NULL,                      -- where the file sits in the bucket
  status        TEXT NOT NULL DEFAULT 'uploaded',   -- uploaded | processing | processed | failed
  total_rows    INT DEFAULT 0,                      -- all data rows we read
  valid_rows    INT DEFAULT 0,                      -- rows that passed checks and were saved
  invalid_rows  INT DEFAULT 0,                      -- rows we skipped because they were bad
  error         TEXT,                               -- the reason, if status = failed
  created_at    TIMESTAMPTZ DEFAULT now(),
  processed_at  TIMESTAMPTZ
);


-- 2) users
-- One row per person from the CSV.
CREATE TABLE IF NOT EXISTS users (
  user_id            TEXT PRIMARY KEY,   -- the CSV gives UUID text; TEXT keeps parsing simple
  name               TEXT,
  email              TEXT NOT NULL,      -- NOT unique: many users share one email in the sample file
  monthly_income     NUMERIC NOT NULL,
  credit_score       INT NOT NULL,
  employment_status  TEXT NOT NULL,      -- stored lowercase: salaried | self-employed | business
  age                INT NOT NULL,
  batch_id           UUID REFERENCES upload_batches(batch_id),
  created_at         TIMESTAMPTZ DEFAULT now()
);

-- Workflow B looks users up by batch, so this index makes that fast.
CREATE INDEX IF NOT EXISTS idx_users_batch ON users(batch_id);


-- 3) loan_products
-- One row per loan product found by the crawler (or loaded from the seed file).
CREATE TABLE IF NOT EXISTS loan_products (
  product_id           SERIAL PRIMARY KEY,
  provider             TEXT NOT NULL,           -- the bank or lender name
  product_name         TEXT NOT NULL,
  source_url           TEXT,                    -- the page it came from
  interest_rate        NUMERIC,                 -- yearly percent, e.g. 10.99
  min_monthly_income   NUMERIC,
  min_credit_score     INT,
  max_credit_score     INT,
  min_age              INT,
  max_age              INT,
  allowed_employment   TEXT[],                  -- e.g. {salaried,self-employed}; NULL means any
  eligibility_text     TEXT,                    -- the raw rules as text, used by the LLM stage
  raw_hash             TEXT,                    -- fingerprint of eligibility_text, used for caching
  last_seen_at         TIMESTAMPTZ DEFAULT now(),
  UNIQUE (provider, product_name)               -- lets the crawler "upsert" without duplicates
);


-- 4) matches
-- One row = "this user may qualify for this product".
CREATE TABLE IF NOT EXISTS matches (
  match_id    SERIAL PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(user_id),
  product_id  INT  NOT NULL REFERENCES loan_products(product_id),
  batch_id    UUID,
  stage       TEXT NOT NULL,                    -- which stage created it: sql | rules | llm
  notified    BOOLEAN DEFAULT FALSE,            -- becomes true after we email the user
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, product_id)                  -- the same pair can never be stored twice
);

-- Workflow C looks for matches that are not yet emailed.
CREATE INDEX IF NOT EXISTS idx_matches_batch_notified ON matches(batch_id, notified);


-- 5) llm_cache
-- Remembers answers from the LLM so we never pay for the same question twice.
CREATE TABLE IF NOT EXISTS llm_cache (
  rule_hash   TEXT PRIMARY KEY,
  result      JSONB NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);


-- 6) pipeline_stats
-- Records how many user/product pairs are left after each filtering stage.
-- We use these numbers in the README to prove the optimization works.
CREATE TABLE IF NOT EXISTS pipeline_stats (
  id          SERIAL PRIMARY KEY,
  batch_id    UUID,
  stage       TEXT NOT NULL,                    -- all_pairs | after_sql | after_rules | llm_calls | final
  pairs       INT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);
