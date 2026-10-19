# Elgin's model

Owner: Elgin, model lead and final report integrator. Neural networks are the
provisional direction, including alternatives to the original architecture.
Samuel develops a separate candidate in `model_samuel`.

**Start with [Elgin's first-step guide](FIRST_STEPS.md).** On 19 October, the
saved historical OOF predictions were verified and rescored using the shared
evaluator: [reference check](reference_check_2026_10_19/README.md).
The [working trainer/predictor](context_reference_v1/README.md) now implements
context-relative features and the exact shared gene groups. Thirty software
tests and a small real data0 check in both modes passed; see
[observed evidence](context_reference_v1/IMPLEMENTATION_CHECK.md).
Full candidate comparison and any improvement conclusion remain pending.

## Available starting point

`baseline_2026_10_07/` preserves actual earlier source, weights, metrics,
training history/log and all three prediction CSVs. See its README. This is
a historical reference, not a new candidate result or winner under the next
protocol. Its weights learned all data0 and cannot initialise a model that is
then presented as never having seen a held-out data0 subset.

The network already combines a seven-base embedding, sequence-conditioned
per-read MLP, gated attention and 63 all-read mean/SD/quantile features. Training
sampled at most 32 reads in its neural branch; predictions used all reads.
Its attention weights are not verified molecule-level modification labels.

## EDA-driven development

Read `../DATA_METHODOLOGY.md` and the received EDA. First map actual existing
features; do not present adding medians/sequence as wholly new. Candidate
questions include stronger or different context conditioning, training-fitted
motif residuals with sparse-group fallbacks, read aggregation and coverage
stability. Signal-only/sequence-only controls can reveal what a combined model
uses. These are hypotheses, not selected experiments or proven gains.

Use the [minimum shared rules](../model_evaluation/SHARED_RULES.md), accepted
by Elgin; Samuel's acknowledgement has not yet been reported. Fresh-fit models
inside each permitted partition, preserve
checkpoints/configuration/commands/costs, and retain negative findings. The
[detailed methodology](../model_evaluation/EVALUATION_PROTOCOL.md) explains
the exact five outer gene groups and optional rotating inner default. Common
scoring code is included. Only small software-check fits have run in the new
pipeline; its full five-fold comparison has not run.

## Handover

Maintain one concise methods/results draft, essential figures/tables and
reproducible code, backed by actual logs and saved predictions. Explain each
meaningful change as EDA observation -> decision -> measured result -> limit.
Do not report proposed changes as completed improvements.
