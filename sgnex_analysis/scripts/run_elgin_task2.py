"""Sequential frozen-model prediction across the agreed SG-NEx run inventory.

No model training or biological comparison occurs. Completed runs are skipped
only after file/provenance and Member 4 coverage checks pass again. Partial
downloads/inference are preserved and refused: this is run-boundary resume,
not byte-range download or partial-CSV resume.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import psutil

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "sgnex_analysis"
SCRIPTS = ROOT / "scripts"
MODEL = REPO / "model_elgin/artifacts/cap128_weight3_v1/model.pt"
MODEL_SHA = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
MODEL_VERSION = "elgin-cap128-weight3-18epoch-" + MODEL_SHA[:12]
SPEC = importlib.util.spec_from_file_location("elgin_task2_pipeline_adapter", SCRIPTS / "predict_elgin_run.py")
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
KEYS = ["transcript_id", "transcript_position"]
DEPTHS = (1, 5, 10, 20, 50, 100)


def sha(path):
    return ADAPTER.sha(path)


def json_read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc():
    return datetime.now(timezone.utc).isoformat()


def json_write(path, payload):
    """Atomic replacement; old interrupted temporary files are never overwritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def prepare_state(state, identity):
    """Take the exclusive lock before initial plan/checkpoint writes."""
    state.mkdir(parents=True, exist_ok=True)
    lock, plan_path, checkpoint_path = state / "run.lock", state / "plan.json", state / "checkpoint.json"
    with lock.open("x", encoding="utf-8") as handle:
        json.dump(dict(pid=os.getpid(), started_utc=utc()), handle)
    try:
        if plan_path.exists():
            if json_read(plan_path).get("identity") != identity:
                raise ValueError("Frozen batch identity changed; preserve previous state")
            checkpoint = json_read(checkpoint_path)
            if checkpoint.get("plan_sha256") != sha(plan_path):
                raise ValueError("Batch checkpoint differs from frozen plan")
        else:
            if any(path != lock for path in state.iterdir()):
                raise ValueError("Incomplete/unrecognised state directory; preserve and use a fresh directory")
            json_write(plan_path, dict(identity=identity, created_utc=utc(),
                                      resume="Completed-run boundaries only; interrupted partial outputs are preserved and refused"))
            checkpoint = dict(status="prepared", plan_sha256=sha(plan_path), runs={},
                              n_selected=len(identity["selected_run_ids"]))
            json_write(checkpoint_path, checkpoint)
        return checkpoint
    except BaseException:
        lock.unlink()
        raise


def rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing/duplicate manifest columns")
        result = list(reader)
    if any(None in record or any(value is None for value in record.values()) for record in result):
        raise ValueError("Malformed CSV fields: " + Path(path).name)
    return result


def within(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("Manifest path escapes its declared directory")
    return path


def selection(args):
    inventory, active = rows(args.inventory), rows(args.manifest)
    if (len(inventory) != 23 or len(active) != 23
            or len({r["run_id"] for r in inventory}) != 23
            or len({r["run_id"] for r in active}) != 23):
        raise ValueError("Both fixed-scope manifests must contain 23 unique runs")
    by_inventory, by_active = ({r["run_id"]: r for r in table} for table in (inventory, active))
    if set(by_inventory) != set(by_active):
        raise ValueError("Active prediction manifest differs from the 23-run inventory")
    if len({r["reference_version"] for r in active}) != 1 or not active[0]["reference_version"].strip():
        raise ValueError("Active manifest must retain one documented reference declaration")
    for run_id, row in by_active.items():
        source = by_inventory[run_id]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
            raise ValueError("Unsafe run ID")
        if any(str(row[key]) != str(source[key]) for key in ("cell_line", "biological_replicate", "sequencing_run")):
            raise ValueError("Run/cell-line/replicate identity differs between manifests")
        if int(row["min_reads"]) != 20 or row["model_version"] != MODEL_VERSION:
            raise ValueError("Active manifest must use selected model and minimum20 reads")
        if (args.manifest.parent / row["coverage_file"]).resolve() != args.coverage:
            raise ValueError("Active coverage path differs from supplied coverage matrix")
        within(args.manifest.parent, row["prediction_file"])
        within(args.signals_dir, source["signal_local_path"])
        if int(source["signal_size_bytes"]) < 1 or not source["signal_download_url"].startswith("https://"):
            raise ValueError("Require a positive saved object size and public HTTPS signal URL")
    requested = set(by_active) if args.all else set(args.run_id)
    if len(requested) != (23 if args.all else len(args.run_id)) or not requested <= set(by_active):
        raise ValueError("Unknown/duplicate requested run ID")
    return [(by_inventory[r["run_id"]], r) for r in active if r["run_id"] in requested]


def source_paths(args):
    core = REPO / "model_elgin/context_reference_v1"
    result = {"runner": Path(__file__), "adapter": SCRIPTS / "predict_elgin_run.py",
              "auditor": SCRIPTS / "audit_elgin_input.py", "downloader": SCRIPTS / "download_signal_inputs.py",
              "inventory": args.inventory, "active_manifest": args.manifest,
              "coverage": args.coverage, "aliases": args.aliases, "model": args.model}
    result.update({"core/" + name: core / name for name in ADAPTER.CORE_FILES})
    result["release_complete"] = args.model.parent / "complete.json"
    return result


def identity_for(args, selected):
    if args.min_reads != 20 or args.threads != 4 or args.batch_size != 32 or args.max_padded_reads != 65536:
        raise ValueError("Batch application is fixed at20reads,4threads,32site batches,65536padded-read budget")
    if sha(args.model) != MODEL_SHA:
        raise ValueError("Unexpected selected-model bytes")
    ADAPTER.guard_model(args.model)
    return dict(schema_version=1, model_sha256=MODEL_SHA,
                paths={name: str(path.resolve()) for name, path in source_paths(args).items()},
                source_sha256={name: sha(path) for name, path in source_paths(args).items()},
                adapter_canonical_sha256=ADAPTER.code_sha(SCRIPTS / "predict_elgin_run.py"),
                core_canonical_sha256={name: ADAPTER.code_sha(REPO / "model_elgin/context_reference_v1" / name)
                                      for name in ADAPTER.CORE_FILES},
                selected_run_ids=[row["run_id"] for _source, row in selected],
                signals_dir=str(args.signals_dir), audit_dir=str(args.audit_dir),
                min_reads=20, threads=4, batch_size=32, max_padded_reads=65536)


def check_pins(identity):
    for name, path in identity["paths"].items():
        if sha(path) != identity["source_sha256"][name]:
            raise ValueError("Frozen pipeline source/input changed: " + name)


def verified_download(source_row, signals_dir):
    """Existing raw bytes require prior successful receipt SHA agreement."""
    path = within(signals_dir, source_row["signal_local_path"])
    if not path.exists():
        return None
    if path.stat().st_size != int(source_row["signal_size_bytes"]):
        raise ValueError("Existing signal size changed; preserve it: " + source_row["run_id"])
    receipt_file = signals_dir / "download_receipts.jsonl"
    if not receipt_file.is_file():
        raise ValueError("Existing signal has no prior download SHA receipt")
    receipts = []
    with receipt_file.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("run_id") == source_row["run_id"] and record.get("status") in (
                    "downloaded_size_checked", "size_checked_existing"):
                receipts.append(record)
    if (not receipts or any(record.get("url") != source_row["signal_download_url"]
                            or record.get("size_bytes") != int(source_row["signal_size_bytes"])
                            for record in receipts)):
        raise ValueError("Prior successful download receipt differs from fixed inventory")
    fingerprints = {record.get("sha256") for record in receipts}
    actual = sha(path)
    if fingerprints != {actual}:
        raise ValueError("Existing signal disagrees with prior download SHA receipt")
    return dict(source_sha256=actual, source_size_bytes=path.stat().st_size,
                download_url=source_row["signal_download_url"],
                prior_download_receipt_sha256=hashlib.sha256(json.dumps(receipts[0], sort_keys=True).encode()).hexdigest())


def verified_audit(path, source_row, download, identity):
    result = json_read(path)
    required = dict(status="complete", run_id=source_row["run_id"],
                    source_sha256=download["source_sha256"], source_size_bytes=download["source_size_bytes"],
                    inventory_sha256=identity["source_sha256"]["inventory"],
                    coverage_sha256=identity["source_sha256"]["coverage"],
                    aliases_sha256=identity["source_sha256"]["aliases"],
                    auditor_sha256=identity["source_sha256"]["auditor"],
                    strict_parser_sha256=identity["source_sha256"]["core/data.py"],
                    n_source_sites=int(source_row["n_candidate_site_rows"]), coverage_key_and_count_match=True,
                    labels_read=False, fitting_or_inference=False)
    if any(result.get(key) != value for key, value in required.items()):
        raise ValueError("Cached full-input audit differs from frozen evidence")
    if any(result["sites_at_least_reads"].get(str(depth)) != int(source_row[f"n_sites_ge{depth}"]) for depth in DEPTHS):
        raise ValueError("Cached full-input audit coverage denominator differs")
    return result


def alias_for(path, run_id):
    remap = {}
    for row in rows(path):
        if row["run_id"] == run_id:
            if row["raw_transcript_id"] in remap:
                raise ValueError("Ambiguous explicit run alias")
            remap[row["raw_transcript_id"]] = row["transcript_id"]
    return remap


def verify_prediction(source_row, active_row, args, identity, download, audit):
    """Independently match scores/QC to all expected eligible coverage keys."""
    output = within(args.manifest.parent, active_row["prediction_file"])
    paths = ADAPTER.paths_for(output)
    if paths["lock"].exists():
        raise ValueError("Adapter lock exists; verify the original process before resuming")
    receipt = json_read(paths["receipt"])
    expected_identity = dict(run_id=source_row["run_id"], input_basename=Path(source_row["signal_local_path"]).name,
                             input_sha256=download["source_sha256"], model_sha256=MODEL_SHA,
                             core_source_sha256=identity["core_canonical_sha256"],
                             adapter_sha256=identity["adapter_canonical_sha256"], min_reads=20,
                             threads=4, batch_size=32, max_padded_reads=65536)
    if (receipt.get("status") != "complete" or receipt.get("identity") != expected_identity
            or receipt.get("final_model_selected") is not True or receipt.get("no_training_or_calibration") is not True
            or receipt.get("model_version") != MODEL_VERSION):
        raise ValueError("Prediction completion differs from frozen model/source/input")
    expected_files = {paths[name].name for name in ("task2", "raw_export", "core_manifest", "eligible_input", "metadata", "qc", "log")}
    if set(receipt.get("files_sha256", {})) != expected_files:
        raise ValueError("Prediction receipt does not include every preserved export/QC/log")
    for name, fingerprint in receipt["files_sha256"].items():
        if sha(output.parent / name) != fingerprint:
            raise ValueError("Changed completed prediction file: " + name)
    qc = json_read(paths["qc"])
    ADAPTER.check_core_manifest(paths, expected_identity, qc)
    if sha(output) != sha(paths["raw_export"]):
        raise ValueError("Task2 CSV differs from original frozen-model export")
    if (qc.get("status") != "complete" or qc.get("original_input_sha256") != download["source_sha256"]
            or qc.get("min_reads") != 20 or qc["counts"]["input_sites"] != audit["n_source_sites"]
            or qc["counts"]["input_reads"] != audit["n_reads"]):
        raise ValueError("All-source QC differs from verified original-input audit")
    remap, observed, raw_keys = alias_for(args.aliases, source_row["run_id"]), {}, set()
    thresholds, n_source, n_reads, n_eligible_reads = Counter(), 0, 0, 0
    seen = set()
    with gzip.open(paths["metadata"], "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = row["transcript_id"], int(row["transcript_position"])
            count = int(row["n_reads_input"])
            if key in seen or key[1] < 0 or count < 1 or int(row["n_reads_finite"]) != count:
                raise ValueError("Duplicate/invalid source QC key or read count")
            ADAPTER.DATA.encode_context(row["sequence_7mer"])
            if row["motif_5mer"] != row["sequence_7mer"][1:6]:
                raise ValueError("QC motif differs from original context")
            seen.add(key)
            n_source += 1
            n_reads += count
            for depth in DEPTHS:
                thresholds[depth] += int(count >= depth)
            if count >= 20:
                if row["prediction_status"] != "eligible":
                    raise ValueError("Eligible source site was excluded")
                canonical = remap.get(key[0], key[0]), key[1]
                if canonical in observed:
                    raise ValueError("Aliases collapse distinct eligible prediction keys")
                observed[canonical] = count
                raw_keys.add(key)
                n_eligible_reads += count
            elif row["prediction_status"] != "below_minimum_source_reads":
                raise ValueError("Low-coverage QC exclusion is not explicit")
    if (n_source != audit["n_source_sites"] or n_reads != audit["n_reads"]
            or any(thresholds[depth] != audit["sites_at_least_reads"][str(depth)] for depth in DEPTHS)
            or n_eligible_reads != qc["counts"]["eligible_reads"]):
        raise ValueError("All-source metadata does not reproduce full-input audit counts")
    expected = {}
    with gzip.open(args.coverage, "rt", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            count = int(row[source_row["run_id"]])
            if count >= 20:
                key = row["transcript_id"], int(row["transcript_position"])
                if key in expected:
                    raise ValueError("Duplicate Member4 eligible coverage key")
                expected[key] = count
    if observed != expected:
        raise ValueError("Predicted/QC sites do not exactly match Member4 eligible coverage keys/counts")
    predicted = set()
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != KEYS + ["score"]:
            raise ValueError("Prediction columns differ from the three-column contract")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed prediction fields")
            key = row["transcript_id"], int(row["transcript_position"])
            score = float(row["score"])
            if key in predicted or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Duplicate prediction key or invalid score")
            predicted.add(key)
    if predicted != raw_keys or len(predicted) != int(source_row["n_sites_ge20"]):
        raise ValueError("Missing/extra eligible prediction keys")
    if receipt["counts"] != dict(qc["counts"], scored_sites=len(predicted)):
        raise ValueError("Completion counts differ from full-source QC and verified predictions")
    return dict(status="complete", run_id=source_row["run_id"], n_source_sites=n_source, n_reads=n_reads,
                eligible_sites=len(predicted), eligible_reads=n_eligible_reads,
                coverage_key_and_count_match=True, original_prediction_keys_preserved=True,
                input_sha256=download["source_sha256"], audit_sha256=sha(args.audit_dir / (source_row["run_id"] + ".json")),
                prediction_sha256=sha(output), receipt_sha256=sha(paths["receipt"]),
                export_files_sha256=receipt["files_sha256"])


def stop_owned_child(process):
    """Terminate only descendants of this still-owned child, never name-scan jobs."""
    if process.poll() is not None:
        return
    try:
        parent = psutil.Process(process.pid)
        owned = parent.children(recursive=True) + [parent]
        for child in reversed(owned):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        _done, alive = psutil.wait_procs(owned, timeout=10)
        for child in alive:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    process.wait(timeout=10)


def command_run(command, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log.open("x", encoding="utf-8") as handle:
        process = subprocess.Popen(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT)
        try:
            code = process.wait()
        except BaseException:
            stop_owned_child(process)
            raise
    if code:
        raise RuntimeError("Stage exited{}; preserve/read {}".format(code, log.name))
    return {"wall_seconds": time.perf_counter()-started, "scope": "Child startup, execution and log writes; no CPU-total claim"}


def run(args):
    for name in ("inventory", "manifest", "coverage", "aliases", "model", "signals_dir", "audit_dir", "state_dir"):
        setattr(args, name, Path(getattr(args, name)).resolve())
    selected = selection(args)
    identity = identity_for(args, selected)
    if args.plan_only:
        print(json.dumps(dict(stage="Task2 prediction plan only; no download/inference", n_runs=len(selected),
                              raw_signal_bytes=sum(int(source["signal_size_bytes"]) for source, _row in selected),
                              source_sha256=identity["source_sha256"],
                              runs=[dict(run_id=row["run_id"], raw_bytes=int(source["signal_size_bytes"]),
                                         expected_eligible_sites=int(source["n_sites_ge20"])) for source, row in selected]), indent=2))
        return
    state, plan_path = args.state_dir, args.state_dir / "plan.json"
    lock, checkpoint_path = state / "run.lock", state / "checkpoint.json"
    checkpoint = prepare_state(state, identity)

    def event(kind, **payload):
        with (state / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(event=kind, recorded_utc=utc(), plan_sha256=checkpoint["plan_sha256"], **payload),
                                    allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def batch_pins():
        check_pins(identity)
        if sha(plan_path) != checkpoint["plan_sha256"]:
            raise ValueError("Frozen batch plan changed during execution")

    def save():
        checkpoint["completed_run_ids"] = [row["run_id"] for _source, row in selected
                                           if checkpoint["runs"].get(row["run_id"], {}).get("status") == "complete"]
        checkpoint["updated_utc"] = utc()
        json_write(checkpoint_path, checkpoint)

    def stage(run_id, name, action):
        batch_pins()
        record = checkpoint["runs"].setdefault(run_id, dict(status="pending", stages={}))
        record["status"], checkpoint["status"] = "running", "running"
        record["current_stage"] = name
        record["stages"][name] = dict(status="running", started_utc=utc())
        save()
        event("stage_started", run_id=run_id, stage=name)
        print("[Task 2] {}/{} complete | {} | {}".format(len(checkpoint["completed_run_ids"]), len(selected), run_id, name), flush=True)
        started = time.perf_counter()
        result = action()
        batch_pins()
        record["stages"][name] = dict(status="complete", completed_utc=utc(), wall_seconds=time.perf_counter()-started,
                                     measurement_scope="This stage including validation/child work; stage timers overlap child receipts", result=result)
        event("stage_completed", run_id=run_id, stage=name, record=record["stages"][name])
        save()
        return result

    def child_command(run_id, label, command):
        log = state / "logs" / run_id / (label + "_" + str(time.time_ns()) + ".log")
        return dict(log_file=str(log.relative_to(state)), resources=command_run(command, log))

    try:
        checkpoint["status"] = "running"
        save()
        event("batch_started_or_resumed")
        for source_row, active_row in selected:
            run_id = source_row["run_id"]
            batch_pins()
            if (state / "stop_after_current_run").exists():
                checkpoint["status"] = "stopped_at_run_boundary"
                save()
                event("stopped_at_run_boundary")
                print("[Task 2] stopped at a completed-run boundary; preserve/remove stop_after_current_run before resuming", flush=True)
                return
            signal = within(args.signals_dir, source_row["signal_local_path"])
            audit_path = args.audit_dir / (run_id + ".json")
            completed = checkpoint["runs"].get(run_id, {}).get("status") == "complete"
            download = verified_download(source_row, args.signals_dir)
            if completed:
                if download is None:
                    raise ValueError("Completed run's original signal is missing")
                audit = verified_audit(audit_path, source_row, download, identity)
                proof = verify_prediction(source_row, active_row, args, identity, download, audit)
                if proof != checkpoint["runs"][run_id]["verification"]:
                    raise ValueError("Completed run no longer matches its verified checkpoint")
                batch_pins()
                event("completed_run_reverified", run_id=run_id, verification=proof)
                print("[Task 2] verified completed run; skipped unchanged {}".format(run_id), flush=True)
                continue

            def download_stage():
                checked = verified_download(source_row, args.signals_dir)
                if checked is not None:
                    return dict(reused=True, **checked)
                if signal.with_name(signal.name + ".partial").exists():
                    raise ValueError("Interrupted download preserved. Helper restarts, not byte-range resumes; preserve/rename partial before a fresh download")
                child_command(run_id, "download", [sys.executable, "-B", "-u", str(SCRIPTS / "download_signal_inputs.py"),
                              "--manifest", str(args.inventory), "--dest", str(args.signals_dir), "--run-id", run_id])
                checked = verified_download(source_row, args.signals_dir)
                if checked is None:
                    raise ValueError("Download completed without verified raw input")
                return dict(reused=False, **checked)

            download = stage(run_id, "download", download_stage)

            def audit_stage():
                if sha(signal) != download["source_sha256"]:
                    raise ValueError("Original signal changed before audit")
                reused = audit_path.exists()
                if not reused:
                    child_command(run_id, "input_audit", [sys.executable, "-B", "-u", str(SCRIPTS / "audit_elgin_input.py"),
                                  "--input", str(signal), "--run-id", run_id, "--manifest", str(args.inventory),
                                  "--coverage", str(args.coverage), "--aliases", str(args.aliases), "--output", str(audit_path)])
                checked = verified_audit(audit_path, source_row, download, identity)
                return dict(reused=reused, audit_sha256=sha(audit_path), n_source_sites=checked["n_source_sites"],
                            expected_eligible_sites=checked["sites_at_least_reads"]["20"])

            stage(run_id, "input_audit", audit_stage)
            audit = verified_audit(audit_path, source_row, download, identity)
            output = within(args.manifest.parent, active_row["prediction_file"])

            def prediction_stage():
                if sha(signal) != download["source_sha256"]:
                    raise ValueError("Original signal changed before inference")
                receipt = ADAPTER.paths_for(output)["receipt"]
                if receipt.exists():
                    verify_prediction(source_row, active_row, args, identity, download, audit)
                    return dict(reused=True, receipt_sha256=sha(receipt))
                result = child_command(run_id, "prediction", [sys.executable, "-B", "-u", str(SCRIPTS / "predict_elgin_run.py"),
                                       "--input", str(signal), "--run-id", run_id, "--model", str(args.model),
                                       "--output", str(output), "--min-reads", "20", "--threads", "4",
                                       "--batch-size", "32", "--max-padded-reads", "65536"])
                return dict(reused=False, receipt_sha256=sha(receipt), **result)

            stage(run_id, "prediction", prediction_stage)
            proof = stage(run_id, "verification", lambda: verify_prediction(source_row, active_row, args, identity, download, audit))
            checkpoint["runs"][run_id].update(status="complete", verification=proof)
            save()
            print("[Task 2] {}/{} verified | {} | {:,} predicted sites".format(
                len(checkpoint["completed_run_ids"]), len(selected), run_id, proof["eligible_sites"]), flush=True)
        checkpoint["status"] = "complete"
        save()
        event("batch_completed")
        print("[Task 2] all{} selected runs complete and verified; no biological comparison has run".format(len(selected)), flush=True)
    except BaseException as error:
        checkpoint.update(status="interrupted_or_failed_partial_evidence_preserved", error=type(error).__name__ + ": " + str(error))
        save()
        event("interrupted_or_failed", error=checkpoint["error"])
        raise
    finally:
        lock.unlink()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    choose = result.add_mutually_exclusive_group(required=True)
    choose.add_argument("--all", action="store_true")
    choose.add_argument("--run-id", action="append", help="Repeat to choose a subset from the same fixed inventory")
    result.add_argument("--plan-only", action="store_true")
    result.add_argument("--inventory", type=Path, default=ROOT / "metadata/sample_manifest.csv")
    result.add_argument("--manifest", type=Path, default=ROOT / "manifest.csv")
    received = ROOT / "outputs/received_member4_20261019"
    result.add_argument("--coverage", type=Path, default=received / "results/coverage_matrix_ge20_union.csv.gz")
    result.add_argument("--aliases", type=Path, default=received / "metadata/transcript_aliases_checked.csv")
    result.add_argument("--model", type=Path, default=MODEL)
    result.add_argument("--signals-dir", type=Path, default=ROOT / "outputs/signals")
    result.add_argument("--audit-dir", type=Path, default=ROOT / "outputs/input_audits")
    result.add_argument("--state-dir", type=Path, default=ROOT / "outputs/elgin_task2_pipeline_v1")
    result.add_argument("--min-reads", type=int, default=20)
    result.add_argument("--threads", type=int, default=4)
    result.add_argument("--batch-size", type=int, default=32)
    result.add_argument("--max-padded-reads", type=int, default=65536)
    return result


if __name__ == "__main__":
    run(parser().parse_args())
