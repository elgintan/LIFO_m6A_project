"""Align completed published m6Anet site scores and call the shared evaluator.

Fold assignments organise scoring only: this published model was not trained
in our five-fold experiment and may overlap with course HCT116 data.
"""
import argparse
import csv
import importlib.util
import io
import json
from pathlib import Path

import prepare_input as adapter

SCORER_PATH = Path(__file__).resolve().parents[1] / "evaluate.py"
SPEC = importlib.util.spec_from_file_location("published_reference_scorer", SCORER_PATH)
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--folds", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    complete = args.reference_dir / "complete.json"
    receipt = json.loads(complete.read_text(encoding="utf-8"))
    if receipt.get("status") != "complete" or receipt.get("labels_used") is not False:
        raise ValueError("A completed label-free inference receipt is required")
    if receipt["input_audit"]["population"] != "full_source":
        raise ValueError("A pilot subset cannot be scored as the full reference")
    source = args.reference_dir / "data.site_proba.csv"
    if adapter.sha256(source) != receipt["output_files"][source.name]["sha256"]:
        raise ValueError("Published site output has changed")
    if adapter.sha256(args.folds) != SCORER.FOLD_SHA256:
        raise ValueError("Use the unchanged shared five gene folds")
    folds = SCORER.read_folds(args.folds)
    scores = {}
    with source.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = SCORER.site_key(row)
            if key in scores:
                raise ValueError("Duplicate published output site")
            scores[key] = row["probability_modified"]
    SCORER.same_keys(folds, scores, "Published reference/folds")
    if len(scores) != receipt["site_output_audit"]["sites"]:
        raise ValueError("Reference count differs from the completed inference audit")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()):
        raise ValueError("Preserve earlier scoring runs; use a fresh output directory")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["transcript_id", "transcript_position", "score", "fold_id"])
    for key, (_gene, fold) in folds.items():
        writer.writerow([key[0], key[1], scores[key], fold])
    prediction = args.output_dir / "data0_reference_scores.csv"
    with prediction.open("w", encoding="utf-8", newline="") as handle:
        handle.write(buffer.getvalue())
    metrics = SCORER.evaluate_files(args.labels, prediction, "data0", folds_path=args.folds)
    adapter.write_json_atomic(args.output_dir / "data0_reference_metrics.json", metrics)
    audit = {
        "status": "complete", "mean_fold": metrics["mean_fold"],
        "pooled": metrics["pooled"], "inference_receipt_sha256": adapter.sha256(complete),
        "site_output_sha256": adapter.sha256(source), "folds_sha256": adapter.sha256(args.folds),
        "labels_sha256": adapter.sha256(args.labels), "scorer_sha256": adapter.sha256(SCORER_PATH),
        "score_adapter_sha256": adapter.sha256(__file__),
        "prediction_sha256": adapter.sha256(prediction),
        "metrics_sha256": adapter.sha256(args.output_dir / "data0_reference_metrics.json"),
        "pretraining_provenance_limit": receipt["pretraining_provenance_limit"],
        "interpretation": "Published pretrained reference; fold-stratified scoring is not five-fold refitting or independent validation.",
    }
    adapter.write_json_atomic(args.output_dir / "scoring_receipt.json", audit)
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
