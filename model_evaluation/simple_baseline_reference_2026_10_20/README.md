# Saved simple-baseline reference checked on20October2026

The existing logistic-regression package was independently rescored on data0
using this repository's common evaluator. No model was fitted, no model
inference was rerun and no data1 input was used in this check.

| Historical configuration | Mean-fold ROC AUC | Trapezoidal PR AUC | AP | S |
|---|---:|---:|---:|---:|
| A: basic, unweighted C1 |0.796838|0.154965|0.155478|0.475901|
| B: balanced class weights C1, historically selected |0.804056|0.149129|0.149553|0.476592|

Both use18 site-level means/population SDs from all nine event features,
training-fold StandardScaler and L2 logistic regression. Supplied code fits a
fresh scaler/model on four gene groups and predicts the fifth. B was selected
from five settings using mean data0 S; its continuous scores exactly match
the B column in the retained all-config score archive. Different features,
losses, seeds and training procedures make this a pipeline comparison, not an
isolated claim about model families.

All121838 sites/5475 positives/3852 genes, labels and exact fold assignments
match. All five historical fold and mean ranking metrics reproduce within
1e-12. The original source, model and OOF files were unchanged by the check.
`A_shared_metrics.json`, `B_shared_metrics.json` and `audit_receipt.json` retain
exact metrics, common-scorer versions and original evidence hashes.

For context, the completed original-feature neural control's mean S is
0.7176418289402133. The cap128 neural experiment is still running; it does not
have a full comparison result yet. These figures are data0 development
evidence and do not establish blind test or cell-line transfer superiority.
The required published m6Anet benchmark remains pending.

## Exact audit commands

Executed from the repository root with the original local LOGREG handover:

```powershell
../advanced_model/.venv/Scripts/python.exe -B model_elgin/outputs/read_cap_v1/checks/logreg_reference/audit_logreg_reference.py
../advanced_model/.venv/Scripts/python.exe -B model_evaluation/evaluate.py --dataset data0 --labels ../data0/data.info.labelled --folds eda/received/shared_folds/data0_folds.csv --predictions model_elgin/outputs/read_cap_v1/checks/logreg_reference/selected_B_data0_oof.csv --output model_elgin/outputs/read_cap_v1/checks/logreg_reference/B_shared_metrics.json
../advanced_model/.venv/Scripts/python.exe -B model_evaluation/evaluate.py --dataset data0 --labels ../data0/data.info.labelled --folds eda/received/shared_folds/data0_folds.csv --predictions model_elgin/outputs/read_cap_v1/checks/logreg_reference/basic_A_data0_oof.csv --output model_elgin/outputs/read_cap_v1/checks/logreg_reference/A_shared_metrics.json
```

The audit script and reformatted per-site predictions stay local/ignored;
these commands need those local evidence files. This compact reference does
not provide a self-contained baseline-training pipeline in a fresh clone.
The original package remains at `../LOGREG_results/logistic_regression/`.
Final submission reproduction needs its reviewed source integration or a
separate documented baseline replay. The actual audit took34.071970seconds;
that is score checking time, not model-training cost.

## Limits

Historical fitting was not replayed. The original receipt lacks a training-
source fingerprint and per-fold fitted scalers/models. Current supplied code,
manifests and exact saved-score alignment support the stated methodology but
do not independently prove historical training separation. Previous data1
exposure remains disclosed; the inspected config-selection code uses data0.
This is a checked historical reference, not a newly trained baseline.
