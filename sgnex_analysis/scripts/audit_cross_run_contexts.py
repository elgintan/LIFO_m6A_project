"""Audit saved contexts at every key in the complete >=20-read coverage union.

All source metadata rows are streamed, including low-read observations. Only
the coverage-union keys can ever enter this selected 23-run score analysis;
outside-union rows are counted but their cross-run contexts are not compared.
No original identifiers, scores, sequences, model files or manifests are edited.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
import time

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
KEYS = ["transcript_id", "transcript_position"]
METADATA_COLUMNS = KEYS + ["sequence_7mer", "motif_5mer", "n_reads_input", "n_reads_finite", "prediction_status"]
SELECTED_MODEL_SHA = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
ENCODER_SOURCE_SHA = "91f8a13e3ecb6cf5461c2f33a640f523e7884362c8545e4125f9f5c4b14ebf70"
IUPAC = set("ACGTURYSWKMBDHVN")
POLICY = {
    "primary": "all_source_consistent",
    "sensitivity": "scored_consistent",
    "scope": "Every coverage-union key; all source observations at those keys, including below20 reads",
    "outside_union": "All metadata rows counted; cross-run contexts outside the scoreable coverage union are not compared",
    "encoding": "ASCII uppercase; U becomes T; recognised ambiguous IUPAC letters map to N (model unknown code4)",
    "primary_rule": "One identical unambiguous central-A model-encoded7mer among all source observations at the key",
    "scored_rule": "Same rule restricted to observations with source reads>=20",
    "no_score_based_selection": True,
    "training_support": "Descriptive only; weak=True if ANY observed known context has<20 data0 positives. False is not assurance for unknown/ambiguous contexts; see training_support_known_for_all_contexts. No support filter",
    "identifiers": "Literal positions; only exact per-run aliases from the supplied table; no generic stripping or offset",
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def file_record(path):
    path = Path(path)
    return {"path": path.name, "sha256": sha(path), "size_bytes": path.stat().st_size}


def integer(value, name="integer", minimum=0):
    text = str(value)
    if not re.fullmatch(r"[0-9]+", text) or int(text) < minimum:
        raise ValueError(f"{name} must be an exact integer >= {minimum}: {text!r}")
    return int(text)


def context_identity(raw):
    if not isinstance(raw, str) or len(raw) != 7 or not raw.isascii() or not set(raw.upper()) <= IUPAC:
        raise ValueError(f"Invalid seven-base IUPAC context: {raw!r}")
    canonical = raw.upper().replace("U", "T")
    encoded = "".join(base if base in "ACGT" else "N" for base in canonical)
    ambiguous = "N" in encoded
    return canonical, encoded, ambiguous, encoded[3] == "A"


def csv_open(path, mode="rt"):
    return gzip.open(path, mode, encoding="utf-8-sig" if "r" in mode else "utf-8", newline="") if str(path).endswith(".gz") else Path(path).open(mode.replace("t", ""), encoding="utf-8-sig" if "r" in mode else "utf-8", newline="")


def load_table(path):
    return pd.read_csv(path, keep_default_na=False, dtype={"transcript_id": str, "transcript_position": str})


def checked_keys(frame, label):
    if not set(KEYS) <= set(frame.columns):
        raise ValueError(f"{label}: missing key columns")
    if frame.transcript_id.astype(str).str.strip().eq("").any():
        raise ValueError(f"{label}: blank transcript")
    frame = frame.copy()
    frame["transcript_position"] = frame.transcript_position.map(lambda x: integer(x, "position"))
    if frame[KEYS].duplicated().any():
        raise ValueError(f"{label}: duplicate site keys")
    return frame


def load_aliases(path, run_ids):
    result = {run: {} for run in run_ids}
    with csv_open(path) as handle:
        for row in csv.DictReader(handle):
            if row["run_id"] not in result:
                raise ValueError("Alias references a run outside the fixed manifest")
            raw, mapped = row["raw_transcript_id"], row["transcript_id"]
            if not raw or not mapped or raw in result[row["run_id"]]:
                raise ValueError("Blank/duplicate/ambiguous explicit alias")
            result[row["run_id"]][raw] = mapped
    return result


def context_summary(raw_codes, read_counts, raw_contexts):
    present = raw_codes > 0
    scored = read_counts >= 20
    raw = {raw_contexts[int(i)] for i in raw_codes[present]}
    all_ids = [context_identity(s) for s in raw]
    scored_ids = [context_identity(raw_contexts[int(i)]) for i in raw_codes[scored]]
    all_encoded = {value[1] for value in all_ids}
    scored_encoded = {value[1] for value in scored_ids}
    all_ambiguous = any(value[2] for value in all_ids)
    scored_ambiguous = any(value[2] for value in scored_ids)
    all_central = all(value[3] for value in all_ids)
    scored_central = all(value[3] for value in scored_ids)
    return {
        "all_source_consistent": len(all_encoded) == 1 and not all_ambiguous and all_central,
        "scored_consistent": len(scored_encoded) == 1 and not scored_ambiguous and scored_central,
        "encoded7mer_all_source": next(iter(all_encoded)) if len(all_encoded) == 1 else "",
        "encoded7mer_scored": next(iter(scored_encoded)) if len(scored_encoded) == 1 else "",
        "n_source_runs": int(present.sum()), "n_scored_runs": int(scored.sum()),
        "n_literal_contexts_all_source": len(raw),
        "n_canonical_contexts_all_source": len({value[0] for value in all_ids}),
        "n_encoded_contexts_all_source": len(all_encoded),
        "n_encoded_contexts_scored": len(scored_encoded),
        "ambiguous_context_all_source": all_ambiguous,
        "ambiguous_context_scored": scored_ambiguous,
        "noncentral_a_all_source": not all_central,
        "noncentral_a_scored": not scored_central,
        "literal_contexts_all_source": "|".join(sorted(raw)),
        "encoded_contexts_all_source": "|".join(sorted(all_encoded)),
        "encoded_contexts_scored": "|".join(sorted(scored_encoded)),
    }


def population_effects(read_counts, manifest, annotated, primary, scored_only):
    lines = sorted(manifest.cell_line.unique())
    records = []
    groups = {}
    for line in lines:
        line_rows = manifest[manifest.cell_line.eq(line)]
        groups[line] = [[manifest.index[manifest.run_id.eq(run)][0] for run in rows.run_id]
                        for _, rows in line_rows.groupby("biological_replicate", sort=True)]
    for depth in (20, 50, 100):
        qualified = {}
        for line in lines:
            n_groups = np.zeros(len(annotated), dtype=np.uint8)
            for indices in groups[line]:
                n_groups += (read_counts[:, indices] >= depth).any(axis=1)
            qualified[line] = n_groups >= 2
        populations = [("all_lines", "|".join(lines), list(lines))]
        populations += [("pairwise", f"{a}|{b}", [a, b]) for a, b in itertools.combinations(lines, 2)]
        populations += [("single_line", line, [line]) for line in lines]
        for kind, name, selected in populations:
            baseline = annotated.copy()
            for line in selected:
                baseline &= qualified[line]
            n = int(baseline.sum())
            records.append({"coverage_threshold": depth, "population_type": kind, "cell_lines": name,
                            "n_annotated_coverage_qualified": n,
                            "n_primary_all_source_consistent": int((baseline & primary).sum()),
                            "n_excluded_primary_context": int((baseline & ~primary).sum()),
                            "n_scored_only_consistent": int((baseline & scored_only).sum()),
                            "n_additional_scored_only_vs_primary": int((baseline & scored_only & ~primary).sum()),
                            "minimum_metadata_groups_per_line": 2})
    return records


def run_audit(manifest_path, coverage_path, annotations_path, aliases_path, training_path, output, *, expected_runs=23, model_sha=SELECTED_MODEL_SHA, model_path=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    json_write(output / "status.json", {"status": "running", "policy": POLICY})
    paths = {"manifest": Path(manifest_path), "coverage": Path(coverage_path), "annotations": Path(annotations_path), "aliases": Path(aliases_path), "training_support": Path(training_path),
             "plan": REPO / "sgnex_analysis/CROSS_RUN_CONTEXT_QC_PLAN.md", "model_encoder_source": REPO / "model_elgin/context_reference_v1/data.py"}
    inputs = {name: file_record(path) for name, path in paths.items()}
    if inputs["model_encoder_source"]["sha256"] != ENCODER_SOURCE_SHA:
        raise ValueError("Frozen model encoder source differs")
    model_path = Path(model_path) if model_path else REPO / "model_elgin/artifacts/cap128_weight3_v1/model.pt"
    if sha(model_path) != model_sha:
        raise ValueError("Current frozen model hash differs from selected artifact")
    inputs["model"] = file_record(model_path)
    source_hash = sha(Path(__file__))
    manifest = pd.read_csv(manifest_path, keep_default_na=False, dtype=str)
    if len(manifest) != expected_runs or manifest.run_id.duplicated().any() or not manifest.min_reads.eq("20").all():
        raise ValueError("Expected the fixed unique manifest and min_reads20")
    if manifest.model_version.nunique() != 1 or manifest.reference_version.nunique() != 1:
        raise ValueError("Mixed model/reference declarations")
    run_ids = manifest.run_id.tolist()
    aliases = load_aliases(aliases_path, run_ids)
    coverage = checked_keys(load_table(coverage_path), "coverage")
    annotations = checked_keys(load_table(annotations_path), "annotations")
    keys = list(coverage[KEYS].itertuples(index=False, name=None))
    key_to_index = {key: i for i, key in enumerate(keys)}
    if set(keys) != set(annotations[KEYS].itertuples(index=False, name=None)):
        raise ValueError("Coverage/annotation key universes differ")
    annotations = annotations.set_index(KEYS).loc[pd.MultiIndex.from_tuples(keys)].reset_index()
    counts_expected = np.column_stack([coverage[run].map(lambda x: integer(x, "coverage")).to_numpy(np.int32) for run in run_ids])
    if not (counts_expected >= 20).any(axis=1).all():
        raise ValueError("Coverage table is not the >=20 union")
    n = len(keys)
    read_counts = np.zeros((n, len(run_ids)), dtype=np.int32)
    context_codes = np.zeros((n, len(run_ids)), dtype=np.uint16)
    raw_contexts = [""]
    context_to_code = {}
    scores = np.full((n, len(run_ids)), np.nan, dtype=np.float64)
    original_transcripts = [{} for _ in run_ids]
    run_summaries = []
    inputs["predictions"], inputs["metadata"], inputs["receipts"] = [], [], []
    inputs["model_sha256"] = model_sha
    training = pd.read_csv(training_path, keep_default_na=False)
    if training.sequence_7mer.duplicated().any():
        raise ValueError("Duplicate training contexts")
    training_support = {row.sequence_7mer: int(row.positive_labels) for row in training.itertuples()}
    collision_path = output / "within_run_key_collisions.csv.gz"
    with csv_open(collision_path, "wt") as collision_handle:
        collision_writer = csv.DictWriter(collision_handle, fieldnames=["run_id", "transcript_id", "transcript_position", "previous_raw_transcript_id", "incoming_raw_transcript_id"])
        collision_writer.writeheader()
        for j, row in enumerate(manifest.itertuples()):
            prediction = (Path(manifest_path).parent / row.prediction_file).resolve()
            metadata = prediction.with_suffix(".site_metadata.csv.gz")
            receipt_path = prediction.with_suffix(".receipt.json")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt["status"] != "complete" or receipt["identity"]["run_id"] != row.run_id or receipt["identity"]["model_sha256"] != model_sha or receipt["identity"]["min_reads"] != 20:
                raise ValueError("Incomplete/mismatched prediction receipt")
            audit_path = prediction.parent.parent / "input_audits" / f"{row.run_id}.json"
            input_audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if (input_audit["status"] != "complete" or input_audit["run_id"] != row.run_id
                    or input_audit["source_sha256"] != receipt["identity"]["input_sha256"]
                    or input_audit["coverage_sha256"] != inputs["coverage"]["sha256"]
                    or input_audit["aliases_sha256"] != inputs["aliases"]["sha256"]
                    or input_audit["coverage_key_and_count_match"] is not True):
                raise ValueError("Saved input-audit source/coverage/alias binding differs")
            inputs.setdefault("input_audits", []).append({"run_id": row.run_id, **file_record(audit_path)})
            for path, category in [(prediction, "predictions"), (metadata, "metadata")]:
                record = file_record(path)
                if record["sha256"] != receipt["files_sha256"][path.name]:
                    raise ValueError(f"Receipt hash mismatch: {path.name}")
                inputs[category].append({"run_id": row.run_id, **record})
            inputs["receipts"].append({"run_id": row.run_id, **file_record(receipt_path)})
            original_scores = {}
            mapped_prediction_keys = set()
            with csv_open(prediction) as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != KEYS + ["score"]:
                    raise ValueError("Prediction columns differ")
                for p in reader:
                    raw_key = p["transcript_id"], integer(p["transcript_position"], "position")
                    key = aliases[row.run_id].get(raw_key[0], raw_key[0]), raw_key[1]
                    value = float(p["score"])
                    if raw_key in original_scores or key in mapped_prediction_keys or key not in key_to_index or not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError("Prediction duplicate/alias collision/unmatched key/invalid score")
                    original_scores[raw_key] = value
                    mapped_prediction_keys.add(key)
                    scores[key_to_index[key], j] = value
            expected_keys = {keys[i] for i in np.flatnonzero(counts_expected[:, j] >= 20)}
            if mapped_prediction_keys != expected_keys:
                raise ValueError("Prediction keys differ from complete eligible coverage set")
            totals = Counter()
            matched_predictions = set()
            with csv_open(metadata) as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != METADATA_COLUMNS:
                    raise ValueError("Metadata columns differ")
                for meta in reader:
                    transcript = meta["transcript_id"]
                    position = integer(meta["transcript_position"], "position")
                    count = integer(meta["n_reads_input"], "source reads", 1)
                    finite = integer(meta["n_reads_finite"], "finite reads", 1)
                    if count != finite:
                        raise ValueError("Source/finite read counts differ")
                    raw = meta["sequence_7mer"]
                    canonical, encoded, ambiguous, central_a = context_identity(raw)
                    if meta["motif_5mer"] != raw[1:6]:
                        raise ValueError("Metadata motif is inconsistent with raw context")
                    if meta["prediction_status"] != ("eligible" if count >= 20 else "below_minimum_source_reads"):
                        raise ValueError("Metadata prediction status contradicts coverage")
                    totals["source_sites"] += 1
                    totals["source_reads"] += count
                    totals["source_ambiguous_contexts"] += ambiguous
                    totals["source_noncentral_a"] += not central_a
                    key = aliases[row.run_id].get(transcript, transcript), position
                    i = key_to_index.get(key)
                    if i is None:
                        totals["outside_coverage_union_sites"] += 1
                        totals["outside_coverage_union_reads"] += count
                        if count >= 20:
                            raise ValueError("Scored metadata key outside coverage union")
                        continue
                    if read_counts[i, j]:
                        collision_writer.writerow({"run_id": row.run_id, "transcript_id": key[0], "transcript_position": position,
                                                   "previous_raw_transcript_id": original_transcripts[j].get(i, key[0]), "incoming_raw_transcript_id": transcript})
                        raise ValueError("Within-run canonical key collision; collision evidence preserved")
                    if raw not in context_to_code:
                        if len(raw_contexts) >= 65536:
                            raise ValueError("Too many literal context variants for compact matrix")
                        context_to_code[raw] = len(raw_contexts)
                        raw_contexts.append(raw)
                    read_counts[i, j] = count
                    context_codes[i, j] = context_to_code[raw]
                    if transcript != key[0]:
                        original_transcripts[j][i] = transcript
                        totals["explicit_alias_observations_in_union"] += 1
                    totals["union_source_observations"] += 1
                    totals["union_source_reads"] += count
                    if count >= 20:
                        raw_key = transcript, position
                        if raw_key not in original_scores or raw_key in matched_predictions:
                            raise ValueError("Scored metadata does not exactly match original prediction identifiers")
                        matched_predictions.add(raw_key)
                        totals["scored_sites"] += 1
                        totals["scored_reads"] += count
                        if count != counts_expected[i, j]:
                            raise ValueError("Metadata/coverage read count mismatch")
            if matched_predictions != set(original_scores):
                raise ValueError("Prediction lacks its exact eligible metadata record")
            for actual, saved in [("source_sites", "input_sites"), ("source_reads", "input_reads"), ("scored_sites", "scored_sites"), ("scored_reads", "eligible_reads")]:
                if totals[actual] != receipt["counts"][saved]:
                    raise ValueError(f"Metadata count mismatch: {actual}")
            if not np.array_equal(read_counts[:, j] >= 20, counts_expected[:, j] >= 20):
                raise ValueError("Scored metadata missing from coverage union")
            run_summaries.append({"run_id": row.run_id, "cell_line": row.cell_line, "biological_replicate": row.biological_replicate, **dict(totals)})
            print(f"Context metadata audited {j + 1}/{len(run_ids)}: {row.run_id} ({totals['source_sites']:,} source rows)", flush=True)
    annotated = annotations.kind.eq("annotated").to_numpy()
    primary = np.zeros(n, dtype=bool)
    scored_only = np.zeros(n, dtype=bool)
    counters = Counter()
    key_fields = KEYS + list(context_summary(np.array([1], dtype=np.uint16), np.array([20]), ["", "AAAACAA"])) + ["kind", "training_positive_labels_all_source", "weak_positive_support_lt20", "zero_positive_support", "unseen_training_context", "training_support_known_for_all_contexts"]
    observation_fields = ["run_id", "cell_line", "biological_replicate", "original_transcript_id", "transcript_id", "transcript_position", "sequence_7mer_literal", "sequence_7mer_upper_u_to_t", "model_encoded_7mer", "n_reads", "scored", "score", "all_source_consistent", "scored_consistent", "kind"]
    with csv_open(output / "key_context_qc.csv.gz", "wt") as key_handle, csv_open(output / "conflicting_context_observations.csv.gz", "wt") as conflict_handle:
        key_writer, conflict_writer = csv.DictWriter(key_handle, fieldnames=key_fields), csv.DictWriter(conflict_handle, fieldnames=observation_fields)
        key_writer.writeheader(); conflict_writer.writeheader()
        for i, key in enumerate(keys):
            result = context_summary(context_codes[i], read_counts[i], raw_contexts)
            primary[i], scored_only[i] = result["all_source_consistent"], result["scored_consistent"]
            encoded = result["encoded7mer_all_source"]
            support = training_support.get(encoded) if result["all_source_consistent"] else None
            observed_contexts = result["encoded_contexts_all_source"].split("|")
            known_support = [training_support[value] for value in observed_contexts if value in training_support]
            result.update({"kind": annotations.kind.iat[i], "training_positive_labels_all_source": support if support is not None else "",
                           "weak_positive_support_lt20": any(value < 20 for value in known_support), "zero_positive_support": any(value == 0 for value in known_support),
                           "unseen_training_context": any(value not in training_support for value in observed_contexts),
                           "training_support_known_for_all_contexts": len(known_support) == len(observed_contexts)})
            key_writer.writerow(dict(zip(KEYS, key), **result))
            counters["coverage_union_keys"] += 1
            counters["primary_all_source_consistent_keys"] += primary[i]
            counters["scored_only_consistent_keys"] += scored_only[i]
            counters["multi_run_source_keys"] += result["n_source_runs"] >= 2
            counters["multi_run_scored_keys"] += result["n_scored_runs"] >= 2
            counters["encoded_conflict_all_source_keys"] += result["n_encoded_contexts_all_source"] > 1
            counters["encoded_conflict_scored_keys"] += result["n_encoded_contexts_scored"] > 1
            counters["literal_difference_only_keys"] += result["n_literal_contexts_all_source"] > 1 and result["n_encoded_contexts_all_source"] == 1
            counters["ambiguous_all_source_keys"] += result["ambiguous_context_all_source"]
            counters["noncentral_a_all_source_keys"] += result["noncentral_a_all_source"]
            if support is not None:
                counters["primary_zero_positive_support_keys"] += support == 0
                counters["primary_lt20_positive_support_keys"] += support < 20
            if primary[i]:
                counters["primary_unseen_training_context_keys"] += encoded not in training_support
            if not primary[i]:
                for j in np.flatnonzero(read_counts[i]):
                    raw = raw_contexts[int(context_codes[i, j])]
                    canonical, encoded, _, _ = context_identity(raw)
                    row = manifest.iloc[j]
                    value = scores[i, j]
                    conflict_writer.writerow({"run_id": row.run_id, "cell_line": row.cell_line, "biological_replicate": row.biological_replicate,
                                              "original_transcript_id": original_transcripts[j].get(i, key[0]), "transcript_id": key[0], "transcript_position": key[1],
                                              "sequence_7mer_literal": raw, "sequence_7mer_upper_u_to_t": canonical, "model_encoded_7mer": encoded,
                                              "n_reads": int(read_counts[i, j]), "scored": int(read_counts[i, j]) >= 20, "score": repr(float(value)) if np.isfinite(value) else "",
                                              "all_source_consistent": bool(primary[i]), "scored_consistent": bool(scored_only[i]), "kind": annotations.kind.iat[i]})
                    counters["conflict_union_observations"] += 1
                    counters["conflict_scored_observations"] += np.isfinite(value)
    populations = population_effects(read_counts, manifest, annotated, primary, scored_only)
    pd.DataFrame(populations).to_csv(output / "population_effects.csv", index=False)
    pd.DataFrame(run_summaries).to_csv(output / "run_qc_counts.csv", index=False)
    totals = {name: sum(row.get(name, 0) for row in run_summaries) for name in set().union(*(row.keys() for row in run_summaries)) - {"run_id", "cell_line", "biological_replicate"}}
    summary = {"status": "complete", "counts": {k: int(v) for k, v in counters.items()}, "source_totals": totals, "policy": POLICY,
               "interpretation": "Context compatibility is not exact FASTA/offset identity, assay validation, independent lab replication or a causal biological effect",
               "resources": {"wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu},
               "resource_scope": "Current process from after new output directory creation to summary construction; excludes later input rehashes and final receipt/status writes. No child process or peak-memory claim",
               "software": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}}
    json_write(output / "summary.json", summary)
    for name, path in paths.items():
        if sha(path) != inputs[name]["sha256"]:
            raise ValueError(f"Input changed during QC: {name}")
    for category in ("predictions", "metadata", "receipts", "input_audits"):
        for record in inputs[category]:
            prediction_row = manifest.loc[manifest.run_id.eq(record["run_id"])].iloc[0]
            parent = (Path(manifest_path).parent / prediction_row.prediction_file).resolve().parent
            if category == "input_audits":
                parent = parent.parent / "input_audits"
            if sha(parent / record["path"]) != record["sha256"]:
                raise ValueError("Prediction/metadata/receipt changed during QC")
    if sha(Path(__file__)) != source_hash:
        raise ValueError("QC source changed during execution")
    if sha(model_path) != model_sha:
        raise ValueError("Model changed during QC")
    outputs = {path.name: file_record(path) for path in output.iterdir() if path.name not in {"complete.json", "status.json"}}
    receipt = {"status": "complete", "inputs": inputs, "outputs": outputs, "policy": POLICY, "script_sha256": source_hash,
               "no_training_or_inference": True, "counts": summary["counts"], "resources": summary["resources"]}
    json_write(output / "complete.json", receipt)
    json_write(output / "status.json", {"status": "complete", "complete_sha256": sha(output / "complete.json")})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base = REPO / "sgnex_analysis"
    received = base / "outputs/received_member4_20261019"
    parser.add_argument("--manifest", type=Path, default=base / "manifest.csv")
    parser.add_argument("--coverage", type=Path, default=received / "results/coverage_matrix_ge20_union.csv.gz")
    parser.add_argument("--annotations", type=Path, default=received / "results/site_annotations.csv.gz")
    parser.add_argument("--aliases", type=Path, default=received / "metadata/transcript_aliases_checked.csv")
    parser.add_argument("--training-support", type=Path, default=base / "training_context_support/training_7mer_support.csv")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    existed_before = args.out.exists()
    try:
        summary = run_audit(args.manifest, args.coverage, args.annotations, args.aliases, args.training_support, args.out)
        print(json.dumps(summary, indent=2), flush=True)
    except BaseException as exc:
        if not existed_before and args.out.exists() and not (args.out / "complete.json").exists():
            json_write(args.out / "status.json", {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
