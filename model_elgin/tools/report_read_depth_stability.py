"""Analyse completed matched-data0 read-depth scores; no fitting or inference.

Primary both arm uses all-recomputed as reference. Secondary bag-only arm uses
all-cache. Repeats quantify sampling variability, never biological replication.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time

import numpy as np
import pandas as pd
import psutil

REPO = Path(__file__).resolve().parents[2]
ALLOWED_ROOT = REPO / "model_elgin/outputs/read_depth_stability_v1"
KEY = ["transcript_id", "transcript_position"]
META = ["site_index", *KEY, "gene_id", "fold_id", "label", "coverage", "motif"]
RANKING = ["roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score"]
ARM_REFERENCE = {"both": "all-recomputed", "bag-only": "all-cache"}
SPEC = importlib.util.spec_from_file_location("shared_depth_scorer", REPO / "model_evaluation/evaluate.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Monitor:
    def __enter__(self):
        self.wall = time.perf_counter(); self.cpu = time.process_time()
        self.proc = psutil.Process(); self.peak = self.proc.memory_info().rss
        self.stop = threading.Event()
        def sample():
            while not self.stop.wait(.2):
                self.peak = max(self.peak, self.proc.memory_info().rss)
        self.thread = threading.Thread(target=sample, daemon=True); self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set(); self.thread.join()
        self.record = {"wall_seconds": time.perf_counter() - self.wall,
                       "process_cpu_seconds": time.process_time() - self.cpu,
                       "sampled_peak_process_rss_mib": max(self.peak, self.proc.memory_info().rss) / 1024**2,
                       "sampling_interval_seconds": .2,
                       "scope": "Reporter process after imports; input checks, table writes, figures and report text calculation. Final report/manifest writing excluded."}


def validate_frame(frame, cohort):
    missing = set(META + ["n_reads_used", "perturbation", "depth", "repeat_id", "repeat_seed", "score", "baseline_score"]) - set(frame)
    require(not missing, f"Missing score columns: {sorted(missing)}")
    require(not frame[META + ["n_reads_used", "perturbation", "depth", "repeat_id", "repeat_seed"]].isna().any().any(), "Missing condition metadata")
    require(set(META) <= set(cohort), "Cohort metadata columns are incomplete")
    require(len(cohort) > 0 and not cohort[META].isna().any().any(), "Empty or missing cohort metadata")
    require(not cohort.duplicated(KEY).any(), "Duplicate cohort site keys")
    require(cohort.site_index.is_unique, "Duplicate cohort site_index")
    require(cohort.groupby("gene_id").fold_id.nunique().max() == 1, "Gene crosses outer folds")
    require(set(cohort.label.unique()) <= {0, 1}, "Only original binary data0 labels are supported")
    require((cohort.coverage >= 100).all(), "Matched cohort must have original coverage >=100")
    require(np.isfinite(frame[["score", "baseline_score"]].to_numpy(float)).all(), "Non-finite score")
    require(frame[["score", "baseline_score"]].ge(0).all().all() and frame[["score", "baseline_score"]].le(1).all().all(), "Scores outside [0,1]")
    require(not frame.duplicated(KEY + ["perturbation", "depth", "repeat_id"]).any(), "Duplicate site/condition scores")
    for _, part in frame.groupby(["perturbation", "depth", "repeat_id", "fold_id"], sort=False):
        fold = int(part.fold_id.iloc[0]); expected = cohort[cohort.fold_id == fold]
        joined = expected[META].merge(part[META], on=KEY, how="outer", suffixes=("_cohort", "_score"), indicator=True, validate="one_to_one")
        require((joined._merge == "both").all() and len(joined) == len(expected), "Condition changed its fixed fold cohort")
        for name in set(META) - set(KEY):
            require(joined[f"{name}_cohort"].equals(joined[f"{name}_score"]), f"Changed condition metadata: {name}")
        depth = str(part.depth.iloc[0])
        expected_reads = part.coverage if depth == "all" else int(depth)
        require((part.n_reads_used == expected_reads).all(), "n_reads_used disagrees with depth")
    require(set(frame.perturbation.unique()) == {"both", "bag-only", "all-cache", "all-recomputed"}, "Need both arms and both all-read controls")
    require((frame.groupby(KEY).baseline_score.nunique() == 1).all(), "Saved OOF reference differs between conditions")
    for control in ARM_REFERENCE.values():
        rows = frame[frame.perturbation == control]
        require(len(rows) == len(cohort) and not rows.duplicated(KEY).any(), f"Incomplete {control} reference")
        require((rows.depth == "all").all() and (rows.repeat_id == -1).all() and (rows.repeat_seed == "all").all(), f"Invalid {control} metadata")
    actual = set(zip(frame.transcript_id, frame.transcript_position))
    require(actual == set(zip(cohort.transcript_id, cohort.transcript_position)), "Score/cohort identity mismatch")


def load_completed(run_dir, allow_trial=False):
    experiment = read_json(run_dir / "experiment.json")
    require(experiment["signature"] == fingerprint({k: v for k, v in experiment.items() if k != "signature"}), "Experiment signature differs from its immutable recipe")
    progress = read_json(run_dir / "progress.json")
    require(progress["experiment_signature"] == experiment["signature"], "Progress is from another experiment")
    progress = {**progress, "is_trial": bool(experiment["is_trial"])}
    require(progress.get("all_completed") is True, "Inference is incomplete; wait for all conditions")
    require(not progress.get("is_trial") or allow_trial, "Trial requires --allow-trial; it is not the full result")
    expected = set(experiment["expected_condition_ids"])
    require(expected == set(progress["completed_condition_ids"]), "Completed condition IDs differ from the recipe")
    cohort_path = run_dir / "cohort.csv"
    cohort = pd.read_csv(cohort_path, float_precision="round_trip")
    require(sha256(cohort_path) == experiment["cohort_sha256"], "Changed matched cohort CSV")
    require(len(cohort) == experiment["cohort_sites"] and int(cohort.label.sum()) == experiment["cohort_positives"], "Cohort counts differ from recipe")
    models = {int(model["fold_id"]): model for model in experiment["models"]}
    require(len(models) == len(experiment["models"]) and set(models) == set(range(5)), "Recipe needs five distinct saved models")
    evidence = {"experiment.json": sha256(run_dir / "experiment.json"), "progress.json": sha256(run_dir / "progress.json"), "cohort.csv": sha256(cohort_path)}
    parts, resources, observed, fold_models = [], [], set(), {}
    for marker in sorted((run_dir / "conditions").rglob("complete.json")):
        complete = read_json(marker)
        require(complete.get("status") == "complete", f"Incomplete condition: {marker.parent}")
        cid = complete.get("condition_id", marker.parent.relative_to(run_dir / "conditions").as_posix())
        require(cid in expected and cid not in observed, f"Unexpected/duplicate condition: {cid}")
        observed.add(cid)
        identity_fields = ("condition_id", "fold_id", "perturbation", "depth", "repeat_id", "repeat_seed", "experiment_signature", "cohort_sha256", "model_sha256")
        identity = {name: complete[name] for name in identity_fields}
        require(complete["signature"] == fingerprint(identity), f"Condition signature differs: {cid}")
        require(complete["experiment_signature"] == experiment["signature"], f"Condition from another experiment: {cid}")
        require(sha256(marker) == progress["complete_receipt_sha256"][cid], f"Completed receipt changed: {cid}")
        csv_path = marker.parent / "predictions.csv"
        require(sha256(csv_path) == complete["predictions_sha256"], f"Changed prediction CSV: {cid}")
        require(complete["cohort_sha256"] == experiment["cohort_sha256"], f"Condition cohort provenance differs: {cid}")
        for path in (marker, csv_path):
            evidence[path.relative_to(run_dir).as_posix()] = sha256(path)
        part = pd.read_csv(csv_path, dtype={"depth": str, "repeat_seed": str}, float_precision="round_trip")
        require(part.fold_id.nunique() == 1, f"Condition mixes held-out models: {cid}")
        fold = int(part.fold_id.iloc[0])
        require(fold == complete["fold_id"] and complete["model_sha256"] == models[fold]["model_sha256"], f"Condition saved-model provenance differs: {cid}")
        for field in ("perturbation", "depth", "repeat_id", "repeat_seed"):
            require(part[field].astype(str).eq(str(complete[field])).all(), f"Condition receipt/CSV metadata differs: {cid}/{field}")
        require(len(part) == complete["n_sites"] and int(part.label.sum()) == complete["n_positives"], f"Condition count mismatch: {cid}")
        require(fold_models.setdefault(fold, complete["model_sha256"]) == complete["model_sha256"], f"Model changed within fold {fold}")
        part["condition_id"] = cid
        parts.append(part)
        resources.append({"condition_id": cid, "resources": complete.get("resources", {})})
    require(observed == expected, "Missing completed condition files")
    frame = pd.concat(parts, ignore_index=True)
    frame["depth"] = frame.depth.astype(str)
    validate_frame(frame, cohort)
    expected_folds = set(cohort.fold_id.unique())
    expected_samples = {(arm, str(depth), repeat, str(seed), int(fold))
                        for arm in experiment["perturbations"] for depth in experiment["depths"]
                        for repeat, seed in enumerate(experiment["repeat_seeds"]) for fold in expected_folds}
    observed_samples = set(frame[frame.perturbation.isin(ARM_REFERENCE)][["perturbation", "depth", "repeat_id", "repeat_seed", "fold_id"]].itertuples(index=False, name=None))
    require(observed_samples == expected_samples, "Numeric depths, repeat seeds or fold coverage differ from the recipe")
    control = frame[frame.perturbation == "all-cache"]
    require(float(np.abs(control.score - control.baseline_score).max()) <= 1e-6, "All-cache saved-OOF numerical guard failed")
    require(set(cohort.fold_id.unique()) == set(range(5)) or allow_trial, "Full analysis needs all five saved outer-fold models")
    require(set(experiment["depths"]) == {20, 32, 50, 100} and experiment["repeat_seeds"] == [2026, 2027, 2028]
            and set(experiment["perturbations"]) == set(ARM_REFERENCE), "This report requires the full prespecified two-arm/depth/repeat design")
    for filename in ("invocation_arguments.json",):
        require((run_dir / filename).is_file(), f"Missing completed-run command evidence: {filename}")
        evidence[filename] = sha256(run_dir / filename)
    return frame, cohort, experiment, progress, evidence, resources


def scored(y, score):
    if len(y) == 0 or set(np.unique(y)) != {0, 1}:
        return {"n_sites": len(y), "n_positives": int(np.sum(y)), "metric_status": "not_applicable_single_or_empty_class", **{k: np.nan for k in RANKING}}
    return {"metric_status": "scored", **SCORER.metrics(y, score)}


def attach_reference(frame):
    references = {arm: frame[frame.perturbation == ref].set_index(KEY).score for arm, ref in ARM_REFERENCE.items()}
    parts = []
    for arm, lookup in references.items():
        rows = frame[frame.perturbation == arm].copy()
        rows["reference_score"] = lookup.reindex(pd.MultiIndex.from_frame(rows[KEY])).to_numpy(float)
        require(rows.reference_score.notna().all(), "Missing arm-correct reference")
        rows["score_delta"] = rows.score - rows.reference_score
        parts.append(rows)
    return pd.concat(parts, ignore_index=True)


def depth_sort(value):
    return 10**9 if str(value) == "all" else int(value)


def calculate_tables(frame, cohort):
    fold_rows, pooled_rows = [], []
    for population, minimum in (("matched_ge100", 100), ("high_coverage_ge200", 200)):
        subset = frame[frame.coverage >= minimum]
        for (arm, depth, repeat), part in subset.groupby(["perturbation", "depth", "repeat_id"], sort=False):
            common = {"population": population, "perturbation": arm, "depth": depth, "repeat_id": int(repeat)}
            pooled_rows.append({**common, **scored(part.label.to_numpy(), part.score.to_numpy())})
            for fold in sorted(cohort.fold_id.unique()):
                group = part[part.fold_id == fold]
                fold_rows.append({**common, "fold_id": int(fold), **scored(group.label.to_numpy(), group.score.to_numpy())})
    folds = pd.DataFrame(fold_rows)
    summaries, paired = [], []
    expected_folds = len(cohort.fold_id.unique())
    for (population, arm, depth), part in folds.groupby(["population", "perturbation", "depth"], sort=False):
        row = {"population": population, "perturbation": arm, "depth": depth,
               "n_sites": int(cohort[cohort.coverage >= (100 if population == "matched_ge100" else 200)].shape[0]),
               "n_repeats": int(part.repeat_id.nunique()), "n_folds_expected": expected_folds}
        for metric in RANKING:
            per_fold = part.groupby("fold_id")[metric].mean()
            supported = len(per_fold) == expected_folds and per_fold.notna().all() and part[metric].notna().all()
            row[f"mean_fold_{metric}"] = float(per_fold.mean()) if supported else np.nan
            row[f"sd_fold_{metric}"] = float(per_fold.std(ddof=1)) if supported and expected_folds > 1 else np.nan
            repeated = part.groupby("repeat_id")[metric].mean()
            row[f"sd_repeat_mean_{metric}"] = float(repeated.std(ddof=1)) if supported and len(repeated) > 1 else 0. if supported else np.nan
        summaries.append(row)
        if arm in ARM_REFERENCE:
            ref = folds[(folds.population == population) & (folds.perturbation == ARM_REFERENCE[arm])].set_index("fold_id")
            for _, item in part.iterrows():
                baseline = ref.loc[item.fold_id]
                paired.append({"population": population, "perturbation": arm, "reference": ARM_REFERENCE[arm],
                               "depth": depth, "repeat_id": int(item.repeat_id), "fold_id": int(item.fold_id),
                               **{f"delta_{m}": item[m] - baseline[m] for m in RANKING}})
    joined = attach_reference(frame)
    drift = []
    for population, minimum in (("matched_ge100", 100), ("high_coverage_ge200", 200)):
        for (arm, depth), part in joined[joined.coverage >= minimum].groupby(["perturbation", "depth"], sort=False):
            for label in ("all", 0, 1):
                group = part if label == "all" else part[part.label == label]
                if not len(group):
                    continue
                delta = group.score_delta.to_numpy(float); absolute = np.abs(delta)
                before = group.reference_score.to_numpy() >= .5; after = group.score.to_numpy() >= .5
                truth = group.label.to_numpy()
                drift.append({"population": population, "perturbation": arm, "reference": ARM_REFERENCE[arm], "depth": depth,
                              "label_stratum": str(label), "n_sites": int(group.site_index.nunique()), "n_predictions": len(group),
                              "threshold_flips": int((before != after).sum()),
                              "new_false_negatives": int(((truth == 1) & before & ~after).sum()),
                              "new_false_positives": int(((truth == 0) & ~before & after).sum()),
                              "mean_signed_delta": float(delta.mean()), "mean_absolute_delta": float(absolute.mean()),
                              "median_absolute_delta": float(np.median(absolute)), "p95_absolute_delta": float(np.quantile(absolute, .95)),
                              "max_absolute_delta": float(absolute.max()), "threshold_flip_fraction": float((before != after).mean()),
                              "negative_to_positive_fraction": float((~before & after).mean()), "positive_to_negative_fraction": float((before & ~after).mean()),
                              "new_false_negative_fraction": float(((truth == 1) & before & ~after).mean()),
                              "new_false_positive_fraction": float(((truth == 0) & ~before & after).mean())})
    variability = joined.groupby(META + ["perturbation", "depth"], dropna=False).agg(
        n_repeats=("score", "size"), mean_score=("score", "mean"), sd_score=("score", "std"),
        min_score=("score", "min"), max_score=("score", "max"), reference_score=("reference_score", "first"),
        mean_absolute_delta=("score_delta", lambda x: float(np.abs(x).mean()))).reset_index()
    variability["range_score"] = variability.max_score - variability.min_score
    motifs = []
    for arm, depth in frame[["perturbation", "depth"]].drop_duplicates().itertuples(index=False):
        part = frame[(frame.perturbation == arm) & (frame.depth == depth)]
        for motif in sorted(cohort.motif.unique()):
            sites = cohort[cohort.motif == motif]; n1 = int(sites.label.sum()); n0 = len(sites) - n1
            supported = n1 >= 20 and n0 >= 20
            repeated = []
            for _, group in part[part.motif == motif].groupby("repeat_id"):
                if supported:
                    repeated.append(scored(group.label.to_numpy(), group.score.to_numpy()))
            motifs.append({"perturbation": arm, "depth": depth, "motif": motif, "n_sites": len(sites),
                           "n_positive": n1, "n_negative": n0, "support_ge20_each_class": supported,
                           "metric_scope": "pooled_sites_within_motif_then_mean_sampling_repeat",
                           **{m: float(np.mean([r[m] for r in repeated])) if repeated else np.nan for m in RANKING}})
    controls = []
    cache = frame[frame.perturbation == "all-cache"].set_index(KEY)
    recompute = frame[frame.perturbation == "all-recomputed"].set_index(KEY).reindex(cache.index)
    for name, left, right in (("all-cache_vs_saved_oof", cache.score, cache.baseline_score),
                              ("all-recomputed_vs_all-cache", recompute.score, cache.score)):
        delta = left.to_numpy(float) - right.to_numpy(float)
        controls.append({"comparison": name, "n_sites": len(delta), "mean_absolute_delta": float(np.abs(delta).mean()),
                         "max_absolute_delta": float(np.abs(delta).max()), "threshold_flips": int(((left.to_numpy() >= .5) != (right.to_numpy() >= .5)).sum())})
    return {"fold_repeat_metrics": folds, "depth_metrics": pd.DataFrame(summaries), "pooled_metrics_supplement": pd.DataFrame(pooled_rows),
            "paired_fold_deltas": pd.DataFrame(paired), "score_drift": pd.DataFrame(drift), "site_repeat_variability": variability,
            "motif_descriptive_metrics": pd.DataFrame(motifs), "numerical_controls": pd.DataFrame(controls)}


def make_figures(tables, output):
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colors = {"both": "#197A82", "bag-only": "#B65F3F"}
    labels = {"both": "Reads and summaries reduced", "bag-only": "Read branch only reduced"}
    metric_labels = {"roc_auc": "ROC AUC", "pr_auc_trapezoid": "PR AUC (trapezoidal)",
                     "average_precision": "Average precision (AP)", "selection_score": "Combined score (S)"}
    summary = tables["depth_metrics"]
    depths = sorted(summary.loc[summary.perturbation == "both", "depth"].unique(), key=depth_sort)
    axis_labels = depths + ["all"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for metric, axis in zip(RANKING, axes.flat):
        for arm in ARM_REFERENCE:
            part = summary[(summary.population == "matched_ge100") & (summary.perturbation == arm)].set_index("depth").reindex(depths)
            ref = summary[(summary.population == "matched_ge100") & (summary.perturbation == ARM_REFERENCE[arm])].iloc[0]
            values = part[f"mean_fold_{metric}"].tolist() + [ref[f"mean_fold_{metric}"]]
            errors = part[f"sd_fold_{metric}"].tolist() + [ref[f"sd_fold_{metric}"]]
            axis.errorbar(range(len(axis_labels)), values, yerr=errors, color=colors[arm], marker="o", capsize=3, label=labels[arm])
        axis.set(xticks=range(len(axis_labels)), xticklabels=axis_labels, xlabel="Reads used (same original sites)", ylabel=metric_labels[metric])
        available = summary.loc[summary.population == "matched_ge100", f"mean_fold_{metric}"]
        if not np.isfinite(available.to_numpy(float)).any():
            axis.text(.5, .5, "Five-fold metric unavailable\n(single-class fold in this trial)",
                      transform=axis.transAxes, ha="center", va="center", fontsize=10)
        axis.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Matched data0 high-coverage cohort: mean fold metrics\nBars = fold SD after averaging three repeat metrics, not confidence intervals")
    fig.tight_layout(); fig.savefig(output / "metrics_by_depth.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    drift = tables["score_drift"]
    for arm in ARM_REFERENCE:
        for population, style in (("matched_ge100", "-"), ("high_coverage_ge200", "--")):
            part = drift[(drift.perturbation == arm) & (drift.population == population) & (drift.label_stratum == "all")].set_index("depth").reindex(depths)
            for axis, field in zip(axes, ("mean_absolute_delta", "threshold_flip_fraction")):
                population_label = "originally ≥100 reads" if population == "matched_ge100" else "originally ≥200 reads"
                axis.plot(range(len(depths)), part[field], style, color=colors[arm], marker="o", label=f"{labels[arm]}, {population_label}")
                field_label = "Mean absolute score change" if field == "mean_absolute_delta" else "Fraction crossing the 0.5 cutoff"
                axis.set(xticks=range(len(depths)), xticklabels=depths, xlabel="Reads used", ylabel=field_label)
                axis.grid(alpha=.2)
    axes[0].legend(fontsize=7)
    fig.suptitle("Paired score movement versus each arm's all-read reference\nFixed 0.5 crossings are descriptive; no cutoff was selected")
    fig.tight_layout(); fig.savefig(output / "score_movement.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    pairs = tables["paired_fold_deltas"]
    for axis, arm in zip(axes, ARM_REFERENCE):
        part = pairs[(pairs.population == "matched_ge100") & (pairs.perturbation == arm)]
        for fold, group in part.groupby("fold_id"):
            values = group.groupby("depth").delta_selection_score.mean().reindex(depths)
            axis.plot(range(len(depths)), values, marker="o", label=f"Fold {fold}")
        axis.axhline(0, color="black", lw=.8)
        axis.set(xticks=range(len(depths)), xticklabels=depths, xlabel="Reads used", title=labels[arm], ylabel="Change in mean ROC/PR score vs arm reference")
        if not np.isfinite(part.delta_selection_score.to_numpy(float)).any():
            axis.text(.5, .5, "Paired ranking metric unavailable", transform=axis.transAxes,
                      ha="center", va="center", fontsize=10)
        axis.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Paired fold comparisons on identical sites; repeat metrics averaged")
    fig.tight_layout(); fig.savefig(output / "paired_fold_score_changes.png", dpi=180); plt.close(fig)


def report_text(tables, cohort, progress, command):
    def value(x):
        return "NA" if pd.isna(x) else f"{x:.6f}"
    main = tables["depth_metrics"].query("population == 'matched_ge100'")
    lines = ["# Read-depth stability: saved data0 models", "",
             f"Scope: {'TRIAL ONLY' if progress.get('is_trial') else 'completed fixed-cohort diagnostic'}, {len(cohort):,} original sites with at least 100 reads, {int(cohort.label.sum()):,} positive labels.", "",
             "This is inference on a matched subset using saved held-out-gene models. It is not training, a new model, an independent test or the full-data0 CV result.", "",
             "## Actual ranking metrics", "", "| Arm | Reads | ROC mean | PR mean | AP mean | S mean | Fold SD of S |", "|---|---|---:|---:|---:|---:|---:|"]
    for _, row in main.sort_values(["perturbation", "depth"], key=lambda x: x.map(depth_sort) if x.name == "depth" else x).iterrows():
        lines.append("| " + " | ".join([row.perturbation, str(row.depth)] + [value(row[f"mean_fold_{m}"]) for m in RANKING] + [value(row.sd_fold_selection_score)]) + " |")
    lines += ["", "S=(ROC AUC + trapezoidal PR AUC)/2. Each numeric-depth point averages three sampling-repeat metrics within each fold, then averages the folds. Fold SD is descriptive and is not a confidence interval. AP is separate from trapezoidal PR area. Pooled metrics are supplementary only.", "",
              "## Score stability and controls", "", "Primary `both` changes the read bag and recomputes all 63 summaries, referenced to `all-recomputed`. Secondary `bag-only` keeps original summaries, referenced to `all-cache`. The numerical-control table separately compares the two full-read paths and the archived OOF scores.", "",
              "`score_drift.csv` records absolute/signed movement, label-stratified movement and fixed-0.5 crossing directions. New false-negative/false-positive fractions use the stated stratum's prediction count as denominator; counts include repeated sampling predictions. `site_repeat_variability.csv` records each site's repeat SD/range. The same >=200-read subset is reported at every depth. Motif metrics pool sites across held-out models within each repeat, then average repeat metrics; they are supplementary and are not fold-average results. Sparse motif metrics are masked unless each label has at least 20 original sites; all motif counts remain.", "",
              "## Interpretation and limitations", "", "Compare the primary arm's depth profile, paired fold deltas and site-level spread before choosing a later experiment. Stable ranking with score movement, unstable ranking, and depth-insensitive results imply different follow-ups; none is assumed in advance. The secondary arm helps distinguish read-branch sensitivity from changes in summary estimation, without proving a causal biological mechanism.", "",
              "These are controlled subsets of originally well-covered sites, not independently sequenced low-depth samples. Repeated draws reuse the original read observations and are not biological replicates. Original high coverage, sequence composition, positive-label prevalence and correlated sites within genes limit extrapolation. Coverage-only label associations were not causal evidence. No significance test, threshold optimisation, relabelling or outlier deletion occurred. Only the frozen saved models used here were investigated; a different future model can behave differently. Data1/SG-NEx were not accessed.", "",
              "## Reproduction and evidence", "", "```text", command, "```", "", "Input recipe, condition completion records, prediction hashes and saved-model provenance are retained in the parent run directory. `analysis_manifest.json` fingerprints input evidence, reporter/scorer and outputs and records this report's computation measurements. Inference costs are retained separately in the condition resource records; they are not new training cost. Numerical data and plots are actual saved-score calculations.", ""]
    return "\n".join(lines)


def observed_details(tables, cohort):
    def value(x):
        return "NA" if pd.isna(x) else f"{x:.6f}"
    summary = tables["depth_metrics"].query("population == 'matched_ge100'")
    drifts = tables["score_drift"].query("population == 'matched_ge100' and label_stratum == 'all'")
    lines = ["", "## Observed paired changes", "", "| Arm | Reads | Change in S vs arm's all-read control | Mean absolute score movement | Fixed-0.5 crossing fraction |", "|---|---|---:|---:|---:|"]
    for arm, reference in ARM_REFERENCE.items():
        ref = summary[summary.perturbation == reference].iloc[0]
        for _, row in summary[summary.perturbation == arm].sort_values("depth", key=lambda x: x.map(depth_sort)).iterrows():
            drift = drifts[(drifts.perturbation == arm) & (drifts.depth == row.depth)].iloc[0]
            delta = row.mean_fold_selection_score - ref.mean_fold_selection_score
            lines.append(f"| {arm} | {row.depth} | {value(delta)} | {value(drift.mean_absolute_delta)} | {value(drift.threshold_flip_fraction)} |")
    lines += ["", "These are paired observations on the same sites. They describe sensitivity under the specified downsampling procedure, not a general accuracy guarantee.", "", "## Numerical controls", "", "| Comparison | Mean absolute score difference | Maximum absolute difference | Fixed-0.5 crossings |", "|---|---:|---:|---:|"]
    for row in tables["numerical_controls"].itertuples(index=False):
        lines.append(f"| {row.comparison} | {value(row.mean_absolute_delta)} | {value(row.max_absolute_delta)} | {row.threshold_flips} |")
    counts = cohort.groupby("fold_id").agg(n_sites=("label", "size"), n_positive=("label", "sum")).reset_index()
    lines += ["", "## Fixed cohort and figures", "", f"Original read count: min {int(cohort.coverage.min())}, median {float(cohort.coverage.median()):.1f}, max {int(cohort.coverage.max())}. The >=200-read sensitivity subset contains {int((cohort.coverage >= 200).sum()):,} sites.", "", "| Held-out fold | Sites | Positive labels |", "|---|---:|---:|"]
    for row in counts.itertuples(index=False):
        lines.append(f"| {row.fold_id} | {row.n_sites} | {row.n_positive} |")
    lines += ["", "![Matched-cohort metrics](metrics_by_depth.png)", "", "![Paired score movement](score_movement.png)", "", "![Per-fold score changes](paired_fold_score_changes.png)", ""]
    return "\n".join(lines)


def portable_command(args):
    parts = ["python", "model_elgin/tools/report_read_depth_stability.py", "--run-dir", args.run_dir.resolve().relative_to(REPO).as_posix()]
    if args.output_dir:
        parts += ["--output-dir", args.output_dir.resolve().relative_to(REPO).as_posix()]
    if args.allow_trial:
        parts.append("--allow-trial")
    return subprocess.list2cmdline(parts)


def portable_inference_command(run_dir):
    arguments = read_json(run_dir / "invocation_arguments.json")["arguments"]
    portable = []
    for argument in arguments:
        if Path(argument).is_absolute():
            portable.append(Path(os.path.relpath(argument, REPO)).as_posix())
        else:
            portable.append(argument)
    return subprocess.list2cmdline(["python", "model_elgin/tools/read_depth_stability.py", *portable])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-trial", action="store_true")
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve(); output = (args.output_dir or run_dir / "analysis").resolve()
    require(run_dir.is_relative_to(ALLOWED_ROOT.resolve()) and run_dir.name in ("trial", "full"), "Run must be trial/full under the isolated read_depth_stability_v1 output root")
    require(output == run_dir / "analysis", "Reports must stay in this run's analysis directory")
    output.mkdir(parents=True, exist_ok=True)
    with Monitor() as monitor:
        frame, cohort, experiment, progress, evidence, inference_resources = load_completed(run_dir, args.allow_trial)
        tables = calculate_tables(frame, cohort)
        for name, table in tables.items():
            table.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        make_figures(tables, output)
        command = portable_command(args)
        report = report_text(tables, cohort, progress, command) + observed_details(tables, cohort)
    for relative, digest in evidence.items():
        require(sha256(run_dir / relative) == digest, f"Input evidence changed during reporting: {relative}")
    condition_wall = sum(item["resources"]["wall_seconds"] for item in inference_resources)
    condition_cpu = sum(item["resources"]["cpu_seconds"] for item in inference_resources)
    condition_peak = max(item["resources"]["sampled_peak_process_tree_rss_mib"] for item in inference_resources)
    costs = ["", "## Computation measurements", "", f"Reporter: {monitor.record['wall_seconds']:.3f} wall seconds; {monitor.record['process_cpu_seconds']:.3f} process CPU seconds; {monitor.record['sampled_peak_process_rss_mib']:.1f} MiB sampled peak process RSS. Imports and final report/manifest writing are outside this measurement.", "", f"Completed inference conditions: {condition_wall:.3f} summed wall seconds; {condition_cpu:.3f} summed process CPU seconds; {condition_peak:.1f} MiB maximum sampled process-tree RSS. These condition measurements include scoring/summary calculation, score writing, verification and metrics. They exclude model loading/preflight and interrupted attempts and are not the experiment's overall elapsed time.", "", "Exact inference arguments, using repository-relative paths and the configured Python environment:", "", "```text", portable_inference_command(run_dir), "```", "", "Individual condition resources, source/model hashes and command evidence are retained in `analysis_manifest.json` and its fingerprinted inputs. No training was performed by this diagnostic.", ""]
    (output / "report.md").write_text(report + "\n".join(costs), encoding="utf-8")
    artifacts = {p.name: sha256(p) for p in output.iterdir() if p.is_file() and p.name != "analysis_manifest.json"}
    write_json(output / "analysis_manifest.json", {"status": "complete", "dataset": "data0", "is_trial": progress.get("is_trial", False),
        "n_sites": len(cohort), "input_sha256": evidence, "reporter_sha256": sha256(__file__),
        "scorer_sha256": sha256(REPO / "model_evaluation/evaluate.py"), "resources": monitor.record,
        "inference_resources": inference_resources, "artifacts_sha256": artifacts,
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "limitations": ["Matched >=100-read cohort, not full CV or independently sequenced low-depth samples", "Fold SD and sampling repeats are not independent biological replication or confidence intervals", "Both and bag-only use different arm-correct full-read controls"]})
    print(f"Saved actual matched-cohort analysis: {len(cohort):,} sites; {len(frame):,} score rows; {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
