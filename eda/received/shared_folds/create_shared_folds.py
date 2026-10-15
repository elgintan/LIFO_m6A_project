"""Create or verify the team's frozen data0 gene-grouped cross-validation split.

Creation needs NumPy/scikit-learn. --verify-only uses Python's standard library.
This script reads metadata, not signal features, and never trains a model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


N_FOLDS = 5
FOLD_COLUMNS = ["transcript_id", "transcript_position", "gene_id", "fold_id"]
SUMMARY_COLUMNS = [
    "fold_id", "validation_sites", "validation_genes",
    "validation_negatives", "validation_positives", "validation_positive_fraction",
    "training_sites", "training_genes",
    "training_negatives", "training_positives", "training_positive_fraction",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nonnegative_integer(text: str, description: str) -> int:
    if not text or not text.isascii() or not text.isdecimal():
        raise ValueError(f"{description}: expected a nonnegative integer, got {text!r}")
    return int(text)


def load_labels(path: Path) -> list[tuple[str, int, str, int]]:
    """Validate site labels and sort by transcript ID then NUMERIC position."""
    records = []
    seen_sites = set()
    transcript_genes = {}
    required = {"transcript_id", "transcript_position", "gene_id", "label"}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Label CSV needs columns: {sorted(required)}")
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(name) is None for name in required):
                raise ValueError(f"Malformed label row at line {line_number}")
            transcript, gene = row["transcript_id"], row["gene_id"]
            if not transcript or transcript != transcript.strip() or not gene or gene != gene.strip():
                raise ValueError(f"Missing or whitespace-padded ID at line {line_number}")
            position = nonnegative_integer(row["transcript_position"], f"Line {line_number} position")
            if row["label"] not in {"0", "1"}:
                raise ValueError(f"Non-binary label at line {line_number}: {row['label']!r}")
            key = (transcript, position)
            if key in seen_sites:
                raise ValueError(f"Duplicate label site: {key}")
            seen_sites.add(key)
            if transcript in transcript_genes and transcript_genes[transcript] != gene:
                raise ValueError(f"Transcript maps to more than one gene: {transcript}")
            transcript_genes[transcript] = gene
            records.append((transcript, position, gene, int(row["label"])))
    if not records:
        raise ValueError("Label CSV is empty")
    records.sort(key=lambda record: (record[0], record[1]))
    if len({record[2] for record in records}) < N_FOLDS:
        raise ValueError("Fewer than five genes available")
    return records


def canonical_labels_hash(records: list[tuple[str, int, str, int]]) -> str:
    """Hash sorted ID/position/gene/label contents independently of line endings."""
    digest = hashlib.sha256()
    for record in records:
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def validate_folds(records, fold_path: Path) -> tuple[list[dict], dict]:
    """Re-read the actual CSV and check full key coverage, genes and both classes."""
    source = {(tx, pos): (gene, label) for tx, pos, gene, label in records}
    assignments = {}
    gene_folds = defaultdict(set)
    file_keys = []
    with fold_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FOLD_COLUMNS:
            raise ValueError(f"Fold CSV header must be exactly {FOLD_COLUMNS}")
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(name) is None for name in FOLD_COLUMNS):
                raise ValueError(f"Malformed fold row at line {line_number}")
            key = (
                row["transcript_id"],
                nonnegative_integer(row["transcript_position"], f"Fold line {line_number} position"),
            )
            fold = nonnegative_integer(row["fold_id"], f"Fold line {line_number} fold_id")
            if key in assignments:
                raise ValueError(f"Duplicate fold site: {key}")
            if key not in source:
                raise ValueError(f"Fold CSV has an extra site: {key}")
            if row["gene_id"] != source[key][0]:
                raise ValueError(f"Gene ID differs from label metadata at {key}")
            if fold not in range(N_FOLDS):
                raise ValueError(f"Invalid fold_id at {key}: {fold}")
            assignments[key] = fold
            gene_folds[row["gene_id"]].add(fold)
            file_keys.append(key)
    missing = source.keys() - assignments.keys()
    if missing:
        raise ValueError(f"Fold CSV is missing {len(missing)} sites; example: {min(missing)}")
    if file_keys != sorted(file_keys):
        raise ValueError("Fold CSV is not sorted by transcript_id and numeric position")
    if set(assignments.values()) != set(range(N_FOLDS)):
        raise ValueError("Fold CSV must contain all five fold IDs: 0, 1, 2, 3, 4")
    leaking_genes = [gene for gene, folds in gene_folds.items() if len(folds) != 1]
    if leaking_genes:
        raise ValueError(f"Genes in multiple folds: {leaking_genes[:5]}")
    class_counts = Counter(record[3] for record in records)
    summaries = []
    for fold in range(N_FOLDS):
        validation = Counter()
        validation_genes = set()
        for tx, pos, gene, label in records:
            if assignments[(tx, pos)] == fold:
                validation[label] += 1
                validation_genes.add(gene)
        training = class_counts - validation
        if any(validation[label] == 0 or training[label] == 0 for label in (0, 1)):
            raise ValueError(f"Fold {fold} lacks both classes in training or validation")
        n_valid, n_train = sum(validation.values()), sum(training.values())
        summaries.append({
            "fold_id": fold,
            "validation_sites": n_valid,
            "validation_genes": len(validation_genes),
            "validation_negatives": validation[0],
            "validation_positives": validation[1],
            "validation_positive_fraction": validation[1] / n_valid,
            "training_sites": n_train,
            "training_genes": len(gene_folds) - len(validation_genes),
            "training_negatives": training[0],
            "training_positives": training[1],
            "training_positive_fraction": training[1] / n_train,
        })
    checks = {
        "complete_metadata_site_coverage": True,
        "unique_site_keys": True,
        "sorted_by_transcript_id_and_numeric_position": True,
        "exactly_five_folds": True,
        "every_gene_in_exactly_one_fold": True,
        "gene_overlap_between_training_and_validation": 0,
        "both_classes_in_every_training_and_validation_partition": True,
        "fold_gene_ids_match_metadata": True,
    }
    return summaries, checks


def write_csv(path: Path, columns: list[str], rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def show_report(records, summaries, fold_path: Path) -> None:
    print(f"data0: {len(records):,} sites; {len({r[2] for r in records}):,} genes")
    print("fold_id | validation sites | genes | positives | positive %")
    for row in summaries:
        print(
            f"{row['fold_id']:7d} | {row['validation_sites']:16,d} | "
            f"{row['validation_genes']:5,d} | {row['validation_positives']:9,d} | "
            f"{100 * row['validation_positive_fraction']:9.4f}"
        )
    print("PASS: complete unique site coverage, five folds, no gene leakage, both classes.")
    print(f"Fold CSV SHA256: {sha256_file(fold_path)}")
    print("No model has been trained.")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=script_dir.parent / "data0" / "data.info.labelled")
    parser.add_argument("--output-dir", type=Path, default=script_dir)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-only", action="store_true", help="Check received files; never regenerate or write them")
    args = parser.parse_args()
    records = load_labels(args.labels)
    canonical_hash = canonical_labels_hash(records)
    fold_path = args.output_dir / "data0_folds.csv"
    metadata_path = args.output_dir / "data0_folds_metadata.json"
    summary_path = args.output_dir / "data0_fold_summary.csv"
    requirements_path = args.output_dir / "fold_generation_requirements.txt"

    if args.verify_only:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if canonical_hash != metadata["input_metadata_canonical_sha256"]:
            raise ValueError("Your data0 IDs/positions/genes/labels differ from the shared source")
        if sha256_file(fold_path) != metadata["fold_csv_sha256"]:
            raise ValueError("Fold CSV hash differs: restore the original CSV from the shared ZIP")
        if sha256_file(summary_path) != metadata["summary_csv_sha256"]:
            raise ValueError("Fold summary CSV hash differs from the shared source")
        summaries, checks = validate_folds(records, fold_path)
        if summaries != metadata["fold_summary"] or checks != metadata["validation_checks"]:
            raise ValueError("Recomputed fold checks or counts differ from the metadata")
        show_report(records, summaries, fold_path)
        if sha256_file(args.labels) != metadata["input_metadata_sha256"]:
            print("NOTE: label file bytes differ, but sorted IDs/positions/genes/labels match exactly.")
        return

    # Refuse to replace a frozen team artifact inadvertently.
    if any(path.exists() for path in (fold_path, metadata_path, summary_path, requirements_path)):
        raise ValueError("Outputs already exist. Use --verify-only; do not regenerate the team's split.")
    import numpy as np
    from sklearn.model_selection import StratifiedGroupKFold

    y = np.array([record[3] for record in records], dtype=np.int8)
    groups = np.array([record[2] for record in records])
    folds = np.full(len(records), -1, dtype=np.int8)
    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=args.seed)
    # X is only a placeholder for splitting; no signal features enter this step.
    for fold_id, (_, validation_indices) in enumerate(splitter.split(np.zeros((len(records), 1)), y, groups)):
        if np.any(folds[validation_indices] != -1):
            raise ValueError("Splitter assigned a site more than once")
        folds[validation_indices] = fold_id
    if np.any(folds == -1):
        raise ValueError("Splitter failed to assign every site")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(fold_path, FOLD_COLUMNS, (
        (tx, pos, gene, int(fold)) for (tx, pos, gene, _), fold in zip(records, folds, strict=True)
    ))
    summaries, checks = validate_folds(records, fold_path)
    write_csv(summary_path, SUMMARY_COLUMNS, (
        [row[column] for column in SUMMARY_COLUMNS] for row in summaries
    ))
    versions = {name: version(name) for name in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")}
    requirements_path.write_text(
        "# Only needed to recreate splits for an audit; teammates should use the supplied CSV.\n"
        + "".join(f"{name}=={installed}\n" for name, installed in versions.items()),
        encoding="utf-8", newline="\n",
    )
    counts = Counter(record[3] for record in records)
    metadata = {
        "artifact_version": 1,
        "team": "LIFO",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "data0",
        "input_metadata_filename": args.labels.name,
        "input_metadata_sha256": sha256_file(args.labels),
        "input_metadata_canonical_sha256": canonical_hash,
        "canonical_hash_definition": "Sorted (transcript_id, numeric position, gene_id, integer label), compact JSON array per UTF-8 LF line",
        "fold_csv_sha256": sha256_file(fold_path),
        "summary_csv_sha256": sha256_file(summary_path),
        "generator_script_sha256": sha256_file(Path(__file__)),
        "sort_order": ["transcript_id ascending", "transcript_position numeric ascending"],
        "splitter": "sklearn.model_selection.StratifiedGroupKFold",
        "n_splits": N_FOLDS,
        "shuffle": True,
        "random_state": args.seed,
        "group_column": "gene_id",
        "python_version": platform.python_version(),
        "generation_platform": platform.system(),
        "generation_package_versions": versions,
        "n_sites": len(records),
        "n_genes": len(set(groups)),
        "n_transcripts": len({record[0] for record in records}),
        "n_negatives": counts[0],
        "n_positives": counts[1],
        "positive_fraction": counts[1] / len(records),
        "validation_checks": checks,
        "fold_summary": summaries,
        "scope": "Metadata split only. Signal-record quality validation and model training not performed.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    show_report(records, summaries, fold_path)
    print(f"Saved shared artifacts in: {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ImportError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
