"""Seeded launcher of unmodified official m6Anet 2.1.0 site inference.

All benchmark settings are fixed here. No labels, fitting, score calibration or
threshold selection are accepted. Read-output identifiers are local row ordinals.
"""
import argparse
import csv
import importlib.metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np

# Deliberately at module scope: Windows spawn imports this file as __mp_main__
# in every official multiprocessing.Pool child, before its sampling task runs.
# Seeding only inside the guarded parent entry point would not seed that child.
FIXED_SEED = 2026
np.random.seed(FIXED_SEED)

import prepare_input as adapter


FIXED = {
    "seed": FIXED_SEED,
    "num_iterations": 1000,
    "n_processes": 1,
    "batch_size": 2048,
    "torch_threads": 4,
    "save_per_batch": 2147483647,
    "pretrained_model": "HCT116_RNA002",
    "device": "cpu",
    "multiprocessing_start_method": "spawn",
}
SITE_HEADER = ["transcript_id", "transcript_position", "n_reads",
               "probability_modified", "kmer", "mod_ratio"]
INDIV_HEADER = ["transcript_id", "transcript_position", "read_index", "probability_modified"]
PROVENANCE = (
    "Off-the-shelf published HCT116_RNA002 reference; potential pretraining overlap "
    "with course HCT116 data is unresolved. This is not independent five-fold "
    "gene-held-out training or an unbiased unseen-data assessment."
)
ORDINAL_WARNING = (
    "data.indiv_proba.csv identifiers are per-site zero-based row ordinals, NOT "
    "biological read identifiers. Keep this file local; do not link molecules "
    "across sites or interpret mod_ratio as a validated biological fraction."
)


def file_record(path):
    path = Path(path)
    return {"bytes": path.stat().st_size, "sha256": adapter.sha256(path)}


def finite_probability(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid numeric " + field) from error
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError("Nonfinite or out-of-range " + field)
    return number


def canonical_position(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError("Invalid transcript position")
    if str(int(value)) != value:
        raise ValueError("Noncanonical transcript position")
    return value


def validate_site_csv(path, expected):
    """Require exactly one finite site probability per eligible input key."""
    seen = set()
    minimum, maximum = 1.0, 0.0
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != SITE_HEADER:
            raise ValueError("Unexpected vendor site CSV header")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed vendor site CSV row")
            key = (row["transcript_id"], canonical_position(row["transcript_position"]))
            if key not in expected or key in seen:
                raise ValueError("Unexpected or duplicate vendor output site: {!r}".format(key))
            if row["n_reads"] != str(expected[key]["n_reads"]):
                raise ValueError("Vendor output read count mismatch")
            if row["kmer"] != expected[key]["central_kmer"]:
                raise ValueError("Vendor output central context mismatch")
            score = finite_probability(row["probability_modified"], "probability_modified")
            finite_probability(row["mod_ratio"], "mod_ratio")
            seen.add(key)
            minimum, maximum = min(minimum, score), max(maximum, score)
    if seen != set(expected):
        raise ValueError("Vendor output site coverage mismatch: {} of {}".format(len(seen), len(expected)))
    return {"sites": len(seen), "minimum_score": minimum, "maximum_score": maximum,
            "unique_exact_input_coverage": True, "score_column": "probability_modified"}


def validate_individual_csv(path, expected):
    """Check complete local ordinal bookkeeping, without a molecule-level claim."""
    count = 0
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != INDIV_HEADER:
            raise ValueError("Unexpected vendor individual CSV header")
        for key, metadata in expected.items():
            for ordinal in range(metadata["n_reads"]):
                row = next(reader, None)
                if row is None or None in row or any(value is None for value in row.values()):
                    raise ValueError("Missing or malformed individual bookkeeping row")
                out_key = (row["transcript_id"], canonical_position(row["transcript_position"]))
                if out_key != key:
                    raise ValueError("Individual output site order/coverage mismatch")
                read_index = float(row["read_index"])
                if not math.isfinite(read_index) or read_index != ordinal:
                    raise ValueError("Individual output row ordinal mismatch")
                finite_probability(row["probability_modified"], "individual probability")
                count += 1
        if next(reader, None) is not None:
            raise ValueError("Unexpected additional individual bookkeeping rows")
    return {"rows": count, "ordinal_bookkeeping_complete": True,
            "biological_read_identifiers": False}


def vendor_inventory(package_root, constants):
    package_root = Path(package_root)
    files = {str(path.relative_to(package_root)).replace("\\", "/"): file_record(path)
             for path in sorted(package_root.rglob("*.py"))}
    weights, _read_threshold, normalization = constants.PRETRAINED_CONFIGS[FIXED["pretrained_model"]]
    for path in (Path(weights), Path(normalization), Path(constants.DEFAULT_MODEL_CONFIG)):
        files[str(path.relative_to(package_root)).replace("\\", "/")] = file_record(path)
    return files


def audit_prepared_input(input_dir, dataset, all_kmers):
    """Verify byte-index/source-value receipt and every context against vendor assets."""
    receipt_path = input_dir / "complete.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["identity"]["schema"] != adapter.SCHEMA:
        raise ValueError("Unexpected input-adapter schema")
    if receipt["identity"]["adapter_sha256"] != adapter.sha256(adapter.__file__):
        raise ValueError("Input adapter code identity differs from preparation receipt")
    if receipt["identity"].get("minimum_reads") != 20:
        raise ValueError("Benchmark requires the declared 20-read input eligibility")
    if receipt.get("labels_used") is not False or receipt.get("original_signal_identity_checked") is not True:
        raise ValueError("Input receipt lacks label-free original-signal identity audit")
    for name in ("data.json", "data.info"):
        if file_record(input_dir / name) != receipt["files"][name]:
            raise ValueError("Input file identity mismatch: " + name)
    if list(dataset.indices) != list(range(9)):
        raise ValueError("Installed vendor does not isolate the original nine feature columns")
    if len(dataset) != receipt["sites"]:
        raise ValueError("Vendor silently excluded input sites")
    if math.ceil(receipt["sites"] / FIXED["batch_size"]) >= FIXED["save_per_batch"]:
        raise ValueError("Input exceeds the fixed vendor flush-workaround batch bound")
    expected = {}
    contexts = set()
    reads_total = 0
    previous_end = 0
    value_chain = "0" * 64
    vendor_vocabulary = set(all_kmers)
    first = None
    with (input_dir / "data.json").open("rb") as signals, (input_dir / "data.info").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        index = csv.DictReader(handle)
        if index.fieldnames != adapter.HEADER:
            raise ValueError("Unexpected input byte-index columns")
        for record in index:
            start, end = int(record["start"]), int(record["end"])
            if start != previous_end or end <= start:
                raise ValueError("Invalid input byte range")
            signals.seek(start)
            raw = signals.read(end - start)
            if len(raw) != end - start or not raw.endswith(b"\n") or not raw.isascii():
                raise ValueError("Incomplete/non-ASCII adapted JSON record")
            transcript, position, context, rows = adapter.decode_site(raw, 10)
            key = (transcript, position)
            if key != (record["transcript_id"], record["transcript_position"]) or key in expected:
                raise ValueError("Input byte-index key mismatch or duplicate site")
            if int(record["n_reads"]) != len(rows):
                raise ValueError("Input byte-index read count mismatch")
            if [row[-1] for row in rows] != list(range(len(rows))):
                raise ValueError("Input bookkeeping is not per-site row ordinals")
            kmers = [context[offset:offset + 5] for offset in range(3)]
            if any(kmer not in vendor_vocabulary for kmer in kmers):
                raise ValueError("Input context outside vendor vocabulary: " + context)
            mean, std = dataset.get_norm_factor(kmers)
            if np.shape(mean) != (9,) or np.shape(std) != (9,) or not np.isfinite(mean).all() or not np.isfinite(std).all() or not (std > 0).all():
                raise ValueError("Invalid/missing published normalization for " + context)
            original_rows = [row[:9] for row in rows]
            value_chain = adapter.signal_chain_update(value_chain, transcript, position, context, original_rows)
            if first is None:
                first = (key, original_rows, len(rows))
            expected[key] = {"n_reads": len(rows), "central_kmer": context[1:6]}
            contexts.add(context)
            reads_total += len(rows)
            previous_end = end
        signals.seek(0, os.SEEK_END)
        if signals.tell() != previous_end:
            raise ValueError("Unindexed trailing input JSON bytes")
    if len(expected) != receipt["sites"] or reads_total != receipt["reads"]:
        raise ValueError("Input population differs from preparation receipt")
    if value_chain != receipt["original_signal_chain_sha256"]:
        raise ValueError("Input original-signal identity mismatch")
    if first is None:
        raise ValueError("Empty input")
    tx_id, tx_pos, read_ids, features, _context = dataset.load_data(0)
    if (tx_id, str(tx_pos)) != first[0] or not np.array_equal(features, np.asarray(first[1])) or not np.array_equal(read_ids, np.arange(first[2])):
        raise ValueError("Vendor loader does not preserve nine signals and separate row ordinals")
    audit = {"sites": len(expected), "reads": reads_total,
             "distinct_contexts": len(contexts), "all_contexts_supported": True,
             "all_published_norm_factors_finite_positive_sd": True,
             "vendor_feature_indices": [int(value) for value in dataset.indices],
             "vendor_first_site_exact_original_nine_values": True,
             "source_original_signal_chain_verified": True,
             "population": receipt["population"]}
    return receipt, expected, audit


def preflight(input_dir):
    """Load official metadata/normalization and inspect features, with no forward pass."""
    import torch
    import m6anet
    from m6anet.utils import constants
    from m6anet.utils.data_utils import NanopolishDS

    if sys.version_info[:2] != (3, 8):
        raise ValueError("Course m6Anet reference requires its separate Python 3.8 environment")
    version = importlib.metadata.version("m6anet")
    if version != "2.1.0":
        raise ValueError("Benchmark is fixed to m6Anet 2.1.0")
    if torch.__version__.split("+")[0] != "1.6.0":
        raise ValueError("Benchmark requires the official PyTorch 1.6.0 dependency")
    if constants.DEFAULT_MIN_READS != 20:
        raise ValueError("Installed vendor minimum-read default differs from the fixed benchmark")
    package_root = Path(m6anet.__file__).resolve().parent
    files = vendor_inventory(package_root, constants)
    _weights, read_threshold, norm_path = constants.PRETRAINED_CONFIGS[FIXED["pretrained_model"]]
    dataset = NanopolishDS(str(input_dir), constants.DEFAULT_MIN_READS, norm_path, mode="Inference")
    receipt, expected, audit = audit_prepared_input(input_dir, dataset, constants.ALL_KMERS)
    summary = {
        "kind": "official_m6anet21_reference_v1",
        "parameters": dict(FIXED),
        "vendor_read_probability_threshold_for_mod_ratio_only": float(read_threshold),
        "runner": file_record(__file__),
        "adapter": file_record(adapter.__file__),
        "input_completion_receipt": file_record(input_dir / "complete.json"),
        "input_files": receipt["files"], "input_source_identity": receipt["identity"],
        "input_audit": audit,
        "vendor_files": files,
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "m6anet": version, "torch": torch.__version__, "numpy": np.__version__,
        },
        "package_versions": {
            name: importlib.metadata.version(name)
            for name in ("m6anet", "torch", "numpy", "pandas", "scipy", "scikit-learn", "joblib", "toml", "ujson", "tqdm")
        },
        "pretraining_provenance_limit": PROVENANCE,
        "individual_output_warning": ORDINAL_WARNING,
        "vendor_source_modified": False, "labels_used": False,
        "site_classification_threshold_selected": False,
        "flush_workaround": (
            "Unmodified vendor uses if (batch_index+1) % save_per_batch. "
            "A fixed value above the entire batch count makes every batch flush, "
            "including the final batch. Exact output coverage is mandatory."
        ),
    }
    return summary, expected, package_root, constants


def run(input_dir, output_dir, inspect_only=False):
    started, started_cpu = time.perf_counter(), time.process_time()
    if inspect_only:
        summary, _expected, _package_root, _constants = preflight(input_dir)
        summary["preflight_wall_seconds"] = time.perf_counter() - started
        summary["status"] = "preflight_complete_no_forward_pass"
        return summary
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("Inference output must be separate from immutable input")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Refusing to reuse a nonempty inference output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"kind": "official_m6anet21_reference_v1", "parameters": dict(FIXED),
               "status": "preflight_running", "runner": file_record(__file__),
               "labels_used": False, "invocation": [sys.executable] + sys.argv}
    adapter.write_json_atomic(output_dir / "runner_status.json", summary)
    try:
        initial_invocation = summary["invocation"]
        summary, expected, package_root, constants = preflight(input_dir)
        summary["invocation"] = initial_invocation
        summary["preflight_wall_seconds"] = time.perf_counter() - started
        summary["status"] = "inference_running"
        adapter.write_json_atomic(output_dir / "runner_status.json", summary)
        import torch
        from m6anet.scripts import inference

        torch.set_num_threads(FIXED["torch_threads"])
        # The standalone launcher owns its process. Spawn makes Pool seeding
        # explicit on both Windows and Linux without editing vendor algorithms.
        multiprocessing.set_start_method("spawn", force=True)
        vendor_arguments = [
            "--input_dir", str(input_dir), "--out_dir", str(output_dir),
            "--pretrained_model", FIXED["pretrained_model"],
            "--device", FIXED["device"], "--seed", str(FIXED["seed"]),
            "--num_iterations", str(FIXED["num_iterations"]),
            "--n_processes", str(FIXED["n_processes"]),
            "--batch_size", str(FIXED["batch_size"]),
            "--save_per_batch", str(FIXED["save_per_batch"]),
        ]
        arguments = inference.argparser().parse_args(vendor_arguments)
        summary["vendor_cli_arguments"] = vendor_arguments
        adapter.write_json_atomic(output_dir / "runner_status.json", summary)
        print(json.dumps({"status": "official_inference_start", "sites": len(expected),
                          "parameters": FIXED}), flush=True)
        infer_start, infer_cpu = time.perf_counter(), time.process_time()
        inference.main(arguments)
        summary["official_inference_resources"] = {
            "wall_seconds": time.perf_counter() - infer_start,
            "parent_process_cpu_seconds": time.process_time() - infer_cpu,
            "cpu_scope": "launcher process only; excludes spawned DataLoader/Pool children",
        }
        summary["site_output_audit"] = validate_site_csv(output_dir / "data.site_proba.csv", expected)
        summary["individual_output_audit"] = validate_individual_csv(output_dir / "data.indiv_proba.csv", expected)
        if vendor_inventory(package_root, constants) != summary["vendor_files"]:
            raise ValueError("Vendor source/weights/normalization changed during inference")
        if file_record(__file__) != summary["runner"]:
            raise ValueError("Runner source changed during inference")
        if file_record(adapter.__file__) != summary["adapter"]:
            raise ValueError("Adapter source changed during inference")
        if file_record(input_dir / "complete.json") != summary["input_completion_receipt"]:
            raise ValueError("Input receipt changed during inference")
        for name in ("data.json", "data.info"):
            if file_record(input_dir / name) != summary["input_files"][name]:
                raise ValueError("Input data changed during inference")
        summary["output_files"] = {
            name: file_record(output_dir / name)
            for name in ("data.site_proba.csv", "data.indiv_proba.csv")
        }
        summary["status"] = "complete"
        summary["exit_code"] = 0
        summary["total_resources"] = {
            "wall_seconds": time.perf_counter() - started,
            "parent_process_cpu_seconds": time.process_time() - started_cpu,
            "cpu_scope": "launcher process only; child CPU and RSS require an external monitor",
        }
        adapter.write_json_atomic(output_dir / "runner_status.json", summary)
        adapter.write_json_atomic(output_dir / "complete.json", summary)
        return summary
    except BaseException as error:
        summary["status"] = "failed_partial_outputs_preserved"
        summary["exit_code"] = 130 if isinstance(error, KeyboardInterrupt) else 1
        summary["error_type"] = type(error).__name__
        summary["error"] = str(error)
        summary["traceback"] = traceback.format_exc()
        summary["total_resources"] = {
            "wall_seconds": time.perf_counter() - started,
            "parent_process_cpu_seconds": time.process_time() - started_cpu,
            "cpu_scope": "launcher process only; excludes spawned children",
        }
        adapter.write_json_atomic(output_dir / "runner_status.json", summary)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--preflight", action="store_true",
                        help="audit assets/input and print a receipt; no forward pass or output files")
    args = parser.parse_args()
    summary = run(args.input_dir.resolve(), args.output_dir.resolve(), args.preflight)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
