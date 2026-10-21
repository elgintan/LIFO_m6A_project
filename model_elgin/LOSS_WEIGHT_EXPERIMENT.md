# Positive-loss-weight experiment: fixed design

Specified before candidate fitting, 21 October 2026. Keep this file unchanged
after the first saved fit; its canonical hash is part of checkpoint identity.
This is the last planned bounded neural training experiment before the
required benchmarks, final nomination and application/report work.

## Question and previous evidence

Does changing positive-label loss weight from3 to1 improve the cap128 model's
held-out-gene ranking or score reliability? The current cap128 model has
mean-fold ROC0.9318281774, trapezoidal PR0.5056010366 and S0.7187146070.
It ranks above Samuel under the agreed rule, but raw-score reliability and
false-positive/missed-positive tradeoffs remain weaknesses. The completed
inner-group threshold study gave no convincing F1 gain and worsened
high-depth recall; 0.5 remains a working reporting rule for weight3.

Weight1 removes the extra positive-example penalty. It may reduce recall or
fail to improve ranking. It is not a demonstrated repair for outliers or
high-coverage misses. Member1's EDA motivates the subgroup checks and retaining
natural prevalence, valid unusual sites and all18sequence motifs. Do not
oversample/relabel/drop sites or add features in this experiment.

## Single intended change

- Comparator: completed cap128 original-feature, weight3 pipeline at
  `outputs/read_cap_v1/cv/none`. Reuse its verified saved fits and scores.
- Candidate: identical pipeline with `pos_weight=1.0`; cap remains128.
  Reuse the unchanged core trainer/model/data/transforms/common scorer through
  `tools/train_loss_weight.py`; do not edit the older frozen source/recipes.
- Preserve width48, dropout0.25, AdamW learning rate0.001, weight decay0.0001,
  batch256, four CPU threads, seed2026+fold (refit+100), maximum20inner epochs,
  patience5, minimum context support30, original seven-base sequence embedding,
  attention/mean/variance read pooling and63all-read summaries. No context
  reference features or explicit coverage inputs are added.
- Preserve all121,838data0 sites,5,475positives and exact accepted five gene
  folds. For outerf, initially fit the three groups excludingf and(f+1)%5,
  select duration on inner(f+1)%5, start fresh weights and freshly refit the
  other four groups for that duration, then assessf. No old all-data0 weights
  or parent best weights initialise a held-out fit.
- Fit preprocessing inside the current fitting groups. Training uses uniform
  read samples capped at128; summaries and all assessment use all reads.
  Seed rules match; resulting gradients and selected durations may differ as
  consequences of the changed objective. Do not force identical epochs.
- No data1/data2/SG-NEx inputs, new cutoff selection, probability calibration
  or final all-data0 model fit is included. The weight3 threshold study cannot
  be called a validated operating policy for a newly trained weight1 model.

## Checks, timing and recovery

Before full CV, test that the candidate differs only in positive loss weight,
that a weight3 delegation reproduces the unchanged trainer exactly, and that
an interrupted weight1 fit resumes with identical optimiser/RNG/results.
Verify all-read summaries/assessment, identity/source mismatch rejection,
fixed gene boundaries and phase lock handling. Run a small whole-gene smoke
check and full-size one-epoch weight1 inner/refit timing trials in separate
directories. These are software/timing evidence, not full comparison scores.

Use the original fitting environment and check its exact version strings.
The new identity inherits every cap128 parent fingerprint and adds the new
wrapper/plan hashes under `loss_weight_entrypoint_sha256` and
`loss_weight_plan_sha256`, with their two entries in the source map. Every
epoch saves last/best weights, optimiser/RNG states, histories and resources.
Resume the identical command; incompatible settings/sources/inputs must fail.
Keep checkpoints/logs and recorded interrupted work. PID locks are only
authoritative within their process namespace; verify the original execution
session has ended before resuming rather than inferring death from an
unrelated tool's missing PID.

## Decision and report

Primary S is the unweighted mean of five fold-level
`(ROC AUC + trapezoidal PR AUC)/2`. Retain ROC, trapezoidal PR, AP, paired
fold changes and sample SD. Preserve all five held-out results, including a
negative or practically unresolved outcome. Fixed0.5 precision/recall/F1 and
raw-score reliability are secondary descriptive checks, not calibrated
probabilities or a newly optimised threshold. Pooled metrics are supplementary.

If weight1 does not justify replacing the current candidate, retain weight3.
If it leads the primary criterion, inspect the same coverage/motif/unusual
groups before nomination and reassess its operating policy separately. Do
not choose a winner using data1. One seed, overlapping training groups and
repeated development limit inference; no universal-best or significance
claim follows from this experiment. A small gain must be weighed against
robustness, computation and the remaining report/application requirements.

The report should retain the full progression: EDA -> failed context-feature
change -> depth/signal investigation -> modest cap128 ranking gain -> mixed
threshold-policy result -> this objective test -> justified final choice.

## Commands from the repository root

```powershell
../advanced_model/.venv/Scripts/python.exe -B -m unittest discover -s model_elgin/tools -p test_train_loss_weight.py -v
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_loss_weight.py --phase smoke
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_loss_weight.py --phase benchmark
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_loss_weight.py --phase cv
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_loss_weight.py
```

Full outputs stay in `model_elgin/outputs/loss_weight_v1/`; public GitHub gets
source, checked aggregate evidence and reproducible commands. Required m6Anet
comparison, final frozen model/data1, same-model dataset predictions and real
23-run SG-NEx analysis/explorer/report remain separate pending deliverables.
