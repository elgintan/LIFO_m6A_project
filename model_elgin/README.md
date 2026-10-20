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
The full matched data0 five-fold comparison completed on 19 October:
original features mean ROC/PR/S = **0.931123/0.504160/0.717642**;
added context features = **0.926982/0.490787/0.708885**. This particular
change reduced the primary score; retain the original-feature version as the
stronger of these two measured pipelines. This is development evidence from
one seed, not universal or statistically established superiority.

Saved-score diagnostics then examined motif, coverage and training-fitted
unusual-signal groups. Both very low and very high coverage warrant further
investigation; an unusual statistical flag alone does not justify excluding a
site. All 121,838 sites were retained. No new training or data1 inference was
performed in those diagnostics. Reproducible analysis tools are in `tools/`;
the full CSVs, plots, checksums and reports remain in local ignored `outputs/`.
The [read-depth stability investigation](READ_DEPTH_STABILITY.md) completed on
20 October: 24,533 matched sites, 130 conditions and 637,858 diagnostic scores.
Using all reads performed best; primary matched-cohort S was 0.732322 with
all reads versus 0.678788 with 20. These subset scores do not replace the
full-data0 score above. Retain all-read inference; see the
[actual results, plots and limits](read_depth_stability_results/README.md).
A new final refit, frozen data1 diagnostics and real SG-NEx predictions remain pending.

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
by Elgin; Samuel's candidate is now merged and unpacked using the exact same
folds, and its saved data0 metrics reproduce with the common scorer. Fresh-fit models
inside each permitted partition, preserve
checkpoints/configuration/commands/costs, and retain negative findings. The
[detailed methodology](../model_evaluation/EVALUATION_PROTOCOL.md) explains
the exact five outer gene groups and optional rotating inner default. Common
scoring code is included, and the complete matched five-fold comparison above
has run. Separate saved-prediction diagnostics do not retrain those models.

## Handover

Maintain one concise methods/results draft, essential figures/tables and
reproducible code, backed by actual logs and saved predictions. Explain each
meaningful change as EDA observation -> decision -> measured result -> limit.
Do not report proposed changes as completed improvements.
