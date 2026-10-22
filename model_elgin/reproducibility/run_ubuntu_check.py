"""Build an isolated Ubuntu image and check the frozen ten-site model example.

Only five inference source files, pins, saved model and its small example are
copied into the build context. No complete repository, environment or raw data
directory is sent to Docker. Logs and partial outputs are retained on failure.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKAGE = REPO / "model_elgin/artifacts/cap128_weight3_v1"
SOURCE = REPO / "model_elgin/context_reference_v1"
MODEL_SHA256 = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "model_elgin/outputs/ubuntu_check")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve the previous attempt; use a fresh output directory")
    if not output.is_relative_to(REPO / "model_elgin/outputs"):
        raise ValueError("Keep check context and results within ignored model_elgin/outputs")
    output.mkdir(parents=True, exist_ok=True)
    context, results = output / "context", output / "results"
    (context / "code").mkdir(parents=True)
    results.mkdir()
    package_receipt = json.loads((PACKAGE / "complete.json").read_text())
    if package_receipt["status"] != "complete" or sha(PACKAGE / "model.pt") != MODEL_SHA256:
        raise ValueError("Expected the complete selected model package")
    for name, expected in package_receipt["files_sha256"].items():
        if sha(PACKAGE / name) != expected:
            raise ValueError("Release file changed: " + name)
    copies = {SOURCE / name: context / "code" / name
              for name in ("predict.py", "model.py", "data.py", "context_features.py", "common.py")}
    copies.update({SOURCE / "requirements.txt": context / "requirements.txt",
        PACKAGE / "model.pt": context / "model.pt",
        PACKAGE / "example/input.json": context / "example_input.json",
        PACKAGE / "example/expected.csv": context / "example_expected.csv",
        HERE / "Dockerfile": context / "Dockerfile",
        HERE / "verify_container.py": context / "verify_container.py"})
    hashes = {}
    for source, destination in copies.items():
        shutil.copyfile(source, destination)
        if sha(source) != sha(destination):
            raise ValueError("Build-context copy changed")
        hashes[str(destination.relative_to(context))] = sha(destination)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag = "lifo-cap128-repro:" + run_id
    record = {"status": "prepared_not_executed", "kind": "local_ubuntu_container_inference_check",
        "not_aws_host_validation": True, "model_sha256": MODEL_SHA256,
        "context_sha256": hashes, "runner_sha256": sha(__file__), "image_tag": tag,
        "commands": [], "measurement_scope": "Host subprocess elapsed wall times; no CPU or memory total claimed"}
    save(output / "status.json", record)
    if args.prepare_only:
        print("PASS: small context prepared; no Docker build or inference")
        return
    def execute(command, logname, timeout):
        start = time.perf_counter()
        with (output / logname).open("w", encoding="utf-8") as handle:
            result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        record["commands"].append({"arguments": command, "log": logname,
            "returncode": result.returncode, "wall_seconds": time.perf_counter()-start})
        save(output / "status.json", record)
        if result.returncode:
            raise RuntimeError("Command failed; retained " + logname)
    try:
        record["status"] = "running"
        save(output / "status.json", record)
        execute(["docker", "info", "--format", "{{.ServerVersion}}"], "docker_status.log", 60)
        execute(["docker", "build", "--progress=plain", "--tag", tag, str(context)], "build.log", 1800)
        image = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], text=True))[0]
        record["image"] = {key: image.get(key) for key in ("Id", "RepoDigests", "Os", "Architecture")}
        execute(["docker", "run", "--rm", "--cpus", "4", "--memory", "2g", "--mount",
                 "type=bind,source=" + str(results) + ",target=/output", tag], "inference.log", 180)
        verified = json.loads((results / "verification.json").read_text())
        if verified.get("status") != "complete" or verified.get("model_sha256") != MODEL_SHA256:
            raise ValueError("Container check is incomplete")
        for source, destination in copies.items():
            if sha(source) != sha(destination):
                raise ValueError("Source changed during check")
        record["verification"] = verified
        record["status"] = "complete"
        record["files_sha256"] = {str(path.relative_to(output)): sha(path)
            for path in sorted(results.iterdir()) if path.is_file()}
        save(output / "status.json", record)
        save(output / "complete.json", record)
        print(json.dumps({"status": "complete", "image": record["image"],
            "maximum_absolute_score_difference": verified["maximum_absolute_score_difference"],
            "not_aws_host_validation": True}, indent=2))
    except BaseException as error:
        record.update(status="failed_partial_outputs_preserved", error=type(error).__name__ + ": " + str(error))
        save(output / "status.json", record)
        raise


if __name__ == "__main__":
    main()
