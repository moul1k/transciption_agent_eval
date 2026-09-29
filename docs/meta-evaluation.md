# Human-calibrated evaluator workflow

This workflow evaluates the evaluators. The old `benchmark` command remains an
identifier-matching baseline and must not be used as evidence of semantic correctness.
The new `meta` commands never infer human labels from expected agent outputs.

## Start a review

From the repository root after `pip install -e ".[dev]"`:

```powershell
meeting-eval meta prepare data/meta/cases.jsonl data/meta/rubric.json artifacts/pilot/review.json
Start-Process artifacts/pilot/review.html
```

Send the same HTML file to each annotator. It is a standalone offline page with the
meeting, output, tool trace, final state, and explicit pass/fail criteria. It contains
no other reviewers' judgments or model identity. It contains the full input data;
share it only with intended reviewers. Annotators enter their own reviewer IDs and
export JSON. They can resume their own exports. Browser state is not automatically
saved. Partial exports are supported; missing labels remain visible in reports.

Place exports in `artifacts/pilot/submissions/` with distinct filenames. These are
append-only experiment artifacts by convention: retain originals rather than editing
someone else's annotations. Command outputs refuse to overwrite existing files.

## I/O contracts

`cases.jsonl`: one `ReviewCase` per line. Required fields: `id`, `meeting_id`, `split`,
`input`, `output`. Optional `tool_trace` and `final_state` default to empty containers.
`input` uses the existing meeting timestamp/timezone/transcript contract and `output`
uses the existing structured meeting schema. Variants of a meeting must have the same
input and split. Use opaque case IDs in real studies; example IDs are descriptive
for teaching and should not be used for blind studies.

`rubric.json`: `id`, `version`, and unique criteria containing `id`, `question`,
`pass_condition`, and `fail_condition`. Pilot criteria are proposals for human
validation, not established ground truth. Keep snapshots when revising a rubric.

Submission JSON: dataset and rubric hashes, rubric ID/version, evaluator ID,
`kind` (`human`, `judge`, or `adjudication`), timezone-aware `created_at`, judgments,
and optional metadata. Every judgment has `case_id`, `criterion_id`, `verdict`,
`rationale`, and evidence strings. Verdicts: `pass`, `fail`, `insufficient_context`,
`not_applicable`. Evidence strings can be transcript quotes or tool references;
their semantic validity still needs review. Strict schemas reject extra fields,
duplicate judgments, unknown references, and mismatched experiment provenance.

```powershell
meeting-eval meta schema artifacts/pilot/submission-schema.json
meeting-eval meta validate data/meta/cases.jsonl data/meta/rubric.json artifacts/pilot/submissions/reviewer-a.json
```

## Run a judge

The adapter protocol is deliberately provider-neutral: an executable receives one
JSON request on stdin and writes one `Judgment` JSON object to stdout. Requests
include a case, criterion, instructions, and JSON output schema, never human labels.
Wrap your model or classifier in that interface; use environment variables for keys.
The config is a trusted local executable configuration, not untrusted dataset content.

```powershell
meeting-eval meta judge data/meta/cases.jsonl data/meta/rubric.json data/meta/example_judge.json artifacts/pilot/submissions/judge.json --split discovery
```

The supplied adapter deliberately abstains: it tests the protocol without implying
model quality or making paid calls. Config fields: `evaluator_id`, `command` as an
argv array (no shell), and optional per-call `timeout` in seconds. Adapter failures
are recorded in submission metadata, leave missing judgments, and return a nonzero
exit status. Full provider stderr is not persisted. Record model, prompt, and adapter
versions in submission metadata when importing model-generated submissions.

An optional structured-output OpenAI adapter is included. Install the `openai`
extra, set `OPENAI_API_KEY` in your environment, and run the same command using
`data/meta/openai_judge.json` as the config. Choose a model you can access by editing
the config's `--model` argument and evaluator ID. This makes paid calls and sends
the review cases to the configured provider. The adapter has not been live-tested
with credentials; the offline smoke adapter exercises the same process protocol.

## Compare and adjudicate

```powershell
meeting-eval meta compare data/meta/cases.jsonl data/meta/rubric.json artifacts/pilot/submissions artifacts/pilot/report.json --split discovery
```

The production default is `--split test`; examples intentionally belong only to
discovery. Never tune judges on test labels. Split entire meetings, not output rows.

Two or more independent human reviewers must unanimously agree on a binary verdict
to establish a reference. Otherwise the cell is unresolved. An explicit adjudication
submission can resolve it; conflicting adjudications stay unresolved. Preserve the
initial human judgments. This is a data protocol, not an identity verification or
access-control system: the study organizer must enforce independent reviewer IDs.

Reports contain per-criterion and pooled confusion counts with failure as the
positive class, precision, recall among answered cases, all-reference failure
detection rate, false acceptance/rejection, prediction coverage, unresolved cells,
and human pairwise agreement. Undefined ratios are JSON null, never perfect scores.
Failure detection includes a reproducible 95% meeting-cluster bootstrap interval
when at least two meetings are present. With too little data or no failures it is
null. Related output variants stay in the same bootstrap cluster. Small samples
can produce degenerate intervals; these do not establish certainty.
Missing/abstaining predictions reduce coverage and all-reference failure detection.
Not-applicable and unresolved human labels are excluded from binary reference metrics
but explicitly listed. Pooled scores count criterion judgments, not independent meetings.

## Study protocol and limits

Start with open-ended independent human critiques before fixing criteria. Store those
in submission metadata (e.g. `freeform_critiques` keyed by case ID); derive criterion
revisions from the critiques and preserve version history. Do not equate agreement
with proof that a rubric captures user value. Independently assess acceptance and
correction effort. Compare human-only and AI-assisted groups in a randomized study;
this offline interface currently implements independent review only.

The three synthetic cases are a protocol demonstration, not a validated benchmark.
Collect real cases and real human labels before reporting results. Include correct
paraphrases, ID-only changes, omissions, wrong owners, invented deadlines, tentative
events, failed tool calls and duplicates. Controlled mutations expose evaluator
weaknesses but must be human verified before being treated as reference labels.

Model selection, LLM provider adapters, statistical power planning, annotation access
control, and Langfuse transport can evolve independently of these portable contracts.
Use multiple independent meetings and report uncertainty before drawing conclusions
from small differences. Existing Langfuse tracing remains available through the old
agent benchmark; these meta-evaluation artifacts are currently local.
