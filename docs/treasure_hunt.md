# Optimization Treasure Hunt: local Workflow B results

Run date: 2026-10-25

Batch: `d36e65da-f86d-4aa0-b48c-6397bdb8814f` (10,000 users)
Products: 30 (18 seeded + 12 discovered from the two mock lenders)

## Funnel from the local run

| Stage | Pairs / calls | Share of all pairs | Change from previous pair stage |
|---|---:|---:|---:|
| All user × product pairs (`all_pairs`) | 300,000 | 100.00% | — |
| After SQL pre-filter (`after_sql`) | 105,339 | 35.11% | 194,661 removed (64.89%) |
| After EMI and rate rules (`after_rules`) | 104,294 | 34.76% | 1,045 removed |
| LLM calls recorded (`llm_calls`) | 0 calls | n/a | No calls recorded by Workflow B |
| Final matches (`final`) | 104,294 | 34.76% | — |

There were **40,986 borderline pairs** after deterministic rules. Workflow B recorded no LLM calls and no cached answers for this batch. The workflow's `LLM_API_KEY` was present in the n8n container, so this result must not be described as proof that the key was unset or that no request was attempted. `pipeline_stats.llm_calls` records zero, meaning no calls were recorded as completed by the workflow. The final count leaves the borderline pairs matched; it does not mean their hidden criteria were resolved.

The parser-created batch triggered Workflow B. A wrong webhook secret returned `401`. The logged funnel stages were monotonic. The batch contains 104,294 matches and 9,919 distinct users with a match. A separate query for this batch found no duplicate `(user_id, product_id)` pairs.

## Why each stage exists

1. **Stage 0 — all pairs.** Establishes the unfiltered baseline: 10,000 users × 30 products.
2. **Stage 1 — SQL.** Postgres checks income, credit score, age, and employment together in one set-based query. It removed 64.89% of potential pairs without moving individual rows through n8n.
3. **Stage 2 — rules.** A fixed ₹300,000 loan over 36 months must have an estimated EMI at or below 40% of monthly income. Products with interest rates at or below 10% also require income of at least ₹40,000. These deterministic rules removed 1,045 more pairs.
4. **Stage 3 — borderline LLM review.** Candidates are within 5% of an income or credit-score threshold, or their eligibility text contains a criterion that is not represented in columns. The workflow groups by rule hash, checks `llm_cache`, and can send at most 20 users per request (up to 100 uncached pairs per run). This run recorded zero LLM calls, so it did not establish LLM-based eligibility judgments.

## LLM call comparison

Assuming one request can judge 20 pairs, calling an LLM for every pair in this batch would require:

```text
300,000 pairs / 20 per request = 15,000 calls
Workflow B calls recorded      =      0 calls
```

This is a call-count comparison only. The actual run did not resolve the 40,986 borderline pairs. Do not re-run Workflow B with the LLM key enabled unless the data transmission to the configured external provider is approved.

## Notification result

Workflow C execution 15 completed with five items routed through its email-failure branch. The batch has zero matches marked `notified`; no successful email delivery was verified. Do not claim that an email arrived. The workflow is configured to send to test inboxes rather than CSV addresses, but Phase 5's delivery checklist failed.

## Honest limits

- The CSV has no business-age field. The LLM prompt tells the model to assume a criterion is met when the needed data is missing; it can only reject based on fields provided.
- At most 100 uncached borderline pairs are selected per run. Pairs beyond that cap remain matched for a later run.
- Workflow C is implemented and ran, but its five test-email sends failed; delivery and idempotent second-send behavior are not verified.
- The 30 products include local mock lender pages and seed data, not live bank offers.
