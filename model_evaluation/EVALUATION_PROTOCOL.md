# Shared candidate evaluation: methodology v1

**Status: accepted by Elgin on 15 October 2026; Samuel's acknowledgement has
not yet been reported.** No new candidate has been trained or selected under
this methodology. The [minimum shared rules](SHARED_RULES.md) define what must
match; this longer document explains the rationale and recommended checks.
Model design and tuning remain independent. Existing outer assignments are
unchanged; [cv_rounds.csv](cv_rounds.csv) supplies optional inner roles.

## 1. Common question and freedom to develop

The supervised question is: can a model rank supplied site-level m6A labels
on data0 genes absent from that particular fit? Transfer to another dataset
and interpretation across SG-NEx cell lines are additional questions.

Both owners use the same data versions, labels, eligible assessment sites,
gene assignments and scoring code. They may choose different model families,
features, read aggregation, losses, optimisers and tuning strategies. Enhanced
LightGBM and neural networks are starting ideas. This compares complete
pipelines; identical features would be needed for an architecture-only claim.

Training and tuning use **data0 only** in this cycle. Preserve natural label
prevalence in every assessment population. Keep valid rare, low-coverage and
unusual sites. Structural problems must be reported and resolved consistently
before fitting; a model cannot quietly omit difficult assessment sites.

## 2. Accepted outer split, with an EDA-based reason

Reuse the exact [historical gene assignments](../eda/received/shared_folds/data0_folds.csv),
whose SHA256 is
`986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
Keep every site/transcript from a gene in its assigned group. Do not regenerate
the file independently, split individual reads, or use gene IDs as features.

The [composition audit](../eda/split_review/README.md) found 121,838 sites,
3,852 genes and 5,475 positives. Each of five held-out groups has 24,344-24,387
sites, 767-775 genes and 1,083-1,105 positives, with 4.45-4.53% positives.
Five rotations therefore give every site a held-out prediction and allow an
80% data0 refit in each rotation. This is why five is recommended now.

A single 60/20/20 allocation would give one assessment population and use
less data for its assessed fit. Three-fold assessment is cheaper but trains
each round on about two-thirds. Neither fixes motifs with only one or two
positives in the whole dataset. More folds increase cost and reduce subgroup
support. A fresh split would also not undo the previous exploration of data0.

The existing five groups are not perfectly supported within motifs: 8 of 90
motif-by-group assessment slices have only one class and 38 have fewer than
20 positives. One four-group training population has no positive example for
one motif. Keep these cases, use information sharing/fallbacks as appropriate,
and disclose the weak support. Do not search for a split that scores better.

## 3. Development, stopping and the five-round comparison

Develop candidates within data0 and nominate **one pipeline/configuration per
owner** for the first full comparison. A shared screening round can reduce
cost. Record screened changes and the actual work performed; an equal number
of hyperparameter trials is not necessarily an equal computation budget.

For each assessment group `f = 0, 1, 2, 3, 4`, keep that group outside fitting.
The following inner rotation is a convenient default, not a requirement to
use identical tuning algorithms. Another documented inner strategy can be
used if genes remain separated and the outer assessment group is excluded:

1. Put group `f` aside for assessment. Use group `(f + 1) % 5` for inner
   validation; the other three groups fit the initial model (about 60% of
   sites). Inner validation selects stopping duration, such as neural epochs
   or boosting iterations. Fix the nominated hyperparameters before the full
   comparison. Declare the stopping metric, patience and maximum epochs/trees
   before that comparison; these can differ between model families. A model
   without early stopping can use its declared fixed count.
2. Fit all learned transformations and weights using those three fitting
   groups. Apply them unchanged to inner validation. Never use assessment
   group `f` for stopping, feature selection, calibration or threshold choice.
3. Having selected the duration, discard those learned weights. **Fit afresh
   on all four non-assessment groups** (about 80%), including refitting their
   preprocessing, for that fixed duration. Score group `f` once and save its
   full-precision predictions. There is no stopping on group `f`.
4. Repeat for the next `f`. Retain all
   five assessment predictions; each data0 site has exactly one out-of-fold
   prediction, meaning it was excluded from the fit that scored it.

For example, round 0 fits groups 2/3/4, stops on group 1, then freshly refits
groups 1/2/3/4 before predicting group 0. This requires up to ten fits per
finalist, including duration selection, rather than five direct fits. Record
the actual cost. Proposed reference training seed: 2026; a seed does not make
different libraries or hardware produce identical randomness.

Check inner populations' motif/class support as well as the already audited
four-group refits before using an inner strategy. Sparse contexts require a
documented fallback, not reassignment based on model results. The supplied
role file identifies default roles; it does not certify every rare subgroup
has positive examples. The existing fold verifier checks the outer assignments.

The old Elgin checkpoint was fitted on all data0. **Do not warm-start any of
these fits from it.** Reusing source/architecture is fine; reusing weights or
learned normalisation from all data0 invalidates held-out-data0 fitting.
Resume an interrupted checkpoint only within the identical permitted fit,
input version, configuration and group assignment.

These are **development comparison results**. Earlier model selection and EDA
already exposed data0, and this comparison selects a pipeline. It is not a
new blind test or an unbiased nested-CV estimate. If changes follow the full
comparison, label them a new development cycle and retain the earlier result.

## 4. Exact common scoring

Join predictions by both `transcript_id` and numeric `transcript_position`.
Require exactly one finite score in [0,1] for every expected site, no extra or
duplicate keys, and a matching source/split version. Never silently inner-join
away missing predictions. Model inability to score a required site is a
reported failure until resolved consistently.

For each held-out group compute:

- ROC AUC, using continuous scores and the supplied binary labels.
- **Trapezoidal PR AUC**: `precision_recall_curve(y, score,
  drop_intermediate=False)` followed by `auc(recall, precision)` in one pinned
  shared environment.
- `S = (ROC AUC + trapezoidal PR AUC) / 2`.

The primary team comparison is the **unweighted mean of the five group S
values**. Also show each component's five values, mean and sample SD
(`ddof=1`). This is our explicit comparison convention; verify any later
official leaderboard implementation separately. Do not substitute average
precision for trapezoidal PR AUC.

Also retain average precision (AP), pooled out-of-fold curves/metrics clearly
labelled as pooled, and precision, recall, F1, specificity, accuracy and
TP/FP/TN/FN at the fixed threshold 0.5. Threshold metrics are secondary:
scores from class-weighted or uncalibrated pipelines need not have the same
probability calibration. Default: no learned calibration or tuned cutoff in
this first comparison. Any later calibration/threshold experiment needs a
declared training-only procedure and separate reporting.

Positive prevalence is only 4.49% in data0: an always-negative classifier has
about 95.51% accuracy, but detects no positives. Ordinary accuracy therefore
cannot be the main winner criterion. PR AUC also depends on the assessment
population/prevalence; do not attribute every data0-to-data1 PR difference to
model deterioration alone.

Report close or conflicting results as such. Fold SD is not a confidence
interval and the fitted folds are not independent experiments. A targeted
second seed or paired gene-resampling analysis can investigate a close result;
do not claim statistical superiority without suitable evidence. If performance
is practically unresolved, explain the choice using robustness, reproducibility
and measured cost rather than declaring a universal winner.

## 5. How Member 1 guides development and report evidence

The architecture is flexible. These are useful shared diagnostic/report ideas,
not compulsory identical modelling experiments for both owners:

- **Sequence context:** show counts/performance for all 18 central motifs,
  including sparse ones; use the seven-base context where relevant. Pooled
  current direction reverses within many motifs, so test context-dependent
  signal handling. Consider a sequence-only reference and a controlled
  context/signal comparison. Existing Elgin sequence inputs are not a new
  contribution merely because the new report discusses them.
- **Coverage:** show bins 20-49, 50-99, 100-199, 200-499 and 500+ reads with
  positives, negatives and metrics. Do a controlled with/without-explicit-
  coverage comparison if coverage is proposed as an input. This tests an EDA
  concern, without forcing both candidates to use coverage. All supplied sites
  have at least 20 reads; behaviour below that is unsupported.
- **Unusual distributions:** inspect a few broad-IQR cases against similar
  context/coverage controls and test one justified robust representation or
  aggregation change. Elgin already has medians/quartiles. An unusual site or
  disagreeing label is not proof of an error; retain valid cases.
- **Sparse groups:** show denominators. Mark one-class ROC/PR comparisons as
  not applicable; flag groups with fewer than 20 positives or negatives as
  weakly supported. Twenty is a display warning, not an eligibility cutoff.
  Do not make a new headline score by averaging only the well-performing motifs.

For a manageable first cycle, two concise comparisons motivated by EDA are
recommended, rather than an exhaustive feature search. Screening-round
evidence is allowed when clearly labelled; it does not replace the common
five-round finalist comparison. Small read-
subsampling checks are optional further evidence: use the same held-out sites
and random read selections for both models. Recompute all read-derived inputs,
including any predictive coverage feature, from the sampled reads. Keep original
coverage separately for slice labels and preserve sequence context. Repeated subsets are not
independent biological replicates.

## 6. data1, data2 and SG-NEx have different roles

**data1: exposed cross-cell-line transfer diagnostic.** Official intermediate
leaderboard slides identify data0 as HCT116, data1 as HEK293T and data2 as
synthetic sequences. Do not use data1 for fitting, early
stopping, hyperparameter choice or winner selection in this cycle. Nominate
both final configurations, refit each on all data0 and save/hash both artifacts
before scoring data1. Report both frozen artifacts on all 90,810 sites, plus
shared-site (67,320) and data1-only-site (23,490) slices. Keep the original
targets, including the 3,872 shared sites with opposing labels.

Site novelty is not gene novelty. 15,137 data1 sites have unresolved gene
mapping through data0; report that limitation and establish provenance before
pooling or claiming gene/cell-line independence. data1 has 7.26% positives.
Its previous evaluation and EDA exposure remain disclosed. If its result
changes our selection or prompts a revision, say explicitly that it informed
development; it has not become a blind test again.

If using the supplied inner-stopping default, use the median of the five
selected stopping counts for each all-data0 refit. Otherwise declare a
training-duration rule derived within data0. Use nominated hyperparameters
and newly fitted data0 preprocessing. Archive
the other candidate for comparison. The selected **single saved pipeline**
then generates all three required dataset predictions and the SG-NEx outputs;
do not use out-of-fold scores for data0 and the final artifact for the others
while claiming all three came from one saved model. Label final-model data0
metrics as in-sample; they are not the out-of-fold evaluation.

**data2: synthetic fractional/template diagnostic.** Preserve its
fractional labels and 189 repeated position/context templates across seven
groups. Describe scores, matched-template ordering and coverage. Do not round
fractions into binary targets, compute ordinary binary AUC on all rows, assume
1,323 independent biological samples, or call the site score a modification
fraction. Suitable quantitative targets require confirmed label semantics and
source-read provenance. Exclude it from tuning in this cycle.

**SG-NEx: application and biological exploration.** Resolve run/sample/cell-
line/replicate metadata and input compatibility, then apply the selected frozen
pipeline. Analyse missingness, coverage/context shift, replicate consistency
and supported between-cell-line contrasts. Missing sites are not negatives;
predictions and agreement with m6Anet are not ground truth. The existing
dashboard scores are simulated and must be replaced before scientific use.
Choose replicate aggregation and comparable-site populations before drawing
biological conclusions; do not tune until biological differences disappear.

The official intermediate leaderboard slides announce four additional datasets
for final ranking, with final-model results also required for the original
three. Check availability, provenance and overlap; reserve eligible new
evaluation data from selection. A fresh independent result requires keeping
its answers and assessment scores outside tuning. A retrospective split does
not become a fresh blind test.

## 7. Lightweight handover and next implementation

Each owner keeps one methods/results draft backed by commands, dependencies,
configurations/seeds, source/split hashes, per-group predictions/metrics,
checkpoints and logs. Record training and inference wall time, hardware/threads,
peak-memory measurement method and artifact size. Include initial plus refit
cost; do not compare timings from different machines as a controlled speed test.
Keep large checkpoints locally or in agreed storage rather than committing
every intermediate file. New claims need actual results, including failures.

The [minimum shared rules](SHARED_RULES.md) link the exact outer manifest,
default inner roles, common prediction validator/scorer and commands. Scoring
checks file consistency, not a model's actual training history. New candidate
training and comparisons remain pending. Coordinate the required
simple baseline and m6Anet benchmark, documenting pretrained-data overlap and
any different eligible populations/settings. Historical rounded LightGBM
metrics are not a fresh controlled baseline.

Use the five-fold development comparison to nominate the final pipeline,
retain frozen data1 diagnostics even if unfavourable, and write two or three
report chains: **EDA observation -> decision -> controlled result -> limitation**.
Members 4/5 can prepare SG-NEx inventory and the interface in parallel.

Method references: [group-aware validation and preprocessing boundaries](https://scikit-learn.org/stable/modules/cross_validation.html),
[precision-recall curve API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_curve.html),
[AP differs from trapezoidal area](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).
Project-specific evidence is in Member 1's received package and the linked
composition audit; this methodology does not replace the course handout.
