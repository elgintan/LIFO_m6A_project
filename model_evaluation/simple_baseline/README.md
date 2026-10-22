# Fixed simple-baseline replay

This independently implements the historical logistic-regression **B** recipe
as a reproducible data0 baseline. It does not repeat the original five-setting
search, fit a final all-data0 deployment model, or predict data1/data2.
The historical checked scores remain in
[the reference](../simple_baseline_reference_2026_10_20/README.md); those are not
results of this new replay. No new full-data result is asserted here.

Each site supplies nine raw read-level measurements. Compute all nine means,
then all nine population SDs (`ddof=0`) in **float64**, directly from the original
JSON(.gz). No neural float32 cache, signed logs, 63-summary normalisation,
sequence feature, outlier filtering or coverage feature is used. Invalid reads
abort instead of silently changing the training population. The seven-base
context is validated but never given to the classifier.

For each of the exact five shared gene groups, fit a fresh `StandardScaler`
and L2 logistic regression on the other four groups, then score the excluded
group. Fixed parameters: `C=1`, `class_weight='balanced'`, `solver='lbfgs'`,
`max_iter=1000`, `tol=1e-4`, seed42 and two CPU threads. Balanced weights come
from that fit's training labels. No inner split or stopping search is needed
because these settings are fixed. The earlier historical selection of B
remains disclosed; this is development evidence, not a blind test.

## Commands from the repository root

Use the existing comparison environment; do not modify it for this baseline:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -m unittest discover -s model_evaluation/simple_baseline -p test_replay.py -v
../advanced_model/.venv/Scripts/python.exe -B model_evaluation/simple_baseline/replay.py --phase prepare
../advanced_model/.venv/Scripts/python.exe -B -u model_evaluation/simple_baseline/replay.py --phase cv
```

`prepare` hashes the pinned raw data0/labels/folds and builds the raw float64
features without fitting. `cv` reuses an identical verified feature cache and
completes all five fits. Optional explicit paths:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -u model_evaluation/simple_baseline/replay.py --phase cv --data ../data0/dataset0.json.gz --labels ../data0/data.info.labelled --folds eda/received/shared_folds/data0_folds.csv --output-dir model_evaluation/simple_baseline/outputs/replay_v1 --threads 2
```

The default local output is `model_evaluation/simple_baseline/outputs/replay_v1`.
Outputs cannot overwrite source files or move outside this module's `outputs/`.
They include float64 features/receipt; per-fold JSON scaler, coefficients and
intercept; split audits; four-column OOF CSVs; completion and invocation
receipts; warnings/iterations; `training.log`; exact argument records; and
`data0_cv_metrics.json` from the unchanged shared scorer. Primary evidence is
mean-fold `(ROC AUC+trapezoidal PR AUC)/2`; pooled metrics/AP remain separate.

Repeat the same command to reuse completed, hash-verified folds. A running
lock prevents duplicate jobs. An interrupted fit restarts that fold; completed
folds are preserved. After a hard process kill, confirm the original execution
session has ended before explicitly removing only its stale `run.lock`.
Changed inputs, source, feature bytes, dependencies or settings require a new
output directory. Never edit a completed receipt to force reuse.

Resource records measure actual wall/process-CPU time and sampled **this-process**
RSS. Per-fold timers cover scaling, fitting, prediction, artifact parity and
metrics, excluding file writes. Invocation timers also include input hashing,
feature work, verification and outputs. Feature and fold records may overlap
invocation timing: do not add them to invocation totals. Interrupted attempts
are retained separately; do not count resumed completed receipts twice.

## Compatibility and verification limits

Source syntax supports Python3.8+. For actual comparison, use the retained
Python3.12 environment and its exact versions. `requirements.txt` provides
older compatible pins for separate environments; Python3.8 execution is not
claimed tested. The L2 parameter spelling adapts to the installed sklearn API
without changing its mathematical objective. Different libraries/hardware can
change floating-point digits; do not hardcode the historical score as a target.
No non-default parameter is chosen from these replay results.

On restricted Windows runners, set `TEMP`, `TMP`, `TMPDIR` and `MPLCONFIGDIR`
to newly created workspace-local scratch folders before software tests. Tests
use small synthetic bags/labels only, checking float64 feature order, population
SD, training-only scaling, gene boundaries, real coefficient learning, JSON
score parity, interrupted/completed-fold recovery and mutation refusal.

Historical Apple hardware recorded 13.55s feature extraction and 2.34s for
25 fits. Those are historical measurements, not a current-machine estimate.
The raw compressed input is about180MB; initial `prepare` timing provides the
current extraction cost. This fixed replay requires only five small
18-feature fits, not another neural search. A full-data run remains pending
until the operator has reviewed the implementation and announced execution.

**Observed software check, 22 October 2026:** all **10 synthetic tests passed**
in **2.205 seconds** of unittest runtime in the retained Python3.12 environment
(startup/import time excluded). The command above used workspace-local
`TEMP`/`TMP`/`TMPDIR` under `outputs/software_checks/tmp_20261022` because the
runner's default temporary folder is restricted. Python3.8 syntax was checked
with the parser; execution on Python3.8 remains unverified. No real data0
extraction or full-data fitting was performed as part of that check.
