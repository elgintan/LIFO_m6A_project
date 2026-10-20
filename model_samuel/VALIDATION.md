# Received evidence and local validation — 20 October 2026

This separates supplied results from checks actually executed on Elgin's
Windows laptop. No full training or full data1 inference was replayed here.

## Training and evaluation evidence supplied by Samuel

- `artifact/model_card.json`: all five exact data0 folds, followed by a fresh
  all-data0 fit; fixed settings, input fingerprints, durations and saved model
  and preprocessing hashes. All 121,838 data0 sites are represented in OOF.
- `results/data0_cv_metrics.json`: mean ROC 0.9218967458283268,
  trapezoidal PR 0.49899625146701865, S 0.7104464986476727. The shared scorer
  independently reproduced the provided OOF metrics during PR review.
- `results/data1_metrics.json`: 90,810 sites, ROC 0.8217642710359293,
  trapezoidal PR 0.3828788018432001, AP 0.3830708269890862,
  S 0.6023215364395647. Earlier data1 feature-selection exposure is disclosed.
- `outputs/data1_predictions.csv` and `outputs/data2_predictions.csv` were
  delivered and retained locally. Data2 received summaries are descriptive.
- Repeat-seed result JSONs are retained under `results/seed_check/`; their
  raw OOF files were not supplied, so these repeats were not independently scored.

These files constitute training/testing evidence, not an independent replay
or proof of the historical order of all development decisions. There are no
whole-run SG-NEx predictions or final selected-model data0 CSV in this ZIP.

## Checks actually completed on this laptop

1. ZIP SHA256 `f76b846e41d49c8ac9ff48283c55e003539eb4aec2da5eb291363bd2ee83b54f`;
   26 files safely unpacked. Original entry hashes are in
   `INTEGRATION_RECEIPT.json`. No credentials or path/symlink traversal entries.
2. Saved model SHA256
   `ba268645ed3fa6c19f59f6a83ed85c794c7b19975d4e474551d211ef78406bb1`
   and reference SHA256
   `ae1e45448a1eb6ca0863e0764b74a529b24b7586a6497883392667f3cf3c93cc`
   match the received model card and remain unchanged after checks.
3. The frozen predictor produced all ten example sites with **maximum numeric
   score difference 0** from the received example. Raw bytes differ only by
   LF/CRLF line endings; normalising line endings yields equality.
4. The common scorer recomputed every pooled data1 metric and the primary
   score **exactly**, using the local canonical labels and supplied scores.
   This is rescoring existing predictions, not a new inference run.
5. Three runtime contract tests passed in **30.653 seconds** after the isolated
   environment finished installing. They check prediction from an unrelated
   working directory with no labels/default model resolution, exact example
   scores, valid unique keys, finite [0,1] outputs, and rejection of input/model/
   reference/card overwrites using disposable copies.
6. The integrated trainer's `--help` exits successfully on Windows. Its
   optional `resource` fallback reports null peak memory; this does not claim
   a complete Windows retraining or a measured Windows training cost.

Prediction environment: Python 3.12.14, LightGBM 4.7.0, numpy 2.4.6, pandas
3.0.6, scipy 1.17.1, scikit-learn 1.9.1. Elgin's neural environment was not
downgraded. An initial `venv` ensurepip failure was recovered by using an
existing pip-enabled Python's `--python` target option. An earlier passing
test log overlapped dependency installation; it was retained and superseded
by the successful stable-environment run above.

## Exact executed commands

From the repository root (PowerShell):

```powershell
model_samuel/.venv/Scripts/python.exe -B model_samuel/code/predict.py --input model_samuel/examples/input_10_sites.json --model-dir model_samuel/artifact --output model_samuel/outputs/integration_20261020/predictions.csv
../advanced_model/.venv/Scripts/python.exe -B model_evaluation/evaluate.py --dataset data1 --labels ../data1/data.info --predictions model_samuel/outputs/data1_predictions.csv --output model_samuel/outputs/integration_20261020/data1_metrics_recomputed.json
model_samuel/.venv/Scripts/python.exe -B model_samuel/code/train.py --help
```

For the stable test run, from `model_samuel/`, with TMP/TEMP/TMPDIR set to
the resolved `outputs/integration_20261020/tmp` directory:

```powershell
.venv/Scripts/python.exe -B test_predict.py
```

Actual local outputs/logs remain under `outputs/integration_20261020/`, ignored
by Git, including `audit.json`, predictions, recomputed metrics,
`test_predict.log` and the superseded installation-overlap log.

Clean AWS Ubuntu prediction, fresh full retraining, a validated calling cutoff,
selected-model final exports and whole-run SG-NEx application remain pending.
