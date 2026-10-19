"""Saved-data0 subgroup/error diagnostics; no neural fitting or inference.

Unusual-signal fences are descriptive central5-conditioned 3*IQR rules,
estimated using only each outer fold's four non-assessment gene groups.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

import numpy as np
import psutil

import summarize_context_cv as saved


REPO = Path(__file__).resolve().parents[2]
ALLOWED_OUTPUT = REPO/"model_elgin/outputs/context_reference_v1/diagnostics"
FEATURES = ("minus1_dwell", "minus1_event_sd", "minus1_current",
            "centre_dwell", "centre_event_sd", "centre_current",
            "plus1_dwell", "plus1_event_sd", "plus1_current")
RANKING = saved.RANKING
DECISIONS = saved.DECISIONS
MIN_CONTEXT_SITES = 30
IQR_MULTIPLIER = 3.0
FLOAT_TOLERANCE = 1e-12
LOW_POSITIVE_SUPPORT = 20
COVERAGE = (("1–29", 1, 30), ("30–49", 30, 50), ("50–99", 50, 100),
            ("100–199", 100, 200), ("200+", 200, None))
SPEC = importlib.util.spec_from_file_location("shared_data0_diagnostic_scorer", REPO/"model_evaluation/evaluate.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def array_hash(values, dtype):
    return hashlib.sha256(np.asarray(values, dtype=dtype).tobytes()).hexdigest()


def text_hash(values):
    return hashlib.sha256(("\n".join(map(str, values))+"\n").encode()).hexdigest()


class Monitor:
    def __enter__(self):
        self.wall = time.perf_counter(); self.cpu = time.process_time()
        self.process = psutil.Process(); self.peak = self.process.memory_info().rss
        self.errors = 0; self.stop = threading.Event()
        def sample():
            while not self.stop.wait(.2):
                try: self.peak = max(self.peak, self.process.memory_info().rss)
                except psutil.Error: self.errors += 1
        self.thread = threading.Thread(target=sample, daemon=True); self.thread.start()
        return self

    def __exit__(self, *error):
        self.stop.set(); self.thread.join()
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.record = dict(wall_seconds=time.perf_counter()-self.wall,
            process_cpu_seconds=time.process_time()-self.cpu,
            sampled_peak_process_rss_mib=self.peak/1024**2,
            sampling_interval_seconds=.2, sampling_errors=self.errors,
            scope="This analysis process; parsing, saved-score checks, subgroup statistics and output generation. Imports and final manifest serialization excluded.")


def bounds(values):
    q1, q3 = np.quantile(values, [.25, .75], axis=0, method="linear")
    iqr = q3-q1
    tolerance = FLOAT_TOLERANCE*np.maximum(1., np.maximum(np.abs(q1), np.abs(q3)))
    return dict(q1=q1.tolist(), q3=q3.tolist(), iqr=iqr.tolist(),
                lower=(q1-IQR_MULTIPLIER*iqr).tolist(), upper=(q3+IQR_MULTIPLIER*iqr).tolist(),
                tolerance=tolerance.tolist())


def fit_crossfold_flags(medians, motifs, folds, genes, min_sites=MIN_CONTEXT_SITES):
    """Pure label-free cross-fit rule. Every site is assessed exactly once."""
    medians = np.asarray(medians, dtype=np.float64)
    motifs, folds, genes = np.asarray(motifs), np.asarray(folds), np.asarray(genes)
    n = len(medians)
    saved.require(medians.shape == (n, 9) and n > 0 and np.isfinite(medians).all(), "Need finite N×9 raw site medians")
    saved.require(motifs.shape == folds.shape == genes.shape == (n,) and set(folds.tolist()) == set(range(5)), "Need five aligned folds")
    saved.require(type(min_sites) is int and min_sites > 0, "min_sites must be positive integer")
    mapping = {}
    for gene, fold in zip(genes, folds):
        saved.require(gene not in mapping or mapping[gene] == int(fold), "A gene crosses outer folds")
        mapping[gene] = int(fold)
    flagged = np.zeros(n, dtype=bool); feature_counts = np.zeros(n, dtype=np.int64)
    levels = np.full(n, "", dtype="U7"); references = []
    for fold in range(5):
        fit = np.flatnonzero(folds != fold); held = np.flatnonzero(folds == fold)
        fit_genes, held_genes = set(genes[fit]), set(genes[held])
        saved.require(len(fit) and len(held) and not fit_genes & held_genes, "Empty or overlapping gene groups")
        global_bounds = bounds(medians[fit])
        counts, by_motif = {}, {}
        for motif in sorted(set(motifs[fit])):
            indices = fit[motifs[fit] == motif]
            counts[str(motif)] = len(indices)
            if len(indices) >= min_sites:
                by_motif[str(motif)] = bounds(medians[indices])
        references.append(dict(assessment_fold=fold, fit_folds=[f for f in range(5) if f != fold],
            fit_sites=len(fit), fit_genes=len(fit_genes), assessment_sites=len(held),
            assessment_genes=len(held_genes), zero_gene_overlap=True,
            fit_indices_sha256=array_hash(fit, "<i8"),
            fit_site_medians_sha256=array_hash(medians[fit], "<f8"),
            fit_motifs_sha256=text_hash(motifs[fit]), fit_genes_sha256=text_hash(sorted(fit_genes)),
            context_support_sites=counts, supported_context_bounds=by_motif, global_bounds=global_bounds))
        for motif in sorted(set(motifs[held])):
            indices = held[motifs[held] == motif]
            reference = by_motif.get(str(motif), global_bounds)
            lower, upper, tolerance = (np.asarray(reference[key]) for key in ("lower", "upper", "tolerance"))
            outside = (medians[indices] < lower-tolerance) | (medians[indices] > upper+tolerance)
            feature_counts[indices] = outside.sum(axis=1)
            flagged[indices] = outside.any(axis=1)
            levels[indices] = "motif" if str(motif) in by_motif else "global"
    saved.require(np.isin(levels, ["motif", "global"]).all(), "A site did not receive a fence reference")
    return flagged, feature_counts, levels, references


def subgroup_metrics(y, score):
    y, score = np.asarray(y, dtype=np.int64), np.asarray(score, dtype=np.float64)
    saved.require(y.shape == score.shape and np.isfinite(score).all() and np.isin(y, [0, 1]).all(), "Invalid subgroup arrays")
    saved.require(np.all((score >= 0) & (score <= 1)), "Invalid score range")
    n, positives = len(y), int(y.sum())
    if positives and positives < n:
        result = SCORER.metrics(y, score)
        result["ranking_status"] = "both_classes"
    else:
        predicted = score >= .5
        tn = int(np.sum((y == 0) & ~predicted)); fp = int(np.sum((y == 0) & predicted))
        fn = int(np.sum((y == 1) & ~predicted)); tp = int(np.sum((y == 1) & predicted))
        result = dict(n_sites=n, n_positives=positives, positive_fraction=positives/n if n else None,
            threshold=.5, tn=tn, fp=fp, fn=fn, tp=tp,
            precision=tp/(tp+fp) if tp+fp else 0., recall=tp/(tp+fn) if tp+fn else None,
            f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            specificity=tn/(tn+fp) if tn+fp else None, accuracy=(tn+tp)/n if n else None,
            ranking_status="single_class_not_scored" if n else "empty_not_scored",
            **{key: None for key in RANKING})
    result.update(n_negatives=n-positives, sparse_positive_support=positives < LOW_POSITIVE_SUPPORT)
    return result


def load_inputs(args):
    cv_root = args.runs/"cv"; cv_hashes = {}
    modes = {mode: saved.load_mode(cv_root, mode, cv_hashes) for mode in saved.MODES}
    a, b = (modes[mode]["recipe"] for mode in saved.MODES)
    saved.require({k:v for k,v in a.items() if k != "config"} == {k:v for k,v in b.items() if k != "config"}, "Non-feature recipes differ")
    saved.require({k:v for k,v in a["config"].items() if k != "context_mode"} == {k:v for k,v in b["config"].items() if k != "context_mode"}, "Non-feature configs differ")
    saved.require(saved.sha256(args.folds) == SCORER.FOLD_SHA256, "Changed immutable fold file")
    saved.require(saved.sha256(args.labels) == a["identity"]["labels_sha256"], "Changed data0 label source")
    labels, label_genes = SCORER.read_labels(args.labels)
    assignments = SCORER.read_folds(args.folds); SCORER.same_keys(labels, assignments, "Labels/folds")
    saved.require(SCORER.canonical_labels_hash(labels, assignments) == SCORER.DATA0_LABELS_CANONICAL_SHA256, "Changed canonical labels")
    saved.require(len(label_genes) == len(labels) and all(label_genes[key] == assignments[key][0] for key in labels), "Gene mappings differ")
    manifest_path = args.cache/"manifest.json"
    saved.require(saved.sha256(manifest_path) == a["identity"]["cache_manifest_sha256"], "Changed training cache manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    saved.require(manifest["status"] == "completed" and manifest["input_sha256"] == saved.DATA0_SHA, "Wrong/incomplete data0 cache")
    for name in ("keys.csv", "summary.npy", "offsets.npy"):
        saved.require(saved.sha256(args.cache/name) == manifest["cache_sha256"][name], "Changed consumed cache payload: "+name)
    cache_info = {}
    for index, row in enumerate(SCORER.csv_rows(args.cache/"keys.csv", ["transcript_id", "transcript_position", "context", "n_reads"], exact=True)):
        key = SCORER.site_key(row); context = row["context"].upper().replace("U", "T")
        saved.require(key not in cache_info and len(context) == 7 and all(c in "ACGTRYSWKMBDHVN" for c in context), "Invalid cached key/context")
        count = SCORER.integer(row["n_reads"], "coverage"); saved.require(count > 0, "Nonpositive coverage")
        cache_info[key] = (index, context[1:6], count)
    SCORER.same_keys(labels, cache_info, "Labels/cache")
    keys = sorted(labels); indices = np.asarray([cache_info[key][0] for key in keys])
    summaries = np.load(args.cache/"summary.npy", mmap_mode="r", allow_pickle=False)
    offsets = np.load(args.cache/"offsets.npy", mmap_mode="r", allow_pickle=False)
    saved.require(summaries.shape == (len(keys), 63) and offsets.shape == (len(keys)+1,), "Cache array shapes differ")
    saved.require(offsets[0] == 0 and np.array_equal(np.diff(offsets), [item[2] for item in cache_info.values()]), "Coverage/offset mismatch")
    medians = np.asarray(summaries[indices, 36:45], dtype=np.float64)
    motifs = np.asarray([cache_info[key][1] for key in keys]); coverage = np.asarray([cache_info[key][2] for key in keys])
    y = np.asarray([labels[key] for key in keys]); folds = np.asarray([assignments[key][1] for key in keys])
    genes = np.asarray([assignments[key][0] for key in keys]); scores = {}
    for mode in saved.MODES:
        predictions, prediction_folds = SCORER.read_predictions(cv_root/mode/"data0_oof.csv", "data0")
        SCORER.same_keys(labels, predictions, "Labels/OOF")
        saved.require(all(prediction_folds[key] == assignments[key][1] for key in keys), "OOF fold IDs differ")
        scores[mode] = np.asarray([predictions[key] for key in keys])
        for f in [None, *range(5)]:
            mask = np.ones(len(y), dtype=bool) if f is None else folds == f
            actual = SCORER.metrics(y[mask], scores[mode][mask])
            expected = modes[mode]["metrics"]["pooled"] if f is None else modes[mode]["rows"][f]
            for name, value in actual.items(): saved.close(value, expected[name], "Reproduced "+mode+" "+name)
    input_hashes = {"data0_labels": saved.sha256(args.labels), "shared_folds": saved.sha256(args.folds),
                    "cache_manifest": saved.sha256(manifest_path),
                    **{"cache/"+name: manifest["cache_sha256"][name] for name in ("keys.csv", "summary.npy", "offsets.npy")},
                    **{"cv/"+name: value for name, value in cv_hashes.items()}}
    return dict(keys=keys, y=y, folds=folds, genes=genes, motifs=motifs, coverage=coverage,
                medians=medians, scores=scores, modes=modes, input_hashes=input_hashes, cv_hashes=cv_hashes)


def member1_context(data):
    base = REPO/"eda/received/tables"; hashes, receipt = {}, {}
    for filename in ("motif_summary.csv", "coverage_label_counts.csv", "within_motif_effects.csv", "unusual_sites_review.csv"):
        path = base/filename; hashes["member1/"+filename] = saved.sha256(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row["dataset"] == "data0"]
        receipt[filename] = {"data0_rows_read": len(rows)}
        if filename == "motif_summary.csv":
            expected = {row["motif"]: (int(row["n_sites"]), int(row["positive_sites"])) for row in rows}
            observed = {str(m): (int(np.sum(data["motifs"] == m)), int(data["y"][data["motifs"] == m].sum())) for m in set(data["motifs"])}
            saved.require(expected == observed, "Member1 data0 motif support differs")
            receipt[filename]["counts_match_current_data0"] = True
        elif filename == "coverage_label_counts.csv":
            expected = {(int(row["label"]), row["coverage_bin"]): int(row["n_sites"]) for row in rows}
            for name, lo, hi in (("20–49", 20, 50), ("50–99", 50, 100), ("100–199", 100, 200), ("200–499", 200, 500), ("500+", 500, None)):
                mask = (data["coverage"] >= lo) & ((data["coverage"] < hi) if hi else True)
                for label in (0, 1): saved.require(int(np.sum(mask & (data["y"] == label))) == expected[(label, name)], "Member1 coverage support differs")
            receipt[filename]["counts_match_current_data0"] = True
        elif filename == "unusual_sites_review.csv":
            keys = set(data["keys"])
            saved.require(all(SCORER.site_key(row) in keys for row in rows), "Member1 reviewed key absent from data0")
            receipt[filename]["scope"] = "Existing within-read-spread review candidates; not equivalent to this across-site-median fence flag"
    return receipt, hashes


def groups_for(data, flags):
    result = []
    result.extend(("central5", str(m), data["motifs"] == m) for m in sorted(set(data["motifs"])))
    result.extend(("coverage", name, (data["coverage"] >= lo) & ((data["coverage"] < hi) if hi else True)) for name, lo, hi in COVERAGE)
    result.extend((("read_depth", "low_<50", data["coverage"] < 50), ("read_depth", "high_>=50", data["coverage"] >= 50),
                   ("unusual_signal", "flagged", flags), ("unusual_signal", "unflagged", ~flags)))
    for family in ("central5", "coverage", "read_depth", "unusual_signal"):
        saved.require(np.array_equal(np.sum([mask for kind, _, mask in result if kind == family], axis=0), np.ones(len(flags))), "Subgroups do not partition sites: "+family)
    return result


def analyse_groups(data, groups):
    rows, differences = [], []
    for family, group, mask in groups:
        by_mode = {}
        for mode in saved.MODES:
            by_mode[mode] = []
            for fold in [*range(5), None]:
                subset = mask if fold is None else mask & (data["folds"] == fold)
                metrics = subgroup_metrics(data["y"][subset], data["scores"][mode][subset])
                row = dict(family=family, subgroup=group, mode=mode, population="pooled_oof_diagnostic" if fold is None else "outer_fold", fold_id=fold, **metrics)
                rows.append(row); by_mode[mode].append(row)
        a, b = by_mode["none"][-1], by_mode["relative"][-1]
        paired = [by_mode["relative"][f]["selection_score"]-by_mode["none"][f]["selection_score"] for f in range(5) if by_mode["none"][f]["selection_score"] is not None]
        old_wrong = (data["scores"]["none"] >= .5) != data["y"]
        new_wrong = (data["scores"]["relative"] >= .5) != data["y"]
        helped, harmed = mask & old_wrong & ~new_wrong, mask & ~old_wrong & new_wrong
        differences.append(dict(family=family, subgroup=group, n_sites=a["n_sites"], n_positives=a["n_positives"],
            positive_fraction=a["positive_fraction"], sparse_positive_support=a["sparse_positive_support"],
            pooled_delta_selection_score=None if a["selection_score"] is None else b["selection_score"]-a["selection_score"],
            pooled_delta_roc_auc=None if a["roc_auc"] is None else b["roc_auc"]-a["roc_auc"],
            pooled_delta_pr_auc=None if a["pr_auc_trapezoid"] is None else b["pr_auc_trapezoid"]-a["pr_auc_trapezoid"],
            paired_evaluable_folds=len(paired), mean_paired_fold_delta_S=float(np.mean(paired)) if paired else None,
            sample_sd_paired_fold_delta_S=float(np.std(paired, ddof=1)) if len(paired) > 1 else None,
            helped_at_05=int(helped.sum()), harmed_at_05=int(harmed.sum()),
            helped_positive=int(np.sum(helped & (data["y"] == 1))), harmed_positive=int(np.sum(harmed & (data["y"] == 1))),
            helped_negative=int(np.sum(helped & (data["y"] == 0))), harmed_negative=int(np.sum(harmed & (data["y"] == 0)))))
    return rows, differences


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    buffer = io.StringIO(newline=""); writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows); saved.atomic_text(path, buffer.getvalue())


def make_plots(output, rows, differences):
    os.environ.setdefault("MPLCONFIGDIR", str(output/".matplotlib_cache"))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pooled = {(r["family"], r["subgroup"], r["mode"]): r for r in rows if r["population"] == "pooled_oof_diagnostic"}
    files = []
    for family, names, filename, title in (
            ("coverage", [name for name, _, _ in COVERAGE], "coverage_diagnostics.png", "Coverage: saved data0 OOF diagnostics"),
            ("unusual_signal", ["flagged", "unflagged"], "unusual_signal_diagnostics.png", "Context-conditioned unusual-signal flag: data0 OOF")):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.8)); x = np.arange(len(names))
        for ax, metric, ylabel in zip(axes, ("pr_auc_trapezoid", "recall"), ("Trapezoidal PR AUC", "Recall at 0.5")):
            for offset, mode in ((-.18, "none"), (.18, "relative")):
                values = [pooled[(family, name, mode)][metric] for name in names]
                ax.bar(x+offset, [np.nan if v is None else v for v in values], width=.36,
                       label="Original features" if mode == "none" else "Added context features")
            labels = [f"{name}\n+{pooled[(family,name,'none')]['n_positives']:,}\nn={pooled[(family,name,'none')]['n_sites']:,}" for name in names]
            ax.set(xticks=x, xticklabels=labels, ylim=(0, 1), ylabel=ylabel,
                   xlabel="Group; + = positive sites, n = all sites")
            ax.tick_params(axis="x", labelsize=9)
            ax.legend(fontsize=8)
        fig.suptitle(title); fig.tight_layout(); target = output/filename; fig.savefig(target, dpi=160); plt.close(fig); files.append(target)
    motif_rows = sorted([r for r in differences if r["family"] == "central5"], key=lambda r: r["subgroup"])
    fig, ax = plt.subplots(figsize=(8, 7.5)); y = np.arange(len(motif_rows))
    for i, row in enumerate(motif_rows):
        value = row["pooled_delta_selection_score"]
        if value is not None: ax.barh(i, value, color="#E69F00" if value < 0 else "#0072B2")
        else: ax.text(0, i, "not scored: single class", va="center", fontsize=8)
    labels = [f"{r['subgroup']}  ({r['n_positives']:,}/{r['n_sites']:,} +){' *' if r['sparse_positive_support'] else ''}" for r in motif_rows]
    ax.axvline(0, color="black", linewidth=.8); ax.set(yticks=y, yticklabels=labels,
        xlabel="Added context features − original features: combined score\nPooled out-of-fold diagnostic",
        title="Central5 motif differences and support\n* fewer than 20 positives; descriptive, potentially unstable")
    fig.tight_layout(); target = output/"motif_diagnostics.png"; fig.savefig(target, dpi=160); plt.close(fig); files.append(target)
    return files


def fmt(value): return "not scored" if value is None else f"{value:.6f}"


def write_report(data, rows, differences, flags, levels):
    lines = ["# Saved data0 error analysis", "",
        "This is a **post-hoc investigation of a known unsuccessful feature experiment**, using completed none/relative OOF predictions. It trains no neural model, performs no inference and does not read data1 inputs. Its predefined subgroup rules describe where the saved pipelines differ; they do not establish causes or a new independent result.", "",
        "## Overall reference", "", "| Mode | Five-fold mean S | Pooled OOF S |", "|---|---:|---:|"]
    for mode in saved.MODES:
        m = data["modes"][mode]["metrics"]
        lines.append(f"| {mode} | {m['primary_score']:.10f} | {m['pooled']['selection_score']:.10f} |")
    lines += ["", "Primary S is the unweighted mean of five fold (ROC AUC + trapezoidal PR AUC)/2. Pooled scores combine different outer models and may reflect their probability-scale differences. They are supplementary diagnostics, not a replacement headline or independent cell-line result.", "",
        "## Definitions fixed before subgroup analysis", "",
        "- Central5 motif is the middle five bases of the supplied seven-base context, with U treated as T. All actual motifs and valid sites remain included.",
        "- Coverage bins: 1–29, 30–49, 50–99, 100–199, 200+ reads. Low coverage is <50 and high coverage is >=50. These are fixed diagnostic bins; observed minimum coverage is "+str(int(data['coverage'].min()))+". No low-coverage site was dropped.",
        "- Primary unusual-signal flag: any of nine **raw site medians** outside its central5-conditioned Q1−3×IQR or Q3+3×IQR fence. Each fold fits fences only on its four non-assessment gene groups, with equal site weight. A motif needs >=30 training sites, otherwise that fold's global fences apply. The values 30 and 3 are engineering choices, not biological thresholds.",
        "- A tolerance of 1e-12×max(1,abs(Q1),abs(Q3)) applies to comparisons. Zero IQR collapses the fence to Q1=Q3; values outside it beyond that tiny tolerance are flagged but retained. A flag is not an error, chemical truth or a reason to remove/relabel a site.",
        "- Context-total support used for fences is separate from positive-label support used to interpret metrics. Groups with <20 positives are marked sparse, not excluded. Empty/single-class groups retain counts/available decision metrics; ROC/PR/AP/S are not scored.", "",
        f"Flagged **{int(flags.sum()):,}/{len(flags):,}** sites; motif-conditioned reference **{int(np.sum(levels=='motif')):,}**, global fallback **{int(np.sum(levels=='global')):,}**. Saved fence statistics include fitting-index/context/value/gene fingerprints and per-context training support. No assessment gene enters its fence fit.", ""]
    for family, title in (("coverage", "Coverage"), ("read_depth", "Low versus high coverage"), ("unusual_signal", "Flagged versus unflagged"), ("central5", "All central5 motifs")):
        lines += ["## "+title, "", "| Group | Positive / all sites | None pooled S | Relative pooled S | Pooled ΔS | Mean paired fold ΔS (evaluable folds) | Helped / harmed at 0.5 |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for item in [r for r in differences if r["family"] == family]:
            group = item["subgroup"]
            a, b = [next(r for r in rows if r["family"]==family and r["subgroup"]==group and r["mode"]==mode and r["population"]=="pooled_oof_diagnostic") for mode in saved.MODES]
            lines.append(f"| {group}{' *' if item['sparse_positive_support'] else ''} | {item['n_positives']:,}/{item['n_sites']:,} | {fmt(a['selection_score'])} | {fmt(b['selection_score'])} | {fmt(item['pooled_delta_selection_score'])} | {fmt(item['mean_paired_fold_delta_S'])} ({item['paired_evaluable_folds']}/5) | {item['helped_at_05']:,} / {item['harmed_at_05']:,} |")
        lines.append("")
    eligible = [r for r in differences if r["family"]=="central5" and r["n_positives"]>=20 and r["n_sites"]-r["n_positives"]>=20 and r["pooled_delta_selection_score"] is not None]
    lines += ["## Descriptive highlights and limitations", ""]
    for label, reverse in (("Largest pooled motif decreases", False), ("Largest pooled motif increases, if any", True)):
        candidates = [r for r in eligible if (r['pooled_delta_selection_score']>0 if reverse else r['pooled_delta_selection_score']<0)]
        selected = sorted(candidates, key=lambda r:r["pooled_delta_selection_score"], reverse=reverse)[:3]
        lines.append(label+": "+("; ".join(f"{r['subgroup']} ΔS={r['pooled_delta_selection_score']:+.6f} ({r['n_positives']} positives/{r['n_sites']} sites)" for r in selected) if selected else "none among motifs with at least20 sites of each class")+".")
    lines += ["", "The highlight support rule is descriptive, not a guarantee of reliability; all groups remain in the tables/CSVs. Helped/harmed counts compare the same labelled sites at the existing0.5 cutoff: one model wrong→right or right→wrong. They do not prove biological mechanisms or dictate a new decision threshold.", "",
        "- Member1 data0 motif/coverage counts were checked against the current aligned population; received within-motif effects and unusual-site review informed the questions. Her within-read-spread review flags differ from these across-site-median fences; neither is verified bad-data truth.",
        "- PR AUC varies with prevalence. Coverage, motif, gene, label quality and signal variability are associated; subgroup gaps cannot isolate which caused an error. Sparse positives and five correlated folds limit confidence; do not claim significance from their SD or select only helpful slices.",
        "- Fold diagnostics use the matching held-out scores; pooled diagnostic rows combine five distinct models. Means of subgroup differences show the number of evaluable folds and do not silently treat single-class folds as zero. They are not the primary five-fold comparison.",
        "- Existing architecture/recipe decisions and previous data0 investigation make this development analysis. Any intervention needs a separately documented data0-only test. No dropping, relabelling, calibration, threshold tuning or new model is performed here.",
        "- Data1 remains an already-exposed transfer diagnostic. No new transfer gain, SG-NEx biological effect, other modification-type prediction or read-level stoichiometry is established here.", "",
        "Full per-fold ROC/PR/AP/S, precision/recall, confusion counts and sparse support are in subgroup_metrics.csv. paired_subgroup_deltas.csv retains paired differences and error transitions. site_flags.csv provides traceable valid-site flags; fence_definitions.json and diagnostics_manifest.json retain rules, input/source/fitting-stat fingerprints and timing.", "",
        "![Coverage diagnostics](coverage_diagnostics.png)", "", "![Motif diagnostics](motif_diagnostics.png)", "", "![Unusual-signal diagnostics](unusual_signal_diagnostics.png)", ""]
    return "\n".join(lines)


def self_test():
    y = np.array([0, 1, 0, 1]); score = np.array([.1, .8, .6, .4])
    actual = subgroup_metrics(y, score)
    for key, value in SCORER.metrics(y, score).items(): saved.close(actual[key], value, key)
    one = subgroup_metrics(np.zeros(3, dtype=int), np.array([.2, .8, .1]))
    assert one["roc_auc"] is None and one["selection_score"] is None and one["fp"] == 1
    folds = np.repeat(np.arange(5), 32); genes = np.array(["gene"+str(f) for f in folds])
    motifs = np.tile(np.array(["AAAAA"]*16+["CCCCC"]*16), 5)
    medians = np.broadcast_to(np.where(motifs=="AAAAA", 100., 200.)[:, None], (160, 9)).copy()
    flags, _, _, before = fit_crossfold_flags(medians, motifs, folds, genes)
    assert not flags.any()
    changed = medians.copy(); changed[128] = 1000.
    changed_flags, _, _, after = fit_crossfold_flags(changed, motifs, folds, genes)
    assert before[4] == after[4] and changed_flags[128]
    _, _, levels, fallback = fit_crossfold_flags(medians, motifs, folds, genes, min_sites=80)
    assert (levels=="global").all() and not fallback[4]["supported_context_bounds"]
    bad_genes = genes.copy(); bad_genes[128] = "gene0"
    try: fit_crossfold_flags(medians, motifs, folds, bad_genes)
    except ValueError: pass
    else: raise AssertionError("Gene leakage not rejected")
    print("PASS synthetic checks: common metrics, single-class guard, held-out fence isolation, fallback and gene overlap rejection. No real data read.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=saved.DEFAULT_RUNS)
    parser.add_argument("--labels", type=Path, default=REPO.parent/"data0/data.info.labelled")
    parser.add_argument("--folds", type=Path, default=SCORER.DEFAULT_FOLDS)
    parser.add_argument("--cache", type=Path, default=REPO.parent/"advanced_model/cache/data0")
    parser.add_argument("--output-dir", type=Path, default=ALLOWED_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test: self_test(); return 0
    for name in ("runs", "labels", "folds", "cache", "output_dir"): setattr(args, name, getattr(args,name).resolve())
    saved.require(args.output_dir == ALLOWED_OUTPUT.resolve() or args.output_dir.is_relative_to(ALLOWED_OUTPUT.resolve()), "Outputs must stay under the ignored diagnostics directory")
    source_hashes = {"diagnose_context_cv.py": saved.sha256(__file__), "summarize_context_cv.py": saved.sha256(saved.__file__), "model_evaluation/evaluate.py": saved.sha256(SCORER.__file__)}
    with Monitor() as measured:
        data = load_inputs(args); member_receipt, member_hashes = member1_context(data)
        flags, feature_counts, levels, references = fit_crossfold_flags(data["medians"], data["motifs"], data["folds"], data["genes"])
        rows, differences = analyse_groups(data, groups_for(data, flags))
        output = args.output_dir; output.mkdir(parents=True, exist_ok=True)
        definitions = dict(feature_names_in_order=FEATURES, raw_summary_columns_zero_based=list(range(36,45)),
            quantile_method="linear", iqr_multiplier=IQR_MULTIPLIER, min_training_context_sites=MIN_CONTEXT_SITES,
            tiny_tolerance_relative=FLOAT_TOLERANCE, reference_hierarchy="central5 support>=30, otherwise global fit-site bounds",
            zero_iqr_policy="collapsed fence; flag beyond tiny tolerance; retain valid site",
            statistical_flag_not_error_truth=True, label_use_in_fence_fitting=False,
            array_order="sorted transcript ID and numeric position", site_key_order_sha256=text_hash([json.dumps(key, separators=(",",":")) for key in data["keys"]]),
            folds=references)
        saved.atomic_text(output/"fence_definitions.json", json.dumps(definitions, indent=2, allow_nan=False)+"\n")
        saved.atomic_text(output/"member1_data0_receipt.json", json.dumps(member_receipt, indent=2, allow_nan=False)+"\n")
        write_csv(output/"subgroup_metrics.csv", rows); write_csv(output/"paired_subgroup_deltas.csv", differences)
        site_rows = [dict(transcript_id=key[0], transcript_position=key[1], fold_id=int(data["folds"][i]),
            label=int(data["y"][i]), central5=str(data["motifs"][i]), n_reads=int(data["coverage"][i]),
            unusual_flag=bool(flags[i]), n_flagged_features=int(feature_counts[i]), fence_reference=str(levels[i]),
            score_none=float(data["scores"]["none"][i]), score_relative=float(data["scores"]["relative"][i])) for i,key in enumerate(data["keys"])]
        write_csv(output/"site_flags.csv", site_rows)
        make_plots(output, rows, differences)
        saved.atomic_text(output/"diagnostics.md", write_report(data, rows, differences, flags, levels))
        saved.require(all(saved.sha256(args.runs/"cv"/name)==value for name,value in data["cv_hashes"].items()), "CV inputs changed during diagnostics")
    filenames = ["fence_definitions.json", "member1_data0_receipt.json", "subgroup_metrics.csv", "paired_subgroup_deltas.csv", "site_flags.csv", "diagnostics.md", "coverage_diagnostics.png", "motif_diagnostics.png", "unusual_signal_diagnostics.png"]
    manifest = dict(status="complete", input_sha256={**data["input_hashes"], **member_hashes}, source_sha256=source_hashes,
        output_sha256={name:saved.sha256(args.output_dir/name) for name in filenames}, measurements=measured.record,
        n_sites=len(data["y"]), n_positives=int(data["y"].sum()), n_flagged=int(flags.sum()),
        no_sites_dropped_or_relabelled=True, neural_fitting_or_inference=False, data1_input_files_read=False,
        member1_existing_tables_filter="dataset == data0", command_template="python model_elgin/tools/diagnose_context_cv.py --runs model_elgin/outputs/context_reference_v1 --labels LOCAL_DATA0_LABELS --cache LOCAL_DATA0_CACHE",
        exact_arguments_portable=dict(runs="model_elgin/outputs/context_reference_v1", labels="../data0/data.info.labelled", folds="eda/received/shared_folds/data0_folds.csv", cache="../advanced_model/cache/data0", output_dir="model_elgin/outputs/context_reference_v1/diagnostics"))
    saved.atomic_text(args.output_dir/"diagnostics_manifest.json", json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    print(f"Saved data0 diagnostics for {len(data['y']):,} retained sites; wall {measured.record['wall_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
