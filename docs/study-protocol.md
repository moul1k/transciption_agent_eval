# Evaluator benchmarking study: pilot protocol

## Research questions and operational measures

| Question | Experiment | Primary evidence |
|---|---|---|
| Does a judge detect consequential errors? | Blind grading against independent human references | Failure precision/detection, false acceptance/rejection, coverage |
| Does irrelevant presentation change its verdict? | Original output versus changed IDs or item order | Invariance violations with paired evidence |
| Does it notice a meaningful change? | Original output versus a removed/replaced task or invented owner | Conditional detection, after checking the original passes |
| Is the same judge stable across runs? | Repeat identical input, rubric and adapter configuration | Binary pair coverage/agreement, complete/stable cell rates |
| Does the rubric ask the right questions? | Independent critiques, rubric revisions, and acceptance decisions | Important issues absent from criteria, documented boundary disagreements |

These questions measure different properties. An always-pass judge is stable and
invariant but useless for detecting failures. Agreement with humans on a rubric does
not prove that the rubric measures user value. Treat pilot rubrics as hypotheses.

## Repeatable demonstration without API credits

From the repository root:

```powershell
pip install -e ".[dev]"
meeting-eval meta demo artifacts/demo-01
```

Open `artifacts/demo-01/report.html`. This creates controlled variants of a teaching
example, scripted reviewer submissions, an always-pass judge, a comparison report,
a robustness report, and a blind review page. Every scripted submission is marked
`synthetic_demo: true`; the comparison report prominently carries that status.
It is a software demonstration, not a human study or model performance result.

## Generate your own challenges

```powershell
meeting-eval meta challenges data/meta/cases.jsonl data/meta/rubric.json artifacts/challenge-01 sample-correct
```

Outputs: `cases.jsonl`, `manifest.json`, `review.json`, `review.html`. Source variants
share the meeting ID, input, and split. Variant IDs are opaque. Transformation names,
intended relations, and review notes live only in the manifest. Do not show the
manifest to blind annotators or judges. Choose a seed that humans judge acceptable.

Supported transformations are deliberately small and inspectable: rename object IDs,
reverse object order when meaningful, replace a task while preserving its ID, omit
an action, and invent an owner where the original has none. Only generate relations
for relevant criterion IDs. Custom rubrics can still be used for ID/order invariance;
the targeted mutations currently recognize the pilot's three criterion IDs.

```powershell
meeting-eval meta judge artifacts/challenge-01/cases.jsonl data/meta/rubric.json data/meta/example_judge.json artifacts/challenge-01/judge.json --split discovery
meeting-eval meta robustness artifacts/challenge-01/cases.jsonl data/meta/rubric.json artifacts/challenge-01/manifest.json artifacts/challenge-01/judge.json artifacts/challenge-01/robustness.json
```

The bundled adapter abstains; zero binary coverage is expected. Replace it with a
configured model or deterministic adapter for substantive experiments. Robustness
results remain marked `proposed_not_human_validated`. A failed base is counted as
`base_not_passed`, not credited as successful detection. Missing and abstaining
responses are counted as unanswered. Invariance can be satisfied even when both
verdicts are wrong, so inspect it alongside human-referenced detection results.

## Repeat a judge

```powershell
meeting-eval meta repeat-judge data/meta/cases.jsonl data/meta/rubric.json data/meta/example_judge.json artifacts/repeats-01 --repeats 3 --split discovery
```

This uses the exact same trusted adapter configuration for each run, recording its
hash, timings, run IDs, dataset/rubric hashes, and software provenance. Real model
adapters incur the normal cost multiplied by the number of repeats. The command
accepts 2–10 repeats. Each submission and `stability.json` is saved separately. Missing
and nonbinary verdicts reduce coverage; two repeated abstentions do not count as
successful binary stability. API errors are recorded and the command exits nonzero.
Results do not estimate semantic correctness. Code and provider configuration must
be kept fixed during repeated runs; the configuration hash is not a snapshot of an
external model service or the contents of referenced scripts.

## Human study procedure

1. Start with discovery meetings covering ambiguous dates, corrections, speaker
   attribution, tentative events, and failed or absent tools. Collect independent
   open-ended critiques before refining the rubric.
2. Have at least two independent reviewers annotate each selected cell. Keep their
   identities stable, hide judge verdicts, and retain their original submissions.
3. Resolve boundary disagreements with explicit adjudication. Record why a rubric,
   annotation, missing-context assumption, or model prediction was wrong.
4. Keep discovery/development/test meetings separate. All variants stay together;
   identical inputs cannot cross splits even under different meeting IDs.
5. Tune prompts and rubric wording on development only. Freeze the rubric and judge
   before opening test references. Report sample sizes and class counts.
6. Run comparison and inspect every false acceptance plus a random set of agreements.
   Use random sampling alongside targeted failures to avoid discovering only the
   mistakes your current judge already recognizes.

```powershell
meeting-eval meta compare path/to/cases.jsonl path/to/rubric.json path/to/submissions artifacts/study-report.json --split test
```

This writes JSON plus `study-report.html`: evaluator metrics, per-criterion results,
an expandable disagreement queue with identities/rationales/evidence, human annotation
completion, critiques outside the rubric, and run provenance. Share the report with
study leads after independent annotation; it reveals judgments and reviewer IDs.
Report artifacts may contain private transcript quotes. Keep them under ignored
`artifacts/` and share deliberately.

## Proposed expanded rubric

`data/meta/rubric_v2.json` adds final calendar intent, decision fidelity, evidence
support, and execution truthfulness to the initial task criteria. The explicit
version is `0.2.0-proposed`. Human review must decide whether these questions are
useful and sufficiently scoped. Do not mix v1 and v2 submissions: provenance checks
intentionally reject comparisons across rubric hashes.

## Deliverables and completion criteria

- Reproducible repo and no-credentials demonstration: implemented.
- Human review interface and portable validated JSON contracts: implemented.
- Controlled challenge tests, repeated-judge analysis, and browsable comparison:
  implemented with automated tests.
- At least two independent human annotations per included reference cell: pending.
- Live judge experiments with frozen config and held-out meetings: pending API access
  and dataset collection; no model results are claimed by the synthetic demo.
- Final findings: report effect sizes, uncertainty, unresolved disagreements, rubric
  revisions, and failures that automated evaluation misses. Generalization beyond
  meeting extraction requires a second task domain; this is not established yet.

Follow-on experiments include human-only versus AI-assisted review (with randomized,
counterbalanced assignments and measured review time), different judge families,
rubric wording ablations, severity-aware acceptance policies, and transfer to a
second bounded agent task. These require additional data and study design; the
current release does not present them as implemented experiments.
