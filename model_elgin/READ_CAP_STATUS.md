# Training read-cap experiment: execution status

**20 October 2026, 17:10 SGT snapshot: full five-fold cap128 training is running.**
This is a dated status record, not a live progress indicator. No completed
candidate score or improvement is available at this snapshot.

The user authorised the single-change experiment after the completed depth
and raw-signal reviews. The immutable [design](READ_CAP_EXPERIMENT.md) changes
only the training read cap32->128. Earlier original-feature full data0 S is
0.7176418289402133; it remains the comparator, not a result of the new run.
Training uses data0 only, the same five gene folds, inner stopping and fresh
four-group refits. Assessment uses all reads. No data1/final all-data0 fit or
threshold selection is part of this run.

## Completed checks and measured trials

- Six meaningful training-contract tests passed in9.834s: exact cap32
  delegated/original tensors/losses/norm/predictions;128-read training bounds;
  original all-read summaries/assessment; exact interrupted cap128 recovery;
  changed-identity refusal; live/stale process-lock handling.
- Fourteen report-contract tests passed in18.214s on the integrator's run.
  They cover incomplete/mutated evidence, exact recipes/split/environment
  signatures, negative results, resource accounting and report/plot hashes.
  A prior local attempt failed because the sandbox's default temporary folder
  was unwritable; workspace-local TMP/TEMP/TMPDIR/MPLCONFIGDIR fixed the test
  environment. Training was unaffected. Both logs are retained.
- Actual whole-gene smoke:3328 data0 sites, fold0, two inner and two refit
  epochs. CLI27.3477181s, exit0; analysis timer13.0849585s, process CPU22.4375s,
  sampled process-tree peak558.574MiB. This is software evidence, not CV quality.
- Full-size one-epoch timing trials, never reused as CV weights:

| Setting | Fit sites | Inner validation sites | Epoch seconds | Fit CPU seconds | Sampled fit peak MiB |
|---|---:|---:|---:|---:|---:|
| cap32 inner |73109|24371|17.998548|78.718750|835.219|
| cap128 inner |73109|24371|31.582003|124.453125|896.703|
| cap128 refit |97480|0|36.449385|144.375000|897.137|

Timing CLI130.3714597s, exit0. Per-fit CPU/memory includes normalisation/setup;
epoch times exclude those operations. Independent sampling intervals can give
different observed memory peaks. These are measurements on this laptop, not
an isolated hardware-fair speed claim. Maximum20+20 epochs per fold projects
113.4minutes of epoch work, excluding startup/normalisation/outer assessment;
early stopping may shorten it. Announced full-run estimate90–120minutes is
conditional, not a completion promise.

## Running and resuming

The full command was launched around17:08 SGT from the repository root:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_read_cap.py --phase cv
```

Local ignored evidence is under `outputs/read_cap_v1/`: `checks/full_cv.log`,
`cv_status.json`, per-invocation resource records, and
`cv/none/fold{0..4}/{inner,refit}/` last/best weights, optimiser/RNG checkpoints,
history and logs. The trainer saves every completed epoch. Run the identical
command after interruption; a live-process lock refuses duplicate writers,
and changed settings/source/input/version signatures refuse incompatible
recovery. Keep the immutable wrapper/plan/core sources fixed during this run.

After all five folds complete, run:

```powershell
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_read_cap.py
```

The reporter refuses partial evidence and writes the actual comparison under
`outputs/read_cap_v1/comparison/`. Publish a compact checked result later;
full site predictions, checkpoints and logs remain local. Record negative or
inconclusive results as carefully as gains. Required baseline/m6Anet checks,
final model/calling-rule selection and real23-run SG-NEx analysis remain
separate work. The saved logistic-regression reference is being audited so
we can reuse valid evidence instead of assuming a missing baseline.
