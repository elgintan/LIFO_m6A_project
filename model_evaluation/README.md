# Candidate comparison and selected-model evaluation

Elgin coordinates this folder with Samuel. It does not assume either candidate
has won. Candidate-specific experiment history stays in its model folder;
this folder will consolidate comparable evidence, selection rationale and
the frozen selected model's evaluation.

Read [shared evaluation proposal v1](EVALUATION_PROTOCOL.md), which gives the
concrete recommendation and rationale. It is not yet agreed or executed.

Before new training, agree that proposal and `../DATA_METHODOLOGY.md`: target/eligible populations,
actual gene-group assignments, tuning/early-stopping boundaries, input versions,
metric definitions and final-assessment exposure. Member 1's context/coverage
findings and the historical-split audit must inform those decisions.

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
