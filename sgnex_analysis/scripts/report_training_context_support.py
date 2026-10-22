"""Report data0 context/label support without fitting, inference or raw rescans.

Derived tables are companion analysis metadata, never new classifier inputs or
site-exclusion rules. The optional first-run summary uses its completed audit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np

REPO = Path(__file__).resolve().parents[2]
DATA0_SHA = "622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e"
LABELS_SHA = "6758f002db36835c188c9d6fb039b4599494ca9dcc816c26cc22a2c04ee42978"
CACHE_HASHES = {
    "seq.npy": "d43d7551943a3c60a6e848f65fbfe68f64e36ba60163ec2a1caafb6b56e48005",
    "keys.csv": "7f2af2c106df526dc5e3a5c46472198e0ee0e4abcd550e2eccc31a8bbeaeff97",
    "offsets.npy": "7d04496524e2cd2cc472f51da8e5f8da917fecb3a51952eaf08841ae7663df93",
}


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def support_row(context, counts, depths, column):
    n, positive = counts
    negative = n - positive
    return {column: context, "training_sites": n, "positive_labels": positive,
            "negative_labels": negative, "training_reads_min": min(depths),
            "training_reads_max": max(depths), "seen_in_data0": True,
            "zero_positive_labels": positive == 0,
            "sparse_positive_label_support_lt20": positive < 20,
            "class_support_ge20_each": min(positive, negative) >= 20}


def report(args, output):
    start, cpu = time.perf_counter(), time.process_time()
    cache = args.cache.resolve()
    manifest = read_json(cache / "manifest.json")
    if (manifest.get("status") != "completed" or manifest.get("input_sha256") != DATA0_SHA
            or manifest.get("n_sites") != 121838 or manifest.get("n_reads_total") != 11027106):
        raise ValueError("Expected the completed agreed data0 cache")
    inputs = {"cache_manifest.json": sha(cache / "manifest.json")}
    for filename, expected in CACHE_HASHES.items():
        observed = sha(cache / filename)
        if observed != expected or manifest["cache_sha256"].get(filename) != expected:
            raise ValueError("Training cache fingerprint differs: " + filename)
        inputs[filename] = observed
    if sha(args.labels) != LABELS_SHA:
        raise ValueError("Label file differs from agreed data0")
    inputs["data0_labels"] = LABELS_SHA
    inputs["member1_motif_summary.csv"] = sha(args.motif_summary)
    labels = {}
    for row in csv_rows(args.labels):
        key = row["transcript_id"], int(row["transcript_position"])
        if key in labels or row["label"] not in ("0", "1"):
            raise ValueError("Duplicate label key or nonbinary training label")
        labels[key] = int(row["label"])
    keys = csv_rows(cache / "keys.csv")
    sequence = np.load(cache / "seq.npy", mmap_mode="r", allow_pickle=False)
    offsets = np.load(cache / "offsets.npy", mmap_mode="r", allow_pickle=False)
    if (sequence.shape != (121838, 7) or len(keys) != len(labels)
            or len(keys) != len(sequence) or offsets.shape != (len(keys) + 1,)
            or int(offsets[0]) != 0 or int(offsets[-1]) != 11027106):
        raise ValueError("Training cache shape/population differs")
    if sequence.dtype.kind not in "iu" or np.any((sequence < 0) | (sequence > 3)):
        raise ValueError("Expected canonical training sequence codes")
    depths = np.diff(offsets).astype(np.int64)
    if np.any(depths <= 0):
        raise ValueError("Invalid training read offsets")
    context_counts, motif_counts = Counter(), Counter()
    context_positive, motif_positive = Counter(), Counter()
    context_depth, motif_depth = defaultdict(list), defaultdict(list)
    seen = set()
    for row, codes, depth in zip(keys, sequence, depths):
        key = row["transcript_id"], int(row["transcript_position"])
        context = "".join("ACGT"[int(code)] for code in codes)
        if key in seen or key not in labels or row["context"].upper().replace("U", "T") != context:
            raise ValueError("Cache sequence/key mismatch")
        if int(row["n_reads"]) != int(depth):
            raise ValueError("Cache read counts differ from offsets")
        seen.add(key)
        motif = context[1:6]
        context_counts[context] += 1
        motif_counts[motif] += 1
        context_positive[context] += labels[key]
        motif_positive[motif] += labels[key]
        context_depth[context].append(int(depth))
        motif_depth[motif].append(int(depth))
    if seen != set(labels) or sum(context_positive.values()) != 5475:
        raise ValueError("Training label alignment or positive count differs")
    motifs = {"".join(p) for p in itertools.product("AGT", "AG", "A", "C", "ACT")}
    universe = {left + motif + right for left, motif, right in itertools.product("ACGT", motifs, "ACGT")}
    if set(context_counts) != universe or set(motif_counts) != motifs:
        raise ValueError("Expected all 288 canonical DRACH-centred training seven-mers")
    member1 = {row["motif"]: (int(row["n_sites"]), int(row["positive_sites"]))
               for row in csv_rows(args.motif_summary) if row["dataset"] == "data0"}
    if member1 != {m: (motif_counts[m], motif_positive[m]) for m in motifs}:
        raise ValueError("Training motif support differs from Member 1's findings")
    rows7 = [support_row(c, (context_counts[c], context_positive[c]), context_depth[c], "sequence_7mer")
             for c in sorted(context_counts)]
    rows5 = [support_row(m, (motif_counts[m], motif_positive[m]), motif_depth[m], "motif_5mer")
             for m in sorted(motifs)]
    for row in rows7:
        row["motif_5mer"] = row["sequence_7mer"][1:6]
    write_csv(output / "training_7mer_support.csv", rows7)
    write_csv(output / "training_motif_support.csv", rows5)
    first = None
    if args.first_input_audit:
        audit = read_json(args.first_input_audit)
        if (audit.get("status") != "complete" or not audit.get("coverage_key_and_count_match")
                or audit.get("labels_read") is not False or audit.get("fitting_or_inference") is not False):
            raise ValueError("Expected a completed label-free first-input audit")
        counts = audit["eligible_central5_counts"]
        eligible = audit["sites_at_least_reads"]["20"]
        if sum(counts.values()) != eligible or audit["ambiguous_context_sites"] != 0:
            raise ValueError("Audit does not support the canonical-context coverage deduction")
        unseen = sum(n for motif, n in counts.items() if motif not in motif_counts)
        if unseen:
            raise ValueError("Audit contains nontraining central motifs; seven-mer deduction unavailable")
        sparse = sum(n for motif, n in counts.items() if motif_positive[motif] < 20)
        first = {"run_id": audit["run_id"], "input_sha256": audit["source_sha256"],
                 "audit_sha256": sha(args.first_input_audit), "eligible_sites_ge20": eligible,
                 "unseen_encoded_central5_sites": unseen, "unseen_encoded_7mer_sites": 0,
                 "unseen_7mer_method": "Deduction from complete training canonical universe and audited canonical central motifs; U maps to T",
                 "distinct_observed_7mers": None, "raw_input_rescanned": False,
                 "sparse_central5_positive_support_sites": sparse,
                 "sparse_central5_positive_support_fraction": sparse / eligible,
                 "raw_sites_below20": audit["n_source_sites"] - eligible,
                 "scope": "One run's input/coverage audit; no SG-NEx prediction completion or label accuracy implied"}
        inputs["first_full_input_audit.json"] = first["audit_sha256"]
        save_json(output / "first_run_context_support.json", first)
    summary = {"status": "complete", "training_sites": len(keys), "positive_labels": 5475,
               "negative_labels": len(keys) - 5475, "training_reads": int(offsets[-1]),
               "training_reads_min": int(depths.min()), "training_reads_max": int(depths.max()),
               "central5_contexts": len(rows5), "exact7_contexts": len(rows7),
               "complete_canonical_DRACH7_universe": True,
               "sevenmers_zero_positive_labels": sum(r["zero_positive_labels"] for r in rows7),
               "sevenmers_fewer_than20_positive_labels": sum(r["sparse_positive_label_support_lt20"] for r in rows7),
               "sevenmers_atleast20_each_class": sum(r["class_support_ge20_each"] for r in rows7),
               "sparse_positive_central5_motifs": [r["motif_5mer"] for r in rows5 if r["sparse_positive_label_support_lt20"]],
               "first_run": first, "source_sha256": inputs,
               "reporter_sha256": sha(__file__),
               "resources": {"wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu},
               "scope": "Existing cache/label/EDA aggregate analysis; no model fitting, inference or raw SG-NEx rescan"}
    save_json(output / "provenance.json", summary)
    first_text = ("The first run's existing input audit supports zero unseen **model-encoded**\n"
                  "canonical contexts among its {:,} eligible sites, with U mapped to T.\n"
                  "Its distinct observed seven-mer count was not enumerated. {:,} sites\n"
                  "({:.3f}%) have one of the three sparse-positive central motifs. This is\n"
                  "an input-support deduction, not a completed-prediction or accuracy result.\n".format(
                      first["eligible_sites_ge20"], first["sparse_central5_positive_support_sites"],
                      100 * first["sparse_central5_positive_support_fraction"])) if first else "No SG-NEx input audit was included.\n"
    (output / "README.md").write_text("""# Training-context support for Task 2

**Task 2 preparation: this report summarises existing data0 support.** It does
not train, predict, change classifier inputs or exclude sites.

All 121,838 training sites contain 18 central DRACH motifs and every one of the
288 canonical seven-base contexts. Training read depth ranges from 20 to 991.
The seven-mer tables contain 5,475 positive and 116,363 negative labels in total.
The 18-motif counts exactly reproduce
[Member 1's supplied motif summary](../../eda/received/tables/motif_summary.csv).

Seen context is different from sufficient positive-label evidence: 56 seven-mers
have zero positive labels; 211 have fewer than 20; 77 have at least 20 examples
of each class. At the central-motif level AAACC has 11 positives, TAACA 1 and
TAACC 2. These motifs were included in training, despite sparse subgroup
evaluation support. The model shares learned parameters across contexts;
zero positives within a seven-mer does not prohibit a positive prediction.

""" + first_text + """
Use `training_7mer_support.csv` for a companion metadata join after canonicalising
sequence to uppercase and U to T. `training_motif_support.csv` supports the
central-five-base join. Preserve the required three-column prediction CSVs.
For genuinely unseen contexts in later inputs, record zero training support
and a separate unseen flag. Never silently remove them or alter thresholds.
Sites below 20 reads lie outside the observed training depth range and outside
the primary Member 4 analysis population. Retain the unchanged raw input and
all-source QC metadata; these low-coverage sites remain explicitly unscored.
The core model export covers all eligible sites only.
Sparse labels are an evidence limitation, not a calibrated uncertainty score.

From the repository root, using the pinned model environment:

```text
python -B sgnex_analysis/scripts/report_training_context_support.py
```

The command reads local cache/labels and the completed first-run audit. Use
`--skip-first-input-audit` for a training-only report, and `--output-dir` with a
fresh directory for a repeated check. Exact input and reporter fingerprints,
counts and measured timing are in `provenance.json`; `complete.json` is written
last. No complete 23-run predictions or biological conclusions are claimed.
""", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO.parent / "advanced_model/cache/data0")
    parser.add_argument("--labels", type=Path, default=REPO.parent / "data0/data.info.labelled")
    parser.add_argument("--motif-summary", type=Path, default=REPO / "eda/received/tables/motif_summary.csv")
    parser.add_argument("--first-input-audit", type=Path, default=REPO / "sgnex_analysis/outputs/preflight/first_full_input_audit.json")
    parser.add_argument("--skip-first-input-audit", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=REPO / "sgnex_analysis/training_context_support")
    args = parser.parse_args()
    if args.skip_first_input_audit:
        args.first_input_audit = None
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Preserve existing reports; choose a fresh output directory")
    save_json(output / "status.json", {"status": "running"})
    try:
        summary = report(args, output)
        save_json(output / "status.json", {"status": "complete"})
        receipt = {"status": "complete", "reporter_sha256": sha(__file__), "files_sha256": {
            path.name: sha(path) for path in sorted(output.iterdir()) if path.name != "complete.json"}}
        save_json(output / "complete.json", receipt)
    except BaseException as error:
        save_json(output / "status.json", {"status": "failed_partial_outputs_preserved", "error_type": type(error).__name__})
        raise
    print(json.dumps({"status": "complete", "training_sites": summary["training_sites"],
                      "central5_contexts": summary["central5_contexts"], "exact7_contexts": summary["exact7_contexts"]}))


if __name__ == "__main__":
    main()
