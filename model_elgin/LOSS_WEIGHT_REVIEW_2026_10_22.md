# Loss-weight experiment: result and decision

Reviewed on 22 October 2026. The full five-fold run finished on 21 October
before the user's stop request. Returning to this work required results
review, not resuming or repeating training.

**Retain cap128 with positive loss weight 3 as the leading neural candidate.**
Removing the extra positive-example penalty did not improve the predeclared
mean-fold score. The difference is very small and mixed across folds; it does
not establish statistical or universal superiority. The completed comparison
and both sets of checkpoints are retained, including the negative outcome.

## Actual comparison

Both versions use all 121,838 data0 sites, including 5,475 positive labels,
with the exact five shared gene folds. Only positive loss weight changes.
Network, inputs, read cap, seed rules, preprocessing boundaries and the
inner-selection/fresh-refit procedure remain fixed. Selected epoch counts
can differ as a consequence of the changed objective.

| Data0 measure | Weight 3, retained | Weight 1, tested |
|---|---:|---:|
| Mean-fold ROC AUC | 0.9318281774 | 0.9332097437 |
| Mean-fold trapezoidal PR AUC | 0.5056010366 | 0.5035528330 |
| Mean-fold AP | 0.5062502328 | 0.5042156259 |
| **Mean-fold S, primary** | **0.7187146070** | **0.7183812884** |
| Pooled OOF S, supplementary | 0.7165539072 | 0.7174893768 |
| Pooled precision at 0.5 | 0.47392897 | 0.63664596 |
| Pooled recall at 0.5 | 0.61424658 | 0.33698630 |
| Pooled F1 at 0.5 | 0.53504097 | 0.44070226 |

S is (ROC AUC + trapezoidal PR AUC)/2, averaged equally over the five folds.
Weight 1 changes this primary score by -0.0003333186. It improves S in three
folds and declines in two, with larger losses in the latter. Preserve those
individual outcomes; do not claim every fold favours weight 3.

The pooled score goes in the opposite direction. This is not an arithmetic
contradiction: pooled curves rank scores from different fitted fold models
together, whereas mean-fold metrics assess each fold separately before
averaging. The protocol selected mean-fold S before this result was known;
we retain that criterion and report the pooled result alongside it.

At the existing 0.5 cutoff, weight 1 makes 2,680 fewer false-positive calls,
but also detects 1,518 fewer labelled positives. Its precision, specificity
and accuracy rise while recall and F1 fall. This is an operating-point
tradeoff, not evidence that weight 1 solves unusual sites or high-depth
misses. No new cutoff was selected, and neither set of scores is established
as calibrated probabilities or molecule-level modification fractions.

Full tables, paired-fold plots, resource disclosures and commands are in
[the checked aggregate comparison](loss_weight_results/README.md).
The [fixed design](LOSS_WEIGHT_EXPERIMENT.md) remains unchanged.

## What was actually executed

The original environment ran ten new fits: five inner-duration fits and five
fresh refits, followed by held-out predictions. Full CV took 5,715.090 seconds
(95.251 minutes) command elapsed. The queued reporter took 12.703 seconds.
Per-fit recorded wall time totals 5,658.540 seconds and CPU time 21,591.812
seconds, with a largest retained sampled process-tree RSS of 973.098 MiB.
These measurement scopes differ; do not add their overlapping times together.
The control's interruption includes a recovered lower-bound resource record,
so its retained cost does not support a precise efficiency comparison.

Before full CV, nine trainer checks and twelve reporter checks passed, plus
an isolated real-data software check and separate full-size one-epoch timings.
The software check and timing fits never initialise CV fits. Earlier Windows
permission failures, their logs, all final checkpoints, optimizer/RNG states,
histories and prediction CSVs remain local. No data1, data2 or SG-NEx inputs
were used in this experiment.

The post-training independent audit verified 99 saved-input hashes, including
20 checkpoint byte hashes, seven aggregate outputs and eleven current source
fingerprints. It reproduced the exact population, gene partitions, fitted
signatures, saved-score metrics and paired/mean/SD arithmetic within1e-12,
and checked that each resource invocation is counted once. The integrator
viewed both figures and reran the guarded aggregate export. The local audit
receipt and export script remain with the experiment's checks. No model
weights were deserialised and no fitting or model inference was performed.

Executed from the repository root:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_loss_weight.py --phase cv
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_loss_weight.py
```

Checksums and reconstructed signatures corroborate saved provenance; these
checks do not independently replay all training. One seed, repeated use of
development folds, overlapping training sets and imperfect labels remain
limitations. Fold SD is descriptive, not a confidence interval.

## How this contributes to the report

The progression is EDA -> tested context-relative features -> read-depth and
unusual-signal investigation -> modest gain from cap128 -> mixed threshold
result -> this loss-weight tradeoff -> a justified candidate choice. Member
1's findings informed feature hypotheses, retained gene grouping and subgroup
checks; they did not guarantee each proposed change would improve performance.

The planned bounded neural search is now complete. Retain the weight 3
pipeline and its working 0.5 reporting rule; continue exporting continuous
scores and disclose threshold sensitivity in Task 2. Samuel remains a valid
comparison with stronger precision and descriptive score reliability on
previously checked evidence. A different model winning one metric does not
invalidate either contribution.

Next, complete the required simple-baseline reproduction and published
m6Anet comparison, formal nomination and fresh all-data0 saved artifact,
frozen exposed-data1 diagnostics and same-model dataset predictions. Then
apply the chosen model to the 23 agreed SG-NEx runs and finish replicate-aware
analysis, the genuine-score explorer, the report and clean Ubuntu prediction
verification. No new neural search, final fit or application run was launched
as part of this review.
