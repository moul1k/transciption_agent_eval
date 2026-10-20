# Making evaluator benchmarking useful in development

## Evidence and implementation decisions

This project measures evaluator behavior and exposes the limits of that measurement.
It combines authored contract tests for known invariants, fresh model runs, trace
inspection, and independent human review. Model agreement with authored synthetic
expectations is not human validity. Tests marked `test` are frozen transfer fixtures
for this run, not a secret independently curated benchmark.

| Source | Guidance relevant here | Implementation |
|---|---|---|
| [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Task-specific evaluations, continuous testing, calibration and representative examples | Versioned cases, explicit contracts, CI thresholds, human review |
| [OpenAI graders](https://developers.openai.com/api/docs/guides/graders) | Test model graders themselves and compare automated grading against expert assessment | Judge artifacts and reference-type separation |
| [Anthropic agent eval guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Distinguish outcomes from claimed success; combine code, model and human graders; isolate trials | Local final-state oracle and full-evidence versus output-only ablation |
| [Hamel Husain](https://hamel.dev/blog/posts/revenge/) | Treat judges as classifiers, inspect real errors, separate development and testing | Frozen transfer cases plus precision, detection, false acceptance and coverage |
| [Shankar et al.](https://arxiv.org/abs/2404.12272) | Human requirements and evaluation criteria evolve during review | Freeform critiques and independent annotations remain authoritative inputs for rubric revision |
| [Zheng et al.](https://arxiv.org/abs/2306.05685) | Judge biases include position, verbosity and self-enhancement | Presentation invariance is distinct from correctness; further pairwise order/verbosity experiments remain planned |
| [DeepMind FACTS Grounding](https://deepmind.google/blog/facts-grounding-a-new-benchmark-for-evaluating-the-factuality-of-large-language-models/) | Separate task completion from grounding and validate automatic judges | Separate scoped criteria; avoid interpreting one score as overall usefulness |
| [Maloyan et al.](https://arxiv.org/abs/2505.13348) | Judge-directed prompt injection can corrupt grading | Paired candidate injection/control fixtures and traces |

These implementations borrow methodology, not published performance claims. The
sources evaluate different tasks/models; their reported accuracies do not transfer
to our application. This review is selective, not exhaustive.

## Framework choice

**Langfuse** is our existing trace backend. Keep prompts, responses, usage, errors and
case IDs linked to experiments. It does not establish that a rubric is meaningful.
The runner already verifies delivery through the observation API.

**Inspect AI** is an optional interoperability layer for reusable tasks, solvers,
scorers and provider support. `integrations/inspect_contracts.py` packages the same
34 authored fixtures as a real Inspect task. Targets stay outside model inputs;
the custom scorer reads a JSON verdict and compares it with the authored target.
The local task construction is tested with Inspect installed. It is not a new source
of human labels. See [Inspect scorers](https://inspect.aisi.org.uk/scorers.html) and
[offline rescoring](https://inspect.aisi.org.uk/scoring-workflow.html).

```powershell
pip install -e ".[inspect,openai]"
# OPENAI_API_KEY must be configured in the environment.
inspect eval integrations/inspect_contracts.py --model openai/gpt-6-luna --limit 4 --log-dir artifacts/inspect-logs
```

This command makes paid calls separately from the budgeted native runner; it does
not inherit its reservation guard or Langfuse instrumentation. Limit samples before
running it. The native audit remains the fully traced, budget-controlled reference.

**JUnit plus the existing JSON contracts** makes regression results usable by CI
without requiring a new vendor. The audit exports `junit.xml`; `meeting-eval meta gate`
exits nonzero when selected point thresholds fail. A threshold on a small synthetic
suite is a regression alarm, not a statistically justified production release policy.

**Promptfoo** is a reasonable alternative when the team wants a CLI prompt matrix,
but we have not implemented a Promptfoo adapter. Its documentation distinguishes
boolean pass/fail from numeric scores and explicitly configured thresholds; these
semantics must be checked before importing any framework's defaults. See
[LLM rubric assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/).
Installing several evaluation libraries alone would not validate our evaluators.

## Experiments implemented and run

The `run_developer_audit.py` plan is persisted before any model call. It fixes model,
effort, token caps, no-retry behavior, fixture/rubric hashes and source-code hash.
It executes 120 GPT-6 Luna judgments at low reasoning, three concurrent requests:

- Scope transfer: six fresh scenarios, each correct, omitted, or with an invented
  owner; legacy versus scoped uncertainty wording, two repeats: 72 judgments.
- Evidence ablation: four local tool scenarios with success and failed/duplicate
  states; full evidence versus withheld trace/state, two repeats: 32 judgments.
- Injection resistance: four synthetic scenarios, each with control and candidate
  injection, two repeats: 16 judgments.

The scope ablation changes only the target criterion wording; criterion inventory
and model settings stay fixed. Other groups should not be interpreted as factorial
tests of every variable. Expected verdicts, categories and contract rationales are
never sent in model inputs. Traces include only the actual case and criterion.

The output-only evidence condition expects `insufficient_context`, because the
candidate claim alone cannot establish tool success. Its contract-match rate tests
appropriate abstention, not accuracy about a hidden final state.

Repeated variants and template-derived cases are correlated. Wilson intervals are
descriptive and labelled accordingly; raw judgment counts are not independent
sample sizes. Broader transfer needs independently collected meetings and domains.

## Developer commands

```powershell
meeting-eval meta contract-suite artifacts/contracts-01
python scripts/run_developer_audit.py --credentials path/to/key.docx --langfuse-credentials path/to/langfuse.txt --output-dir artifacts/audit-01 --budget-usd 0.50
meeting-eval meta gate artifacts/audit-01/report.json --condition scope_scoped --condition tool_full --condition tool_output_only --condition injection --minimum-match 0.95 --maximum-false-acceptances 0
```

The native runner writes generic cases, rubric snapshots per condition, a blind
human-review page, model submissions, per-call rows/traces/usage, comparison metrics,
review queue and JUnit results. Failures and abstentions remain in denominators.
Both keys and private transcript artifacts stay outside Git.

Gate selected candidate conditions, not the deliberately ambiguous legacy control.
Without `--condition`, every group is checked, including controls. The manual
`manual-live-evaluator-audit` GitHub Action uses the selected candidate conditions;
it requires repository secrets for OpenAI and Langfuse. It is never triggered by a
push or PR. Secrets can also be supplied as environment variables locally without
credential file flags. The optional Inspect integration was executed end to end
against its mock model with one sample, confirming malformed output scores incorrect.

## What still establishes fundamental validity

Get at least two independent humans to review representative traces and boundary
cases, preserve disagreements, and freeze rubric decisions before a final test set.
Measure the importance and coverage of criteria against independent acceptance and
correction effort. A synthetic suite can test known evaluator defects today but
cannot prove user usefulness. Human-only versus AI-assisted annotation, cross-family
judge ensembles, real tool-environment execution, and representative production
sampling are next studies, not completed evidence.
