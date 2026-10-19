"""Summarise completed saved data0 CV; never load labels, fit or run inference.

Uses only saved metrics/recipes/fold audits/completion and resource records,
plus byte fingerprints of OOF predictions and retained best artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np


REPO = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = REPO / "model_elgin/outputs/context_reference_v1"
MODES = ("none", "relative")
RANKING = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")
DECISIONS = ("precision", "recall", "f1", "specificity", "accuracy")
COUNTS = ("tn", "fp", "fn", "tp")
FOLD_SHA = "986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0"
DATA0_SHA = "622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e"
LABELS_CANONICAL_SHA = "153f4658b82e4f6d95c449723d238b63153cd0102c826a3c61e3a652749b1a87"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_tree(value):
    if isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)
    elif isinstance(value, float):
        require(math.isfinite(value), "Non-finite numeric value in saved evidence")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path, evidence, cv_root):
    path = Path(path)
    require(path.is_file(), f"Incomplete evidence: missing {path.name}")
    payload = path.read_bytes()
    result = json.loads(payload, object_pairs_hook=unique_object)
    finite_tree(result)
    require(isinstance(result, dict), f"Expected JSON object: {path.name}")
    evidence[path.relative_to(cv_root).as_posix()] = hashlib.sha256(payload).hexdigest()
    return result


def number(value, name, minimum=0.0, maximum=None):
    require(type(value) in (int, float) and math.isfinite(value), f"Invalid finite number: {name}")
    require(value >= minimum and (maximum is None or value <= maximum), f"Out-of-range number: {name}")
    return float(value)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"Invalid integer: {name}")
    return value


def close(actual, expected, name):
    require(abs(float(actual) - float(expected)) <= 1e-12, f"Inconsistent saved value: {name}")


def check_metrics(row):
    n = integer(row["n_sites"], "n_sites", 1)
    positive = integer(row["n_positives"], "n_positives", 1)
    require(positive < n, "Both binary classes are required")
    for key in (*RANKING, *DECISIONS, "positive_fraction"):
        number(row[key], key, maximum=1.0)
    close(row["selection_score"], (row["roc_auc"] + row["pr_auc_trapezoid"])/2, "selection_score")
    close(row["positive_fraction"], positive/n, "positive_fraction")
    close(row["threshold"], .5, "threshold")
    tn, fp, fn, tp = [integer(row[key], key) for key in COUNTS]
    require(tn+fp+fn+tp == n and fn+tp == positive, "Confusion counts disagree with population")
    expected = dict(precision=tp/(tp+fp) if tp+fp else 0., recall=tp/(tp+fn),
                    f1=2*tp/(2*tp+fp+fn), specificity=tn/(tn+fp), accuracy=(tp+tn)/n)
    for key, value in expected.items():
        close(row[key], value, key)


def resource_record(record):
    return dict(wall_seconds=number(record["wall_seconds"], "wall_seconds"),
                cpu_seconds=number(record["cpu_seconds"], "cpu_seconds"),
                sampled_peak_process_tree_rss_mib=number(record["sampled_peak_process_tree_rss_mib"], "sampled RSS"),
                sampling_errors=integer(record["sampling_errors"], "sampling_errors"),
                sampling_interval_seconds=number(record["sampling_interval_seconds"], "sampling interval", minimum=1e-12))


def load_mode(cv_root, mode, evidence):
    directory = cv_root/mode
    recipe = read_json(directory/"recipe.json", evidence, cv_root)
    progress = read_json(directory/"progress.json", evidence, cv_root)
    require(recipe["smoke"] is False and progress["smoke"] is False, "Smoke output is not full CV")
    require(progress["full_five_folds"] is True and progress["full_data0_population"] is True,
            "Refusing report: full-population five-fold CV is not complete")
    require(sorted(progress["completed_folds"]) == list(range(5)), "Missing/duplicated completed folds")
    require(recipe["config"]["context_mode"] == mode, "Mode/config mismatch")
    identity = recipe["identity"]
    require(identity["folds_sha256"] == FOLD_SHA and identity["data0_input_sha256"] == DATA0_SHA,
            "Different data0 input or immutable shared fold file")
    metric_path, oof_path = directory/"data0_cv_metrics.json", directory/"data0_oof.csv"
    metrics = read_json(metric_path, evidence, cv_root)
    oof_hash = sha256(oof_path)
    evidence[oof_path.relative_to(cv_root).as_posix()] = oof_hash
    require(progress["oof_sha256"] == oof_hash and progress["cv_metrics_sha256"] == sha256(metric_path),
            "Changed OOF/metrics fingerprints")
    require(metrics["dataset"] == "data0" and metrics["evaluation_kind"] == "data0_gene_grouped_oof_development",
            "Expected data0 gene-fold development metrics")
    require(metrics["data0_labels_canonical_sha256"] == LABELS_CANONICAL_SHA, "Wrong canonical data0 labels")
    require(metrics["inputs"]["predictions"]["sha256"] == oof_hash
            and metrics["inputs"]["labels"]["sha256"] == identity["labels_sha256"]
            and metrics["inputs"]["folds"]["sha256"] == FOLD_SHA
            and metrics["scorer_sha256"] == identity["source_sha256"]["model_evaluation/evaluate.py"],
            "Saved scorer/input provenance differs from recipe")
    rows = metrics["per_fold"]
    require(len(rows) == 5 and {row["fold_id"] for row in rows} == set(range(5)), "Need five distinct fold metrics")
    rows = sorted(rows, key=lambda row: row["fold_id"])
    for row in [*rows, metrics["pooled"]]:
        check_metrics(row)
    require(metrics["pooled"]["n_sites"] == 121838 and metrics["pooled"]["n_positives"] == 5475,
            "Not the complete agreed data0 population")
    for key in ("n_sites", "n_positives", *COUNTS):
        require(sum(row[key] for row in rows) == metrics["pooled"][key], "Pooled counts disagree with fold counts")
    for key in RANKING:
        values = np.asarray([row[key] for row in rows])
        close(metrics["mean_fold"][key], values.mean(), "mean "+key)
        close(metrics["sample_sd_fold_ddof1"][key], values.std(ddof=1), "sample SD "+key)
    close(metrics["primary_score"], metrics["mean_fold"]["selection_score"], "primary score")
    epochs, resources = [], []
    for fold, row in enumerate(rows):
        fold_dir = directory/f"fold{fold}"
        result = read_json(fold_dir/"fold_result.json", evidence, cv_root)
        audit = read_json(fold_dir/"split_audit.json", evidence, cv_root)
        require(result["fold_id"] == fold and audit["assessment_fold"] == fold
                and audit["inner_validation_fold"] == (fold+1)%5 and audit["zero_gene_overlap"] is True,
                "Saved split/round audit differs")
        held = audit["populations"]["assessment"]
        require(held["sites"] == row["n_sites"] and held["positives"] == row["n_positives"], "Assessment counts differ")
        for key, value in result["metrics"].items():
            close(row[key], value, f"fold{fold} "+key)
        prediction = fold_dir/"predictions.csv"
        require(sha256(prediction) == result["predictions_sha256"], "Changed saved fold predictions")
        evidence[prediction.relative_to(cv_root).as_posix()] = result["predictions_sha256"]
        selected = integer(result["selected_epochs"], "selected_epochs", 1)
        require(selected <= recipe["max_epochs"], "Selected epochs exceed declared maximum")
        epochs.append(selected)
        completed_fits = {}
        for stage, population in (("inner", "initial_fit"), ("refit", "refit")):
            fit_dir = fold_dir/stage
            completed = read_json(fit_dir/"complete.json", evidence, cv_root)
            completed_fits[stage] = completed
            require(completed["config"] == recipe["config"], "Fit config differs from recipe")
            require(completed["seed"] == recipe["seed"] + fold + (100 if stage == "refit" else 0), "Fit seed differs")
            require(completed["train_sites"] == audit["populations"][population]["sites"]
                    and completed["fit_indices_sha256"] == audit["populations"][population]["indices_sha256"],
                    "Fit training partition differs from split audit")
            require(completed["validation_sites"] == (0 if stage == "refit" else audit["populations"]["inner_validation"]["sites"]),
                    "Fit validation count differs")
            require(completed["best_epoch"] == selected, "Selected/best epoch counts differ")
            require(1 <= completed["epochs_completed"] <= (selected if stage == "refit" else recipe["max_epochs"]),
                    "Invalid completed epoch count")
            if stage == "refit":
                require(completed["epochs_completed"] == selected, "Refit stopped before selected duration")
            best = fit_dir/"best.pt"
            require(sha256(best) == completed["best_sha256"], "Changed completed best artifact")
            evidence[best.relative_to(cv_root).as_posix()] = completed["best_sha256"]
            invocations = sorted(fit_dir.glob("invocation_*.json"))
            require(bool(invocations), "Missing per-fit invocation measurements")
            for invocation in invocations:
                record = read_json(invocation, evidence, cv_root)
                require(record["status"] in ("complete", "interrupted_or_failed"), "Unknown resource invocation status")
                resources.append(dict(mode=mode, fold_id=fold, fit_stage=stage,
                    invocation=invocation.relative_to(cv_root).as_posix(), status=record["status"],
                    **resource_record(record["resources"])))
        require(result["refit_signature"] == completed_fits["refit"]["signature"], "Refit signature differs")
    return dict(recipe=recipe, metrics=metrics, rows=rows, selected_epochs=epochs, resources=resources)


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix="."+path.name+".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def csv_text(rows, fields):
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return handle.getvalue()


def plots(data, output):
    os.environ.setdefault("MPLCONFIGDIR", str(output/".matplotlib_cache"))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return [], "Matplotlib unavailable; optional plots were not generated."
    files = []
    positions = np.arange(5)
    for name, keys, labels in (("paired_fold_scores.png", None, [str(i) for i in range(5)]),
                              ("mean_roc_pr.png", ("roc_auc", "pr_auc_trapezoid"), ["ROC AUC", "Trapezoidal PR AUC"])):
        x = positions if keys is None else np.arange(len(keys))
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for offset, mode in ((-.18, "none"), (.18, "relative")):
            values = ([row["selection_score"] for row in data[mode]["rows"]] if keys is None else
                      [data[mode]["metrics"]["mean_fold"][key] for key in keys])
            ax.bar(x+offset, values, width=.36, label=mode)
        ax.set(xticks=x, xticklabels=labels, ylim=(0, 1), ylabel="Score",
               xlabel="Outer gene fold" if keys is None else "Unweighted mean over five folds",
               title="Paired outer-fold development scores" if keys is None else "Matched data0 development comparison")
        ax.legend(); fig.tight_layout()
        target = output/name
        temporary = output/("."+name+".tmp")
        try:
            fig.savefig(temporary, format="png", dpi=150)
            os.replace(temporary, target)
        finally:
            plt.close(fig)
            if temporary.exists(): temporary.unlink()
        files.append(target)
    return files, "Optional plots show descriptive point estimates; no significance/CI claim."


def report(data, difference):
    recipe = data["none"]["recipe"]
    if abs(difference) <= 1e-12:
        verdict = "The two modes have the same mean score within the report's numeric comparison tolerance."
    else:
        winner = "relative" if difference > 0 else "none"
        verdict = f"**{winner} has the higher measured mean score in this controlled experiment.**"
    lines = ["# Context-reference data0 comparison", "", verdict,
        f"Relative minus matched none control: **{difference:+.10f}** mean selection score. This describes these saved runs only; it is not statistical significance or a global best-model claim.", "",
        "Both full-population five-fold data0 evaluations passed saved-evidence checks. No labels or data1 inputs were read, no metrics were re-scored from labels, and no fitting or inference was performed by this tool.", "",
        "## Actual ranking metrics", "", "| Mode | Evidence | ROC AUC | PR AUC trapezoidal | AP | S |",
        "|---|---|---:|---:|---:|---:|"]
    for mode in MODES:
        for label, key in (("Mean fold", "mean_fold"), ("Sample SD ddof=1", "sample_sd_fold_ddof1"), ("Pooled OOF", "pooled")):
            lines.append(f"| {mode} | {label} | "+" | ".join(f"{data[mode]['metrics'][key][metric]:.10f}" for metric in RANKING)+" |")
    lines += ["", "## Paired fold evidence", "", "| Fold | None ROC / PR / AP / S | Relative ROC / PR / AP / S | Relative − none S | Epochs none / relative |",
              "|---|---|---|---:|---|"]
    for fold in range(5):
        a, b = data["none"]["rows"][fold], data["relative"]["rows"][fold]
        lines.append(f"| {fold} | "+" / ".join(f"{a[k]:.8f}" for k in RANKING)+" | "+
                     " / ".join(f"{b[k]:.8f}" for k in RANKING)+
                     f" | {b['selection_score']-a['selection_score']:+.10f} | {data['none']['selected_epochs'][fold]} / {data['relative']['selected_epochs'][fold]} |")
    lines += ["", "## Stored decisions at 0.5", "",
              "Counts below are the **pooled OOF counts stored by the shared scorer**, checked against the sum of fold counts. They are not averages of confusion counts. Full per-fold decision statistics are retained in metrics.csv when requested.", "",
              "| Mode | TN | FP | FN | TP | Precision | Recall | F1 | Specificity | Accuracy |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for mode in MODES:
        pooled = data[mode]["metrics"]["pooled"]
        lines.append(f"| {mode} | "+" | ".join(str(pooled[k]) for k in COUNTS)+" | "+
                     " | ".join(f"{pooled[k]:.8f}" for k in DECISIONS)+" |")
    lines += ["", "## Matched recipe and feature definition", "",
        f"Both modes use the same immutable five gene groups, seed **{recipe['seed']}**, maximum **{recipe['max_epochs']}** inner epochs, patience **{recipe['patience']}**, batch size **{recipe['batch_size']}** and **{recipe['threads']}** CPU threads. For assessment fold f, the inner validator is (f+1)%5: initially fit three groups, select duration on the separate inner group, then freshly refit all four non-assessment groups before scoring f. Fold-specific epochs are listed above.", "",
        "`none` retains the original context-aware network and 63 all-read summaries. `relative` appends nine derived site features, so the head has nine extra inputs. It subtracts training-only per-feature medians of raw **site medians**, preferring exact 7-mer support >= min_sites, then central 5-mer support >= min_sites, then global training-site median. Sites have equal reference weight. Dwell residuals use signed log1p(abs(x)*1000), signal-SD residuals signed log1p(abs(x)), and mean-current residuals remain linear; residual centre/population SD use only fitting sites, with SD<1e-8 replaced by1.0. This is an engineering representation, not unmodified biological ground truth.", "",
        f"Configuration apart from context_mode: `{json.dumps({k:v for k,v in recipe['config'].items() if k != 'context_mode'}, sort_keys=True)}`. No data1-derived selection, calibration or threshold is performed by this summariser.", "",
        "## Measured fitting work", "", "| Mode | Completed fits | Invocation records | Failed/interrupted invocations | Wall seconds | CPU seconds | Largest sampled tree RSS MiB |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for mode in MODES:
        records = data[mode]["resources"]
        lines.append(f"| {mode} | 10 | {len(records)} | {sum(r['status'] != 'complete' for r in records)} | "+
                     f"{sum(r['wall_seconds'] for r in records):.3f} | {sum(r['cpu_seconds'] for r in records):.3f} | "+
                     f"{max(r['sampled_peak_process_tree_rss_mib'] for r in records):.3f} |")
    records = [row for mode in MODES for row in data[mode]["resources"]]
    lines.append(f"| Both (distinct work) | 20 | {len(records)} | {sum(r['status'] != 'complete' for r in records)} | "+
                 f"{sum(r['wall_seconds'] for r in records):.3f} | {sum(r['cpu_seconds'] for r in records):.3f} | "+
                 f"{max(r['sampled_peak_process_tree_rss_mib'] for r in records):.3f} |")
    lines += ["", "Resource sums include each saved per-fit invocation exactly once, including recorded interrupted attempts. They do **not** add complete.json's cumulative checkpoint resource snapshots again. Wall totals are cumulative fitting work, not end-to-end elapsed time or a cloud bill. CPU is process CPU time; memory is the maximum of recorded sampled process-tree RSS peaks, not additive RAM or an exact OS peak. Imports, startup/cache hashing, metadata joins, orchestration and outer prediction/OOF aggregation outside fit timers are excluded. Unrecorded failures cannot be reconstructed. Sampling errors and intervals are retained in resources.csv.", "",
        "## Limits and provenance", "",
        "- Five assessment groups have overlapping training data; their paired differences and sample SDs are descriptive, not five independent experiments or confidence intervals. One seed and a previously selected architecture limit attribution/generalisation.",
        "- Adding nine inputs changes parameter count. Context/coverage robustness and biological interpretation need separate evidence; no automatic removal or relabelling of valid unusual sites is justified.",
        "- The historical October7 score 0.7184458125 is background, **not this experiment's matched control**. Differences against it cannot isolate the added feature effect under a different trainer/stopping setup.",
        "- No new Samuel result is available to this report. No cross-owner winner, blind-test success, data1 transfer gain, SG-NEx cell-line effect or chemical stoichiometry is established here. Data1 was already exposed previously and remains outside tuning.",
        "- Hashes, counts and saved split audits corroborate the evidence, but this is not an independent replay of training or label-based re-evaluation. Keep executed code, logs and checkpoints.", "",
        "See comparison_manifest.json for exact input/output fingerprints; metrics.csv/resources.csv are optional machine-readable companions."]
    return "\n".join(lines)+"\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS, help="Root containing cv/none and cv/relative")
    parser.add_argument("--output-dir", type=Path, help="Default: RUNS/comparison")
    parser.add_argument("--plots", action="store_true", help="Optional matplotlib Agg paired-fold and mean ROC/PR PNGs")
    parser.add_argument("--no-csv", action="store_true", help="Skip optional metrics/resource CSVs")
    args = parser.parse_args(argv)
    runs = args.runs.resolve(); cv_root = runs/"cv"
    output = (args.output_dir or runs/"comparison").resolve()
    require(not output.is_relative_to(cv_root), "Output must not overwrite CV evidence")
    evidence = {}
    try:
        data = {mode: load_mode(cv_root, mode, evidence) for mode in MODES}
        a, b = data["none"]["recipe"], data["relative"]["recipe"]
        require({k:v for k,v in a.items() if k != "config"} == {k:v for k,v in b.items() if k != "config"},
                "Non-feature recipe/identity settings differ")
        require({k:v for k,v in a["config"].items() if k != "context_mode"} ==
                {k:v for k,v in b["config"].items() if k != "context_mode"}, "Non-feature model settings differ")
        require(data["none"]["metrics"]["versions"] == data["relative"]["metrics"]["versions"], "Scorer versions differ")
        for fold in range(5):
            for key in ("n_sites", "n_positives"):
                require(data["none"]["rows"][fold][key] == data["relative"]["rows"][fold][key], "Different assessment populations")
        difference = data["relative"]["metrics"]["primary_score"] - data["none"]["metrics"]["primary_score"]
        # Recheck every source fingerprint after collecting all evidence.
        require(all(sha256(cv_root/name) == expected for name, expected in evidence.items()), "Evidence changed during summary")
    except (KeyError, OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Comparison refused; no report written: {error}\n")
    output.mkdir(parents=True, exist_ok=True)
    written = []
    if not args.no_csv:
        rows = []
        for mode in MODES:
            for row in data[mode]["rows"]:
                rows.append(dict(mode=mode, evidence="fold", selected_epochs=data[mode]["selected_epochs"][row["fold_id"]], **row))
            for label, key in (("pooled_oof", "pooled"), ("mean_fold", "mean_fold"), ("sample_sd", "sample_sd_fold_ddof1")):
                rows.append(dict(mode=mode, evidence=label, **data[mode]["metrics"][key]))
        fields = ["mode", "evidence", "fold_id", "selected_epochs", "n_sites", "n_positives", *RANKING, "threshold", *COUNTS, *DECISIONS]
        atomic_text(output/"metrics.csv", csv_text(rows, fields)); written.append(output/"metrics.csv")
        resources = [row for mode in MODES for row in data[mode]["resources"]]
        atomic_text(output/"resources.csv", csv_text(resources, list(resources[0]))); written.append(output/"resources.csv")
    plot_files, plot_note = plots(data, output) if args.plots else ([], "Optional plots not requested.")
    written += plot_files
    text = report(data, difference)+"\n"+plot_note+"\n"
    if plot_files:
        text += "\n"+"\n".join(f"![{path.stem}]({path.name})" for path in plot_files)+"\n"
    atomic_text(output/"comparison.md", text); written.append(output/"comparison.md")
    manifest = dict(status="complete", scope="saved data0 matched development comparison only",
        reads_labels=False, reads_data1=False, performs_fitting_or_inference=False,
        relative_minus_none_mean_score=difference, input_sha256=evidence,
        output_sha256={path.name:sha256(path) for path in written}, tool_sha256=sha256(__file__))
    atomic_text(output/"comparison_manifest.json", json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    print(f"Saved verified comparison: {output/'comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
