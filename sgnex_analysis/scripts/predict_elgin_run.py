"""Strict full-source QC, then frozen cap128 prediction on eligible SG-NEx sites.

Every source site/read is checked and counted. Sites below the declared >=20
source-read rule remain in QC metadata, not silently called unmodified. Only
eligible original JSON records reach the unchanged model predictor, which uses
all their reads. No training, imputation, alias mapping or coordinate changes.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "model_elgin/context_reference_v1"
PACKAGE = REPO / "model_elgin/artifacts/cap128_weight3_v1"
SELECTED_MODEL_SHA = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
CORE_FILES = ("predict.py", "model.py", "data.py", "context_features.py", "common.py")
SPEC = importlib.util.spec_from_file_location("elgin_task2_strict_data", CORE / "data.py")
DATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DATA)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(2 ** 20), b""):
            digest.update(block)
    return digest.hexdigest()


def code_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, payload):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def paths_for(output):
    output = Path(output).resolve()
    raw_export = output.with_name(output.stem + ".model_export.csv")
    eligible = output.with_suffix(".eligible_input.json.gz")
    metadata = output.with_suffix(".site_metadata.csv.gz")
    return dict(task2=output, raw_export=raw_export,
                core_manifest=raw_export.with_suffix(".csv.manifest.json"),
                eligible_input=eligible, metadata=metadata, qc=output.with_suffix(".input_qc.json"),
                log=output.with_suffix(".inference.log"), receipt=output.with_suffix(".receipt.json"),
                status=output.with_suffix(".adapter_status.json"), lock=output.with_suffix(".adapter.lock"),
                partial=output.with_suffix(".csv.partial"),
                eligible_partial=eligible.with_name(eligible.name + ".partial"),
                meta_partial=metadata.with_name(metadata.name + ".partial"),
                core_partial=raw_export.with_suffix(".csv.tmp"))


def guard_model(model):
    """The artifact and immutable prediction source must match this release."""
    if sha(model) != SELECTED_MODEL_SHA:
        raise ValueError("Expected the selected cap128/weight3/18-epoch model bytes")
    release = read_json(PACKAGE / "complete.json")
    if release.get("status") != "complete":
        raise ValueError("Selected model release is incomplete")
    for name, expected in release["files_sha256"].items():
        if sha(PACKAGE / name) != expected:
            raise ValueError("Selected release changed: " + name)
    expected = read_json(PACKAGE / "example/expected.csv.manifest.json")["code_sha256"]
    actual = {name: code_sha(CORE / name) for name in CORE_FILES}
    if actual != expected:
        raise ValueError("Prediction source differs from the selected release")
    return actual


def prepare_eligible_input(source, paths, min_reads, input_sha256):
    """Validate ALL sites; retain eligible original record bytes without recoding.

    Two streaming source handles pair the unchanged strict parser with original
    line bytes. Eligible records are copied verbatim into deterministic gzip;
    no float32 round trip, column projection or numeric reserialization occurs.
    """
    counts = dict(input_sites=0, eligible_sites=0, below_minimum_source_reads=0,
                  input_reads=0, finite_reads=0, eligible_reads=0, reads_discarded_nonfinite=0)
    eligible_bytes = hashlib.sha256()
    opener = gzip.open if source.suffix.lower() == ".gz" else open
    with opener(source, "rb") as raw, paths["eligible_partial"].open("xb") as destination, \
            gzip.open(paths["meta_partial"], "xt", newline="", encoding="utf-8") as metadata:
        meta = csv.writer(metadata, lineterminator="\n")
        meta.writerow(["transcript_id", "transcript_position", "sequence_7mer", "motif_5mer",
                       "n_reads_input", "n_reads_finite", "prediction_status"])
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as selected:
            for transcript, position, context, reads in DATA.iter_sites(source):
                original = raw.readline()
                if not original:
                    raise ValueError("Original-record byte stream ended before strict source parser")
                n_reads = len(reads)
                eligible = n_reads >= min_reads
                if eligible:
                    selected.write(original)
                    eligible_bytes.update(original)
                meta.writerow([transcript, position, context, context[1:6], n_reads, n_reads,
                               "eligible" if eligible else "below_minimum_source_reads"])
                counts["input_sites"] += 1
                counts["input_reads"] += n_reads
                counts["finite_reads"] += n_reads
                counts["eligible_sites"] += int(eligible)
                counts["eligible_reads"] += n_reads if eligible else 0
                counts["below_minimum_source_reads"] += int(not eligible)
        if raw.readline():
            raise ValueError("Original-record stream has unchecked trailing data")
        destination.flush()
        os.fsync(destination.fileno())
    if not counts["input_sites"] or not counts["eligible_sites"]:
        raise ValueError("No input sites or no sites meet the declared minimum-read rule")
    if sha(source) != input_sha256:
        raise ValueError("Original source changed during full-input QC")
    os.replace(paths["eligible_partial"], paths["eligible_input"])
    os.replace(paths["meta_partial"], paths["metadata"])
    # Independently check compression retained precisely the original eligible bytes.
    observed = hashlib.sha256()
    with gzip.open(paths["eligible_input"], "rb") as handle:
        for block in iter(lambda: handle.read(2 ** 20), b""):
            observed.update(block)
    if observed.hexdigest() != eligible_bytes.hexdigest():
        raise ValueError("Compressed eligible input differs from original selected record bytes")
    qc = dict(status="complete", original_input_sha256=input_sha256,
              eligible_input_sha256=sha(paths["eligible_input"]),
              eligible_original_record_bytes_sha256=eligible_bytes.hexdigest(),
              min_reads=min_reads, counts=counts,
              selection="Source reads >= declared minimum; strict validity checks apply to ALL source sites",
              transformation="Original eligible JSON record bytes copied verbatim into gzip; no signal/context/key changes",
              exclusion_meaning="Below-minimum sites are unscored for coverage QC, not labelled unmodified",
              nonfinite_policy="Abort full run even if the malformed site is below the coverage threshold")
    save_json(paths["qc"], qc)
    return qc


def run_core_prediction(args, paths):
    command = [sys.executable, "-B", "-u", str(CORE / "predict.py"),
               "--input", str(paths["eligible_input"]), "--model", str(args.model),
               "--output", str(paths["raw_export"]), "--threads", str(args.threads),
               "--batch-size", str(args.batch_size),
               "--max-padded-reads", str(args.max_padded_reads)]
    with paths["log"].open("x", encoding="utf-8") as handle:
        process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT)
        try:
            returncode = process.wait()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            raise
    if returncode:
        raise RuntimeError("Core predictor failed; preserve its log/partial output")


def check_core_manifest(paths, identity, qc):
    manifest = read_json(paths["core_manifest"])
    if (manifest.get("status") != "complete" or manifest.get("stage") != "final_data0"
            or manifest.get("model_sha256") != identity["model_sha256"]
            or manifest.get("input_sha256") != qc["eligible_input_sha256"]
            or sha(paths["eligible_input"]) != qc["eligible_input_sha256"]
            or manifest.get("code_sha256") != identity["core_source_sha256"]
            or manifest.get("output_sha256") != sha(paths["raw_export"])
            or manifest.get("threads") != identity["threads"]
            or manifest.get("batch_size_limit") != identity["batch_size"]
            or manifest.get("max_padded_reads_budget") != identity["max_padded_reads"]
            or manifest.get("all_reads_used") is not True or manifest.get("labels_read") is not False
            or manifest.get("exact_input_key_coverage") is not True
            or manifest.get("n_sites") != qc["counts"]["eligible_sites"]
            or manifest.get("n_reads") != qc["counts"]["eligible_reads"]):
        raise ValueError("Core inference receipt differs from frozen model/source or eligible-input QC")
    return manifest


def predict(args):
    if (args.min_reads < 20 or min(args.threads, args.batch_size, args.max_padded_reads) < 1
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id)
            or args.run_id in (".", "..")):
        raise ValueError("Require min_reads>=20, positive batching/threads and a safe run ID")
    args.input, args.model = Path(args.input).resolve(), Path(args.model).resolve()
    paths = paths_for(args.output)
    if paths["task2"].suffix.lower() != ".csv" or paths["task2"].is_relative_to(PACKAGE):
        raise ValueError("Use a CSV output outside the immutable artifact package")
    if {args.input, args.model} & set(paths.values()):
        raise ValueError("Outputs must not overwrite input or model")
    identity = dict(run_id=args.run_id, input_basename=args.input.name,
                    input_sha256=sha(args.input), model_sha256=SELECTED_MODEL_SHA,
                    core_source_sha256=guard_model(args.model), adapter_sha256=code_sha(__file__),
                    min_reads=args.min_reads, threads=args.threads, batch_size=args.batch_size,
                    max_padded_reads=args.max_padded_reads)
    exported = ("task2", "raw_export", "core_manifest", "eligible_input", "metadata", "qc", "log")
    if paths["lock"].exists():
        raise ValueError("Adapter lock exists; verify its original process before removing only that lock")
    if paths["receipt"].exists():
        receipt = read_json(paths["receipt"])
        if receipt.get("status") != "complete" or receipt.get("identity") != identity:
            raise ValueError("Existing completion receipt differs from this invocation")
        expected_files = {paths[name].name for name in exported}
        if set(receipt.get("files_sha256", {})) != expected_files:
            raise ValueError("Existing receipt lacks the export/metadata/QC/log contract")
        for name, expected in receipt["files_sha256"].items():
            if sha(paths["task2"].parent / name) != expected:
                raise ValueError("Changed completed inference file: " + name)
        check_core_manifest(paths, identity, read_json(paths["qc"]))
        print("PASS: reused complete selected-model Task 2 export with unchanged fingerprints", flush=True)
        return receipt
    if any(path.exists() for path in paths.values()) or any(
            path.with_name(path.name + ".tmp").exists() for path in (paths["status"], paths["receipt"], paths["qc"])):
        raise ValueError("Incomplete prior work exists; preserve it and use a fresh output filename")
    paths["task2"].parent.mkdir(parents=True, exist_ok=True)
    with paths["lock"].open("x", encoding="utf-8") as handle:
        json.dump(dict(pid=os.getpid(), run_id=args.run_id), handle)
    started, cpu_started = time.perf_counter(), time.process_time()
    try:
        save_json(paths["status"], dict(status="input_qc_running", identity=identity))
        qc = prepare_eligible_input(args.input, paths, args.min_reads, identity["input_sha256"])
        save_json(paths["status"], dict(status="frozen_model_inference_running", identity=identity, counts=qc["counts"]))
        run_core_prediction(args, paths)
        manifest = check_core_manifest(paths, identity, qc)
        if sha(args.input) != identity["input_sha256"] or guard_model(args.model) != identity["core_source_sha256"]:
            raise ValueError("Original input/model/source changed during Task 2 export")
        if code_sha(__file__) != identity["adapter_sha256"]:
            raise ValueError("Adapter source changed during execution")
        with paths["raw_export"].open("rb") as source, paths["partial"].open("xb") as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        if sha(paths["partial"]) != manifest["output_sha256"]:
            raise ValueError("Task 2 copy differs from unchanged core prediction export")
        os.replace(paths["partial"], paths["task2"])
        files = {paths[name].name: sha(paths[name]) for name in exported}
        counts = dict(qc["counts"], scored_sites=manifest["n_sites"])
        receipt = dict(status="complete", final_model_selected=True,
                       model_version="elgin-cap128-weight3-18epoch-" + SELECTED_MODEL_SHA[:12],
                       identity=identity, counts=counts, files_sha256=files,
                       completed_utc=datetime.now(timezone.utc).isoformat(),
                       original_source_retained=True, source_qc_complete=True,
                       eligibility="source reads >= declared min_reads; all reads used for every eligible site",
                       unscored_low_coverage_meaning="Coverage QC exclusion, not an unmodified label",
                       nonfinite_policy="Abort; no filtering/imputation; finite/source counts identical",
                       no_training_or_calibration=True, core_inference_resources=manifest["resources"],
                       adapter_resources=dict(wall_seconds=time.perf_counter()-started,
                                              process_cpu_seconds_excluding_child=time.process_time()-cpu_started),
                       resource_scope="Wrapper wall includes full-source QC, child prediction and export audit; core timings overlap. Wrapper process CPU excludes predictor child; no total-CPU claim.",
                       coordinates="Original transcript IDs/integer positions; no alias mapping or coordinate shift",
                       reference_limit="Schema/count checks do not establish reference/event-preprocessing compatibility or chemical coordinate meaning",
                       interpretation="Predicted m6A candidate-site scores; not modified-molecule fractions, per-read labels or independent biological validation")
        save_json(paths["status"], dict(status="complete", identity=identity, counts=counts))
        save_json(paths["receipt"], receipt)  # Commit completion only after every export/hash succeeds.
        print(json.dumps(dict(status="complete", run_id=args.run_id, **counts)), flush=True)
        return receipt
    except BaseException as error:
        save_json(paths["status"], dict(status="failed_partial_files_preserved", identity=identity,
                                       error=type(error).__name__ + ": " + str(error)))
        raise
    finally:
        paths["lock"].unlink()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--input", required=True, type=Path)
    result.add_argument("--run-id", required=True)
    result.add_argument("--output", required=True, type=Path, help=">=min-reads Task 2 CSV; original source/QC retained")
    result.add_argument("--model", type=Path, default=PACKAGE / "model.pt")
    result.add_argument("--min-reads", type=int, default=20)
    result.add_argument("--threads", type=int, default=4)
    result.add_argument("--batch-size", "--batch-sites", dest="batch_size", type=int, default=32)
    result.add_argument("--max-padded-reads", type=int, default=65536)
    return result


if __name__ == "__main__":
    predict(parser().parse_args())
