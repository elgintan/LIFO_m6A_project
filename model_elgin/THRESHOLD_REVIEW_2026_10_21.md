# Calling-threshold result and decision

21 October 2026. The [fixed-design study](THRESHOLD_EXPERIMENT.md) is complete.
See [actual aggregate results and figures](threshold_results/README.md).

**Retain 0.5 as the working reporting cutoff.** The training-side maximum-F1
policy offers no convincing overall F1 gain, and worsens high-coverage recall.
This is a pragmatic development decision, not proof that 0.5 is globally
optimal, calibrated or a biological modification threshold. Continue exporting
continuous scores. The median alternative remains a proposal, not an active
change to the prediction pipeline.

## Actual excluded-outer results

Every cutoff was selected using only the appropriate inner data0 gene group,
then applied to its excluded outer group's existing refit scores. No neural
training, calibration or data1 evaluation occurred. Original checkpoints,
scores, preprocessing and ranking performance remain unchanged.

| Pooled outer metric | Fixed 0.5 | Inner-selected F1 policy |
|---|---:|---:|
| Precision | 0.473929 | 0.482096 |
| Recall | 0.614247 | 0.600000 |
| F1 | 0.535041 | 0.534624 |
| False positives | 3,733 | 3,529 |
| True positives | 3,363 | 3,285 |

The learned policy produces 204 fewer false positives and 78 fewer true
positives. Three folds improve in F1 and two decline. Mean-fold F1 changes
from 0.534952 to 0.535132, a negligible +0.000180; pooled F1 changes by
-0.000417. Both summaries are retained, without choosing whichever tells a
more favourable story. There is no statistical-significance claim.

At 200+ reads, recall declines from 168/461 (0.364425) to 157/461 (0.340564),
and F1 from 0.460274 to 0.438547. False positives decrease only from 101 to98.
The policy does not solve the previously identified high-depth weakness.

The five cutoffs are 0.528605998, 0.460746258, 0.593996286, 0.510309458 and
0.483205169. Their median is **0.510309457779**. The reported learned-policy
outer results use the five round-specific cutoffs; they do **not** validate
one global cutoff of 0.510309457779. No all-data0 model exists yet for this
pipeline, so transfer of that median to its score scale is still untested.

## Interpretation and next work

The inner cutoffs were selected from three-group models and applied to fresh
four-group refits. Their score scales may differ; the measured result does
not identify a single cause. Using one inner group for both epoch and cutoff
selection makes inner F1 optimistic, while outer groups remain outside both
choices. Prior architecture development still limits generalisation claims.

The current cap128 candidate remains the leader under our agreed ranking
score, S=0.7187146070. A cutoff cannot change that score. If another training
experiment is undertaken, the next bounded hypothesis remains positive-loss
weight3 versus1 with all other settings fixed. That experiment is **unrun**;
it could reduce recall and is not a demonstrated remedy for high-depth misses.
Do not alter the completed cap128 recipe in place or silently change the
objective after seeing an outcome.

Probability calibration is also separate and unperformed. Scores/cutoffs
validated under supplied site labels do not establish the fraction of RNA
molecules modified or the same operating performance in SG-NEx cell lines.
For Task2, keep continuous-score views and threshold-sensitivity comparisons.

The required m6Anet comparison, final nomination/refit, frozen data1 transfer,
same-model dataset CSVs, real23-run SG-NEx predictions, final report/explorer
and Ubuntu reproduction remain pending. These deliverables should not be
displaced by an unlimited training search.

## Checks and computation

Fourteen synthetic contract tests passed on the integrator's run in0.136s,
including160 independent exact brute-force selection cases, tied scores,
missing classes, key/fold mismatches and checkpoint-boundary checks.
All five selected inner checkpoint predictions reproduced their saved
history metrics. Existing source, input, OOF and checkpoint hashes remained
unchanged. Per-round inner scores and receipts are retained locally for
checked resume; no site-level predictions are published with this report.

The actual command exited0 in41.862s, including imports/preflight. Measured
post-preflight analysis/inference work was27.480s wall and71.031s process CPU,
with951.086MiB sampled process RSS peak. No model was retrained. Public
aggregate copies have byte-hash receipts; full unique-score selection curves
and inner prediction tables stay local.
