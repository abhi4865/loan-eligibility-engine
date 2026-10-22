-- db/seed_products.sql
-- Fallback loan products, so the pipeline works even if the crawler (Workflow A)
-- fails. The lender names are made up on purpose; this is practice data.
--
-- The thresholds are tuned to the real users.csv:
--   income 25,000 to 150,000 | credit score 650 to 800 | age 22 to 50
-- so some products match almost everyone, some match few, and some match nobody.
--
-- Column order in every row below:
--   provider, product_name, source_url, interest_rate,
--   min_monthly_income, min_credit_score, max_credit_score,
--   min_age, max_age, allowed_employment, eligibility_text
--
-- NULL means "no limit" for that rule.
-- Rows 6, 7, 11 and 17 have extra rules in eligibility_text that the columns
-- cannot express. These are the ones the LLM stage will check later.

INSERT INTO loan_products (
  provider, product_name, source_url, interest_rate,
  min_monthly_income, min_credit_score, max_credit_score,
  min_age, max_age, allowed_employment, eligibility_text, raw_hash
)
SELECT
  v.provider, v.product_name, v.source_url, v.interest_rate,
  v.min_monthly_income, v.min_credit_score, v.max_credit_score,
  v.min_age, v.max_age, v.allowed_employment, v.eligibility_text,
  md5(v.eligibility_text)          -- fingerprint used later for LLM caching
FROM (VALUES
  -- ---------------- Alpha Bank ----------------
  ('Alpha Bank', 'Alpha Quick Personal Loan', 'seed', 14.50::numeric,
   20000::numeric, 650, NULL::int, 21, 60,
   ARRAY['salaried','self-employed','business']::text[],
   'Open to salaried, self-employed and business applicants. Minimum income 20,000 per month, credit score 650 or more, age 21 to 60.'),

  ('Alpha Bank', 'Alpha Prime Personal Loan', 'seed', 10.99,
   40000, 720, NULL, 23, 58,
   ARRAY['salaried','self-employed']::text[],
   'For salaried and self-employed applicants. Minimum income 40,000 per month, credit score 720 or more, age 23 to 58.'),

  ('Alpha Bank', 'Alpha Elite Loan', 'seed', 9.99,
   100000, 780, NULL, 25, 55,
   ARRAY['salaried']::text[],
   'Premium loan for salaried applicants only. Minimum income 100,000 per month, credit score 780 or more, age 25 to 55.'),

  -- ---------------- Beta Finance ----------------
  ('Beta Finance', 'Beta Starter Loan', 'seed', 16.00,
   25000, 650, 700, 21, 50,
   ARRAY['salaried','self-employed','business']::text[],
   'Entry-level loan for credit scores between 650 and 700. Minimum income 25,000 per month, age 21 to 50.'),

  ('Beta Finance', 'Beta Flex Loan', 'seed', 13.25,
   30000, 680, NULL, 22, 60,
   ARRAY['salaried','self-employed','business']::text[],
   'Flexible loan for all employment types. Minimum income 30,000 per month, credit score 680 or more, age 22 to 60.'),

  ('Beta Finance', 'Beta Business Boost', 'seed', 12.50,
   50000, 700, NULL, 25, 60,
   ARRAY['self-employed','business']::text[],
   'For self-employed and business owners. Minimum income 50,000 per month, credit score 700 or more. The business must be at least 2 years old.'),

  ('Beta Finance', 'Beta Salary Advance', 'seed', 15.50,
   25000, 650, NULL, 22, 45,
   ARRAY['salaried']::text[],
   'For salaried applicants aged 22 to 45. Minimum income 25,000 per month. The applicant must have worked at the current job for at least 6 months.'),

  -- ---------------- Gamma Credit ----------------
  ('Gamma Credit', 'Gamma Easy Loan', 'seed', 18.00,
   25000, 650, 680, 21, 65,
   ARRAY['salaried','self-employed','business']::text[],
   'High-approval loan for credit scores between 650 and 680. Minimum income 25,000 per month, age 21 to 65.'),

  ('Gamma Credit', 'Gamma Smart Loan', 'seed', 11.75,
   50000, 700, NULL, 24, 58,
   ARRAY['salaried','self-employed','business']::text[],
   'For all employment types. Minimum income 50,000 per month, credit score 700 or more, age 24 to 58.'),

  ('Gamma Credit', 'Gamma Premium Loan', 'seed', 10.25,
   75000, 750, NULL, 25, 55,
   ARRAY['salaried','business']::text[],
   'For salaried and business applicants. Minimum income 75,000 per month, credit score 750 or more, age 25 to 55.'),

  ('Gamma Credit', 'Gamma Self-Made Loan', 'seed', 13.00,
   40000, 690, NULL, 25, 60,
   ARRAY['self-employed']::text[],
   'For self-employed applicants. Minimum income 40,000 per month, credit score 690 or more. The applicant must have filed income tax returns for the last 2 years.'),

  -- ---------------- Delta NBFC ----------------
  ('Delta NBFC', 'Delta Instant Cash', 'seed', 19.50,
   20000, 650, 720, 21, 45,
   ARRAY['salaried','self-employed','business']::text[],
   'Small instant loan for credit scores between 650 and 720. Minimum income 20,000 per month, age 21 to 45.'),

  -- No limits at all: every user should match this one (good for testing).
  ('Delta NBFC', 'Delta Open Door Loan', 'seed', 21.00,
   0, 300, NULL, 18, 100, NULL::text[],
   'Open to everyone. No minimum income, no minimum credit score, any age from 18.'),

  ('Delta NBFC', 'Delta Salary Plus', 'seed', 11.50,
   60000, 730, NULL, 26, 55,
   ARRAY['salaried']::text[],
   'For salaried applicants. Minimum income 60,000 per month, credit score 730 or more, age 26 to 55.'),

  -- Very strict: almost nobody should match this one.
  ('Delta NBFC', 'Delta Mega Loan', 'seed', 9.50,
   125000, 790, NULL, 28, 50,
   ARRAY['salaried','self-employed','business']::text[],
   'Very high limits. Minimum income 125,000 per month, credit score 790 or more, age 28 to 50.'),

  ('Delta NBFC', 'Delta Young Professional', 'seed', 12.99,
   30000, 680, NULL, 22, 30,
   ARRAY['salaried']::text[],
   'For young salaried applicants aged 22 to 30. Minimum income 30,000 per month, credit score 680 or more.'),

  -- ---------------- Alpha Bank (business) ----------------
  ('Alpha Bank', 'Alpha Business Growth Loan', 'seed', 11.00,
   75000, 720, NULL, 35, 60,
   ARRAY['business']::text[],
   'For business owners aged 35 to 60. Minimum income 75,000 per month, credit score 720 or more. Applicants must provide proof of annual business turnover.'),

  -- ---------------- Beta Finance (premium) ----------------
  ('Beta Finance', 'Beta Premium Plus', 'seed', 10.75,
   90000, 760, NULL, 25, 55,
   ARRAY['salaried','self-employed','business']::text[],
   'Premium loan for all employment types. Minimum income 90,000 per month, credit score 760 or more, age 25 to 55.')
) AS v(
  provider, product_name, source_url, interest_rate,
  min_monthly_income, min_credit_score, max_credit_score,
  min_age, max_age, allowed_employment, eligibility_text
)
-- If a product with the same provider + name already exists, skip it.
ON CONFLICT (provider, product_name) DO NOTHING;
