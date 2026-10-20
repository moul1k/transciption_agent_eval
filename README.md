# Meeting Agent Evaluation Lab

An eval-first test bed for an agent that turns meeting transcripts into action items,
calendar events, decisions, and follow-ups. The agent is intentionally small; the
benchmarking loop is the product.

## Evaluate the evaluators

The primary workflow now supports independent human annotation and evaluator
comparison. See [the complete protocol and I/O guide](docs/meta-evaluation.md).

For the study design, controlled challenges, repeated runs, and mentor-facing reports,
see [the benchmarking study protocol](docs/study-protocol.md). Run a complete offline
demonstration with explicitly synthetic labels:

```bash
meeting-eval meta demo artifacts/demo-01
```

Open `artifacts/demo-01/report.html`. The demo demonstrates an always-pass judge that
is invariant to ID changes but misses injected errors. It is not a human-validated
model benchmark. Real comparison runs now also export HTML reports with a review
queue, human critiques and annotation completion.

An actual low-cost GPT-6 Luna discovery pilot has also been executed:
[October 20 results and limitations](docs/results/luna-pilot-2026-10-20.md).
It includes real transcript extraction, controlled challenges, repeated judgments,
and a post-hoc rubric scope ablation, with all traces verified in Langfuse.

```bash
meeting-eval meta prepare data/meta/cases.jsonl data/meta/rubric.json artifacts/pilot/review.json
meeting-eval meta schema artifacts/pilot/submission-schema.json
```

Open the generated `review.html`, collect independent reviewer exports, run a judge
adapter, and compare judgments against human consensus or explicit adjudication.
The example judge is a protocol smoke test that abstains; no real human labels are
bundled. The legacy benchmark below uses exact IDs, not semantic matching, and its
"no_hallucinations" score is only an ID-set check. Do not interpret it as validated
agent quality. Its known defects are baseline counterexamples for meta-evaluation.

The design follows [Hamel Husain's eval workflow](https://hamel.dev/blog/posts/evals/):
split behavior into scoped scenarios, run cheap assertions on every change, inspect
traces, and only then add human/LLM judges.

## What is measured

| Feature | Scenarios | Deterministic metrics |
|---|---|---|
| Action items | explicit owner/due date, missing owner, no action | precision, recall, owner and due-date accuracy |
| Calendar | explicit time, relative date, tentative event, no event | precision, recall, start-time accuracy |
| Decisions | explicit decision, rejected proposal | precision and recall |
| Safety | ambiguity, prompt injection, unsupported inference | hallucination count, schema validity |

Every expected object has a stable ID. This makes failures attributable to a feature
and scenario rather than hiding them inside one overall score.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
meeting-eval benchmark --provider fixture
```

The fixture provider copies the expected result and exists to validate the harness.
To measure a real model:

```bash
pip install -e ".[openai,langfuse]"
set OPENAI_API_KEY=...
meeting-eval benchmark --provider openai --model gpt-4.1-mini
```

Reports are written to `artifacts/runs/<timestamp>.json`; the summary includes the
git SHA, prompt version, model, latency, per-case failures, and aggregate scores.

## Langfuse tracing

Real transcript extraction now supports traced OpenAI calls and a linked human-review
packet. Credentials are loaded at runtime from environment variables or an explicitly
selected credentials text file; they are never copied into artifacts.

```powershell
# Set OPENAI_API_KEY in your environment, or include it in your local credentials file.
meeting-eval extract path/to/transcript.txt artifacts/live-run --langfuse --credentials path/to/keys.txt
```

Use a new output directory for each run. The result includes `candidate.json`,
`cases.jsonl`, `review.html`, and `run.json` containing the Langfuse trace URL and
prompt hash. Tracing uploads the input and output to your configured Langfuse project.
Unknown meeting dates and timezones remain null. The default extraction model is
`gpt-4.1-mini`; override it with `--model`.

The bundled OpenAI judge can also trace each criterion evaluation:

```powershell
meeting-eval meta judge artifacts/live-run/cases.jsonl data/meta/rubric.json data/meta/openai_judge.json artifacts/live-run/judge.json --split discovery --langfuse --credentials path/to/keys.txt
```

Langfuse captures generations (prompt, response, model, usage) nested within extraction
or evaluator observations. Explicit flushing delivers queued observations before exit.
Human annotations stay in the local review workflow; they are not uploaded automatically.

Set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`, then add
`--langfuse`. Each benchmark item becomes a trace and deterministic scores are
attached to the experiment.

```bash
meeting-eval benchmark --provider openai --langfuse --run-name prompt-v2
meeting-eval seed-langfuse --dataset meeting-agent-v1
```

## Workflow

1. Add a real or synthetic failure to `data/benchmark.jsonl`.
2. Assign a `feature` and narrow `scenario`; write only observable expectations.
3. Reproduce it with `meeting-eval benchmark` and inspect the trace.
4. Change the prompt/model/tool logic, then compare run artifacts.
5. Label sampled traces `good`/`bad` with a critique. Calibrate any model judge
   against those labels using precision and recall, not raw agreement.

CI runs deterministic tests and a fixture smoke benchmark. Real-model benchmarks
should run on a schedule or before releases because they cost money and can vary.

## Data policy

Meeting transcripts can contain sensitive data. The sample dataset is synthetic.
Before tracing production inputs, obtain consent, redact secrets/PII, define retention,
and verify the configured Langfuse region or self-hosted deployment.
