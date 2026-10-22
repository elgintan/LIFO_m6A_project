"""Verify and report the frozen cap128 release; no fitting or model inference."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("final_shared_scorer", REPO / "model_evaluation/evaluate.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)
MODEL_HASH = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
PREDICTIONS = REPO / "model_elgin/outputs/final_cap128_v1"
PACKAGE = REPO / "model_elgin/artifacts/cap128_weight3_v1"
FINAL = REPO / "model_elgin/outputs/read_cap_v1/final/none"
METRICS = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score",
           "precision", "recall", "f1", "specificity", "accuracy")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def check_receipt(folder, filename, field):
    receipt = read_json(folder / filename)
    if receipt.get("status") != "complete":
        raise ValueError("Incomplete evidence: " + str(folder.relative_to(REPO)))
    for name, expected in receipt[field].items():
        if SCORER.sha256(folder / name) != expected:
            raise ValueError("Changed evidence file: " + name)
    return receipt


def check_metrics(checked, saved, name):
    for field in ("pooled", "mean_fold"):
        if field not in checked:
            continue
        for key, value in checked[field].items():
            if abs(value - saved[field][key]) > 1e-12:
                raise ValueError("Saved metrics differ for {} / {} / {}".format(name, field, key))


def csv_table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows, columns):
    result = ["| " + " | ".join(title for _name, title in columns) + " |",
              "| " + " | ".join("---" if name == "model" else "---:" for name, _title in columns) + " |"]
    for row in rows:
        values = [row[name] if name == "model" else "{:.6f}".format(row[name]) for name, _title in columns]
        result.append("| " + " | ".join(values) + " |")
    return "\n".join(result)


def build_report(output):
    check_receipt(PACKAGE, "complete.json", "files_sha256")
    metadata = read_json(PACKAGE / "metadata.json")
    phase = read_json(REPO / "model_elgin/outputs/read_cap_v1/final_phase/status.json")
    if (metadata["model_sha256"] != MODEL_HASH or phase["model_sha256"] != MODEL_HASH
            or phase["status"] != "final_model_complete_no_predictions" or metadata["epochs"] != 18):
        raise ValueError("Final-fit nomination or completed model differs")
    for filename, expected in phase["final_files_sha256"].items():
        if SCORER.sha256(FINAL / filename) != expected:
            raise ValueError("Changed final-fit evidence: " + filename)
    folds_path = REPO / "eda/received/shared_folds/data0_folds.csv"
    folds = SCORER.read_folds(folds_path)
    labels0_path = REPO.parent / "data0/data.info.labelled"
    labels1_path = REPO.parent / "data1/data.info"
    labels0, _genes = SCORER.read_labels(labels0_path)
    labels1, _genes = SCORER.read_labels(labels1_path)
    manifests, arrays, provenance = {}, {}, {}
    for index, expected_sites in enumerate((121838, 90810, 1323)):
        dataset = "data{}".format(index)
        path = PREDICTIONS / (dataset + "_predictions.csv")
        manifest = read_json(path.with_suffix(".csv.manifest.json"))
        raw = REPO.parent / dataset / ("dataset{}.json.gz".format(index))
        if (manifest.get("status") != "complete" or manifest.get("stage") != "final_data0"
                or manifest.get("model_sha256") != MODEL_HASH or manifest.get("labels_read") is not False
                or manifest.get("exact_input_key_coverage") is not True or manifest.get("all_reads_used") is not True
                or manifest.get("n_sites") != expected_sites
                or manifest.get("output_sha256") != SCORER.sha256(path)
                or manifest.get("input_sha256") != SCORER.sha256(raw)):
            raise ValueError("Incomplete or changed final predictions: " + dataset)
        predictions, _ = SCORER.read_predictions(path, "data1")
        if len(predictions) != expected_sites:
            raise ValueError("CSV row count differs from prediction manifest")
        if index == 0:
            SCORER.same_keys(folds, predictions, "final data0 coverage")
        elif index == 1:
            SCORER.same_keys(labels1, predictions, "final data1 coverage")
            arrays["Elgin cap128"] = predictions
        manifests[dataset] = manifest
        provenance[dataset] = {"prediction": str(path.relative_to(REPO)).replace("\\", "/"),
                               "prediction_sha256": SCORER.sha256(path),
                               "manifest_sha256": SCORER.sha256(path.with_suffix(".csv.manifest.json"))}
    sources = [
        ("Elgin cap128", "data0", REPO / "model_elgin/outputs/read_cap_v1/cv/none/data0_oof.csv",
         REPO / "model_elgin/outputs/read_cap_v1/cv/none/data0_cv_metrics.json"),
        ("Samuel LightGBM", "data0", REPO / "model_samuel/outputs/data0_oof.csv",
         REPO / "model_samuel/results/data0_cv_metrics.json"),
        ("Elgin cap128", "data1", PREDICTIONS / "data1_predictions.csv", PREDICTIONS / "data1_metrics.json"),
        ("Samuel LightGBM", "data1", REPO / "model_samuel/outputs/data1_predictions.csv",
         REPO / "model_samuel/results/data1_metrics.json"),
    ]
    checked_metrics, validation_rows, diagnostic_rows = {}, [], []
    for name, dataset, prediction, metric in sources:
        checked = SCORER.evaluate_files(labels0_path if dataset == "data0" else labels1_path,
                                        prediction, dataset, folds_path=folds_path)
        check_metrics(checked, read_json(metric), name + dataset)
        identity = name + "/" + dataset
        checked_metrics[identity] = checked
        provenance[identity] = {"prediction": str(prediction.relative_to(REPO)).replace("\\", "/"),
                                "prediction_sha256": SCORER.sha256(prediction),
                                "original_metrics_sha256": SCORER.sha256(metric)}
        if dataset == "data0":
            validation_rows.append(dict(model=name, **checked["mean_fold"]))
        else:
            diagnostic_rows.append(dict(model=name, **checked["pooled"]))
            if name == "Samuel LightGBM":
                arrays[name], _ = SCORER.read_predictions(prediction, "data1")
    history = read_json(FINAL / "history.json")
    if [row["epoch"] for row in history] != list(range(1, 19)):
        raise ValueError("Final fit must contain exactly eighteen complete epochs")
    summary = {
        "status": "prepared_pending_report_and_figures", "model_sha256": MODEL_HASH,
        "model": metadata, "metrics": checked_metrics, "predictions": manifests,
        "final_fit_resources": phase["wrapper_resources"], "resource_scope": phase["resource_scope"],
        "provenance": provenance, "scorer_sha256": SCORER.sha256(REPO / "model_evaluation/evaluate.py"),
        "reporter_sha256": SCORER.sha256(__file__), "folds_sha256": SCORER.sha256(folds_path),
        "final_phase_sha256": SCORER.sha256(REPO / "model_elgin/outputs/read_cap_v1/final_phase/status.json"),
        "training_history": history,
    }
    csv_table(output / "data0_mean_fold_comparison.csv", validation_rows)
    csv_table(output / "data1_comparison.csv", diagnostic_rows)
    csv_table(output / "training_history.csv", history)
    os.environ.setdefault("MPLCONFIGDIR", str(REPO / "model_elgin/outputs/final_cap128_v1/mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve, auc

    fig, ax = plt.subplots(figsize=(6.4, 3.5), constrained_layout=True)
    ax.plot([row["epoch"] for row in history], [row["loss"] for row in history], color="#16697a", marker="o", ms=3)
    ax.set(xlabel="Epoch", ylabel="Weighted training loss", title="Fresh all-data0 final fit: 18 prescribed epochs",
           xticks=[1, 3, 6, 9, 12, 15, 18])
    ax.grid(alpha=.2)
    for extension in ("png", "svg"):
        fig.savefig(output / ("final_training_loss." + extension), dpi=220)
    plt.close(fig)
    keys = sorted(labels1)
    y = np.asarray([labels1[key] for key in keys])
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    for name, color in (("Elgin cap128", "#16697a"), ("Samuel LightGBM", "#a05b2a")):
        scores = np.asarray([arrays[name][key] for key in keys])
        fpr, tpr, _ = roc_curve(y, scores)
        precision, recall, _ = precision_recall_curve(y, scores)
        axes[0].plot(fpr, tpr, color=color, lw=1.7, label="{}: {:.4f}".format(name, auc(fpr, tpr)))
        axes[1].plot(recall, precision, color=color, lw=1.7, label="{}: {:.4f}".format(name, auc(recall, precision)))
    axes[0].plot([0, 1], [0, 1], ls=":", color="grey", lw=.8)
    axes[1].axhline(float(y.mean()), ls=":", color="grey", lw=.8)
    for ax in axes:
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.grid(alpha=.15)
        ax.legend(frameon=False, fontsize=8)
    axes[0].set(xlabel="False-positive rate", ylabel="True-positive rate", title="data1 ROC (AUC in legend)")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="data1 PR (trapezoidal AUC)")
    fig.suptitle("Frozen models: 90,810 sites; data1 is previously exposed", fontsize=10)
    for extension in ("png", "svg"):
        fig.savefig(output / ("data1_curves." + extension), dpi=220)
    plt.close(fig)
    elgin, samuel = [checked_metrics[name + "/data1"]["pooled"] for name in ("Elgin cap128", "Samuel LightGBM")]
    better = "Elgin cap128" if elgin["selection_score"] > samuel["selection_score"] else "Samuel LightGBM"
    higher_elgin = [key for key in METRICS if elgin[key] > samuel[key]]
    higher_samuel = [key for key in METRICS if samuel[key] > elgin[key]]
    contents = """# Final cap128 model: actual training, predictions and evaluation

**Task 1: final fitting, three supplied-dataset predictions and frozen data1
evaluation are complete.** {better} has the higher data1 combined score in
this measured comparison. This does not establish universal superiority or
performance on the new unlabelled test set.

The final artifact is [the saved model](../artifacts/cap128_weight3_v1/model.pt),
SHA256 `{model_hash}`. It was fitted afresh on **121,838 data0 sites,
5,475 positives and 3,852 genes** for the prescribed 18 epochs. It uses
normalisers learned on data0 and no data1, data2 or SG-NEx fitting. The same
unchanged artifact generated all three application files.

## Actual comparison with Samuel's LightGBM

Data0 validation uses the exact shared five gene folds: a gene is held out
with all its sites, including sites from different transcripts of that gene.
Inner training-gene validation selected duration, followed by fresh refitting
within each outer training partition. Primary S is the unweighted mean of
five `(ROC AUC + trapezoidal PR AUC)/2` values. The final all-data0 prediction
file is **fitted-data output, not validation**.

{validation_table}

Data1 is a **previously exposed transfer diagnostic**, not a blind final test.
The final model and its 18-epoch duration were fixed before these predictions;
this result does not select another model, epoch or threshold. Both models
cover the same 90,810 sites, including 6,593 positives.

{data1_table}

At the shared working cutoff 0.5:

{threshold_table}

On data1, Elgin's higher metrics are {higher_elgin}. Samuel's higher metrics
are {higher_samuel}. These point estimates use the same rows and scoring
implementation; no significance or repeat-seed guarantee is claimed. Accuracy
alone can hide missed positives because only 7.260% of data1 sites are positive.
Average precision (AP) is retained separately in the CSV/JSON; it is not the
trapezoidal PR AUC used in S.

![Actual data1 ROC and PR curves](data1_curves.png)

## What this model learns

This is a **sequence-aware attention multiple-instance neural network**.
Each candidate site is a bag of reads with one site label. Each read contains
nine measurements: dwell time, signal SD and mean signal at each of three
neighbouring events. The seven-base sequence is embedded into 28 learned
features and joined to each read's nine transformed/normalised measurements.
A two-layer width-48 encoder represents each read. Gated attention, mean and
SD of those representations are combined with the sequence and **63 all-read
distribution summaries**: nine means, nine population SDs and five quantiles
(10th, 25th, 50th, 75th and 90th percentiles) for each of nine measurements.
A 235-to-48-to-24-to-1 classifier returns a sigmoid site score.

The architecture is a project-specific MIL pipeline, not an exact reimplementation
of published m6Anet. Attention weights are not a validated per-read modification
label or a causal biological explanation. `context_mode=none` disables only
the extra proposed relative-reference branch; it does **not** remove the
seven-base sequence or the existing summaries.

Final settings: AdamW, learning rate0.001, weight decay0.0001, positive-class
loss weight3, dropout0.25, seed2026, batch256 and four CPU threads. Training
samples at most128 reads per site; **prediction uses all available reads**.
All valid sites are retained, including unusual signals and difficult
high-coverage sites. The 18-epoch prescription is the median of inner choices
9/20/19/18/17, fixed before the fresh final fit.

![Actual final training loss](final_training_loss.png)

This curve shows the completed training objective only; it contains no
validation series and does not show unseen-data improvement across epochs.
Epoch checkpoints, optimizer/RNG state, history and console logs remain in
local ignored `model_elgin/outputs/read_cap_v1/final/none/`.

## EDA, model progression and limits

Member 1's findings affected gene-separated evaluation, retaining valid
unusual sites and testing sequence context, read-depth stability and
high-coverage errors. The added relative-context branch reduced mean S to
0.708885; that negative result remains documented. Increasing the read cap
32-to-128 raised mean S0.717642-to-0.718715, while fixed-cutoff metrics were
slightly worse. Removing positive loss weighting gave S0.718381 and reduced
recall/F1 at0.5; weight3 was retained. A training-side cutoff study did not
deliver a convincing F1 gain, so **0.5 remains a working reporting cutoff**,
not a fitted probability calibration or biological modification threshold.
See [the fixed nomination](../FINAL_MODEL_SELECTION.md) and the linked
diagnostic reports in [the model guide](../README.md).

The separate external experiment has higher data0 S0.726644, but was not
promoted after its recorded recall/subgroup/stability tradeoffs. Retaining
cap128 is a conservative documented choice, not proof it is globally best.
Repeated development comparisons make the data0 score optimistic as a
generalisation estimate. Grouping excludes identical genes across folds;
it does not establish homology-family or external-cell-line independence.

These are m6A candidate-site scores. They do not establish other RNA marks,
modified-molecule fractions or causal cell-line biology. Data2 has fractional
labels and is not silently converted into the same binary evaluation.
No final-model SG-NEx predictions, clean AWS Ubuntu execution, new unlabelled
test submissions or finished Task2 report/explorer are claimed here.

## Verified prediction files and measured computation

| Dataset | Sites | Reads used | Wall seconds | Process CPU seconds | Sampled peak tree RSS MiB |
|---|---:|---:|---:|---:|---:|
{resource_rows}

All CSVs contain exactly `transcript_id,transcript_position,score`, unique
input keys, finite scores in[0,1] and complete input-site coverage. Their
manifests agree on the model SHA above and record `labels_read=false`,
`all_reads_used=true` and `stage=final_data0`. Full CSVs and console logs remain
local under `model_elgin/outputs/final_cap128_v1/`; `summary.json` retains
their hashes, counts and timing evidence. Data0 scores here are training-data
predictions. Data2's1,323 rows are predictions without a binary AUC claim.

Final-fit wrapper: **{wall:.3f}s wall ({minutes:.2f}min), {cpu:.3f}s process CPU,
{rss:.2f}MiB sampled peak process-tree RSS**,0sampling errors at0.2s sampling.
This includes preflight and core delegation and overlaps core fit timers;
do not add the two. Inference timings include model/input hashing/loading,
full parsing, prediction, CSV writing and verification, excluding Python
imports. Training cache construction, historical CV/search, environment
setup, report generation and clean-host checks are outside these final-fit
and inference totals. CPU/RSS scopes differ from Samuel's received training
measurements, so these are not matched algorithm-speed comparisons.

## Exact commands

These commands run from the repository root. The actual Windows interpreter
was `../advanced_model/.venv/Scripts/python.exe`; `python` below is its portable
replacement in the pinned Python3.12 environment. Installation and public
fresh-training instructions are in [FINAL_MODEL_USAGE.md](../FINAL_MODEL_USAGE.md).

```text
python -B model_elgin/tools/final_fit_cap128.py --check-only
python -B -u model_elgin/tools/final_fit_cap128.py --fit
python -B model_elgin/tools/package_final_cap128.py
python -B model_elgin/train_final.py --input ../data0/dataset0.json.gz --labels ../data0/data.info.labelled --output-dir model_elgin/outputs/public_final_check --cache ../advanced_model/cache/data0 --check-only
python -B -u model_elgin/context_reference_v1/predict.py --input ../data0/dataset0.json.gz --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output model_elgin/outputs/final_cap128_v1/data0_predictions.csv --threads 4
python -B -u model_elgin/context_reference_v1/predict.py --input ../data1/dataset1.json.gz --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output model_elgin/outputs/final_cap128_v1/data1_predictions.csv --threads 4
python -B -u model_elgin/context_reference_v1/predict.py --input ../data2/dataset2.json.gz --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output model_elgin/outputs/final_cap128_v1/data2_predictions.csv --threads 4
python -B model_evaluation/evaluate.py --dataset data1 --labels ../data1/data.info --predictions model_elgin/outputs/final_cap128_v1/data1_predictions.csv --output model_elgin/outputs/final_cap128_v1/data1_metrics.json
python -B model_elgin/tools/report_final_cap128.py
```

The report command performs independent file rescoring and receipt checks;
it never trains or predicts. It requires all source outputs to have completed
and refuses an existing nonempty report directory. Use `--output-dir` with
a fresh path to retain a later verification. Ubuntu installation and numeric
parity remain pending; actual native Windows inference and the ten-site
real software example have passed. New unlabelled-test filenames and inputs
must follow the instructions supplied with that release; these three supplied
datasets do not substitute for that submission.
""".format(
        better=better, model_hash=MODEL_HASH,
        validation_table=markdown_table(validation_rows, [("model", "Pipeline"), ("roc_auc", "Mean ROC AUC"),
            ("pr_auc_trapezoid", "Mean PR AUC"), ("selection_score", "Mean S")]),
        data1_table=markdown_table(diagnostic_rows, [("model", "Frozen pipeline"), ("roc_auc", "ROC AUC"),
            ("pr_auc_trapezoid", "PR AUC"), ("selection_score", "S")]),
        threshold_table=markdown_table(diagnostic_rows, [("model", "Pipeline"), ("precision", "Precision"),
            ("recall", "Recall"), ("f1", "F1"), ("specificity", "Specificity"), ("accuracy", "Accuracy")]),
        higher_elgin=", ".join(higher_elgin) or "none", higher_samuel=", ".join(higher_samuel) or "none",
        resource_rows="\n".join("| {} | {:,} | {:,} | {:.3f} | {:.3f} | {:.2f} |".format(
            dataset, manifest["n_sites"], manifest["n_reads"], manifest["resources"]["wall_seconds"],
            manifest["resources"]["cpu_seconds"], manifest["resources"]["sampled_peak_process_tree_rss_mib"])
            for dataset, manifest in manifests.items()),
        wall=phase["wrapper_resources"]["wall_seconds"], minutes=phase["wrapper_resources"]["wall_seconds"]/60,
        cpu=phase["wrapper_resources"]["cpu_seconds"],
        rss=phase["wrapper_resources"]["sampled_peak_process_tree_rss_mib"])
    (output / "results.md").write_text(contents, encoding="utf-8")
    summary["status"] = "complete"
    save_json(output / "summary.json", summary)
    return {"data1_higher_S": better, "data1_elgin": elgin, "data1_samuel": samuel}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "model_elgin/final_cap128_results")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Use a fresh report directory; preserve previous evidence")
    save_json(output / "status.json", {"status": "running"})
    try:
        result = build_report(output)
        receipt = {"status": "complete", "files_sha256": {
            str(path.relative_to(output)).replace("\\", "/"): SCORER.sha256(path)
            for path in sorted(output.iterdir()) if path.name != "status.json"}}
        save_json(output / "status.json", receipt)
        save_json(output / "complete.json", receipt)
    except BaseException as error:
        save_json(output / "status.json", {"status": "failed_partial_outputs_preserved",
                                          "error": type(error).__name__ + ": " + str(error)})
        raise
    print(json.dumps({"status": "complete", **result}, indent=2))


if __name__ == "__main__":
    main()
