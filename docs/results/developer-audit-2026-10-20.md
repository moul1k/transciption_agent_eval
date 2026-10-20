# Developer evaluator audit on October 20 2026

Executed 120 real GPT-6 Luna low-reasoning judgments on 34 fresh synthetic cases,
grouped into 14 template-derived scenario groups. All 120 calls returned valid
judgments, and all 120 trace IDs were verified through Langfuse's observation API.
The plan, source hash, fixture/rubric snapshots and expected contracts were saved
before execution. No expected labels were included in model inputs.

Measured usage: 47,250 input tokens, 14,899 output tokens, no reported cached-read or
cache-write tokens. Estimated Standard API cost: **$0.0121745**. This is a token-based
estimate using the rates checked at
https://developers.openai.com/api/docs/models/gpt-6-luna, not an invoice. Median call
latency was 3.18 seconds. Each call was capped at 1,000 output tokens, with no retries.

| Condition | Contract match | Repeat agreement | False acceptances | Binary coverage |
|---|---:|---:|---:|---:|
| Legacy uncertainty wording | 26/36 (72.2%) | 16/18 (88.9%) | 0 | 100% |
| Scoped uncertainty wording | 36/36 (100%) | 18/18 (100%) | 0 | 100% |
| Full tool trace and state | 16/16 (100%) | 8/8 (100%) | 0 | 100% |
| Tool evidence withheld | 16/16 expected abstentions | 8/8 (100%) | 0 | 0% |
| Injection and matched controls | 16/16 (100%) | 8/8 (100%) | 0 | 100% |

## What the results mean

The legacy wording repeatedly penalized omitted tasks under the uncertainty criterion.
All ten mismatches were false rejections against the authored contract that omissions
belong to coverage. The scoped criterion made that boundary explicit and matched all
36 transfer judgments. This demonstrates improved alignment with a specified testing
policy, not proof that the policy is what users want. Unlike the earlier post-hoc
pilot, these examples were newly constructed and the criterion inventory stayed fixed.

With full tool evidence, the judge distinguished actual single-event success from
absent or duplicate events. With evidence withheld, it returned insufficient_context
for every case rather than treating a successful-sounding message as proof of execution.
The latter condition tests appropriate abstention, not hidden-state accuracy.

The injection experiment used four scenario variations and **one attack template**,
each with an unmodified control and two repetitions. None of the attacked candidates
received a passing verdict. This does not establish robustness to optimized attacks,
different injection locations, or broader attack distributions.

## Validity and deployment limits

References are authored synthetic specifications, not independent human consensus.
Variants, templates and repeats are correlated. Only a narrow local event-creation
contract was tested; no real external tool execution occurred. Broad generalization,
human agreement and business usefulness remain unmeasured. A clean contract test is
a development regression signal, not a deployment guarantee.

Independent human annotations remain the next required evidence. Review all ten
mismatches and a random set of matches; independently assess whether the criterion
boundaries match the intended workflow. Test the frozen chosen policy on real traces
and a second tool domain before making production claims.

## Developer integration

The repo now includes a 34-case generic artifact export, deterministic final-state
oracle, JUnit export, selected-condition regression gate and manually triggered live
GitHub Action. The optional Inspect AI task was instantiated with all 34 cases and
executed against a mock model for one sample; malformed output scored incorrect.
The native 120-call run supplies the live Langfuse evidence, not the mock smoke test.

Live results, model rationales, review pages and trace links stay in ignored local
artifacts. See [the design and literature mapping](../developer-evaluation-design.md)
for reproduction commands and framework choices.
