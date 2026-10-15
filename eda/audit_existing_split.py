"""Describe existing gene folds using received EDA summaries; never generate a split."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bin_name(n):
    return "20-49" if n < 50 else "50-99" if n < 100 else "100-199" if n < 200 else "200-499" if n < 500 else "500+"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--summaries", type=Path, default=root / "received/tables/data0_site_summaries.csv.gz")
    parser.add_argument("--folds", type=Path, default=root / "received/shared_folds/data0_folds.csv")
    parser.add_argument("--output-dir", type=Path, default=root / "split_review")
    args = parser.parse_args()
    assignments, gene_fold = {}, {}
    with args.folds.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["transcript_id"], int(row["transcript_position"]))
            assert key not in assignments
            fold = int(row["fold_id"])
            assert fold in range(5)
            gene = row["gene_id"]
            assert gene_fold.setdefault(gene, fold) == fold
            assignments[key] = (fold, gene)
    counts = Counter()
    coverage_counts, motif_counts = Counter(), Counter()
    gene_sets = defaultdict(set)
    seen, motifs = set(), set()
    with gzip.open(args.summaries, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["transcript_id"], int(row["transcript_position"]))
            assert key not in seen
            seen.add(key)
            fold, gene = assignments[key]
            label = int(row["label"])
            assert row["dataset"] == "data0" and row["gene_id"] == gene and label in (0, 1)
            n = int(row["coverage"])
            assert n >= 20
            motif = row["motif"]
            assert motif == row["sequence"][1:6]
            motifs.add(motif)
            counts[fold, label] += 1
            gene_sets[fold].add(gene)
            coverage_counts[fold, bin_name(n), label] += 1
            motif_counts[fold, motif, label] += 1
    assert seen == set(assignments)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    folds = []
    for fold in range(5):
        negative, positive = counts[fold, 0], counts[fold, 1]
        folds.append({"fold": fold, "genes": len(gene_sets[fold]), "sites": negative + positive,
                      "negative": negative, "positive": positive,
                      "positive_fraction": positive / (negative + positive)})
    with (args.output_dir / "fold_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(folds[0]))
        writer.writeheader(); writer.writerows(folds)
    rows = []
    for fold in range(5):
        for motif in sorted(motifs):
            val0, val1 = motif_counts[fold, motif, 0], motif_counts[fold, motif, 1]
            train1 = sum(motif_counts[f, motif, 1] for f in range(5) if f != fold)
            rows.append({"fold": fold, "motif": motif, "validation_negative": val0,
                         "validation_positive": val1, "training_positive": train1,
                         "both_validation_classes": val0 > 0 and val1 > 0,
                         "validation_positive_below_20": val1 < 20})
    with (args.output_dir / "motif_support.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    cov_rows = [{"fold": f, "coverage_bin": b, "negative": coverage_counts[f, b, 0],
                 "positive": coverage_counts[f, b, 1]}
                for f in range(5) for b in ("20-49", "50-99", "100-199", "200-499", "500+")]
    with (args.output_dir / "coverage_support.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cov_rows[0]))
        writer.writeheader(); writer.writerows(cov_rows)
    result = {"status": "passed", "scope": "descriptive audit of historical assignments; no new split, filtering, training or prediction",
              "fold_sha256": sha(args.folds), "summary_sha256": sha(args.summaries),
              "sites": len(seen), "genes": len(gene_fold), "motifs": len(motifs),
              "folds": folds, "gene_overlap": False,
              "motif_fold_groups": len(rows),
              "motif_fold_groups_without_both_validation_classes": sum(not r["both_validation_classes"] for r in rows),
              "motif_fold_groups_with_zero_training_positive": sum(r["training_positive"] == 0 for r in rows),
              "motif_fold_groups_with_fewer_than_20_validation_positives": sum(r["validation_positive_below_20"] for r in rows),
              "note": "20 is a descriptive display-support reference, not an exclusion rule. Findings inform protocol choice; no design is approved by this audit."}
    (args.output_dir / "composition_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
