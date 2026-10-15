# Candidate comparison and selected-model evaluation

Elgin coordinates this folder with Samuel. It does not assume either candidate
has won. Candidate-specific experiment history stays in its model folder;
this folder will consolidate comparable evidence, selection rationale and
the frozen selected model's evaluation.

Start with [minimum shared rules](SHARED_RULES.md): Elgin accepted the
methodology on 15 October 2026; Samuel's acknowledgement has not yet been
reported. Exact outer assignments already exist, so no resplitting is needed.
The common [scorer](evaluate.py), [dependencies](requirements.txt) and
[optional default inner roles](cv_rounds.csv) are included. The
[detailed methodology](EVALUATION_PROTOCOL.md) gives rationale and EDA/report
suggestions. Architecture, features and tuning remain independent.

Verify local inputs against the manifest before new fitting. Keep assessment
genes outside all learned fitting and use the same evaluation population.
No new model has been trained or selected under these rules yet.

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
