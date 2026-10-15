# Elgin's model

Owner: Elgin, model lead and final report integrator. Neural networks are the
provisional direction, including alternatives to the original architecture.
Samuel develops a separate candidate in `model_samuel`.

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

Agree evaluation populations and preprocessing boundaries with Samuel before
new training. Fresh-fit models inside each permitted partition, preserve
checkpoints/configuration/commands/costs, and retain negative findings. The
number of folds and any fixed holdout remain open until the data support and
resource trade-offs have been reviewed.

## Handover

Maintain one concise methods/results draft, essential figures/tables and
reproducible code, backed by actual logs and saved predictions. Explain each
meaningful change as EDA observation -> decision -> measured result -> limit.
Do not report proposed changes as completed improvements.
