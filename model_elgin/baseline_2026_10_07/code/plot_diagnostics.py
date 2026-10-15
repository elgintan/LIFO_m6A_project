"""Post-training data0 plots and saved-model read-sampling sensitivity.

Uses completed data0 evidence only. Never fits, tunes or accesses data1/data2.
Run after training finishes so this diagnostic's CPU use does not compete with
the recorded training workload. All diagnostic probabilities are separate from
the three final-model prediction CSVs.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/".matplotlib_cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from common import Measure, metrics, save_json
from data import sha256
from train import Cache, aligned_metadata, predict_cache, restore


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_csv(path, frame):
    path = Path(path)
    temporary = path.with_name(path.name+".tmp")
    frame.to_csv(temporary, index=False, float_format="%.17g")
    os.replace(temporary, path)


def history_plots(runs, output):
    files = []
    for prefix, title in (("screen_", "Configuration screening"), ("repeat_", "Independent optimisation seed")):
        candidates = sorted(runs.glob(prefix+"*/complete.json"))
        if not candidates:
            raise ValueError(f"No completed {prefix} histories")
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
        for path in candidates:
            result = read_json(path)
            history = result["history"]
            if not history:
                raise ValueError(f"Empty completed history: {path}")
            name = result["config"]["id"]
            epochs = [r["epoch"] for r in history]
            axes[0].plot(epochs, [r["loss"] for r in history], label=name)
            axes[1].plot(epochs, [r["selection_score"] for r in history], label=name)
        axes[0].set(xlabel="Completed epoch", ylabel="Training BCE loss")
        axes[1].set(xlabel="Completed epoch", ylabel="Inner gene-holdout selection score")
        for ax in axes:
            ax.grid(alpha=.2)
            ax.legend(fontsize=7)
        fig.suptitle(title+" — data0 training-side evidence")
        fig.tight_layout()
        target = output/("screen_learning_curves.png" if prefix == "screen_" else "repeat_learning_curves.png")
        fig.savefig(target, dpi=160)
        plt.close(fig)
        files.append(target)
    return files


def fold_plot(cvs, output):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    x = np.arange(5)
    width = .8/len(cvs)
    for index, cv in enumerate(cvs):
        folds = sorted(cv["folds"], key=lambda r:r["fold_id"])
        if len(folds) != 5 or [r["fold_id"] for r in folds] != list(range(5)):
            raise ValueError("Full five-fold results required for every finalist")
        at = x-.4+width/2+index*width
        for ax, metric, title in zip(axes, ("roc_auc", "pr_auc_trapezoid", "selection_score"),
                                     ("ROC AUC", "Trapezoidal PR AUC", "Selection score")):
            ax.bar(at, [r[metric] for r in folds], width=width, label=cv["config"]["id"])
            ax.set(xticks=x, xlabel="Shared held-out gene fold", ylabel=title, ylim=(0, 1))
            ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=7)
    fig.suptitle("All finalist outer folds — data0 development validation")
    fig.tight_layout()
    target = output/"cv_fold_scores.png"
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return target


def aligned_scores(path, keys):
    key = ["transcript_id", "transcript_position"]
    frame = pd.read_csv(path, float_precision="round_trip")
    if frame.columns.tolist() != key+["score"] or frame.duplicated(key).any():
        raise ValueError(f"Invalid score CSV: {path}")
    joined = keys[key].merge(frame, how="outer", on=key, indicator=True, validate="one_to_one", sort=False)
    if not (joined["_merge"] == "both").all() or len(joined) != len(keys):
        raise ValueError("OOF keys differ from complete data0 cache")
    # Explicit identity alignment avoids relying on merge output order.
    lookup = frame.set_index(key)["score"]
    values = lookup.reindex(pd.MultiIndex.from_frame(keys[key])).to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any((values<0)|(values>1)):
        raise ValueError("Invalid aligned OOF probabilities")
    return values


def coverage_diagnostic(cache, meta, scores, output):
    n_reads = np.diff(cache.off)
    if not np.array_equal(n_reads, cache.keys["n_reads"].to_numpy()):
        raise ValueError("Cache keys/read offsets counts differ")
    # qcut keeps coverage ties together; bins can be unequal or fewer than ten.
    categories, boundaries = pd.qcut(n_reads, 10, duplicates="drop", retbins=True)
    rows = []
    y = meta["label"].to_numpy()
    for index in range(len(categories.categories)):
        at = categories.codes == index
        selected_y, selected_p = y[at], scores[at]
        row = {
            "coverage_bin": index+1, "n_sites": int(at.sum()),
            "min_reads": int(n_reads[at].min()), "max_reads": int(n_reads[at].max()),
            "mean_reads": float(n_reads[at].mean()), "n_positives": int(selected_y.sum()),
            "positive_fraction": float(selected_y.mean()),
            "mean_score": float(selected_p.mean()),
        }
        if set(np.unique(selected_y)) == {0, 1}:
            row.update({k:v for k,v in metrics(selected_y, selected_p).items()
                        if k in ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")})
        else:
            row.update(roc_auc=None, pr_auc_trapezoid=None, average_precision=None, selection_score=None)
        rows.append(row)
    csv_path = output/"oof_coverage_deciles.csv"
    atomic_csv(csv_path, pd.DataFrame(rows))
    save_json(output/"oof_coverage_deciles.json", {
        "scope": "selected data0 OOF development probabilities; descriptive coverage subgroups, no filtering/tuning",
        "quantile_boundaries": boundaries.tolist(), "bins_requested": 10,
        "bins_actual": len(rows), "ties_policy": "equal read counts kept in the same bin; duplicate boundaries dropped",
        "rows": rows, "interpretation": "ROC/PR/score differences are descriptive; prevalence and gene/context composition vary, so they do not establish coverage causality.",
    })
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    x = np.arange(1, len(rows)+1)
    axes[0].plot(x, [r["mean_score"] for r in rows], "o-", label="Mean OOF probability")
    axes[0].plot(x, [r["positive_fraction"] for r in rows], "o-", label="Labelled positive fraction")
    axes[0].set(xlabel="Read-coverage quantile bin", ylabel="Probability / fraction")
    for metric, name in (("roc_auc", "ROC AUC"), ("pr_auc_trapezoid", "Trapezoidal PR AUC")):
        axes[1].plot(x, [r[metric] if r[metric] is not None else np.nan for r in rows], "o-", label=name)
    axes[1].set(xlabel="Read-coverage quantile bin", ylabel="Ranking measure", ylim=(0, 1))
    for ax in axes:
        ax.set_xticks(x)
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle("Selected data0 OOF coverage diagnosis — no sites excluded")
    fig.tight_layout()
    target = output/"oof_coverage_deciles.png"
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return rows, [csv_path, output/"oof_coverage_deciles.json", target]


def sampling_diagnostic(model, cache, meta, indices, output, cap, repeats, batch_size):
    y = meta["label"].to_numpy()[indices]
    full = predict_cache(model, cache, indices, batch_size=batch_size)
    seeds = [915+i for i in range(repeats)]
    sampled = []
    rows = [{"inference": "all_reads", "seed": None, "cap": None, **metrics(y, full)}]
    key = cache.keys.iloc[indices][["transcript_id", "transcript_position"]].copy()
    frame = key.copy()
    frame["score"] = full
    atomic_csv(output/"fold0_all_read_diagnostic.csv", frame)
    for seed in seeds:
        p = predict_cache(model, cache, indices, batch_size=batch_size, cap=cap, seed=seed)
        sampled.append(p)
        row = {"inference": "uniform_cap_sample", "seed": seed, "cap": cap, **metrics(y, p)}
        row["mean_absolute_probability_difference_from_all_reads"] = float(np.abs(p-full).mean())
        row["max_absolute_probability_difference_from_all_reads"] = float(np.abs(p-full).max())
        row["decision_disagreements_at_0_5"] = int(((p>=.5)!=(full>=.5)).sum())
        rows.append(row)
        frame = key.copy()
        frame["score"] = p
        atomic_csv(output/f"fold0_cap{cap}_seed{seed}_diagnostic.csv", frame)
    matrix = np.stack(sampled)
    average = matrix.mean(0)
    rows.append({"inference": "mean_of_fixed_seed_samples_diagnostic_only", "seed": None,
                 "cap": cap, **metrics(y, average),
                 "mean_absolute_probability_difference_from_all_reads": float(np.abs(average-full).mean()),
                 "max_absolute_probability_difference_from_all_reads": float(np.abs(average-full).max()),
                 "decision_disagreements_at_0_5": int(((average>=.5)!=(full>=.5)).sum())})
    frame = key.copy()
    frame["score"] = average
    atomic_csv(output/"fold0_sample_average_diagnostic.csv", frame)
    probability_sd = matrix.std(axis=0, ddof=1) if repeats>1 else np.zeros(len(full))
    record = {
        "scope": "selected candidate saved outer-fold0 refit, scored only held-out data0 genes; no fitting/tuning",
        "read_branch_active": model.config["pool"] != "summary",
        "cap": cap, "seeds": seeds, "sample_policy": "uniform without replacement; all reads used for summaries in every procedure",
        "all_read_summary_branch_fixed": True,
        "rows": rows,
        "across_sample_probability_sd": {"mean": float(probability_sd.mean()), "max": float(probability_sd.max())},
        "interpretation": "Descriptive inference sensitivity, not a new selection experiment. The fixed final model/policy is unchanged. For a summary-only model sampling has no effect because its features always use the full bag.",
    }
    save_json(output/"read_sampling_robustness.json", record)
    atomic_csv(output/"read_sampling_robustness.csv", pd.DataFrame(rows))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    labels = ["All reads"]+[f"Cap {cap}\nseed {s}" for s in seeds]+["Sample\naverage"]
    x = np.arange(len(rows))
    axes[0].bar(x-.18, [r["roc_auc"] for r in rows], width=.36, label="ROC AUC")
    axes[0].bar(x+.18, [r["pr_auc_trapezoid"] for r in rows], width=.36, label="Trapezoidal PR AUC")
    axes[0].set(xticks=x, xticklabels=labels, ylabel="Ranking measure", ylim=(0, 1))
    axes[0].legend(fontsize=8)
    delta = average-full
    axes[1].hist(delta, bins=50)
    axes[1].set(xlabel="Sample-average probability minus all-read probability", ylabel="Held-out data0 sites")
    fig.suptitle("Outer-fold0 read-sampling sensitivity — frozen outer model")
    fig.tight_layout()
    target = output/"read_sampling_robustness.png"
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return record, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT/"runs")
    parser.add_argument("--cache", type=Path, default=ROOT/"cache/data0")
    parser.add_argument("--output-dir", type=Path, default=ROOT/"diagnostics")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    if min(args.threads, args.repeats, args.batch_size)<1:
        raise ValueError("Threads, repeats and batch size must be positive")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    runs, output = args.runs.resolve(), args.output_dir.resolve()
    spec = read_json(runs/"frozen_specification.json")
    cvs = read_json(runs/"cv_results.json")
    selected = next(r for r in cvs if r["config"]["id"] == spec["config"]["id"])
    if spec["cv_metrics_sha256"] != sha256(runs/spec["config"]["id"]/"cv_metrics.json"):
        raise ValueError("Frozen selected CV evidence changed")
    model_path = runs/f"{spec['config']['id']}_fold0_refit"/"best.pt"
    complete = read_json(model_path.parent/"complete.json")
    model_hash = sha256(model_path)
    if model_hash != complete["best_sha256"]:
        raise ValueError("Outer-fold0 saved model changed")
    signature = {
        "outer_fold0_model_sha256": model_hash,
        "frozen_specification_sha256": sha256(runs/"frozen_specification.json"),
        "selected_oof_sha256": sha256(runs/spec["config"]["id"]/"oof_predictions.csv"),
        "data0_labels_sha256": sha256(ROOT.parent/"data0/data.info.labelled"),
        "cache_manifest_sha256": sha256(args.cache/"manifest.json"),
        "source_sha256": {name:sha256(ROOT/name) for name in
                          ("plot_diagnostics.py", "train.py", "model.py", "data.py", "common.py")},
        "threads": args.threads, "repeats": args.repeats, "batch_size": args.batch_size,
    }
    manifest_path = output/"diagnostics_manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        if existing.get("status") == "complete" and existing.get("signature") == signature:
            for name, expected in existing["output_sha256"].items():
                if sha256(output/name) != expected:
                    raise ValueError("Diagnostic output changed: "+name)
            print("Reused completed diagnostics", output)
            return
        raise ValueError("Existing diagnostic manifest differs; preserve its evidence and use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    with Measure() as measure:
        cache = Cache(args.cache)
        meta = aligned_metadata(cache, ROOT.parent/"data0/data.info.labelled",
                                ROOT.parent/"shared_folds/data0_folds.csv")
        oof = aligned_scores(runs/spec["config"]["id"]/"oof_predictions.csv", cache.keys)
        if metrics(meta["label"].to_numpy(), oof) != selected["pooled_oof"]:
            # Float text round-trip should reproduce precisely; fail rather than
            # relabel changed predictions as the original selected evidence.
            raise ValueError("OOF probabilities do not reproduce saved pooled metrics")
        plots = history_plots(runs, output)
        plots.append(fold_plot(cvs, output))
        coverage, coverage_files = coverage_diagnostic(cache, meta, oof, output)
        model, _ = restore(model_path)
        hold = np.flatnonzero(meta["fold_id"].to_numpy() == 0)
        robustness, sampling_plot = sampling_diagnostic(model, cache, meta, hold, output,
                                                       spec["config"]["cap"], args.repeats, args.batch_size)
        # Verify the independently inferred all-read scores reproduce outer CV.
        expected = next(r for r in selected["folds"] if r["fold_id"] == 0)
        measured = robustness["rows"][0]
        for name in ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score"):
            if abs(expected[name]-measured[name])>1e-12:
                raise ValueError("Saved fold0 inference no longer reproduces its CV metric: "+name)
        if sha256(model_path) != model_hash:
            raise ValueError("Outer model changed during diagnostics")
    hashes = {path.name:sha256(path) for path in output.iterdir() if path.is_file() and path != manifest_path}
    save_json(manifest_path, {
        "status": "complete", "signature": signature, "selected_config": spec["config"]["id"],
        "data1_or_data2_accessed": False, "training_or_tuning_performed": False,
        "resources": measure.record, "output_sha256": hashes,
        "scope": "post-training data0 descriptive plots and frozen outer-fold0 inference sensitivity",
    })
    print(json.dumps({"status": "complete", "diagnostics": str(output),
                      "coverage_bins": len(coverage), "heldout_fold0_sites": len(hold),
                      "resources": measure.record}, indent=2))


if __name__ == "__main__":
    main()
