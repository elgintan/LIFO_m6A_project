# Task 1: selected model, training and prediction

The selected configuration is the original sequence-aware multiple-instance
neural network: training cap128, positive loss weight3 and no extra relative
context branch. Its seven-base embedding and63 distribution summaries remain.
The [selection decision](FINAL_MODEL_SELECTION.md) retains the external
candidate's higher ranking score and unresolved promotion tradeoffs.

The packaged artifact is `artifacts/cap128_weight3_v1/model.pt`.
`metadata.json` records its SHA256, data0-only fitting population and18-epoch
recipe. `complete.json` fingerprints the release files. Epoch checkpoints,
optimizer/RNG state and training logs remain in local ignored outputs.

## Environment

Use Python3.12 and the pinned main-model requirements. For example, from the
repository root in a Python3.12 environment:

```text
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r model_elgin/context_reference_v1/requirements.txt
```

This is separate from the legacy Python3.8 Conda environment used for published
m6Anet. Install the CPU Torch wheel first, as in the passed Docker recipe, to
avoid requesting a CUDA runtime for this CPU predictor. Native Windows and
[hosted Ubuntu24.04 prediction](ubuntu_prediction_results_2026_10_23/README.md)
are checked. The separate user-executed [native RONIN/AWS Ubuntu26.04 example](aws_prediction_results_2026_10_24/README.md)
also passed with isolated Python3.12.15 and identical model/package pins. The
AWS preflight is additional assurance, not an extra deliverable in the handout.
See [submission readiness](SUBMISSION_READINESS.md) and the
[AWS reproduction instructions](AWS_PREFLIGHT.md). Installation commands alone do not
establish a completed prediction check.

## Small real prediction example

```text
python -B model_elgin/context_reference_v1/predict.py --input model_elgin/artifacts/cap128_weight3_v1/example/input.json --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output example_predictions.csv --threads 4
```

Expected output is ten rows with exactly three comma-separated columns:
`transcript_id,transcript_position,score`. Compare keys and scores with
`example/expected.csv`; allow absolute tolerance3e-6 for platform-dependent
floating-point differences. The example is the first ten real data0 sites,
for software checks only. It is training data, not unseen validation.
The sidecar `example_predictions.csv.manifest.json` must report complete
coverage, `stage=final_data0`, `all_reads_used=true` and the expected model hash.

For another compatible nine-feature JSON/JSON.gz file, replace only the input
and output paths. Predictions use the saved normalisers and every available
valid read. No labels are required by the predictor. A training cap of128
does not truncate prediction bags. Preserve output manifests alongside CSVs;
the script refuses incompatible existing output rather than silently overwriting.
For the actual new unlabelled test, follow its supplied naming/upload contract.
Do not automatically transfer Task2's >=20-read population filter to Task1.

## Reproduce the fixed final fit

Obtain the original course data0 signals and labels, then run:

```text
python -B -u model_elgin/train_final.py --input LOCAL_DATA/data0/dataset0.json.gz --labels LOCAL_DATA/data0/data.info.labelled --output-dir model_elgin/outputs/reproduced_final
```

This prepares a fresh label-free cache and fits fresh weights/normalisers on
all121,838data0 sites for the frozen18epochs, seed2026, batch256, four threads.
No historical private CV checkpoints or prior model weights are required.
The public `training_specification.json` supplies fixed settings, not learned
initial weights. The script accepts only the pinned agreed data0 input/labels;
it does not expose a new tuning search. Output is `model.pt` and its fingerprint,
plus recoverable per-epoch checkpoints under `fit/`.

Repeat the identical command to resume completed-epoch work. Changed
input/source/configuration is rejected. If a hard process kill leaves
`run.lock`, first verify its original execution ended before removing only
that lock. Preserve partial artifacts. `--check-only` validates/prepares input
without fitting; `--cache EXISTING_DATA0_CACHE` optionally uses a verified
existing cache as read-only input. Cache manifests contain local paths, so a
fresh reproduction has its own provenance hash.

The actual nominated release was produced with the stricter local evidence
gate, after checking the completed five-fold source/split/score receipts:

```text
python -B model_elgin/tools/final_fit_cap128.py --check-only
python -B -u model_elgin/tools/final_fit_cap128.py --fit
python -B model_elgin/tools/package_final_cap128.py
```

Those release commands expect the locally retained development outputs.
The public fixed-recipe command uses the same frozen fitting implementation;
it does not independently regenerate historical OOF scores or reproduce the
entire development search. Use the documented CV workflows for that study.

## Evaluation and calling rule

Validation remains the original five gene-held-out OOF predictions: mean
ROC0.931828177, trapezoidal PR0.505601037 and S0.718714607. Predictions from
the final all-data0 model on data0 are fitted-data scores, not new validation.
Data1 has already been explored; its frozen-model result is a transfer
diagnostic, not a blind final test or a basis for further winner selection.
Data2 has fractional labels and separate descriptive interpretation.

The actual final artifact produced all121,838/90,810/1,323 supplied sites.
Its frozen data1 ROC/PR/S is0.827381010/0.382349993/0.604865501. At0.5,
precision/recall/F1 is0.484693/0.444259/0.463596. LightGBM's S is0.602321536;
LightGBM has slightly higher PR and higher precision/specificity/accuracy,
while neural has higher ROC/recall/F1. Preserve these tradeoffs rather than
claiming every metric improved. Full CSVs, input/model/source fingerprints
and measured inference resources remain in local `outputs/final_cap128_v1/`.
See [the completed results report](final_cap128_results/results.md) for all
metric comparisons, figures and exact application/evaluation commands.

Export continuous probabilities. The working site-call threshold is0.5,
with sensitivity analyses; it is not a calibrated biological threshold or a
measured modified-read fraction. Keep one unchanged artifact for all supplied,
new-test and later SG-NEx application inputs. Actual predictions and current
completion status are tracked in [CURRENT_STAGE.md](../CURRENT_STAGE.md).
