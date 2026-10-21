# Training read-cap experiment: execution status

**Latest: resumed at the user's request on 21 October 2026, 09:11 SGT.**
Training is running. Completed outer folds0/1 were reused and fold2 inner
training continued at epoch4, as confirmed by the new console log. This is
a dated snapshot, not a live progress indicator; no full candidate score or
improvement is available yet. The remaining-time estimate at resume was
60–90 minutes, conditional on early stopping and laptop speed.

Before launch, source/settings/environment signatures and all five retained
last-checkpoint hashes matched the pause receipts. Weights, optimiser/RNG
states, embedded best weights and histories passed recovery checks. Wrapper,
immutable plan and core training sources remain unchanged. Original logs and
the verified117-file pause ZIP remain preserved; new timestamped logs are
used for the resumed invocation.

The same local PowerShell job runs the comparison reporter only if training
finishes successfully. There is no separate waiting helper to restart.
`checks/resume_pipeline_status.json` records this job's phase and exit codes.
The older `checks/after_cv.py` helper remains stopped. No second trainer or
reporter should be launched while this job is active.

**Historical pause, 20 October:** both original sessions stopped at the user's
request with folds0/1 complete and fold2 inner epoch3 saved. The verified ZIP,
pause receipts and `outputs/read_cap_v1/PAUSED.md` preserve that recovery point;
their paused status is superseded by the explicit resume above.

**20 October 2026, 17:10 SGT snapshot: full five-fold cap128 training is running.**
The running snapshot below is historical; the latest resume is recorded above.
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
- After the pause, fifteen report-contract tests passed in15.648s on the
  integrator's21October run. They also verify that a recovered resource
  snapshot is disclosed as a lower bound and counted once, alongside the
  separate resumed invocation. Fold2 inner epoch3 retained88.1514156 wall
  seconds and329.921875 process CPU seconds. Its original exit receipt was
  not flushed; unmeasured work after that checkpoint and before interruption
  is omitted. No exact total for the lost work is claimed.
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
The PID-based duplicate check was verified within one process namespace.
Codex Windows tool invocations can have isolated PID views, so a missing PID
in another invocation does not prove the worker stopped. Confirm the original
execution session has ended before resuming; never start a second copy merely
because another tool's process list cannot see the first.

The resumed job is already queued to run the following after all five folds
complete. For a later manual replay after that job has ended, use:

```powershell
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_read_cap.py
```

The reporter refuses partial evidence and writes the actual comparison under
`outputs/read_cap_v1/comparison/`. Publish a compact checked result later;
full site predictions, checkpoints and logs remain local. Record negative or
inconclusive results as carefully as gains. Required baseline/m6Anet checks,
final model/calling-rule selection and real23-run SG-NEx analysis remain
separate work. The saved logistic-regression reference audit is complete;
its limits are disclosed in the linked results below.

Historical continuation: an ignored local `checks/after_cv.py` helper waited
for the20October run. It was stopped with training and is not active after
the21October resume. Its first attempt incorrectly treated a PID hidden by
the Windows tool boundary as dead; the still-updating original session
disproved that assumption. A subsequent timestamp-based timeout also stopped
the helper while the original training later advanced. The final helper waited
for authoritative full completion/failure status; it started no training and
did not infer failure from PID visibility or elapsed inactivity. Its attempt
logs/status remain local. No model source or weights were changed by those
helper corrections. The [simple-baseline saved-score audit](../model_evaluation/simple_baseline_reference_2026_10_20/README.md)
is now complete; full baseline reproduction integration and m6Anet remain pending.
