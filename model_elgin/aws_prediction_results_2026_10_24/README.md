# Native AWS prediction example: completed 24 October 2026

The user ran the public saved-model prediction command on their course RONIN
AWS machine at commit `fc1e369e67b5d298620a5bb8e0062825cc0889c0`.
Ubuntu26.04 LTS/x86_64 initially supplied Python3.14.4, without Python3.12 or
Docker. User-local uv0.13.5 installed CPython3.12.15 and a fresh seeded virtual
environment. The system interpreter and all model/package pins stayed unchanged.
The five declared model dependencies matched and `pip check` passed.

The example completed with **10 unique sites and 1,887 reads**, `final_data0`,
original context mode and all-read prediction. The assistant checked the supplied
CSV/manifest against the public release, input, five inference sources and expected
scores. All fingerprints matched. Maximum absolute score difference from the
packaged Windows example was **1.4901161193847656e-8**, below the fixed **3e-6**
tolerance. The selected model SHA remains
`b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.

Actual prediction command, from the fresh clone with its environment activated:

```text
python -B model_elgin/context_reference_v1/predict.py --input model_elgin/artifacts/cap128_weight3_v1/example/input.json --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output model_elgin/outputs/aws_preflight_20261024/predictions.csv --threads 4
```

## Evidence delivery and verification

The user supplied complete terminal CSV and sidecar JSON text, not a downloaded
binary archive. `predictions.csv` reconstructs that exact displayed content with
the predictor's LF line endings. Its SHA256 exactly matches the remote manifest's
`output_sha256`: `819cd36bc62113e32cc0726370e4757f60c48c26ca8ecd4d162a11710ce8e96f`.
`prediction_manifest.json` preserves all supplied JSON fields; its original
remote byte formatting is not independently claimed. Private host prompts,
addresses, key names and key contents are excluded.

`verification.json` records the assistant's checks; `score_comparison.csv` keeps
all ten actual/expected scores and absolute differences. `environment.json`
records actual declared/transitive versions from installation output.
`provenance.json` distinguishes user execution, assistant checks and unconfirmed
shutdown. An independent implementation checked the compact evidence; see
`independent_check.json`. `publication_manifest.json` fingerprints this package.
AWS provenance comes from the user's RONIN setup/terminal context; no credentials
or instance-metadata service were queried, and a kernel string alone is not used
as proof of provider identity.

## Measured scope and limits

The predictor manifest reports **0.027595092s wall**, **0.054654251s process CPU**
and **400.625MiB peak sampled process-tree RSS**, with0.2s sampling and no reported
sampling errors. Its measured section includes input/model hashing/loading,
parsing, prediction, CSV verification/write, **excluding imports**. These are not
whole-installation or command-start-to-finish timings. The sampled memory maximum
is not a guaranteed instantaneous peak or a minimum hardware requirement.
The host reported32 logical CPUs; inference used4threads. Full installation time
and resources were not measured and are not inferred from download progress bars.

This establishes the public native prediction path on the tested AWS setup.
The ten examples are data0 training sites: this is software portability/parity,
not independent accuracy, a training replay or a full-input capacity benchmark.
The earlier [hosted Ubuntu24.04 result](../ubuntu_prediction_results_2026_10_23/README.md)
and failed laptop Docker startup history remain separate evidence.

No retraining, model search or SG-NEx rerun occurred. Actual new-test input,
release contract, validated predictions and submission remain pending here.
Cloud Stop state was not confirmed when this evidence was assembled; the user
was instructed to Stop while retaining the disks/results after the bounded check.
Follow [the reproduction guide](../AWS_PREFLIGHT.md) for a fresh run, preserving
existing outputs and checking actual OS/Python versions.
