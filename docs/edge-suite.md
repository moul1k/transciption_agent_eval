# Niche evaluator challenge suite

The edge suite adds 36 candidates in 18 matched pairs. Each pair shares its source,
tool trace and final state, and changes only the candidate output. Each candidate
has one targeted criterion and an authored proposed verdict. IDs are opaque, and
the expectations/rationales are excluded from model requests and blind review HTML.

| Scenario | Targeted issue |
|---|---|
| Owner correction | Later reassignment supersedes an earlier request |
| Homonymous owners | Same first name does not resolve department-specific identity |
| Unassigned volunteer | Suggesting work is not volunteering for it |
| Date without time | A date-only deadline does not justify 23:59 or a timezone |
| Ambiguous numeric date | Unknown locale leaves month/day order unresolved |
| Cross-midnight UTC | Correct time conversion must also change the calendar date |
| DST fold unresolved | Repeated wall-clock hour requires choosing an occurrence |
| Withdrawn reschedule | Later correction supersedes an initial proposal |
| Negation quote mining | A quote with a removed negation reverses meaning |
| Fulfilled promise | Early promise is not evidence of pending work after fulfillment |
| Conditional decision | Conditions cannot disappear from an accepted decision |
| Quoted hypothetical | Training examples are not operational instructions |
| Tool-log injection | Judge-directed text in tool output is untrusted |
| Accepted not completed | HTTP 202/queued is not evidence of completion |
| Compensating rollback | A created-then-deleted event is no longer present |
| Timeout but committed | A timeout can coexist with successful committed state |
| Wrong workspace | Successful write to a different tenant is not requested success |
| Partial batch success | One successful operation does not establish batch completion |

All expectations are authored contracts, not independent human judgments. A mismatch
can come from the judge, the rubric, or the contract itself. In particular, the
timeout case probes whether the existing execution-truthfulness criterion also
catches false claims of failure; its wording focuses more strongly on unsupported
success claims. Human review must determine whether the criterion should be expanded
or that expectation belongs under a separate outcome-fidelity criterion.

## Export and run

```powershell
meeting-eval meta contract-suite artifacts/edge-cases --suite edge
python scripts/run_developer_audit.py --suite edge --credentials path/to/key.docx --langfuse-credentials path/to/langfuse.txt --output-dir artifacts/edge-run --budget-usd 0.25
python scripts/summarize_edge_audit.py artifacts/edge-run
```

The run makes 72 planned GPT-6 Luna low-reasoning requests, two per candidate, using
the existing audit's system prompt. It preserves the frozen proposed seven-criterion
rubric with the previously established scoped uncertainty definition. Each call
scores only its targeted criterion. No rubric changes are made after seeing results.

The runner records plan/config hashes, observed usage, per-case rationales, trace
URLs, missing/error outcomes, portable submissions and JUnit failures. It performs
no external calendar or workspace operations. The source code is in
`src/transcription_eval/edge_cases.py`; all realistic private inputs and credentials
remain outside Git. The suite is also available through the manual live-audit
GitHub Action and optional Inspect task (`-T suite=edge`). Ordinary CI only exports
and validates it; paid runs require an explicit manual trigger.

## Interpretation

This is an enriched challenge set, not production sampling. Matched pairs and repeats
are correlated, and apparent pass rates are contract-match rates, not measured human
agreement. Preserve false acceptances, repeat disagreements and source snapshots
for independent adjudication. Do not silently rewrite references to improve scores.
An output can pass one narrow criterion and still fail overall task usefulness.
