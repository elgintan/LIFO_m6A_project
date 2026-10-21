# Candidate comparison and selected-model evaluation

Elgin coordinates this folder with Samuel. It does not assume either candidate
has won. Candidate-specific experiment history stays in its model folder;
this folder will consolidate comparable evidence, selection rationale and
the frozen selected model's evaluation.

Start with [minimum shared rules](SHARED_RULES.md): Elgin accepted the
methodology on 15 October 2026; Samuel subsequently supplied a candidate using
these rules. Exact outer assignments already exist, so no resplitting is needed.
The common [scorer](evaluate.py), [dependencies](requirements.txt) and
[optional default inner roles](cv_rounds.csv) are included. The
[detailed methodology](EVALUATION_PROTOCOL.md) gives rationale and EDA/report
suggestions. Architecture, features and tuning remain independent.

Verify local inputs against the manifest before new fitting. Keep assessment
genes outside all learned fitting and use the same evaluation population.
Elgin's full matched neural CV and Samuel's received CV are complete; the
shared scorer independently reproduces Samuel's provided data0 scores.
The [21 October shared comparison](../model_elgin/read_cap_shortfalls_results/README.md)
favours cap128 under the primary data0 criterion: S0.718715 versus cap32
0.717642 and Samuel0.710446. Samuel performs better on some secondary metrics;
the [review](../model_elgin/SHORTFALL_REVIEW_2026_10_21.md) documents those tradeoffs
and a proposed training-side threshold assessment. No cutoff or calibrated
probability was fitted in that saved-score analysis.
The later [training-side cutoff study](../model_elgin/THRESHOLD_REVIEW_2026_10_21.md)
selected maximum-F1 cutoffs on each round's inner genes and assessed only its
excluded outer genes. Pooled F1 changed0.535041->0.534624; mean-fold F1 was
nearly unchanged. The0.510309 median is an unevaluated final-model proposal,
not the cutoff used for those pooled results. Keep0.5 as the working rule;
this is a development choice, not a biological threshold/calibration claim.
The next authorised [weight3-to1 comparison](../model_elgin/LOSS_WEIGHT_EXPERIMENT.md)
preserves the same cap128 network, all sites, gene folds and evaluator. Its
[execution status](../model_elgin/LOSS_WEIGHT_STATUS.md) distinguishes checks
from full CV; a new full candidate score is not yet available.
No final model has been selected. Current comparisons and outstanding work
are in [integration status](../INTEGRATION_STATUS.md). New all-data0 fitting
for Elgin's eventual nominated pipeline and real SG-NEx predictions are
still pending. Historical 7 October evidence remains distinct.

Software verification on 15 October: 14 scorer tests passed, and the existing
fold verifier passed against the real 121,838-site data0 labels with 3,852
genes. The exact fold file and all archived source hashes are unchanged.
These are file/software checks, not new model results. Checked on Windows
with Python 3.12; a clean Ubuntu run remains pending. To run the small checks:

```text
python -B model_evaluation/test_evaluate.py
```

Both models use the same evaluation sites and score conventions. Record ROC
AUC, explicitly named trapezoidal PR AUC and AP separately. Keep thresholds
and confusion metrics explicit. Preserve full-precision predictions, class
counts, motif/coverage support, costs and verified code/model versions. AUCs
for one-class subgroups are undefined; small groups need honest limitations.

Model selection uses the agreed development comparison. A reserved future
official/eligible external evaluation, if available, must stay outside selection.
Supplied datasets have previous exposure; do not call repeated scoring blind.

The report requires comparison against a simple baseline and published m6Anet.
Those new controlled comparisons remain pending. Prespecify their input
coverage, provenance, prediction/training settings and comparable populations.
Record differences in eligible sites rather than silently dropping difficult
cases to make one method appear better.

Expected handover: one short evaluation draft, metrics/comparison table,
essential plots and reproducible checking code. State which changes helped,
which did not and why one final pipeline was selected. Only actual verified
results belong in the final-results section.
