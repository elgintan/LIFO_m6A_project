# Model shortfalls and recommended next step

21 October 2026. The analysis is completed; the next threshold experiment and
any further neural training described here are proposals, not completed work.
See the [reproducible diagnostic results](read_cap_shortfalls_results/README.md).

The cap128 neural pipeline is the leading candidate under our agreed data0
ranking criterion. Keep it as the current reference. The next priority is a
validated calling rule; current evidence does not justify a larger network or
an open-ended architecture search.

## What the actual results say

All three saved candidates were rescored on the same 121,838 sites and exact
five gene folds. These are comparisons of complete development pipelines,
not an isolated experiment on neural networks versus trees.

| Pipeline | Mean ROC AUC | Mean trapezoidal PR AUC | Mean S | Precision at 0.5 | Recall at 0.5 |
|---|---:|---:|---:|---:|---:|
| Neural cap32 | 0.931123 | 0.504160 | 0.717642 | 0.478953 | **0.615160** |
| Neural cap128 | 0.931828 | 0.505601 | **0.718715** | 0.473929 | 0.614247 |
| Samuel LightGBM | 0.921897 | 0.498996 | 0.710446 | **0.627457** | 0.355616 |

The two threshold columns are pooled OOF metrics at an unvalidated reporting
cutoff. They are not comparisons of separately optimised operating points.
Samuel also has better specificity and smaller descriptive score-calibration
error; no model wins every metric. Cap128 has higher S in all five folds
against both comparators, but its gain over cap32 is small and from one seed.

The read-cap experiment did help the intended ranking groups:

- At 200+ reads, pooled S rose from 0.692223 to 0.695188 on 10,219 sites,
  including 461 positive labels. The within-group fold S difference was
  positive in three of five folds. At 0.5, both versions detect 168 of the
  461 positives, and cap128 adds three false positives. Better ranking has
  not repaired the high-depth missed-positive count at this cutoff.
- Across the 1,645 training-defined unusual-signal sites (102 positive),
  pooled S rose from 0.736653 to 0.741478. These flags are descriptive;
  valid sites stay in the data.
- The lowest observed coverage group, 20–29 reads, has a small pooled S
  decrease of 0.000811. Ten of the 18 central motifs improved in pooled S;
  eight declined. Rare motifs have very few positives, so do not treat large
  apparent differences as reliable biological effects.
- Member 1's 36 named review sites are a separate cohort with only two
  positives. Its pooled S decreased. Keep this negative finding and its
  limited support; do not merge it with the larger fence-flagged cohort.

At 0.5, cap128 and Samuel miss 2,095 of the same positive sites; Samuel finds
only 17 positives missed by cap128. That is weak evidence for assuming a
blend will repair the neural model's misses. Different thresholds could
change this overlap; it is not a proof that an ensemble cannot help.

## Recommended immediate experiment: validate the calling cutoff

A cutoff converts the continuous score into a yes/no call. It does not change
ROC/PR ranking. Recommend F1 as the initial declared operating objective,
balancing precision and recall under the supplied site labels. It is a
modelling choice, not an official biological threshold or guaranteed optimum
for every research application.

For each outer fold f:

1. Reuse its saved cap128 inner model, trained on the three permitted groups
   with stopping selected on inner group (f+1)%5.
2. Obtain scores only for that inner group. Select the cutoff maximising F1
   there, using `score >= cutoff` and the higher cutoff to break ties.
3. Apply that fixed cutoff to the existing fresh four-group refit's scores on
   the excluded outer fold. Report its precision, recall, F1 and confusion
   counts alongside the unchanged ranking score and fixed-0.5 reference.

Selecting epoch and cutoff on the same inner block is internal model
selection; its apparent F1 is optimistic and must not be called assessment
performance. The outer fold assesses the complete proposed procedure. Score
scales can differ between a three-group model and a fresh four-group refit;
the outer results must show whether the learned cutoff transfers.

Do not learn an outer round's cutoff from the other four ordinary OOF
partitions: the models that generated those scores may have trained on that
round's assessment genes. A pooled OOF cutoff search after repeated model
development is also not a new unbiased evaluation.

Before executing, freeze the final cutoff-aggregation rule as well. The
recommended simple rule is the median of the five training-side cutoffs for
the later all-data0 model. It is not guaranteed to maximise that final model's
F1, and the earlier per-round outer F1 is not a direct test of this one median
cutoff. Record that distinction. No numeric cutoff has been selected yet.

Probability calibration is a separate subsequent option. The neural loss
gives positive examples weight 3; its raw score need not equal a site-label
probability. The cap128 raw mean score is 0.080590 versus label prevalence
0.044937; ten-bin descriptive ECE is 0.035654, compared with Samuel's 0.006305.
These observations motivate checking reliability but do not isolate the cause.
Fit any calibrator on held-out training-side genes and evaluate reliability
outside those fitting genes. Brier score combines reliability and other
properties; it is not calibration alone. See the official
[calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).

## One possible further training change

If another training experiment is warranted after the operating-policy
review, test **positive loss weight 3 versus 1**, keeping cap128, features,
architecture, seed rule, inner stopping and all-read assessment unchanged.
This directly tests the current training objective rather than adding more
layers. Loss weighting can trade precision against recall, as described in
the [PyTorch loss documentation](https://docs.pytorch.org/docs/2.14/generated/torch.nn.BCEWithLogitsLoss.html).
Whether weight 1 improves our ranking, reliability or final operating metrics
is untested; a gain is not promised. Do not change the current frozen recipe
in place. Use a separate versioned experiment with fresh weights, checkpoint
identity and preserved logs/results on the identical five gene folds.

Keep the current winner unless the agreed full-data0 criterion and secondary
robustness evidence justify replacing it. Retain a negative result. Neither
repeating a failed context-relative feature idea nor oversampling a handful
of unusual sites is justified by this review. Explicit coverage as an input
is another possible hypothesis, but Member 1 showed coverage patterns can
shift between datasets; it is lower priority than the declared loss/cutoff
questions and would require its own controlled experiment.

## Report and completion priorities

The project story is now: Member 1's observations -> context features that
failed -> depth and raw-signal investigations -> cap128's modest ranking gain
and remaining errors -> validated operating policy -> frozen model -> real
SG-NEx patterns and researcher-facing visualisation.

The required published m6Anet benchmark, final all-data0 fit, frozen data1
transfer diagnostic, same-model dataset prediction CSVs, genuine predictions
for the agreed 23 processed SG-NEx runs, replicate-aware Task 2 analysis,
explorer, final report and Ubuntu reproduction remain pending. Thresholds
validated against supplied data0 labels do not establish an SG-NEx biological
truth or a modified-molecule fraction. Retain continuous scores and
threshold-sensitivity views when reporting cell-line comparisons.
