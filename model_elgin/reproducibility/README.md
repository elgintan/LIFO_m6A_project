# Ubuntu inference reproducibility check

**23 October 2026 status: prepared, but not executed on Ubuntu.** The installed
Docker Desktop backend crashed during startup while creating its Inference
manager Unix socket. The recent backend log reported that the socket file
could not be accessed and that the filename/directory/volume syntax was
incorrect. No image or package download, Linux model execution, Docker reset,
WSL installation or operating-system change was performed.

Native Windows inference and the real ten-site example have passed separately.
That does not establish clean Ubuntu or AWS execution. Task 2 can continue in
the working native environment while this separate portability check remains
open.

## Run later with a working Docker Linux backend

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
to avoid CUDA dependencies. Installing those packages has **not** been tested
in this attempt; unavailable dependencies must produce a failed check rather
than silently changing version pins.

On an actual successful run, `complete.json` is written last, after the
unchanged predictor produces exactly ten unique sites and 1,887 reads, keeps
the frozen model fingerprint, uses every read and matches the Windows example
within absolute score tolerance `3e-6`. Receipts preserve actual versions,
image identity, code/model/context hashes, commands, log filenames and scoped
wall times. Failed partial outputs remain available.

A successful local Ubuntu-container check would still **not** establish the
handout's fresh AWS Ubuntu host check, installation performance on AWS,
training reproducibility or unseen biological performance. This is inference
portability evidence only.

The present local status and prepared-context checks are retained under ignored
`model_elgin/outputs/ubuntu_check/` and
`model_elgin/outputs/ubuntu_check_prepared_20261023/`.
