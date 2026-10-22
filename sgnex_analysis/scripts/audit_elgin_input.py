"""Check genuine event input against Member 4's fixed coverage population.

No model fitting/inference, label inspection, reference reconstruction or
coordinate conversion. Original IDs remain in input; only an explicit run
alias is used for comparison with the inherited coverage matrix.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import json
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "model_elgin/context_reference_v1"))
from data import iter_sites, sha256


def audit(source, run_id, manifest, coverage, aliases, output):
    if output.exists():
        raise ValueError("Preserve existing audit; use a fresh output path")
    start, cpu = time.perf_counter(), time.process_time()
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 23 or len({r["run_id"] for r in rows}) != 23:
        raise ValueError("Expected the agreed 23-run inventory")
    row = next((r for r in rows if r["run_id"] == run_id), None)
    if row is None or source.stat().st_size != int(row["signal_size_bytes"]):
        raise ValueError("Unknown run or source size differs from inventory")
    source_hash = sha256(source)
    remap = {}
    with aliases.open(newline="", encoding="utf-8-sig") as handle:
        for alias in csv.DictReader(handle):
            if alias["run_id"] == run_id:
                raw, mapped = alias["raw_transcript_id"], alias["transcript_id"]
                if raw in remap:
                    raise ValueError("Ambiguous explicit alias")
                remap[raw] = mapped
    expected = {}
    with gzip.open(coverage, "rt", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if run_id not in reader.fieldnames:
            raise ValueError("Run absent from coverage matrix")
        for record in reader:
            count = int(record[run_id])
            if count >= 20:
                key = record["transcript_id"], int(record["transcript_position"])
                if key in expected:
                    raise ValueError("Duplicate inherited coverage key")
                expected[key] = count
    observed, motifs = {}, Counter()
    thresholds = {depth: 0 for depth in (1, 5, 10, 20, 50, 100)}
    n_sites = n_reads = ambiguous = noncentral_a = 0
    for transcript, position, context, reads in iter_sites(source):
        count = len(reads)
        n_sites += 1
        n_reads += count
        for depth in thresholds:
            thresholds[depth] += int(count >= depth)
        canonical = context.upper().replace("U", "T")
        ambiguous += int(any(base not in "ACGT" for base in canonical))
        noncentral_a += int(canonical[3] != "A")
        if count >= 20:
            key = remap.get(transcript, transcript), position
            if key in observed:
                raise ValueError("Aliases collapse distinct eligible sites")
            observed[key] = count
            motifs[canonical[1:6]] += 1
    if n_sites != int(row["n_candidate_site_rows"]):
        raise ValueError("Full candidate count differs from Member 4 inventory")
    for depth, count in thresholds.items():
        if count != int(row[f"n_sites_ge{depth}"]):
            raise ValueError(f"Coverage denominator differs at {depth} reads")
    if observed != expected:
        missing = len(expected.keys() - observed.keys())
        extra = len(observed.keys() - expected.keys())
        changed = sum(observed[k] != expected[k] for k in observed.keys() & expected.keys())
        raise ValueError(f"Coverage mismatch: {missing} missing, {extra} extra, {changed} changed counts")
    if sha256(source) != source_hash:
        raise ValueError("Source changed during audit")
    result = {
        "status": "complete", "run_id": run_id, "source_basename": source.name,
        "source_sha256": source_hash, "source_size_bytes": source.stat().st_size,
        "inventory_sha256": sha256(manifest), "coverage_sha256": sha256(coverage),
        "aliases_sha256": sha256(aliases), "auditor_sha256": sha256(Path(__file__)),
        "strict_parser_sha256": sha256(REPO / "model_elgin/context_reference_v1/data.py"),
        "n_source_sites": n_sites, "n_reads": n_reads,
        "sites_at_least_reads": thresholds, "coverage_key_and_count_match": True,
        "eligible_central5_counts": dict(sorted(motifs.items())),
        "ambiguous_context_sites": ambiguous, "noncentral_a_sites": noncentral_a,
        "explicit_run_aliases": len(remap), "labels_read": False,
        "fitting_or_inference": False,
        "resources": {"wall_seconds": time.perf_counter() - start,
                      "process_cpu_seconds": time.process_time() - cpu},
        "limitations": [
            "Feature/coverage compatibility does not establish exact historical preprocessing or FASTA identity.",
            "Literal positions are retained; nucleotide origin and event offsets remain unverified.",
            "Coverage populations are not modified-site counts or independent biological replication.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=REPO / "sgnex_analysis/metadata/sample_manifest.csv")
    received = REPO / "sgnex_analysis/outputs/received_member4_20261019"
    parser.add_argument("--coverage", type=Path, default=received / "results/coverage_matrix_ge20_union.csv.gz")
    parser.add_argument("--aliases", type=Path, default=received / "metadata/transcript_aliases_checked.csv")
    args = parser.parse_args()
    result = audit(args.input, args.run_id, args.manifest, args.coverage, args.aliases, args.output)
    print(json.dumps({key: result[key] for key in ("status", "run_id", "n_source_sites", "n_reads", "sites_at_least_reads", "coverage_key_and_count_match", "resources")}), flush=True)


if __name__ == "__main__":
    main()
