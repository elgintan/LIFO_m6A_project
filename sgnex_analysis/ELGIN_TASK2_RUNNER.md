# Sequential Task 2 prediction with the selected model

Run commands from the repository root. Use the Python3.12 environment in
[the final model guide](../model_elgin/FINAL_MODEL_USAGE.md); on the current
laptop its executable is `../advanced_model/.venv/Scripts/python.exe`.
The received Member4 coverage matrix and explicit alias table must already be
restored as described in [the analysis guide](README.md).

This workflow uses the **same saved cap128/weight3/18-epoch model for every
run**. It does not retrain, tune a cutoff, perform biological comparisons or
build the explorer. The inventory fixes23 runs. The active prediction manifest
fixes cell-line/replicate identities, output paths and the selected model.

## Check the plan without starting work

```text
python -B sgnex_analysis/scripts/run_elgin_task2.py --all --plan-only
```

This reports all23 run IDs, their saved raw-file sizes, expected >=20-read
prediction counts and source fingerprints. It creates no batch state and
starts no downloads or inference. Full raw inputs total33,365,823,342bytes;
derived eligible inputs, QC tables, CSVs and logs require additional local
storage. This is a storage inventory, not a measured full-batch runtime.

## Verify an already completed run and its resume behaviour

After its raw signal, successful download receipt, frozen-model output and
full-input audit exist, this command checks that one run:

```text
python -B -u sgnex_analysis/scripts/run_elgin_task2.py --run-id SGNex_Hct116_directRNA_replicate3_run4 --state-dir sgnex_analysis/outputs/checks/runner_completed_first_v1
```

The canonical audit path is
`sgnex_analysis/outputs/input_audits/SGNex_Hct116_directRNA_replicate3_run4.json`.
Existing raw bytes require agreement with their earlier successful download
SHA256 receipt; matching file size alone is insufficient. A cached audit must
match the current input, inventory, coverage, alias, auditor and parser hashes.

Repeat the **identical command** to check completed-run resume. The runner
rechecks all prediction/export/QC/log hashes, original prediction keys and
Member4's coverage counts before skipping that completed run. A marker or
checkpoint alone does not prove completion. Software-test runs do not replace
this real-data check.

## Run the full23-run pipeline

Use a separate state directory for the full population:

```text
python -B -u sgnex_analysis/scripts/run_elgin_task2.py --all --state-dir sgnex_analysis/outputs/elgin_task2_pipeline_v1
```

The stages execute sequentially for each run:

1. Download missing raw signals using the unchanged public-manifest helper.
   Existing inputs are checked against prior recorded content hashes.
2. Audit every source site/read against the fixed Member4 inventory and
   coverage table. Only explicit per-run aliases are used for this comparison.
3. Apply the selected model: full-source strict QC, then a label-free
   >=20-source-read input containing eligible original JSON record bytes.
   The unchanged predictor uses every read at each eligible site.
4. Verify all source counts, eligible prediction keys, original score-export
   bytes, model/source hashes and exact Member4 eligible coverage counts.

Low-coverage sites remain in QC metadata with an explicit exclusion reason.
They are **unscored for coverage QC**, not labelled unmodified. Malformed or
nonfinite reads fail the run even below the coverage threshold. Valid unusual
eligible sites are retained. Prediction IDs/positions are unchanged; explicit
aliases are used only when checking the inherited coverage population.

The batch uses fixed minimum20 reads, four threads,32-site batches and a
65,536 padded-read budget. Later50/100-read sensitivity analyses use subsets
of these same scores. Changing the model, source code, inputs, coverage,
aliases, selected population or pinned parameters is refused within an
existing batch identity.

## Progress, logs and safe stopping

The state directory contains `plan.json`, `checkpoint.json`, append-only
`events.jsonl` and unique per-run stage logs. The plan fingerprints the model,
code, manifests and Member4 inputs. The checkpoint records the current stage
and verified completed runs. Stage wall timers include their checks/child
work and overlap child inference receipts; do not add overlapping timers or
describe them as total CPU measurements.

For a clean stop after the current run, create this control file while the
batch runs:

```powershell
New-Item -ItemType File -Path sgnex_analysis/outputs/elgin_task2_pipeline_v1/stop_after_current_run
```

The runner checks it before starting another run and records
`stopped_at_run_boundary`. Once the original process has exited, remove only
that control file and repeat the identical batch command:

```powershell
Remove-Item -LiteralPath sgnex_analysis/outputs/elgin_task2_pipeline_v1/stop_after_current_run
```

Do not remove `run.lock` or an adapter lock while its original process may
still be active. An immediate interrupt stops only the runner's own child
tree and preserves partial evidence. Completed runs can be verified and
skipped later. **Partial downloads/CSV inference do not resume in place.**
The original download helper restarts transfers rather than using byte ranges;
this wrapper refuses an existing `.partial` so it cannot silently overwrite
that evidence. A failed run's partial files require a deliberate preserved
attempt/fresh retry after checking the original process, while completed-run
checkpoints remain intact.

## What completion means

All23 verified prediction outputs are prerequisites for the Member4
replicate-aware comparisons and Member5 display build. Pipeline completion
does not establish exact historical reference/preprocessing provenance,
chemical coordinate offsets, calibration, modified-read fractions or causal
cell-line differences. Those limitations remain in MODEL_INFO and subsequent
scientific analysis. Keep full signals, derived site data and logs in ignored
local storage; publish documented code and supported aggregate evidence.

Focused software checks (synthetic fixtures; no downloads/training):

```text
python -B -m unittest discover -s sgnex_analysis/tests -p test_elgin_prediction.py -v
python -B -m unittest discover -s sgnex_analysis/tests -p test_elgin_pipeline.py -v
```
