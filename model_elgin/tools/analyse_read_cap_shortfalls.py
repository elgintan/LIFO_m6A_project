"""Matched saved-data0 diagnostics. Never fit, infer, tune cutoffs or read data1."""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd

import diagnose_context_cv as diagnostic
import report_read_cap as reference

REPO = Path(__file__).resolve().parents[2]
SAVED, SCORER = reference.SAVED, diagnostic.SCORER
MODELS = ("cap32", "cap128", "samuel")
PAIRS = (("cap32", "cap128"), ("samuel", "cap128"))
KEY = ["transcript_id", "transcript_position"]
DEFAULT = REPO / "model_elgin/outputs/read_cap_v1/shortfalls"


def align_scores(keys, assignments, predictions, prediction_folds):
    SCORER.same_keys(dict.fromkeys(keys), predictions, "Expected sites/predictions")
    SAVED.require(all(prediction_folds[k] == assignments[k][1] for k in keys), "Wrong prediction fold")
    values = np.asarray([predictions[k] for k in keys], dtype=float)
    SAVED.require(np.isfinite(values).all() and ((values >= 0) & (values <= 1)).all(), "Invalid scores")
    return values


def verified_flags(frame, flags):
    SAVED.require(not flags.duplicated(KEY).any(), "Duplicate prior flag key")
    SAVED.require(set(map(tuple, flags[KEY].values)) == set(map(tuple, frame[KEY].values)), "Incomplete prior flags")
    metadata = [*KEY, "fold_id", "label", "central5", "n_reads"]
    joined = frame[metadata].merge(flags[[*metadata, "unusual_flag"]],
                         on=KEY, how="left", suffixes=("", "_flag"), validate="one_to_one")
    for field in ("fold_id", "label", "central5", "n_reads"):
        SAVED.require(np.array_equal(joined[field], joined[field + "_flag"]), "Prior flag metadata mismatch: " + field)
    values = joined.unusual_flag
    SAVED.require(values.isin([True, False]).all(), "Invalid prior flag type")
    return values.to_numpy(dtype=bool)


def error_overlap(y, a, b, mask):
    wrong_a, wrong_b = (a >= .5) != y, (b >= .5) != y
    changed = {}
    for label, name in ((1, "positive"), (0, "negative")):
        sub = mask & (y == label)
        changed.update({name + "_" + key: int((sub & condition).sum()) for key, condition in (
            ("both_wrong", wrong_a & wrong_b), ("both_correct", ~wrong_a & ~wrong_b),
            ("fixed_by_candidate", wrong_a & ~wrong_b), ("new_candidate_error", ~wrong_a & wrong_b))})
    SAVED.require(sum(changed.values()) == int(mask.sum()), "Error overlap does not partition sites")
    return changed


def load_inputs(args):
    evidence = {}
    def record(path):
        path = Path(path).resolve()
        key = os.path.relpath(path, REPO).replace("\\", "/")
        digest = SAVED.sha256(path)
        evidence[key] = digest
        return digest
    roots = dict(cap32=REPO / "model_elgin/outputs/context_reference_v1/cv",
                 cap128=REPO / "model_elgin/outputs/read_cap_v1/cv")
    hashes = {name: {} for name in roots}
    saved = {name: SAVED.load_mode(root, "none", hashes[name]) for name, root in roots.items()}
    reference.validate_pairs(saved, roots, hashes)
    reference.validate_training_signatures(saved, roots, hashes)
    reference.current_source_evidence(saved["cap128"]["recipe"])
    for model, files in hashes.items():
        for relative, digest in files.items():
            evidence[os.path.relpath(roots[model] / relative, REPO).replace("\\", "/")] = digest
    identity = saved["cap128"]["recipe"]["identity"]
    SAVED.require(record(args.labels) == identity["labels_sha256"], "Changed label source")
    SAVED.require(record(args.folds) == SCORER.FOLD_SHA256, "Changed shared folds")
    labels, label_genes = SCORER.read_labels(args.labels)
    assignments = SCORER.read_folds(args.folds)
    SCORER.same_keys(labels, assignments, "Labels/folds")
    SAVED.require(SCORER.canonical_labels_hash(labels, assignments) == SCORER.DATA0_LABELS_CANONICAL_SHA256,
                  "Wrong canonical data0 population")
    SAVED.require(all(label_genes[k] == assignments[k][0] for k in labels), "Wrong gene mapping")
    keys = sorted(labels)
    frame = pd.DataFrame(keys, columns=KEY)
    frame["label"] = [labels[k] for k in keys]
    frame["fold_id"] = [assignments[k][1] for k in keys]
    frame["gene_id"] = [assignments[k][0] for k in keys]
    SAVED.require(frame.groupby("gene_id").fold_id.nunique().max() == 1, "Gene crosses folds")
    SAVED.require(record(args.cache / "manifest.json") == identity["cache_manifest_sha256"], "Changed cache manifest")
    cache_manifest = json.loads((args.cache / "manifest.json").read_text())
    SAVED.require(record(args.cache / "keys.csv") == cache_manifest["cache_sha256"]["keys.csv"], "Changed cache keys")
    cache = pd.read_csv(args.cache / "keys.csv")
    SAVED.require(not cache.duplicated(KEY).any() and set(map(tuple, cache[KEY].values)) == set(keys), "Wrong cache sites")
    frame = frame.merge(cache, on=KEY, validate="one_to_one", how="left")
    SAVED.require(list(map(tuple, frame[KEY].values)) == keys, "Key ordering changed")
    SAVED.require(frame.n_reads.ge(1).all() and frame.context.str.fullmatch("[ACGT]{7}").all(), "Invalid context/coverage")
    frame["central5"] = frame.context.str[1:6]
    prior = REPO / "model_elgin/outputs/context_reference_v1/diagnostics"
    record(prior / "diagnostics_manifest.json")
    manifest = json.loads((prior / "diagnostics_manifest.json").read_text())
    SAVED.require(manifest["status"] == "complete", "Prior flags not complete")
    for name in ("site_flags.csv", "fence_definitions.json"):
        SAVED.require(record(prior / name) == manifest["output_sha256"][name], "Changed prior flag artifact")
    for key, path in (("data0_labels", args.labels), ("shared_folds", args.folds), ("cache_manifest", args.cache / "manifest.json")):
        SAVED.require(record(path) == manifest["input_sha256"][key], "Different prior flag population")
    fence = json.loads((prior / "fence_definitions.json").read_text())
    SAVED.require(len(fence["folds"]) == 5, "Missing prior fence folds")
    for f, fitted in enumerate(fence["folds"]):
        SAVED.require(fitted["assessment_fold"] == f and fitted["fit_folds"] == [i for i in range(5) if i != f]
                      and fitted["zero_gene_overlap"] is True, "Wrong fence boundary")
    frame["unusual_flag"] = verified_flags(frame, pd.read_csv(prior / "site_flags.csv"))
    member_path = REPO / "eda/received/tables/unusual_sites_review.csv"
    record(member_path)
    member = pd.read_csv(member_path)
    member = member.loc[member.dataset.eq("data0")]
    member_keys = set(map(tuple, member[KEY].values))
    SAVED.require(member_keys <= set(keys), "Member1 reviewed site absent")
    frame["member1_reviewed"] = [k in member_keys for k in keys]
    paths = {name: roots[name] / "none/data0_oof.csv" for name in roots}
    paths["samuel"] = REPO / "model_samuel/outputs/data0_oof.csv"
    record(REPO / "model_samuel/results/data0_cv_metrics.json")
    saved["samuel"] = dict(metrics=json.loads((REPO / "model_samuel/results/data0_cv_metrics.json").read_text()))
    scores = {}
    for name in MODELS:
        metrics = saved[name]["metrics"]
        SAVED.require(record(paths[name]) == metrics["inputs"]["predictions"]["sha256"], "Changed OOF " + name)
        SAVED.require(metrics["scorer_sha256"] == record(REPO / "model_evaluation/evaluate.py"), "Different scorer")
        SAVED.require(metrics["inputs"]["labels"]["sha256"] == identity["labels_sha256"] and
                      metrics["inputs"]["folds"]["sha256"] == SCORER.FOLD_SHA256, "Different scoring inputs")
        predictions, folds = SCORER.read_predictions(paths[name], "data0")
        scores[name] = align_scores(keys, assignments, predictions, folds)
        for f in [None, *range(5)]:
            mask = np.ones(len(frame), dtype=bool) if f is None else frame.fold_id.to_numpy() == f
            actual = SCORER.metrics(frame.label.to_numpy()[mask], scores[name][mask])
            expected = metrics["pooled"] if f is None else next(r for r in metrics["per_fold"] if r["fold_id"] == f)
            for field, value in actual.items(): SAVED.close(value, expected[field], name + ": " + field)
    return frame, scores, saved, evidence, len(member)


def groups(frame):
    yield "all", "all_data0", np.ones(len(frame), dtype=bool)
    depth = frame.n_reads.to_numpy()
    for label, low, high in diagnostic.COVERAGE:
        yield "coverage", label, (depth >= low) & ((depth < high) if high is not None else True)
    for low in (100, 200): yield "depth_target", str(low) + "+", depth >= low
    for column in ("central5", "context"):
        for name in sorted(frame[column].unique()): yield column, name, frame[column].eq(name).to_numpy()
    flags = frame.unusual_flag.to_numpy()
    yield "unusual_signal", "flagged", flags
    yield "unusual_signal", "unflagged", ~flags
    yield "member1", "reviewed_unique_sites", frame.member1_reviewed.to_numpy()
    for name in sorted(frame.central5.unique()):
        yield "high_depth_central5", name, (depth >= 200) & frame.central5.eq(name).to_numpy()


def analyse(frame, scores):
    y, folds = frame.label.to_numpy(), frame.fold_id.to_numpy()
    genes = frame.gene_id.to_numpy()
    rows, changes, overlaps = [], [], []
    for family, group, mask in groups(frame):
        by_model = {}
        for model in MODELS:
            by_model[model] = []
            for fold in [*range(5), None]:
                sub = mask if fold is None else mask & (folds == fold)
                result = diagnostic.subgroup_metrics(y[sub], scores[model][sub])
                result.update(n_genes=len(set(genes[sub])), sparse_class_support=min(result["n_positives"], result["n_negatives"]) < 20)
                row = dict(family=family, subgroup=group, model=model, population="pooled_oof_diagnostic" if fold is None else "outer_fold",
                           fold_id=fold, **result)
                rows.append(row); by_model[model].append(row)
        for control, candidate in PAIRS:
            base, new = by_model[control], by_model[candidate]
            paired = [new[f]["selection_score"] - base[f]["selection_score"] for f in range(5) if base[f]["selection_score"] is not None]
            change = dict(family=family, subgroup=group, control=control, candidate=candidate,
                          n_sites=base[-1]["n_sites"], n_positives=base[-1]["n_positives"], n_genes=base[-1]["n_genes"],
                          sparse_class_support=base[-1]["sparse_class_support"], evaluable_folds=len(paired),
                          mean_evaluable_fold_delta_S=float(np.mean(paired)) if paired else None,
                          sample_sd_paired_delta_S=float(np.std(paired, ddof=1)) if len(paired) > 1 else None,
                          higher_folds=sum(x > 0 for x in paired), lower_folds=sum(x < 0 for x in paired),
                          pooled_delta_S=None if base[-1]["selection_score"] is None else new[-1]["selection_score"] - base[-1]["selection_score"])
            changes.append(change)
            overlap = error_overlap(y, scores[control], scores[candidate], mask)
            overlaps.append(dict(family=family, subgroup=group, control=control, candidate=candidate,
                                 n_sites=int(mask.sum()), **overlap))
    return rows, changes, overlaps


def reliability(y, scores):
    rows, summary = [], []
    for name, score in scores.items():
        indices = np.minimum((score * 10).astype(int), 9)
        ece = 0.
        for bin_id in range(10):
            mask = indices == bin_id
            n = int(mask.sum())
            predicted, observed = (float(score[mask].mean()), float(y[mask].mean())) if n else (None, None)
            if n: ece += n / len(y) * abs(predicted - observed)
            rows.append(dict(model=name, bin_id=bin_id, lower=bin_id / 10, upper=(bin_id + 1) / 10,
                             n_sites=n, n_positives=int(y[mask].sum()), mean_score=predicted, observed_positive_fraction=observed))
        summary.append(dict(model=name, brier_score=float(np.mean((score-y)**2)),
                            equal_width_10bin_ece=ece, mean_score=float(score.mean()), positive_fraction=float(y.mean())))
    return rows, summary


def plots(output, rows, changes, reliability_rows):
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    files = []
    for family in ("coverage", "central5"):
        selected = [r for r in changes if r["family"] == family and r["control"] == "cap32"]
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(selected))
        values = [np.nan if r["pooled_delta_S"] is None else r["pooled_delta_S"] for r in selected]
        ax.bar(x, values, color=["#328267" if value >= 0 else "#ba5931" for value in values])
        ax.axhline(0, color="black", lw=.8)
        ax.set(xticks=x, xticklabels=[r["subgroup"] for r in selected], ylabel="Cap128 minus cap32 pooled subgroup S",
               title="Same-site development diagnostic: " + family)
        ax.tick_params(axis="x", rotation=60 if family == "central5" else 0)
        for i, row in enumerate(selected):
            if row["pooled_delta_S"] is None: ax.text(i, 0, "NA", ha="center", fontsize=9)
            elif row["sparse_class_support"]: ax.text(i, 0, "*", ha="center", fontsize=14)
        fig.text(.02, .01, "* Fewer than 20 positives or negatives. NA: ranking undefined. Compare versions within each group.", fontsize=8)
        fig.tight_layout(rect=(0, .04, 1, 1))
        path = output / (family + "_paired_changes.png")
        fig.savefig(path, dpi=150); plt.close(fig); files.append(path)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for model in MODELS:
        selected = [r for r in reliability_rows if r["model"] == model and r["n_sites"]]
        ax.plot([r["mean_score"] for r in selected], [r["observed_positive_fraction"] for r in selected], "o-", label=model)
    ax.plot([0, 1], [0, 1], "k--", alpha=.5)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean uncalibrated model score", ylabel="Supplied label-1 fraction",
           title="Pooled data0 OOF reliability: descriptive only")
    ax.legend(); fig.tight_layout()
    path = output / "score_reliability.png"; fig.savefig(path, dpi=150); plt.close(fig); files.append(path)
    return files


def make_report(frame, rows, changes, overlaps, reliability_summary):
    pooled = {(r["family"], r["subgroup"], r["model"]): r for r in rows if r["population"] == "pooled_oof_diagnostic"}
    lines = ["# Cap128 shortfalls and shared candidate comparison", "",
             "Completed saved-data0 analysis only: no training, model inference, data1 access, cutoff search or calibration fitting. All 121,838 sites and 3,852 genes are retained. This is reused development evidence, not a new blind test.", "",
             "## Full-data0 comparison", "", "The primary score remains mean-fold S=(ROC AUC+trapezoidal PR AUC)/2; pooled subgroup results below do not replace it.", "",
             "| Model | Mean-fold ROC AUC | Mean-fold PR AUC | Mean-fold S | Pooled precision at 0.5 | Recall at 0.5 | F1 at 0.5 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for model in MODELS:
        folded = [r for r in rows if r["family"] == "all" and r["model"] == model and r["fold_id"] is not None]
        point = pooled[("all", "all_data0", model)]
        means = [np.mean([r[k] for r in folded]) for k in ("roc_auc", "pr_auc_trapezoid", "selection_score")]
        lines.append(f"| {model} | {means[0]:.9f} | {means[1]:.9f} | {means[2]:.9f} | {point['precision']:.6f} | {point['recall']:.6f} | {point['f1']:.6f} |")
    lines += ["", "## Matched subgroup results", "", "These are pooled OOF metrics on identical sites for each version. PR AUC depends on group prevalence. All five fold-level values, support warnings and paired changes are retained in the CSVs. Sparse or single-class groups are not removed; ranking is undefined for a one-class group.", "",
              "| Group | Sites | Positive labels | Cap32 S | Cap128 S | Samuel S | Cap128 minus cap32 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for family, group, _ in groups(frame):
        if family not in ("coverage", "depth_target", "unusual_signal", "member1"): continue
        values = [pooled[(family, group, model)] for model in MODELS]
        fmt = lambda x: "NA" if x is None else f"{x:.6f}"
        delta = None if values[0]["selection_score"] is None else values[1]["selection_score"] - values[0]["selection_score"]
        lines.append(f"| {family}: {group} | {values[0]['n_sites']} | {values[0]['n_positives']} | " + " | ".join(fmt(v["selection_score"]) for v in values) + f" | {fmt(delta)} |")
    lines += ["", "The first historical coverage bin is named 1–29, but all observed sites in it have 20–29 reads. The earlier read-depth report's approximately 0.732322 for the 100+ cohort is a mean-fold value; its corresponding pooled value is 0.727391, matching cap32 above. Do not compare that mean-fold score with these pooled subgroup scores.", "",
              "## What changed at the fixed 0.5 cutoff?", "", "0.5 is an unvalidated reporting cutoff; versions need not have comparable score calibration. A fixed/new error is a crossing of this cutoff, not verified chemical correction.", "",
              "| Scope / control -> cap128 | Positive errors fixed | New positive errors | Negative errors fixed | New negative errors |", "|---|---:|---:|---:|---:|"]
    for r in overlaps:
        if r["family"] != "all" and not (r["family"] == "depth_target" and r["subgroup"] == "200+"): continue
        lines.append(f"| {r['family']}:{r['subgroup']} / {r['control']} | {r['positive_fixed_by_candidate']} | {r['positive_new_candidate_error']} | {r['negative_fixed_by_candidate']} | {r['negative_new_candidate_error']} |")
    lines += ["", "## Score reliability", "", "| Model | Brier score | Equal-width 10-bin ECE | Mean score | Label prevalence |", "|---|---:|---:|---:|---:|"]
    for r in reliability_summary:
        lines.append(f"| {r['model']} | {r['brier_score']:.6f} | {r['equal_width_10bin_ece']:.6f} | {r['mean_score']:.6f} | {r['positive_fraction']:.6f} |")
    lines += ["", "These describe raw OOF score reliability under the supplied labels, not calibrated molecule-level probabilities or SG-NEx modification fractions. Brier score includes class imbalance; ECE depends on the declared ten bins. No calibration/threshold was fitted or selected, and no improved ranking can be claimed from a monotonic rescaling alone.", "",
              "## EDA links and limitations", "",
              "- Coverage/context groups follow the existing diagnostics. The primary investigated shortfall is >=200 reads; >=100 is a secondary comparison with the earlier depth cohort. All 288 exact 7-base contexts and all 18 central 5-base motifs are retained, including sparse groups, in subgroup_metrics.csv.",
              "- Unusual flags reuse the previous label-free central5-conditioned 3-IQR fences fitted on the four non-assessment gene groups, with the same minimum 30-site fallback. No flags, labels or model scores are changed. Member 1 review entries are separate handoff candidates; repeated entries are counted once per site for metrics.",
              "- Model-source/input signatures and hashes are checked; saved scores are rescored with the common evaluator. This corroborates saved evidence, not independent retraining of Samuel's or the neural pipelines. Their modelling/tuning budgets and loss weights differ.",
              "- Many subgroup comparisons are exploratory, not independent biological experiments or significance tests. Fold means with fewer than five evaluable folds are labelled with that denominator, not a new headline score.",
              "- Threshold/calibration fitting must use training-side data0 genes. A naive pooled-OOF threshold search after repeated development cannot be reported as an unbiased improvement; ordinary OOF predictions from other folds can still depend on a nominal assessment fold through those folds' training sets.",
              "- These results do not select a new architecture, prove an outlier mechanism, evaluate data1 or produce a final all-data0 model/SG-NEx predictions. A candidate decision and next experiment rationale are recorded separately after review.", "",
              "![Coverage changes](coverage_paired_changes.png)", "", "![Motif changes](central5_paired_changes.png)", "", "![Score reliability](score_reliability.png)", "",
              "## Exact command", "", "From the repository root, using the retained local inputs and saved runs:", "", "```powershell",
              "../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/analyse_read_cap_shortfalls.py", "```", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=REPO.parent / "data0/data.info.labelled")
    parser.add_argument("--folds", type=Path, default=REPO / "eda/received/shared_folds/data0_folds.csv")
    parser.add_argument("--cache", type=Path, default=REPO.parent / "advanced_model/cache/data0")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    SAVED.require(output.is_relative_to(REPO / "model_elgin/outputs"), "Output must stay within local model_elgin/outputs")
    output.mkdir(parents=True, exist_ok=True)
    status = output / "analysis_status.json"
    SAVED.atomic_text(status, json.dumps(dict(status="running")))
    try:
        source_paths = [Path(__file__), Path(diagnostic.__file__), Path(reference.__file__), Path(SAVED.__file__), REPO / "model_evaluation/evaluate.py"]
        sources = {p.relative_to(REPO).as_posix(): SAVED.sha256(p) for p in source_paths}
        with diagnostic.Monitor() as measurement:
            frame, scores, saved, evidence, member_entries = load_inputs(args)
            rows, changes, overlaps = analyse(frame, scores)
            reliability_rows, reliability_summary = reliability(frame.label.to_numpy(), scores)
            products = {"subgroup_metrics.csv": rows, "paired_subgroup_changes.csv": changes,
                        "error_overlap.csv": overlaps, "reliability_bins.csv": reliability_rows, "reliability_summary.csv": reliability_summary}
            written = []
            for name, table in products.items():
                diagnostic.write_csv(output / name, table); written.append(output / name)
            written.extend(plots(output, rows, changes, reliability_rows))
            report = output / "README.md"
            SAVED.atomic_text(report, make_report(frame, rows, changes, overlaps, reliability_summary)); written.append(report)
            SAVED.require(all(SAVED.sha256(REPO / rel) == digest for rel, digest in {**evidence, **sources}.items()), "Inputs/source changed during analysis")
        manifest = dict(status="complete", scope="Saved full-data0 shortfalls/candidate comparison; descriptive only",
                        no_fitting_or_model_inference=True, no_data1_access=True, no_threshold_or_calibration_selection=True,
                        n_sites=len(frame), n_positive_labels=int(frame.label.sum()), n_genes=frame.gene_id.nunique(),
                        member1_review_entries=member_entries, member1_unique_reviewed_sites=int(frame.member1_reviewed.sum()),
                        input_sha256=evidence, source_sha256=sources, measurements=measurement.record,
                        arguments=list(sys.argv[1:] if argv is None else argv),
                        output_sha256={p.name: SAVED.sha256(p) for p in written})
        manifest_path = output / "analysis_manifest.json"
        SAVED.atomic_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
        SAVED.atomic_text(status, json.dumps(dict(status="complete", manifest_sha256=SAVED.sha256(manifest_path)), indent=2) + "\n")
        print(json.dumps(dict(status="complete", output=os.path.relpath(output, REPO), measurements=measurement.record)))
        return 0
    except Exception as exc:
        SAVED.atomic_text(status, json.dumps(dict(status="failed", error=str(exc), old_outputs_non_authoritative=True), indent=2) + "\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
