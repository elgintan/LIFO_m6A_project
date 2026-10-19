"""Validate and export existing historical data0 OOF scores; never fit or predict.

The export adds only the original fold_id metadata required by the team scorer.
Raw labels/signals are read locally for provenance checks, never exported.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FOLD_SHA = "986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0"
KEY = ["transcript_id", "transcript_position"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_rows(path, expected_columns):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_columns, f"Wrong columns: {Path(path).name}")
        rows = []
        seen = set()
        for line, row in enumerate(reader, 2):
            require(None not in row and all(value is not None for value in row.values()),
                    f"Malformed CSV row {line}: {Path(path).name}")
            transcript = row["transcript_id"]
            position = row["transcript_position"]
            require(bool(transcript) and transcript == transcript.strip(), "Invalid transcript ID")
            require(re.fullmatch(r"0|[1-9][0-9]*", position) is not None,
                    "Position must be a canonical non-negative integer")
            key = transcript, int(position)
            require(key not in seen, f"Duplicate site: {Path(path).name}")
            seen.add(key)
            if "score" in row:
                score = float(row["score"])
                require(math.isfinite(score) and 0 <= score <= 1, "Invalid prediction score")
            rows.append((key, row))
    require(bool(rows), f"Empty CSV: {Path(path).name}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-run", type=Path, required=True,
                        help="Completed original candidate directory containing OOF and five fold CSVs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--folds", type=Path, default=REPO / "eda/received/shared_folds/data0_folds.csv")
    parser.add_argument("--labels", type=Path, help="Optional explicit local data0 label path")
    parser.add_argument("--raw-input", type=Path, help="Optional explicit local data0 JSON/gzip path")
    args = parser.parse_args()
    run = args.historical_run.resolve()
    historical_root = run.parent.parent
    labels = args.labels or historical_root.parent / "data0/data.info.labelled"
    raw = args.raw_input or historical_root.parent / "data0/dataset0.json.gz"
    inputs = {}
    locations = {}

    def checked(name, path, expected=None):
        actual = sha256(path)
        require(expected is None or actual == expected, f"Changed input fingerprint: {name}")
        inputs[name] = {"basename": Path(path).name, "sha256": actual}
        locations[name] = Path(path)
        return actual

    checked("search_manifest", run.parent / "search_manifest.json")
    plan = read_json(run.parent / "search_manifest.json")
    checked("shared_folds", args.folds, FOLD_SHA)
    require(plan["shared_fold_sha256"] == FOLD_SHA, "Historical run used different outer folds")
    checked("data0_labels", labels, plan["labels_sha256"])
    for name, expected in plan["source_sha256"].items():
        checked("training_source/" + name, historical_root / name, expected)
    cache_path = historical_root / "cache/data0/manifest.json"
    checked("data0_cache_manifest", cache_path, plan["cache_manifest_sha256"])
    cache = read_json(cache_path)
    require(cache["status"] == "completed", "Incomplete historical data0 cache")
    checked("data0_raw_input", raw, cache["input_sha256"])

    checked("cv_metrics", run / "cv_metrics.json")
    cv = read_json(run / "cv_metrics.json")
    checked("frozen_specification", run.parent / "frozen_specification.json")
    frozen = read_json(run.parent / "frozen_specification.json")
    require(cv["config"] == frozen["config"], "Run is not the frozen historical candidate")
    require(cv["config"]["id"] == run.name, "Candidate directory/configuration mismatch")
    require(inputs["cv_metrics"]["sha256"] == frozen["cv_metrics_sha256"], "Changed historical CV metrics")
    require(sorted(row["fold_id"] for row in cv["folds"]) == list(range(5)), "Incomplete CV metric folds")
    checked("fold_metrics", run / "fold_metrics.json")
    require(read_json(run / "fold_metrics.json") == cv["folds"], "Historical fold metric records disagree")

    folds = dict(read_rows(args.folds, KEY + ["gene_id", "fold_id"]))
    genes = {}
    for key, row in folds.items():
        require(row["fold_id"] in {"0", "1", "2", "3", "4"}, "Invalid fold ID")
        previous = genes.setdefault(row["gene_id"], row["fold_id"])
        require(previous == row["fold_id"], "A gene crosses outer folds")
    labels_by_key = dict(read_rows(labels, ["gene_id"] + KEY + ["label"]))
    require(set(labels_by_key) == set(folds), "Labels and frozen fold populations differ")
    require(all(row["label"] in {"0", "1"} for row in labels_by_key.values()), "Non-binary data0 labels")
    require(all(labels_by_key[key]["gene_id"] == row["gene_id"] for key, row in folds.items()),
            "Label/fold gene mapping differs")
    checked("historical_oof", run / "oof_predictions.csv")
    oof_rows = read_rows(run / "oof_predictions.csv", KEY + ["score"])
    oof = dict(oof_rows)
    require(set(oof) == set(folds), "Historical OOF does not cover the complete frozen population")
    per_fold_counts = {}
    for number in range(5):
        path = run / f"fold{number}_predictions.csv"
        checked(f"fold{number}_predictions", path)
        predictions = dict(read_rows(path, KEY + ["score"]))
        expected_keys = {key for key, row in folds.items() if row["fold_id"] == str(number)}
        require(set(predictions) == expected_keys, f"Incomplete or wrong fold {number} prediction keys")
        require(all(float(row["score"]) == float(oof[key]["score"]) for key, row in predictions.items()),
                f"OOF values differ from saved fold {number} scores")
        stored = next(row for row in cv["folds"] if row["fold_id"] == number)
        require(stored["n_sites"] == len(expected_keys), "Saved fold count differs")
        fit_dir = run.parent / f"{run.name}_fold{number}_refit"
        checked(f"fold{number}_refit_complete", fit_dir / "complete.json")
        complete = read_json(fit_dir / "complete.json")
        require(complete["config"] == cv["config"], "Refit configuration differs")
        require(complete["validation_sites"] == 0, "Outer refit unexpectedly uses stopping validation")
        require(complete["train_sites"] == len(folds) - len(expected_keys), "Refit training count differs")
        require(complete["best_epoch"] == stored["selected_epochs"], "Refit epoch count differs")
        checked(f"fold{number}_refit_model", fit_dir / "best.pt", complete["best_sha256"])
        per_fold_counts[str(number)] = len(expected_keys)

    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(KEY + ["score", "fold_id"])
    for key, row in oof_rows:
        writer.writerow([key[0], key[1], row["score"], folds[key]["fold_id"]])
    csv_bytes = text.getvalue().encode("utf-8")
    receipt = {
        "status": "validated_historical_reference_export",
        "script_sha256": sha256(__file__), "candidate_config": cv["config"],
        "n_sites": len(oof), "n_genes": len(genes), "per_fold_sites": per_fold_counts,
        "new_training": False, "new_predictions": False, "data1_or_data2_read": False,
        "prediction_change": "none; original OOF score text/order retained; immutable fold_id added",
        "inputs": inputs,
        "output": {"basename": "data0_oof.csv", "sha256": hashlib.sha256(csv_bytes).hexdigest()},
        "historical_fold_mean": cv["mean"], "historical_fold_sample_sd": cv["sample_sd"],
        "limitations": ["Historical development reference; prior architecture search used data0.",
                        "No claim of a new independent test or a new training run.",
                        "Trainer provenance and hashes corroborate, but do not alone prove, all training boundaries."],
        "command_template": "python model_elgin/tools/prepare_reference.py --historical-run HISTORICAL_RUN --output-dir OUTPUT_DIR [--labels LOCAL_DATA0_LABELS --raw-input LOCAL_DATA0_JSON]"
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    for name, path in locations.items():
        require(sha256(path) == inputs[name]["sha256"], f"Input changed during verification: {name}")
    output = args.output_dir.resolve()
    outputs = {"data0_oof.csv": csv_bytes, "reference_receipt.json": receipt_bytes}
    # Validate every existing destination before any write. Changed or partial
    # previous output is preserved for inspection, never silently replaced.
    exists = [(output / name).exists() for name in outputs]
    require(not any(exists) or all(exists), "Partial prior export exists; use a fresh output directory")
    if all(exists):
        require(all((output / name).read_bytes() == data for name, data in outputs.items()),
                "Existing export differs; refusing overwrite")
        print("PASS: reused identical validated historical reference export")
        return
    output.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        temporary = output / (name + ".tmp")
        require(not temporary.exists(), "Partial temporary output exists; preserve it and use a fresh directory")
    for name, data in outputs.items():
        temporary = output / (name + ".tmp")
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    for name in outputs:
        require(not (output / name).exists(), "Destination appeared during export; refusing overwrite")
        os.replace(output / (name + ".tmp"), output / name)
    print(f"PASS: {len(oof):,} unchanged historical scores; all five exact outer folds; no fitting/prediction")


if __name__ == "__main__":
    main()
