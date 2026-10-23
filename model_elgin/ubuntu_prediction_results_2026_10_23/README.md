# Frozen-model Ubuntu prediction: completed

The [hosted job](https://github.com/elgintan/LIFO_m6A_project/actions/runs/39885223601)
passed on 23 October 2026 at commit `4510ef463447b81522ab7f17aeac145a169cb5f6`.
It built the existing isolated Ubuntu 24.04 image, installed the exact CPU pins,
loaded the unchanged selected artifact and predicted the real ten-site example.
All ten original keys and 1,887 reads passed completion checks. Maximum absolute
score difference from the Windows example was **1.4901161193847656e-08**, within
the fixed 3e-6 tolerance. This is software parity on training-data examples,
not independent accuracy or an AWS-host test.

Ubuntu Python was 3.12.3; NumPy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1,
psutil 7.2.2 and CPU Torch 2.14.1+cpu match the declared library pins.
The model SHA remains
`b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.

The downloaded eight-file evidence ZIP matched GitHub's SHA256
`587f1dd1e00acf9515a4c48d07b4dd372a8dc17d0ba27525063ca99058eea78f`.
CRC, every result hash, exact keys and score differences were independently
checked locally. `independent_artifact_check.json` and `verification.json`
preserve the compact evidence; full logs/archive remain locally retained and
in the workflow artifact. The earlier laptop Docker-startup failure is preserved.

Reproduction uses [the existing recipe](../reproducibility/README.md) and the
[bounded workflow](../../.github/workflows/ubuntu_prediction.yml). A fresh AWS
prediction check and the actual new unlabelled-test input/submission remain
separate pending requirements. No training or SG-NEx inference was repeated.
