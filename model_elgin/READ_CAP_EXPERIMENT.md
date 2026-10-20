# Training read-cap experiment: fixed design

Specified before candidate outcomes, 20 October 2026. Keep this file unchanged
after the first saved fit: its canonical hash is part of checkpoint identity.
Record progress/results separately.

## Question and EDA link

Does increasing the training read-branch sample from32 to128 improve the
original-feature neural model's held-out-gene ranking on the full data0?
Member1 motivated coverage/unusual-read analysis. Subsequent matched depth
tests supported keeping all-read inference, and case inspection found varied
overlapping error distributions rather than one universal outlier signature.
The current training branch sees at most32 reads but inference uses all reads.
Larger training bags are a coherent hypothesis, not a proven repair or gain.
Do not delete unusual valid sites, add motif overrides or infer molecule labels.

## Single intended change

- Candidate: original network/features with `cap=128`. Comparator: completed
  original-feature `cap=32` full CV at `outputs/context_reference_v1/cv/none`.
- Reuse the unchanged frozen trainer, model, data parser/transforms and common
  scorer through `tools/train_read_cap.py`. Fingerprint wrapper and this plan
  in addition to the original core source. Verify the comparator before fitting.
- Preserve width48, dropout0.25, AdamW lr0.001/weight decay0.0001, positive
  loss weight3, batch256, four CPU threads, seed2026, maximum20 inner epochs,
  patience5, original sequence embedding and63 all-original-read summaries.
- Preserve the exact121838 data0 sites and immutable five gene folds. For foldf,
  use inner(f+1)%5: train three groups, select stopping duration on the separate
  inner group, then freshly refit four groups and evaluate foldf. Fit every
  transform only on permitted fitting groups. Start every fit from fresh weights.
- Keep existing uniform sampling without replacement and RNG algorithm;
  sampling/gradients and selected epoch counts may change as consequences of
  changing cap. Do not engineer nested32/128 training draws as another change.
- Assessment always uses all available reads and original all-read summaries.
  No data1/data2/SG-NEx, calibration, threshold selection or final all-data0
  model fit is authorised by this experiment entrypoint.

## Checks, timing and recovery

First verify configuration/core-source equality to the saved comparator,
cap32 delegated-versus-original tiny-fit equality, actual128-read batch bounds,
unchanged summaries/all-read assessment and interrupted-fit recovery.
Run a small whole-gene data0 smoke check. Measure full-size fold0 one-epoch
inner fits at32/128 and a128 four-group refit in a separate timing directory.
These are software/timing trials, not performance comparisons or warm starts.
The full candidate then starts fresh in `outputs/read_cap_v1/cv/none`.

Every completed epoch saves last/best weights, optimiser/RNG states and logs.
Resume the identical command; incompatible config/source/input hashes fail.
A per-phase process lock refuses simultaneous writers; stale locks are retained
as evidence. Completion of a requested partial fold list is not full five-fold
completion. Keep wrapper/core/plan fixed during the run. Full experiment
resource records and console logs include actual wall/CPU/RAM measurements;
sampled memory is not an exact OS maximum. Lost mid-epoch work may be replayed.

## Decision and reporting

Primary S: mean over the five held-out gene folds of (ROC AUC + trapezoidal
PR AUC)/2. Also retain ROC, trapezoidal PR, AP, paired fold differences and
sample SD. Cutoff0.5 precision/recall/F1 are descriptive, not an optimised or
validated biological operating rule. Never substitute a high-depth subset
score for the full-CV result or choose a winner from data1.

Keep the candidate only if the measured evidence justifies it; retain negative
or inconclusive findings. One seed, reused development folds, overlapping
training groups and previous architecture decisions limit generalisation and
attribution. This comparison cannot establish universal best performance,
independent biological significance or cross-cell-line transfer gains.
Required simple-baseline/m6Anet benchmarks, final nomination/refit, data0-inner
cutoff validation and real SG-NEx predictions remain separate pending work.

## Commands from the repository root

Use the same original local data0 cache/labels and environment. Outputs remain
ignored; public GitHub receives source and compact results rather than raw data.

```powershell
../advanced_model/.venv/Scripts/python.exe -B -m unittest discover -s model_elgin/tools -p test_train_read_cap.py -v
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_read_cap.py --phase smoke
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_read_cap.py --phase benchmark
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_read_cap.py --phase cv
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_read_cap.py
```
