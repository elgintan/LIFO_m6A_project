# Ubuntu inference reproducibility check

**Current status, 23 October 2026: hosted Ubuntu24.04 check PASSED.**
The completed [job and independent artifact verification](../ubuntu_prediction_results_2026_10_23/README.md)
establish exact pins, unchanged model,10 sites/1887 reads and maximum score
difference1.49e-8 within3e-6. No new training or bulk prediction was performed.
Separate direct AWS-host execution remains a recommended preflight, not a
separate submission requirement explicitly imposed by the handout. See the
[prepared direct-host commands](../AWS_PREFLIGHT.md).

**Earlier laptop attempt, preserved as failure history:** the installed
Docker Desktop backend crashed during startup while creating its Inference
manager Unix socket. The recent backend log reported that the socket file
could not be accessed and that the filename/directory/volume syntax was
incorrect. No image or package download, Linux model execution, Docker reset,
WSL installation or operating-system change was performed.

Native Windows inference and the real ten-site example had passed separately.
That earlier evidence did not establish Linux execution; the later hosted job
now supplies it. The laptop Docker startup problem has not been reset or repaired.

## Reproduce with a working Docker Linux backend, if needed

From the repository root, in the documented Python environment:

```text
python -B model_elgin/reproducibility/run_ubuntu_check.py --output-dir model_elgin/outputs/ubuntu_check_attempt2
```

Use a fresh output directory: the helper preserves earlier attempts rather
than overwriting their logs and receipts. `--prepare-only` copies and verifies
the small context without starting Docker, building images or running inference.

The helper copies only five unchanged inference source files, pinned
requirements, the frozen 98-KB model and its ten-site real example. It does
not send the whole repository, virtual environments, labels, full signals,
training checkpoints or credentials to the Docker build.

The Dockerfile uses Ubuntu 24.04 with Python 3.12 and the project's pinned
requirements. It explicitly obtains Torch from the official CPU wheel index
to avoid CUDA dependencies. Installation succeeded in the later hosted job;
unavailable dependencies on a different host must produce a failed check rather
than silently changing version pins.

On an actual successful run, `complete.json` is written last, after the
unchanged predictor produces exactly ten unique sites and 1,887 reads, keeps
the frozen model fingerprint, uses every read and matches the Windows example
within absolute score tolerance `3e-6`. Receipts preserve actual versions,
image identity, code/model/context hashes, commands, log filenames and scoped
wall times. Failed partial outputs remain available.

A successful Ubuntu-container check establishes that userspace prediction path.
The handout says classmates evaluate code on AWS Ubuntu; our recommended own
AWS preflight adds host-specific assurance. This container receipt does not
establish AWS-host execution, training reproducibility or unseen accuracy.

The earlier local status and prepared-context checks are retained under ignored
`model_elgin/outputs/ubuntu_check/` and
`model_elgin/outputs/ubuntu_check_prepared_20261023/`.
