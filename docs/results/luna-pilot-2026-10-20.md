# GPT-6 Luna discovery pilot on October 20 2026

Executed 72 real `gpt-6-luna` Responses API calls with Standard processing, explicit
output caps, zero automatic retries, and Langfuse tracing. All calls succeeded and
all 72 trace IDs were confirmed through the Langfuse observation API. API keys,
transcript contents, candidates, and per-call trace links remain outside Git under
local ignored artifacts.

Measured usage: 122,518 input tokens, 9,092 output tokens, 94,510 reported cache-write
tokens, and no cached-read tokens. Using the published Standard rates of $0.10/M
input, $0.125/M cache write and $0.50/M output gives an estimated $0.01916055 total.
This is a token-based estimate, not an invoice. Median latency across all calls was
2.04 seconds. Rates were checked at
https://developers.openai.com/api/docs/models/gpt-6-luna on the execution date.

## Experiments

1. One real meeting extraction (`low`, 5,000 output-token cap), followed by seven
   independent criterion calls (`low`, 1,600 tokens per call). The extraction took
   8.63 seconds and produced six tasks, two calendar entries, two decisions and two
   follow-ups. The judge flagged coverage because deliverables were omitted and
   passed the other six proposed criteria. These are model judgments, pending humans.
2. One synthetic challenge meeting, four output variants, three criteria, two
   repetitions at each of `none` and `low`: 48 judgments. The variants include an
   ID-only change, an unsupported task replacement preserving its ID, and omission
   of a task. Expectations are proposed, not human-validated reference labels.
3. A post-hoc scope ablation on the same four variants with only the uncertainty
   criterion: two repetitions at each effort, 16 judgments. The wording explicitly
   assigns omissions to coverage and unsupported task meanings to grounding.

| Setting | Repeated-cell agreement | Binary pair coverage | ID invariance checks | Targeted detection checks | Median challenge judgment latency |
|---|---:|---:|---:|---:|---:|
| Original rubric, none | 10/12 (83.3%) | 100% | 6/6 | 4/4 | 1.76 s |
| Original rubric, low | 11/12 (91.7%) | 100% | 6/6 | 4/4 | 1.92 s |
| Scoped criterion, none | 4/4 (100%) | 100% | Not measured | Not measured | See local per-call records |
| Scoped criterion, low | 4/4 (100%) | 100% | Not measured | Not measured | See local per-call records |

The original uncertainty criterion sometimes penalized omissions or unsupported task
meanings and sometimes treated them as out of scope. This is a concrete example of
criterion boundaries affecting repeatability. A stable judge can still be wrong;
the post-hoc ablation does not establish semantic correctness or generalization.
Wording and rubric context both changed, and only one synthetic meeting was used.

## Remaining evidence

No independent human reference labels were collected in this run, so human-agreement
precision/recall and evaluator accuracy are unavailable. The same model family
generated and judged the real output. Collect independent annotations and test the
scoped criterion on fresh meetings before selecting an evaluator or claiming an
improvement. Preserve original labels and rubric versions.

## Reproduction

Install `.[openai,langfuse,dev]`, then run from the repository root:

```powershell
python scripts/run_luna_pilot.py --credentials path/to/openai-key.docx --langfuse-credentials path/to/langfuse-keys.txt --transcript path/to/meeting.txt --output-dir artifacts/new-pilot --budget-usd 0.25
python scripts/run_luna_pilot.py --credentials path/to/openai-key.docx --langfuse-credentials path/to/langfuse-keys.txt --transcript path/to/meeting.txt --output-dir artifacts/new-ablation --ablation-source artifacts/new-pilot --budget-usd 0.08
python scripts/summarize_luna_pilot.py artifacts/new-pilot artifacts/new-ablation
```

Model outputs are stochastic, so reruns need not reproduce the numerical results.
The ablation's examples are reused discovery data. The runner records calls and
usage locally, reserves a conservative per-request cost estimate before each call,
and stops on authentication/quota failures. Credentials from DOCX are read as data
and never copied into artifacts. No external account-management actions are taken.
