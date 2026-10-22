"""Report actual completed data0 references; never trains or selects a model."""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SPEC = importlib.util.spec_from_file_location("benchmark_shared_scorer", HERE / "evaluate.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)

SOURCES = [
    ("Logistic regression", "fixed18_balanced_C1", "gene-held-out development fits",
     "model_evaluation/simple_baseline/outputs/replay_v1/data0_oof.csv",
     "model_evaluation/simple_baseline/outputs/replay_v1/data0_cv_metrics.json"),
    ("Samuel LightGBM", "samuel", "received gene-held-out development fits",
     "model_samuel/outputs/data0_oof.csv", "model_samuel/results/data0_cv_metrics.json"),
    ("Elgin cap128 control", "elgin_cap128", "gene-held-out development fits",
     "model_elgin/outputs/read_cap_v1/cv/none/data0_oof.csv",
     "model_elgin/outputs/read_cap_v1/cv/none/data0_cv_metrics.json"),
    ("Published m6Anet", "m6anet", "pretrained reference; possible HCT116 overlap",
     "model_evaluation/outputs/m6anet_v1/scored/data0_reference_scores.csv",
     "model_evaluation/outputs/m6anet_v1/scored/data0_reference_metrics.json"),
]


def build_report(output):
    labels_path = REPO.parent / "data0/data.info.labelled"
    folds_path = REPO / "eda/received/shared_folds/data0_folds.csv"
    labels, _genes = SCORER.read_labels(labels_path)
    folds = SCORER.read_folds(folds_path)
    keys = list(folds)
    y = np.asarray([labels[key] for key in keys], dtype=int)
    if len(keys) != 121838 or int(y.sum()) != 5475:
        raise ValueError("Wrong complete comparison population")
    reference = json.loads((HERE / "outputs/m6anet_v1/full_run/complete.json").read_text())
    baseline = json.loads((HERE / "simple_baseline/outputs/replay_v1/status.json").read_text())
    if reference.get("status") != "complete" or baseline.get("status") != "complete":
        raise ValueError("Both required references must be complete")
    rows, curves, provenance = [], [], {}
    for name, ident, design, prediction_rel, metric_rel in SOURCES:
        prediction, metric = REPO / prediction_rel, REPO / metric_rel
        checked = SCORER.evaluate_files(labels_path, prediction, "data0", folds_path=folds_path)
        saved = json.loads(metric.read_text())
        for field in ("mean_fold", "pooled"):
            for number in ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score"):
                if abs(checked[field][number] - saved[field][number]) > 1e-12:
                    raise ValueError("Saved score does not reproduce: " + name)
        scores, _assignment = SCORER.read_predictions(prediction, "data0")
        SCORER.same_keys(folds, scores, name)
        curves.append((name, np.asarray([scores[key] for key in keys])))
        rows.append(dict(model=name, design=design, **checked["mean_fold"]))
        provenance[ident] = dict(predictions=prediction_rel, predictions_sha256=SCORER.sha256(prediction),
                                 metrics=metric_rel, metrics_sha256=SCORER.sha256(metric),
                                 mean_fold=checked["mean_fold"], pooled=checked["pooled"])
    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    measure_path = HERE / "outputs/m6anet_v1/measurements/full_run/measurement.json"
    measurement = json.loads(measure_path.read_text())
    if measurement["status"] != "complete" or measurement["exit_code"] != 0:
        raise ValueError("Full reference process did not complete")
    # Only compact, public-safe facts; no local command paths or site-level rows.
    resources = {
        "baseline_invocation": baseline["invocation_resources"],
        "baseline_feature_cache_reused": baseline["feature_cache_reused"],
        "baseline_fresh_fits_in_invocation": sum(not fold["reused"] for fold in baseline["folds"]),
        "m6anet_command": {k: measurement[k] for k in (
            "wall_seconds", "sampled_process_tree_cpu_seconds_lower_bound",
            "sampled_peak_tree_rss_mib", "sampling_interval_seconds", "sampling_errors")},
        "m6anet_official_inference": reference["official_inference_resources"],
    }
    summary = dict(status="prepared_pending_figures_and_readme", population=dict(sites=len(keys), positives=int(y.sum()),
                    genes=len(set(value[0] for value in folds.values()))),
                   primary="unweighted mean of five fold (ROC AUC + trapezoidal PR AUC)/2",
                   candidates=provenance, resources=resources,
                   m6anet_parameters=reference["parameters"], vendor_files=reference["vendor_files"],
                   benchmark_source_sha256=SCORER.sha256(__file__), scorer_sha256=SCORER.sha256(HERE / "evaluate.py"),
                   labels_sha256=SCORER.sha256(labels_path), folds_sha256=SCORER.sha256(folds_path),
                   limits=[reference["pretraining_provenance_limit"],
                           "Repeated development folds and historical data exposure do not establish blind-test performance.",
                           "The separate audited external neural candidate is not integrated or nominated in this comparison.",
                           "Resource scopes differ; pretrained inference time is not neural training time."])
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.environ.setdefault("MPLCONFIGDIR", str(HERE / "outputs/m6anet_v1/checks/mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve, auc

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    colors = ["#707070", "#9467bd", "#1f77b4", "#008678"]
    for (name, score), color in zip(curves, colors):
        false_positive, true_positive, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        style = "--" if name == "Published m6Anet" else "-"
        axes[0].plot(false_positive, true_positive, color=color, ls=style, lw=1.7,
                     label="{} ({:.3f})".format(name, auc(false_positive, true_positive)))
        axes[1].plot(recall, precision, color=color, ls=style, lw=1.7,
                     label="{} ({:.3f})".format(name, auc(recall, precision)))
    axes[0].plot([0, 1], [0, 1], color="#aaaaaa", lw=.8, ls=":")
    axes[1].axhline(float(y.mean()), color="#aaaaaa", lw=.8, ls=":")
    for axis in axes:
        axis.set(xlim=(0, 1), ylim=(0, 1))
        axis.grid(alpha=.15); axis.legend(fontsize=7.5, loc="best", frameon=False)
    axes[0].set(xlabel="False-positive rate", ylabel="True-positive rate", title="Pooled site ROC (AUC in legend)")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Pooled site PR (trapezoidal AUC)")
    fig.suptitle("data0: 121,838 sites; published m6Anet may overlap in pretraining", fontsize=10)
    fig.savefig(output / "reference_curves.png", dpi=220)
    fig.savefig(output / "reference_curves.svg")
    plt.close(fig)
    table = "\n".join("| {model} | {roc_auc:.6f} | {pr_auc_trapezoid:.6f} | {selection_score:.6f} |".format(**row) for row in rows)
    text = """# Completed required references — 22 October 2026

Actual data0 predictions were checked against the unchanged shared evaluator.
All methods cover 121,838 sites, 5,475 positives and 3,852 genes. Primary values below
are the **unweighted mean of five fold metrics**, not pooled curve areas.

| Pipeline | Mean ROC AUC | Mean trapezoidal PR AUC | Mean S |
|---|---:|---:|---:|
""" + table + """

**The published m6Anet row is a pretrained reference, not gene-held-out
refitting.** Its HCT116 model used SG-NEx HCT116 replicate 2/run 1; exact overlap with
course data0 remains unresolved. Our fold IDs only stratify its scores.
Consequently, this table cannot establish independent superiority over that
published model. The Elgin row is the existing cap128 control; a separate
audited external candidate has not yet been integrated or nominated here.

The simple baseline was fitted afresh on four gene groups per round using
18 raw float64 read means/population SDs, training-only scaling and fixed
balanced-C1 L2 logistic regression. Its historical recipe selection remains
disclosed; no new search was conducted. Models, coefficients/scalers, exact
split audits, OOF scores, logs and resumable completed folds remain local.

Published m6Anet 2.1.0 uses its unmodified HCT116_RNA002 weights and normalization,
CPU/four Torch threads, seed 2026, 1,000 sampling iterations, batch 2048 and one
spawned worker. Module-level seeding makes each pool restart deterministic.
The original nine signals are unchanged; the tenth column is a local row
ordinal used only for output bookkeeping. A fixed large save_per_batch
avoids the vendor's missing-final-batch bug. Both final two-batch pilots had
identical official CSV hashes. No labels were used in preparation/inference.

![Pooled ROC and PR curves](reference_curves.png)

The figure pools site scores; its legend AUCs therefore need not equal the
mean-fold table. Dashed teal is the pretrained reference with possible overlap.
The PR chance line equals the 4.494% positive prevalence. Do not read a site
probability as a measured modified-molecule fraction or a different RNA mark.

## Measured computation

"""
    b = resources["baseline_invocation"]; m = resources["m6anet_command"]
    text += "- Logistic replay invocation: {:.3f}s wall, {:.3f}s process CPU, {:.2f}MiB sampled process RSS; {}fresh fits; feature cache reused={}. Includes applicable preparation, verification and scoring.\n".format(b["wall_seconds"], b["process_cpu_seconds"], b["sampled_peak_process_rss_mib"], resources["baseline_fresh_fits_in_invocation"], resources["baseline_feature_cache_reused"])
    text += "- Published reference command: {:.3f}s wall, {:.3f}s sampled process-tree CPU lower bound, {:.2f}MiB sampled simultaneous tree RSS; includes preflight, inference and output audit, excludes earlier format preparation and later scoring.\n".format(m["wall_seconds"], m["sampled_process_tree_cpu_seconds_lower_bound"], m["sampled_peak_tree_rss_mib"])
    text += """
These scopes differ; they are not a matched training-speed comparison. CPU
sampling can miss work after the last observation of short-lived workers.
Do not add overlapping parent and process-tree timers. Interrupted preparation
and pilot/setup costs are retained separately and are not included in these
two command totals. Detailed fingerprints/counts are in `summary.json`.

## Reproduce

From the repository root, first obtain the pinned local data0 inputs. Follow
[the baseline commands](../simple_baseline/README.md) and
[the m6Anet setup/preparation/inference/scoring commands](../m6anet_reference/README.md).
Large inputs, environments, weights, checkpoints and site predictions are ignored.
Then, from the main comparison environment:

```text
python -B model_evaluation/report_benchmarks.py
```

Windows execution is checked; clean Ubuntu reproduction remains pending.
This finishes the two required reference comparisons, not the final saved
submission model, data1 diagnostic, new-test predictions or SG-NEx analysis.
Repeated development and possible pretraining overlap limit generalisation
claims. No final threshold or probability calibrator was fitted here.
"""
    (output / "README.md").write_text(text, encoding="utf-8")
    summary["status"] = "complete"
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "benchmark_results_2026_10_22")
    args = parser.parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Preserve earlier report runs; use a fresh output directory")

    def status(value):
        temporary = output / "status.tmp"
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.replace(str(temporary), str(output / "status.json"))

    status({"status": "running"})
    try:
        rows = build_report(output)
        receipt = {"status": "complete", "files": {
            name: SCORER.sha256(output / name) for name in (
                "README.md", "comparison.csv", "summary.json", "reference_curves.png", "reference_curves.svg")}}
        status(receipt)
        temporary = output / "complete.tmp"
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        os.replace(str(temporary), str(output / "complete.json"))
    except BaseException as error:
        status({"status": "failed_partial_outputs_preserved", "error": type(error).__name__ + ": " + str(error)})
        raise
    print(json.dumps({"status": "complete", "comparison": rows}, indent=2), flush=True)


if __name__ == "__main__":
    main()
