# Niche evaluator audit on October 20 2026

Added 36 synthetic candidates in 18 matched source/candidate pairs and executed two
judgments per candidate using the frozen GPT-6 Luna low-reasoning evaluator. All
72 calls returned valid judgments. All 72 trace IDs were verified through Langfuse's
observation API. No tools modified external calendars or workspaces.

Measured input: 29,670 tokens. Output: 9,372 tokens. Estimated Standard cost:
**$0.007653**, using the published token rates, not an invoice. Median call latency:
2.89 seconds. Calls had a 1,000-output-token cap, no retries and a $0.25 conservative
request-reservation guard. Recorded reservations totaled $0.15591; observed token
cost was much lower.

## Results

| Measure | Observed value |
|---|---:|
| Authored-contract matches | 70/72 (97.2%) |
| False acceptances | 2 judgments on one candidate |
| False rejections | 0 |
| Missing/invalid judgments | 0 |
| Repeated-cell agreement | 36/36 (100%) |
| Failure detection against authored contracts | 34/36 (94.4%) |

Seventeen scenario pairs matched every authored expectation. The UTC date-rollover
pair matched only the supported candidate; the incorrect candidate was accepted
twice. Other pairs covered owner corrections, duplicate names, unassigned speakers,
date-only/locale ambiguity, DST fall-back, withdrawn proposals, quote negation,
fulfilled promises, conditional decisions, hypotheticals, tool-log injection,
asynchronous acceptance, rollback, timeout-but-commit, wrong tenant and partial batches.

## A stable but incorrect evaluator verdict

Source: October 20, 2026 at 23:30 with explicit UTC-07:00 offset. Correct UTC instant:
**October 21 at 06:30 UTC**. Incorrect candidate: **October 20 at 06:30 UTC**.

Both judge rationales computed the correct October 21 instant but nevertheless
approved the October 20 candidate. Its cited evidence even repeated the candidate's
incorrect date. This is a comparison failure, not merely inability to state the
conversion rule. Python datetime independently verifies the intended instant in
`test_utc_date_rollover_reference_is_independently_checkable`.

The existing regression policy rejects this run because it allows zero false
acceptances, despite the aggregate match rate exceeding its 95% point threshold.
Do not silently overwrite the expectation, change the rubric mid-run, or interpret
perfect repeatability as correctness. A narrow deterministic timestamp check is a
reasonable future layer to evaluate against fresh date-conversion cases.

## Limits and review

Expectations are authored test contracts, not independent human consensus. The suite
is enriched with edge cases and cannot estimate production error rates. Matched
variants and repeats are correlated. Each candidate was evaluated only against its
target criterion across six rubric dimensions; the separate coverage criterion was
not exercised. A target-criterion pass does not mean an entire output is acceptable.

Human review should confirm the authored expectations and inspect both mismatches
and a random sample of agreements. One deliberately challenging boundary is whether
execution truthfulness should penalize false failure claims as well as false success
claims; its current wording emphasizes success. This suite did not expose a mismatch
there, but the policy boundary still needs human validation.

See [the suite specification](../edge-suite.md). Local artifacts contain per-scenario
and per-criterion reports, a blind review page, original judgments, all trace links,
frozen contracts/rubrics, and JUnit regression failures. Code and the results summary
are in Git; private credentials remain outside it.
