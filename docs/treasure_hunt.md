# Optimization Treasure Hunt: real funnel results

Run date: 2026-10-22

Batch: `cd58f598-f784-43e4-ab7f-9775259d339c` (10,000 users)
Products: 30 (18 seeded + 12 discovered from the two mock lenders)

## Funnel from the real run

| Stage | Pairs / calls | Share of all pairs | Change from previous pair stage |
|---|---:|---:|---:|
| All user × product pairs (`all_pairs`) | 300,000 | 100.00% | — |
| After SQL pre-filter (`after_sql`) | 105,339 | 35.11% | 194,661 removed (64.89%) |
| After EMI and rate rules (`after_rules`) | 104,294 | 34.76% | 1,045 removed |
| LLM calls (`llm_calls`) | 0 calls | n/a | LLM key was not configured |
| Final matches (`final`) | 104,294 | 34.76% | — |

There were **40,986 borderline pairs** after the deterministic rules. None were sent to an LLM and there were no cache answers because `LLM_API_KEY` is unset. Workflow B kept those undecided pairs matched (benefit of the doubt). The zero-call result means this run did not make an LLM eligibility judgment; it is a safe local run of the full funnel, not a claim that the hidden criteria were resolved.

Authentication was also checked: the valid webhook secret returned `202`; the wrong secret returned `401`. A second valid run left **104,294** matches for the batch and created no duplicate `(user_id, product_id)` pairs.

## Why each stage exists

1. **Stage 0 — all pairs.** Establishes the unfiltered baseline: 10,000 users × 30 products.
2. **Stage 1 — SQL.** Postgres checks income, credit score, age, and employment together in one set-based query. It removed 64.89% of potential pairs without moving individual rows through n8n.
3. **Stage 2 — rules.** A fixed ₹300,000 loan over 36 months must have an estimated EMI at or below 40% of monthly income. Products with interest rates at or below 10% also require income of at least ₹40,000. These deterministic rules removed 1,045 more pairs.
4. **Stage 3 — borderline LLM review.** Candidates are within 5% of an income or credit-score threshold, or their eligibility text contains a criterion that is not represented in columns. The workflow groups by rule hash, checks `llm_cache`, and would send at most 20 users per request (up to 100 uncached pairs per run). With no key configured, it skips requests, leaves unresolved matches in place, and records zero calls.

## LLM call comparison

Assuming one request can judge 20 pairs, calling an LLM for every pair in this batch would require:

```text
300,000 pairs / 20 per request = 15,000 calls
Workflow B in this run             =      0 calls
Call reduction                     = 15,000 calls (100%)
```

This is a call-count comparison only. The actual zero-call run did not judge the 40,986 borderline pairs. To enable that review, set `LLM_API_KEY` and `LLM_MODEL` in `.env`, recreate n8n, and rerun the batch. The workflow then uses the configured OpenAI-compatible endpoint and caches valid JSON decisions by rule hash plus user profile.

## Honest limits

- The CSV has no business-age field. The LLM prompt tells the model to assume a criterion is met when the needed data is missing; it can only reject based on fields provided.
- At most 100 uncached borderline pairs are selected per run. Pairs beyond that cap remain matched for a later run.
- Workflow C is not implemented yet. The final node attempts its `matching-complete` webhook and continues if it is unavailable; implement Workflow C in Phase 5.
- The 30 products include local mock lender pages and seed data, not live bank offers.
