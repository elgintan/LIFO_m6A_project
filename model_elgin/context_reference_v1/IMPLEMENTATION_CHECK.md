# Implementation check — 19 October 2026

These are assistant-executed software and small-run checks on Windows CPU.
They do **not** establish an improved model or a winner. Full data0 five-fold
comparison and new frozen data1 evaluation have not been run.

## What was implemented

The historical sequence-aware attention network has a fresh matched control
(`none`) and a candidate (`relative`) adding nine context-reference residual
features. Member 1's pooled versus within-motif signal differences motivate
the experiment. This is a hypothesis to measure, not a proven improvement.

References use equal-weight training-site medians with a fixed 7-base ->
central 5-base -> global fallback. The 30-site support cutoff is an engineering
choice. Absolute inputs remain present, and valid unusual sites are retained.
References do not represent known unmodified chemistry.

Gene grouping is implemented using the exact existing shared fold file:
`986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
The trainer verifies all 121,838 data0 sites before fitting. It selects epochs
on a separate gene group, then fits fresh weights and preprocessing on the
four permitted groups. It does not read data1.

Checkpoint recovery includes optimiser and random states, a consistent retained
best artifact, history and source/split/configuration fingerprints. Final fits
are promoted to a portable `model.pt` only after completion. Prediction checks
semantic source fingerprints, uses all reads and requires no labels/gene IDs.
Code fingerprints normalise Windows/Linux line endings; this is not a claim
that Linux execution has been tested.

## Observed checks

- **30 synthetic tests passed**, test runtime 82.833 seconds, exit 0. Tests cover
  training-only references/normalisation, fallback arithmetic, whole-gene
  boundaries, mask/permutation invariance, save/load, source/stage guards,
  complete prediction CSVs, exact interrupted/uninterrupted weights in both
  modes, best/checkpoint write gaps and final-fit promotion. Toy scores printed
  by tests are not course-data results.
- The existing complete data0 cache was verified and reused: 121,838 sites,
  11,027,106 site-read entries. Its stored preparation measurements describe
  the historical cache build, not this short verification invocation.
- **Both modes completed one real smoke round**, outer fold 0, one inner
  training epoch and one fresh-refit epoch each. A deterministic label-neutral
  selection retained 20 whole genes per shared group: **100 genes/3,328 sites**.
- Assessment CSVs each contain exactly 676 unique sites from the held-out
  group. Split audits and saved normaliser/reference fit-index hashes agree.
- A repeated identical command reused all completed fits successfully.
- The development predictor produced the exact three-column CSV for **10 real
  example sites/1,887 reads**, with full key coverage, finite probabilities,
  every read retained, and a manifest. This smoke-model example is a software
  check, not a submission or independent accuracy assessment.
- All **216 archived source-receipt files** and the shared folds remain byte
  unchanged. No shared methodology or Samuel model files were changed.

| Smoke round 0 role | Sites | Genes | Positive sites |
|---|---:|---:|---:|
| Initial fitting: groups 2/3/4 | 1,901 | 60 | 79 |
| Inner validation: group 1 | 751 | 20 | 34 |
| Fresh refit: groups 1/2/3/4 | 2,652 | 80 | 113 |
| Assessment: group 0 | 676 | 20 | 25 |

The two modes use these same populations. Assessment genes have zero overlap
with refitting genes; inner-validation genes have zero overlap with initial
fitting genes. The full five-fold performance result cannot be inferred from
this subset or its one-epoch scores.

## Interruption actually encountered

The first real run saved its completed initial-control epoch, then Windows
returned `PermissionError: [WinError 5]` replacing `history.json`. Its checkpoint
and error log were retained. Rerunning the **same command** restored that epoch
and completed the remaining fits. Another identical run reused all fits.
This verifies recovery from this observed filesystem error; it does not mean
Windows/OneDrive will never interrupt writes. Preserve existing outputs and
rerun unchanged, rather than editing fingerprints or deleting checkpoints.

The five measured fit invocations, including the failed/recovered invocation,
totalled **19.163 s wall / 24.484 s process CPU**, with maximum sampled process
tree RSS **551.07 MiB**. Measurement scopes cover per-fit preprocessing,
training/inner scoring and checkpoint/log work; they exclude top-level imports,
cache verification and metadata joins. These are smoke-check measurements,
not full-training costs or a fair mode-speed benchmark: startup, an interruption,
and overlapping software checks affect them. Each fit invocation and outer
inference has its own resource record, sampled every 0.2 seconds.

## Exact executed commands

Run from the repository root in PowerShell, using the existing local virtual
environment. No installation was needed.

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B -m unittest discover -s model_elgin/context_reference_v1 -p 'test_*.py' -v

& '../advanced_model/.venv/Scripts/python.exe' -B model_elgin/context_reference_v1/prepare.py --input ../data0/dataset0.json.gz --output-dir ../advanced_model/cache/data0

& '../advanced_model/.venv/Scripts/python.exe' -B -u model_elgin/context_reference_v1/train.py --cache ../advanced_model/cache/data0 --labels ../data0/data.info.labelled --output-dir model_elgin/outputs/context_reference_v1 --phase smoke --mode both --outer-folds 0 --max-epochs 1 --patience 1 --smoke-genes-per-fold 20 --threads 4 --batch-size 128

& '../advanced_model/.venv/Scripts/python.exe' -B model_elgin/context_reference_v1/predict.py --input model_elgin/baseline_2026_10_07/examples/input_10_sites.json --model model_elgin/outputs/context_reference_v1/smoke/relative/fold0/refit/best.pt --output model_elgin/outputs/context_reference_v1/smoke/example_predictions.csv --threads 4 --batch-size 32 --allow-development-model
```

The smoke command was invoked three times: failed initial write, successful
recovery, then successful completed-stage reuse. No hyperparameter was changed
between them. PowerShell `Tee-Object` retained console output under the local
ignored `model_elgin/outputs/context_reference_v1/checks/` folder.

## Retained evidence and next work

Code, tests, pinned requirements and this check are in this working folder.
Large local evidence is retained under `model_elgin/outputs/context_reference_v1/`:
`checks/unit_tests.log`, three smoke console logs, `checks/artifact_audit.json`,
`smoke/<mode>/fold0/{inner,refit}/` checkpoints/history/resources, split audits,
assessment predictions and the example CSV/manifest. The ignore rule prevents
accidental public upload of local caches/run metadata/checkpoints. Historical
reference metrics and predictions remain in
[the reference check](../reference_check_2026_10_19/README.md).

Next, complete the matched full-data0 five-fold runs and use the common scorer
to answer report RQ1. Then examine coverage/unusual-valid-site weaknesses for
RQ2. Nominate and freeze the selected data0 recipe before the already-exposed
data1 transfer diagnostic (RQ3). New full OOF metrics, comparative plots, a
new final artifact, three full prediction files and real Task 2 SG-NEx analysis
are **pending**. Use the [working guide](README.md) for those commands.
