"""Training-side threshold selection with frozen cap128 models; no NN fitting."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
import pandas as pd
import diagnose_context_cv as diagnostic
import report_read_cap as reference

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "model_elgin/THRESHOLD_EXPERIMENT.md"
DEFAULT = REPO / "model_elgin/outputs/threshold_v1"
SAVED, SCORER = reference.SAVED, diagnostic.SCORER
KEY = ["transcript_id", "transcript_position"]


def require(condition, message):
    if not condition: raise ValueError(message)


def arrays(y, scores):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    require(y.ndim == scores.ndim == 1 and y.shape == scores.shape and len(y) > 0,
            "Need aligned nonempty label/score vectors")
    require(np.isin(y, [0, 1]).all() and np.isfinite(scores).all() and
            ((scores >= 0) & (scores <= 1)).all(), "Invalid labels or score range")
    return y.astype(np.int64), scores


def decisions(y, calls):
    y, calls = np.asarray(y), np.asarray(calls)
    require(y.ndim == calls.ndim == 1 and y.shape == calls.shape and np.isin(y, [0, 1]).all()
            and calls.dtype == np.bool_, "Invalid labels/boolean calls")
    tn, fp = int(((y == 0) & ~calls).sum()), int(((y == 0) & calls).sum())
    fn, tp = int(((y == 1) & ~calls).sum()), int(((y == 1) & calls).sum())
    return dict(n_sites=len(y), n_positives=tp+fn, tn=tn, fp=fp, fn=fn, tp=tp,
                precision=tp/(tp+fp) if tp+fp else 0., recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
                specificity=tn/(tn+fp) if tn+fp else None, accuracy=(tn+tp)/len(y) if len(y) else None)


def select_threshold(y, scores):
    """Exact F1 objective and higher-cutoff tie rule over grouped score ties."""
    y, scores = arrays(y, scores)
    positive = int(y.sum())
    require(0 < positive < len(y), "Cutoff selection requires both classes")
    order = np.argsort(-scores, kind="stable")
    ranked = scores[order]
    cumulative = np.cumsum(y[order])
    ends = np.flatnonzero(np.r_[ranked[1:] != ranked[:-1], True])
    best_num, best_den, best_at = -1, 1, None
    curve = []
    for at in ends:
        count, tp = int(at)+1, int(cumulative[at])
        numerator, denominator = 2*tp, positive+count
        curve.append(dict(cutoff=float(ranked[at]), predicted_positive=count, tp=tp,
                          fp=count-tp, fn=positive-tp, f1=numerator/denominator,
                          precision=tp/count, recall=tp/positive))
        if numerator*best_den > best_num*denominator:
            best_num, best_den, best_at = numerator, denominator, len(curve)-1
    chosen = curve[best_at]
    result = dict(cutoff=chosen["cutoff"], objective="max_inner_site_F1", tie_rule="higher_cutoff",
                  comparison="score >= cutoff", n_distinct_cutoffs=len(curve),
                  f1_numerator=best_num, f1_denominator=best_den,
                  inner=decisions(y, scores >= chosen["cutoff"]))
    return result, curve


def align_prediction(meta, prediction):
    require(not prediction.duplicated(KEY).any() and not meta.duplicated(KEY).any(), "Duplicate prediction/metadata key")
    require(set(map(tuple, meta[KEY].values)) == set(map(tuple, prediction[KEY].values)), "Incomplete/extra prediction sites")
    joined = meta[[*KEY, "fold_id"]].merge(prediction, on=KEY, how="left", validate="one_to_one", suffixes=("", "_prediction"))
    require(np.array_equal(joined.fold_id, joined.fold_id_prediction), "Wrong prediction fold")
    _, result = arrays(np.zeros(len(joined)), joined.score.to_numpy())
    return result


def verify_bundle(bundle, recipe, complete, fit_indices_sha256):
    require(bundle["kind"] == "context_reference_v1" and bundle["stage"] == "cv_inner", "Need trusted inner best model")
    require(bundle["config"] == recipe["config"] and bundle["epoch"] == complete["best_epoch"]
            and bundle["seed"] == complete["seed"] and bundle["fit_signature"] == complete["signature"]
            and bundle["input_fingerprints"] == recipe["identity"], "Inner checkpoint identity mismatch")
    require(bundle["norm"]["fit_indices_sha256"] == fit_indices_sha256 and
            bundle["norm"]["fit_sites"] == complete["train_sites"] and bundle["context_reference"] is None,
            "Inner normalisation or context fitting boundary mismatch")


def immutable_json(path, value):
    if path.exists(): require(json.loads(path.read_text()) == value, "Changed study identity; use a new output directory")
    else: SAVED.atomic_text(path, json.dumps(value, indent=2, allow_nan=False)+"\n")


def metrics_close(actual, expected, tolerance=1e-6):
    for key, value in actual.items():
        require(abs(float(value)-float(expected[key])) <= tolerance, "Inner prediction does not reproduce history: " + key)


def plot_results(output, selected, outer, curve_rows):
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(range(5), [r["cutoff"] for r in selected], "o-", label="Chosen on inner genes")
    axes[0].axhline(.5, color="grey", ls="--", label="Original0.5")
    axes[0].set(xticks=range(5), ylim=(0, 1), xlabel="Excluded outer gene fold", ylabel="Raw score cutoff", title="Training-side cutoff variation")
    axes[0].legend()
    x = np.arange(5)
    for policy, offset in (("fixed_0.5", -.17), ("inner_F1", .17)):
        axes[1].bar(x+offset, [r["f1"] for r in outer if r["policy"] == policy], width=.34, label=policy)
    axes[1].set(xticks=x, ylim=(0, 1), xlabel="Excluded outer gene fold", ylabel="F1", title="Outer assessment: same saved scores")
    axes[1].legend(); fig.tight_layout(); fig.savefig(output / "cutoffs_and_outer_f1.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for fold in range(5):
        curve = [r for r in curve_rows if r["outer_fold"] == fold]
        axes[0].plot([r["cutoff"] for r in curve], [r["f1"] for r in curve], label=str(fold))
        chosen = selected[fold]
        axes[0].plot(chosen["cutoff"], chosen["inner_f1"], "o")
    axes[0].set(xlim=(0, 1), ylim=(0, 1), xlabel="Raw score cutoff", ylabel="Selected-inner F1 (optimistic)", title="Inner selection curves; not assessment")
    axes[0].legend(title="Outer round")
    for policy, marker in (("fixed_0.5", "o"), ("inner_F1", "s")):
        rows = [r for r in outer if r["policy"] == policy]
        axes[1].scatter([r["recall"] for r in rows], [r["precision"] for r in rows], marker=marker, label=policy)
        for r in rows: axes[1].annotate(str(r["outer_fold"]), (r["recall"], r["precision"]), xytext=(4, 3), textcoords="offset points")
    axes[1].set(xlim=(0, 1), ylim=(0, 1), xlabel="Outer recall", ylabel="Outer precision", title="Excluded-outer operating tradeoff")
    axes[1].legend(); fig.tight_layout(); fig.savefig(output / "inner_selection_outer_tradeoff.png", dpi=150); plt.close(fig)


def report(selected, outer, pooled, summary, measurements):
    lines = ["# Cap128 training-side calling-threshold study", "",
             "Completed threshold-only data0 development study. Saved neural weights and continuous scores are unchanged; no neural training, probability calibration or data1 evaluation occurred.", "",
             "For each excluded outer fold f, the saved three-group inner best model predicted only inner group(f+1)%5. Its maximum-F1 cutoff, with higher-cutoff exact ties, was applied to that round's existing four-group refit OOF scores. Inner F1 is selected and optimistic, not evaluation performance.", "",
             "## Cutoffs selected without their outer assessment genes", "", "| Outer fold | Inner group | Inner sites | Inner positives | Chosen cutoff | Selected inner F1 | Outer F1 at0.5 | Outer F1 at chosen cutoff |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in selected:
        old, new = [next(x for x in outer if x["outer_fold"] == r["outer_fold"] and x["policy"] == p) for p in ("fixed_0.5", "inner_F1")]
        lines.append(f"| {r['outer_fold']} | {r['inner_fold']} | {r['inner_sites']} | {r['inner_positives']} | {r['cutoff']:.9f} | {r['inner_f1']:.6f} | {old['f1']:.6f} | {new['f1']:.6f} |")
    lines += ["", "## Excluded-outer assessment", "", "Pooled rows sum all outer confusion counts. Learned-policy pooled decisions use five different training-side cutoffs. Fold means are unweighted; sample SD is descriptive, not a confidence interval.", "", "| Summary / policy | Precision | Recall | F1 | Specificity | Accuracy |", "|---|---:|---:|---:|---:|---:|"]
    for r in [*pooled, *summary]:
        lines.append("| "+r["summary"]+" / "+r["policy"]+" | "+" | ".join(f"{r[k]:.6f}" for k in ("precision", "recall", "f1", "specificity", "accuracy"))+" |")
    median = float(np.median([r["cutoff"] for r in selected]))
    lines += ["", f"The predeclared median of five inner cutoffs is **{median:.12g}**, a proposal for the later all-data0 deployment model. It was not evaluated as a single global cutoff on these outer rows, is not guaranteed F1-optimal, and its score-scale transfer to a future all-data0 model is untested.", "",
              "ROC AUC, trapezoidal PR AUC, AP and S are unchanged. Mean-fold cap128 ROC/PR/S remain0.9318281774/0.5056010366/0.7187146070. Threshold adjustment must not be presented as improved ranking.", "",
              "## Limits and retained evidence", "",
              "- Choosing epoch and cutoff on one inner group is model selection. Each outer assessment group stays outside both choices. Architecture/model selection has already used these development folds; this is not a new blind or unbiased final test.",
              "- The selected cutoff comes from a three-group model and is applied to a fresh four-group refit. The outer results measure that transfer; the final median rule is a separate engineering aggregation.",
              "- The objective is site-label F1. It does not encode a verified biological false-discovery rate, calibrated probability, molecule fraction or optimum for every SG-NEx cell line. Retain continuous scores and threshold sensitivity for Task2.",
              "- No cutoff is fitted from other rounds' ordinary OOF scores. Full inner predictions, unique-score curves, matching checkpoint receipts and per-round selected results stay local and permit checked resume. No assessment site is dropped or relabelled.",
              f"- This invocation's measured analysis work: wall{measurements['wall_seconds']:.3f}s, process CPU{measurements['process_cpu_seconds']:.3f}s, sampled process RSS peak{measurements['sampled_peak_process_rss_mib']:.3f}MiB. Scope: {measurements['scope']} Reused rounds are disclosed in the manifest; prior invocations are not included in this timer.", "",
              "![Cutoffs and outer F1](cutoffs_and_outer_f1.png)", "", "![Inner selection and outer tradeoff](inner_selection_outer_tradeoff.png)", "",
              "## Exact command", "", "From the repository root:", "", "```powershell", "../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/validate_calling_threshold.py", "```", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    require(output.is_relative_to(REPO / "model_elgin/outputs"), "Output must remain in local model outputs")
    output.mkdir(parents=True, exist_ok=True)
    status = output / "analysis_status.json"
    SAVED.atomic_text(status, json.dumps(dict(status="running")))
    try:
        sys.path.insert(0, str(REPO / "model_elgin/context_reference_v1"))
        import train as fitting
        import torch
        import sklearn
        versions = dict(python=platform.python_version(), torch=str(torch.__version__),
                        numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__)
        require(versions == reference.TRAINING_VERSIONS, "Changed inference software; use the retained fitting environment")
        roots = dict(cap32=REPO / "model_elgin/outputs/context_reference_v1/cv", cap128=REPO / "model_elgin/outputs/read_cap_v1/cv")
        hashes = {name: {} for name in roots}
        models = {name: SAVED.load_mode(root, "none", hashes[name]) for name, root in roots.items()}
        reference.validate_pairs(models, roots, hashes)
        reference.validate_training_signatures(models, roots, hashes)
        recipe = models["cap128"]["recipe"]
        core_sources = reference.current_source_evidence(recipe)
        torch.set_num_threads(4)
        sources = {p.relative_to(REPO).as_posix(): SAVED.sha256(p) for p in
                   (Path(__file__), PLAN, Path(diagnostic.__file__), Path(reference.__file__), Path(SAVED.__file__))}
        identity = dict(study="threshold_v1", policy="inner_max_F1_tie_higher", final_rule="median_five_inner_cutoffs",
                        batch_size=64, threads=4, versions=versions, recipe=recipe, source_sha256=sources)
        immutable_json(output / "study_identity.json", identity)
        evidence = {os.path.relpath(roots[m] / name, REPO).replace("\\", "/"): digest for m in roots for name, digest in hashes[m].items()}
        evidence.update({name: values["raw_sha256"] for name, values in core_sources.items()})
        selected, outer, pooled, summaries, curves, round_records = [], [], [], [], [], []
        with diagnostic.Monitor() as measurement:
            cache_path = REPO.parent / "advanced_model/cache/data0"
            labels_path, folds_path = REPO.parent / "data0/data.info.labelled", REPO / "eda/received/shared_folds/data0_folds.csv"
            cache = fitting.Cache(cache_path)
            meta = fitting.align_metadata(cache, labels_path, folds_path)
            require(cache.source == recipe["identity"]["cache_manifest_sha256"] and
                    SAVED.sha256(labels_path) == recipe["identity"]["labels_sha256"], "Wrong fitted data0 inputs")
            for path in (labels_path, folds_path, cache_path / "manifest.json", *[cache_path / n for n in json.loads((cache_path / "manifest.json").read_text())["cache_sha256"]]):
                evidence[os.path.relpath(path, REPO).replace("\\", "/")] = SAVED.sha256(path)
            prediction = pd.read_csv(roots["cap128"] / "none/data0_oof.csv", float_precision="round_trip")
            oof = align_prediction(meta, prediction)
            y, folds = meta.label.to_numpy(), meta.fold_id.to_numpy()
            learned_calls = np.zeros(len(meta), dtype=bool)
            for fold in range(5):
                initial, inner, refit, assessment, audit = fitting.partition(meta, np.arange(len(meta)), fold)
                folder = roots["cap128"] / f"none/fold{fold}"
                require(json.loads((folder / "split_audit.json").read_text()) == audit, "Different inference partitions")
                complete = json.loads((folder / "inner/complete.json").read_text())
                history_path = folder / "inner/history.json"
                evidence[history_path.relative_to(REPO).as_posix()] = SAVED.sha256(history_path)
                history = json.loads(history_path.read_text())
                expected = next(r for r in history if r["epoch"] == complete["best_epoch"])
                directory = output / f"fold{fold}"
                directory.mkdir(exist_ok=True)
                model_path = folder / "inner/best.pt"
                round_identity = dict(study_identity_sha256=SAVED.sha256(output / "study_identity.json"),
                                      outer_fold=fold, inner_fold=(fold+1)%5, checkpoint_sha256=SAVED.sha256(model_path),
                                      initial_indices_sha256=fitting.index_hash(initial), inner_indices_sha256=fitting.index_hash(inner))
                receipt_path, scores_path = directory / "complete.json", directory / "inner_predictions.csv"
                reused = receipt_path.exists()
                if reused:
                    receipt = json.loads(receipt_path.read_text())
                    require(receipt["identity"] == round_identity and SAVED.sha256(scores_path) == receipt["predictions_sha256"], "Changed saved inference receipt")
                    inner_scores = align_prediction(meta.iloc[inner], pd.read_csv(scores_path, float_precision="round_trip"))
                else:
                    model, bundle = fitting.restore(model_path)
                    verify_bundle(bundle, recipe, complete, fitting.index_hash(initial))
                    require(all(torch.isfinite(v).all() for v in model.state_dict().values()), "Nonfinite saved weights")
                    began = time.perf_counter()
                    inner_scores = fitting.predict_cache(model, cache, inner, bundle["context_reference"], batch_size=64)
                    prediction_seconds = time.perf_counter()-began
                    fitting.write_predictions(scores_path, meta, inner, inner_scores)
                actual = SCORER.metrics(y[inner], inner_scores)
                metrics_close(actual, expected)
                choice, curve = select_threshold(y[inner], inner_scores)
                round_result = dict(identity=round_identity, predictions_sha256=SAVED.sha256(scores_path), choice=choice)
                if reused:
                    require(receipt["choice"] == choice, "Saved cutoff selection changed")
                else:
                    round_result["prediction_wall_seconds"] = prediction_seconds
                    SAVED.atomic_text(receipt_path, json.dumps(round_result, indent=2, allow_nan=False)+"\n")
                    receipt = round_result
                round_records.append(dict(outer_fold=fold, reused=reused, receipt_sha256=SAVED.sha256(receipt_path),
                                          predictions_sha256=SAVED.sha256(scores_path), prediction_wall_seconds=receipt["prediction_wall_seconds"]))
                selected.append(dict(outer_fold=fold, inner_fold=(fold+1)%5, inner_sites=len(inner), inner_positives=int(y[inner].sum()),
                                     cutoff=choice["cutoff"], inner_f1=choice["inner"]["f1"], inner_precision=choice["inner"]["precision"],
                                     inner_recall=choice["inner"]["recall"], checkpoint_epoch=complete["best_epoch"]))
                curves.extend(dict(outer_fold=fold, **r) for r in curve)
                learned_calls[assessment] = oof[assessment] >= choice["cutoff"]
                for policy, calls, cutoff in (("fixed_0.5", oof[assessment] >= .5, .5), ("inner_F1", learned_calls[assessment], choice["cutoff"])):
                    outer.append(dict(outer_fold=fold, policy=policy, cutoff=cutoff, **decisions(y[assessment], calls)))
                print(f"Outer fold{fold}: cutoff{choice['cutoff']:.9f}; inference {'reused' if reused else 'completed'}; outer decisions assessed", flush=True)
            for policy, calls in (("fixed_0.5", oof >= .5), ("inner_F1", learned_calls)):
                pooled.append(dict(summary="pooled_outer", policy=policy, **decisions(y, calls)))
                rows = [r for r in outer if r["policy"] == policy]
                for kind, ddof in (("mean_fold", None), ("sample_sd_fold", 1)):
                    summaries.append(dict(summary=kind, policy=policy, **{key: float(np.mean([r[key] for r in rows])) if ddof is None else float(np.std([r[key] for r in rows], ddof=ddof)) for key in ("precision", "recall", "f1", "specificity", "accuracy")}))
            expected_pooled = models["cap128"]["metrics"]["pooled"]
            metrics_close({k:v for k,v in pooled[0].items() if k in expected_pooled}, expected_pooled, tolerance=1e-12)
            coverage = []
            for name, low, high in diagnostic.COVERAGE:
                mask = meta.n_reads.ge(low).to_numpy() & (meta.n_reads.lt(high).to_numpy() if high else True)
                for policy, calls in (("fixed_0.5", oof >= .5), ("inner_F1", learned_calls)):
                    coverage.append(dict(coverage_bin=name, policy=policy, **decisions(y[mask], calls[mask])))
            outputs = []
            for name, rows in (("selected_cutoffs.csv", selected), ("outer_metrics.csv", outer), ("pooled_metrics.csv", pooled),
                               ("fold_summary.csv", summaries), ("coverage_decisions.csv", coverage), ("inner_selection_curves.csv", curves)):
                diagnostic.write_csv(output / name, rows); outputs.append(output / name)
            plot_results(output, selected, outer, curves)
            outputs.extend(output / name for name in ("cutoffs_and_outer_f1.png", "inner_selection_outer_tradeoff.png"))
            require(all(SAVED.sha256(REPO / name) == digest for name, digest in {**evidence, **sources}.items()), "Source/input changed during study")
        measurement.record["scope"] = "After saved-CV/source/version preflight: cache validation/loading, all required inner inference or receipt reuse, threshold/outer analysis and figures. Imports, initial preflight and final report/manifest writes excluded."
        report_path = output / "README.md"
        SAVED.atomic_text(report_path, report(selected, outer, pooled, summaries, measurement.record)); outputs.append(report_path)
        proposal_path = output / "final_cutoff_proposal.json"
        SAVED.atomic_text(proposal_path, json.dumps(dict(rule="median_five_training_side_cutoffs", cutoff=float(np.median([r["cutoff"] for r in selected])),
                          status="proposal_for_future_all_data0_fit_not_deployed", directly_evaluated_as_single_global_cutoff=False,
                          calibrated_probability=False), indent=2)+"\n"); outputs.append(proposal_path)
        manifest = dict(status="complete", no_neural_training=True, no_calibration=True, no_data1_access=True, versions=versions,
                        assessment="five_training_side_cutoffs_on_matching_excluded_outer_groups", final_rule="unevaluated median proposal",
                        n_sites=len(meta), n_positive_labels=int(y.sum()), n_genes=int(meta.gene_id.nunique()), rounds=round_records,
                        input_sha256=evidence, source_sha256=sources, frozen_core_sources=core_sources, measurements=measurement.record,
                        output_sha256={p.name: SAVED.sha256(p) for p in outputs})
        manifest_path = output / "analysis_manifest.json"
        SAVED.atomic_text(manifest_path, json.dumps(manifest, indent=2, allow_nan=False)+"\n")
        SAVED.atomic_text(status, json.dumps(dict(status="complete", manifest_sha256=SAVED.sha256(manifest_path)), indent=2)+"\n")
        print(json.dumps(dict(status="complete", measurements=measurement.record, median_cutoff_proposal=float(np.median([r["cutoff"] for r in selected])))))
        return 0
    except BaseException as error:
        SAVED.atomic_text(status, json.dumps(dict(status="failed_or_interrupted", error=str(error), older_outputs_non_authoritative=True), indent=2)+"\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
