"""Run the unchanged saved-model predictor and check the real ten-site example."""
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy
import pandas
import psutil
import sklearn
import torch

MODEL_SHA256 = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
TOLERANCE = 3e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["transcript_id", "transcript_position", "score"]:
            raise ValueError("Prediction CSV header changed")
        records = list(reader)
    result = {(row["transcript_id"], int(row["transcript_position"])): float(row["score"])
              for row in records}
    if len(result) != len(records) or len(result) != 10:
        raise ValueError("Expected ten unique real example sites")
    return result


def main():
    output = Path("/output")
    destination = output / "predictions.csv"
    if sha("model.pt") != MODEL_SHA256:
        raise ValueError("Saved model fingerprint changed")
    if destination.exists():
        raise ValueError("Use an empty output directory")
    command = [sys.executable, "-B", "/work/code/predict.py", "--input", "/work/example_input.json",
               "--model", "/work/model.pt", "--output", str(destination), "--threads", "4"]
    subprocess.run(command, check=True)
    actual, expected = rows(destination), rows("example_expected.csv")
    if actual.keys() != expected.keys():
        raise ValueError("Prediction site keys changed")
    maximum = max(abs(actual[key] - expected[key]) for key in actual)
    if not all(numpy.isfinite(value) and 0 <= value <= 1 for value in actual.values()) or maximum > TOLERANCE:
        raise ValueError("Prediction numeric parity failed")
    manifest = json.loads(destination.with_suffix(".csv.manifest.json").read_text())
    if (manifest["model_sha256"] != MODEL_SHA256 or manifest["stage"] != "final_data0"
            or manifest["n_sites"] != 10 or manifest["n_reads"] != 1887
            or manifest["all_reads_used"] is not True or manifest["labels_read"] is not False):
        raise ValueError("Prediction completion metadata changed")
    os_release = Path("/etc/os-release").read_text()
    if 'ID=ubuntu' not in os_release or 'VERSION_ID="24.04"' not in os_release:
        raise ValueError("Expected an Ubuntu 24.04 userspace")
    receipt = {"status": "complete", "kind": "local_ubuntu_container_inference_check",
        "not_aws_host_validation": True, "model_sha256": MODEL_SHA256,
        "python": platform.python_version(), "platform": platform.platform(),
        "os_release": os_release, "versions": {"numpy": numpy.__version__, "pandas": pandas.__version__,
            "psutil": psutil.__version__, "scikit_learn": sklearn.__version__, "torch": torch.__version__},
        "cuda_available": torch.cuda.is_available(), "n_sites": 10, "n_reads": 1887,
        "absolute_tolerance": TOLERANCE, "maximum_absolute_score_difference": maximum,
        "prediction_sha256": sha(destination), "command": command,
        "inference_resources": manifest["resources"],
        "scope": "Fresh Linux CPU inference on a real data0 example; no training, new biological validation or AWS-host check"}
    (output / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
