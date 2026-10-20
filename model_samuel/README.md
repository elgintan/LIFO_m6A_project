# Samuel: sequence-relative LightGBM candidate

Received from Samuel's merged PR #1 and unpacked on 20 October 2026. This is
an actual trained candidate, not the selected final team model. The unchanged
saved model/reference, source receipt, small example and received metric
summaries are included. Large prediction CSVs remain local under `outputs/`.

## Actual evidence

| Population | ROC AUC | trapezoidal PR AUC | S |
|---|---:|---:|---:|
| data0, mean of five exact shared gene folds | 0.921896746 | 0.498996251 | 0.710446499 |
| data1, already-exposed transfer diagnostic | 0.821764271 | 0.382878802 | 0.602321536 |

S averages ROC and trapezoidal PR AUC; AP is separate in `results/`. The data0
scores were independently recomputed with the shared scorer during review.
See [current validation](VALIDATION.md) for integration checks and their limits.
Data1 was inspected during earlier feature exploration and is not a blind test.
The received repeat-seed JSONs are reported evidence, not independently replayed
training. Model/reference checksums match `artifact/model_card.json`.

The pipeline aggregates each of nine read measurements with mean, population
SD and five quantiles, giving 63 features. Training-fitted sequence references
produce 7-mer-relative features, with supported 5-mer/global fallbacks, plus
seven categorical bases. LightGBM uses 1,500 trees. See the
[preserved received description](docs/RECEIVED_README.md) for original choices,
metrics and limitations. Its older comparison/status statements are historical;
current team status is [here](../INTEGRATION_STATUS.md). Data2 fractional labels
are descriptive targets of unresolved detailed provenance, not demonstrated
modified-molecule fractions. A 0.5 cutoff is not calibrated automatically.

## Predict a small example

From the repository root, using Python 3.11 or 3.12:

```text
python -m venv model_samuel/.venv
```

Windows PowerShell:

```powershell
model_samuel/.venv/Scripts/python.exe -m pip install -r model_samuel/requirements-predict.txt
model_samuel/.venv/Scripts/python.exe -B model_samuel/code/predict.py --input model_samuel/examples/input_10_sites.json --output model_samuel/outputs/example_predictions.csv
model_samuel/.venv/Scripts/python.exe -B model_samuel/test_predict.py
```

Ubuntu:

```bash
model_samuel/.venv/bin/python -m pip install -r model_samuel/requirements-predict.txt
model_samuel/.venv/bin/python -B model_samuel/code/predict.py --input model_samuel/examples/input_10_sites.json --output model_samuel/outputs/example_predictions.csv
model_samuel/.venv/bin/python -B model_samuel/test_predict.py
```

The predictor needs no labels. Its default model path is independent of the
current directory; use `--model-dir` to specify another frozen bundle. The
output has exactly `transcript_id,transcript_position,score`. Compare numeric
scores with `examples/predictions.csv`; tiny cross-platform differences are
allowed. This ten-site example is a software check, not new performance evidence.
On Ubuntu, install the system OpenMP runtime `libgomp1` if LightGBM cannot load.
A clean AWS Ubuntu run remains pending.

If Windows environment creation fails during `ensurepip`, an existing
pip-enabled Python can install into that environment without changing itself:

```text
EXISTING_PYTHON -m pip --python model_samuel/.venv/Scripts/python.exe install pip -r model_samuel/requirements-predict.txt
```

Replace `EXISTING_PYTHON` with your actual existing Python executable.

## Reproduce training or scoring

Install `requirements.txt` in a separate candidate environment for training
and diagnostics; do not change Elgin's environment. From the repository root:

```text
python model_samuel/code/train.py --data0 LOCAL_DATA/data0/dataset0.json.gz --labels LOCAL_DATA/data0/data.info.labelled --folds eda/received/shared_folds/data0_folds.csv --out model_samuel/outputs/new_run --model-dir model_samuel/outputs/new_run/artifact
python model_evaluation/evaluate.py --dataset data0 --labels LOCAL_DATA/data0/data.info.labelled --predictions model_samuel/outputs/new_run/data0_oof.csv --output model_samuel/outputs/new_run/data0_metrics.json
```

Use a new output/model directory: the received final artifact must stay intact.
Training uses only data0 and the fixed configuration. It produces held-out OOF
scores and then an all-data0 model. The received trainer does not provide
mid-training resumption; preserve logs and completed outputs. Elgin's neural
trainer has separate resumable checkpoints.

The received `outputs/data0_oof.csv` is NOT the single final model's data0
prediction file. If this candidate is selected, run its frozen predictor on
all three required datasets and the 23 application runs. Do not substitute OOF
scores for the required same-model dataset0 export.

`diagnostics.py` is retained as received research code. It additionally needs
Samuel's external site-summary parquet and old 18-feature OOF file, neither
supplied by this ZIP. Its docstring's `--folds` option is unsupported. Use the
current shared evaluator and documented team diagnostics for reproducible
comparisons; do not treat that legacy command as a complete pipeline.

## Disclosed integration changes

`INTEGRATION_RECEIPT.json` records original ZIP entry hashes. The saved model,
reference and received result files are unchanged. Training's Unix-only
`resource` import is now optional; Windows writes a null peak-RAM measurement
rather than an invented value. Prediction now rejects overwriting its input
or saved model and creates the output parent directory. These changes do not
alter learned features, weights, tree settings or intended scores. Original
received source remains in the local review archive.
