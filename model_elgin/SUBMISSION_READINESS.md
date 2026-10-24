# Prediction and submission readiness — 24 October 2026

Current stage: final prediction interface and evidence checked; actual new-test
input, release instructions and submission have not been supplied/completed here.
The final selected model and its18-epoch all-data0 fit remain unchanged.

## What the course requires

The original handout, Task1/code availability section, requires executable public
GitHub code, training and prediction interfaces, installation/run documentation
and a small prediction example. Other students evaluate it on AWS Ubuntu.
Our separate AWS-host run is recommended additional assurance. The handout does
not explicitly require us to launch RONIN or submit our own AWS test receipt.
RONIN is a way to access AWS resources, not a special model dependency.

| Item | Checked state | Evidence / next action |
|---|---|---|
| Public final model | Complete | `artifacts/cap128_weight3_v1/model.pt`, SHA256 b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668; seven release-file pins in complete.json |
| Training interface | Available; full-input/cache/config check previously passed | [Fixed training command](FINAL_MODEL_USAGE.md); no new fit needed for prediction |
| Prediction interface/example | Complete | Unchanged `context_reference_v1/predict.py`; real ten-site input, expected CSV and completion manifest public |
| Python/CPU install instructions | Documented | Python3.12; CPU Torch index first, then exact requirements; separate from legacy m6Anet environment |
| Ubuntu execution | Passed | [Hosted Ubuntu24.04 job and independent check](ubuntu_prediction_results_2026_10_23/README.md), ten sites/1887 reads, max difference1.49e-8<3e-6 |
| Separate direct AWS-host execution | Passed, user-executed 24October | [Native RONIN Ubuntu26.04/Python3.12.15 example](aws_prediction_results_2026_10_24/README.md); ten keys/1887reads/all fingerprints and parity checked. Cloud Stop state remains unconfirmed |
| Actual new-test input and release contract | Not provided in this chat | Obtain the released file(s), naming/header requirements and upload route; do not assume they are globally unreleased |
| Actual new-test prediction/submission | Pending actual inputs | Same artifact, full input-site coverage, unique keys, finite[0,1]scores, correct release filenames and retained manifests |

Code and new-test predictions remain due28October23:59Singapore. Report and
interactive visualisation are due8November; the extended exact time is unconfirmed.

## What runs where

The readiness audit and report/explorer work use saved laptop outputs. The optional
AWS preflight uses only the small public example. Existing completed training,
five-fold comparisons and23-run SG-NEx inference do not need repeating.
Actual new-test runtime and machine size depend on its unknown size/coverage;
the ten-site preflight does not establish full-test capacity.

For a new test file, the current entry point is:

```text
python -B model_elgin/context_reference_v1/predict.py --input ACTUAL_RELEASE_FILE --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output RELEASE_REQUIRED_FILENAME.csv --threads 4
```

The two capitalised paths above are placeholders, not files already supplied.
Read the release instructions before using this command. Do not apply Task2's
>=20-read eligibility filter automatically: Task1's predictor preserves all
compatible input keys and all available reads. It rejects malformed/duplicate
sites and invalid measurements rather than silently dropping them.

When the actual file arrives, first inspect its schema/size and release contract,
announce the expected prediction duration, then run once. Independently compare
the final CSV's exact key set/count to that input, verify finite scores in[0,1]
and the model/input/output/source hashes, and inspect the complete sidecar.
Only after these checks use the announced submission route and retain proof of
submission. Input labels are unavailable, so no new-test ROC/PR claim is possible.

## Interpretation of tests

The example is data0 training data: it tests installation, software execution,
output format and numerical portability. It does not measure unseen accuracy.
A local audit of an existing Ubuntu receipt is not a newly executed AWS check.
Do not turn a prepared command, running machine or successful package installation
into a claim that prediction/submission has completed.
