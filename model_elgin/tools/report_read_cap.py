"""Compare complete saved cap32 and cap128 data0 CV evidence, without fitting.

Reads saved metrics, split audits, predictions' byte hashes and trusted artifacts'
byte hashes. It does not load labels, model weights, or run inference. The shared
scorer remains responsible for metrics. Failed/incomplete attempts are refused.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time

import numpy as np
import psutil

REPO = Path(__file__).resolve().parents[2]
BASELINE_CV = REPO / "model_elgin/outputs/context_reference_v1/cv"
CANDIDATE_CV = REPO / "model_elgin/outputs/read_cap_v1/cv"
RANKING = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")
DECISIONS = ("precision", "recall", "f1", "specificity", "accuracy")
COUNTS = ("tn", "fp", "fn", "tp")
NAMES = ("cap32", "cap128")
WRAPPER_KEY = "tools/train_read_cap.py"
PLAN_KEY = "READ_CAP_EXPERIMENT.md"
PROVENANCE = {"training_entrypoint_sha256": WRAPPER_KEY,
              "experiment_plan_sha256": PLAN_KEY}
# Exact package strings recorded in the original fit-signature contract. The
# signature check below binds all saved fits to this same declared environment;
# no Torch import or model deserialisation is needed to reproduce the digest.
TRAINING_VERSIONS = dict(python="3.12.14", torch="2.14.1+cpu", numpy="2.5.3",
                         pandas="3.0.6", sklearn="1.9.1")
RECOVERED_RESOURCE_KIND = "recovered_checkpoint_snapshot_lower_bound"
SPEC = importlib.util.spec_from_file_location("saved_cv_summary", Path(__file__).with_name("summarize_context_cv.py"))
SAVED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAVED)
require = SAVED.require
sha256 = SAVED.sha256


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def atomic_text(path, text):
    """Keep temporary names short enough for Windows and replace atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".cap_", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def powershell_argument(value):
    """Literal single-quoted PowerShell argument, including embedded apostrophes."""
    return "'" + str(value).replace("'", "''") + "'"


class Monitor:
    """Small reporter-only resource monitor; does not include fitting again."""
    def __enter__(self):
        self.wall = time.perf_counter()
        self.cpu = time.process_time()
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.errors = 0
        self.stop = threading.Event()

        def sample():
            while not self.stop.wait(.2):
                try:
                    self.peak = max(self.peak, self.process.memory_info().rss)
                except psutil.Error:
                    self.errors += 1
        self.worker = threading.Thread(target=sample, daemon=True)
        self.worker.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.worker.join()
        try:
            self.peak = max(self.peak, self.process.memory_info().rss)
        except psutil.Error:
            self.errors += 1
        self.record = dict(wall_seconds=time.perf_counter() - self.wall,
                           process_cpu_seconds=time.process_time() - self.cpu,
                           sampled_peak_process_rss_mib=self.peak / 1024**2,
                           sampling_interval_seconds=.2, sampling_errors=self.errors,
                           scope="Reporter after imports: saved-evidence validation, tables, figures and report construction; final report/manifest writes excluded.")


def validate_recipes(baseline, candidate):
    """Allow precisely the planned cap change and recorded wrapper provenance."""
    require(baseline["smoke"] is False and candidate["smoke"] is False,
            "Only full CV recipes may be compared")
    a_config, b_config = baseline["config"], candidate["config"]
    require(type(a_config["cap"]) is int and a_config["cap"] == 32
            and type(b_config["cap"]) is int and b_config["cap"] == 128,
            "Expected the prespecified training cap32 to cap128 comparison")
    require({k: v for k, v in a_config.items() if k != "cap"} ==
            {k: v for k, v in b_config.items() if k != "cap"},
            "Model settings changed beyond the training read cap")
    require(a_config["context_mode"] == "none", "Original features are required")
    require({k: v for k, v in baseline.items() if k not in ("config", "identity")} ==
            {k: v for k, v in candidate.items() if k not in ("config", "identity")},
            "Training recipe, seeds, grouping, or population changed")
    expected = dict(max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4)
    require(all(baseline[k] == value for k, value in expected.items()),
            "Recipe differs from the fixed original control")
    a_id, b_id = baseline["identity"], candidate["identity"]
    require(set(b_id) == set(a_id) | set(PROVENANCE), "Unexpected identity additions/removals")
    require(not set(a_id) & set(PROVENANCE), "Control already contains candidate provenance")
    require({k: v for k, v in a_id.items() if k != "source_sha256"} ==
            {k: v for k, v in b_id.items() if k not in (*PROVENANCE, "source_sha256")},
            "Data, labels, cache or shared-fold identity changed")
    a_sources, b_sources = a_id["source_sha256"], b_id["source_sha256"]
    require(set(b_sources) == set(a_sources) | set(PROVENANCE.values()),
            "Unexpected source-map additions/removals")
    require(all(b_sources[k] == v for k, v in a_sources.items()), "Frozen production source changed")
    for identity_key, source_key in PROVENANCE.items():
        value = b_id[identity_key]
        require(isinstance(value, str) and len(value) == 64 and
                all(c in "0123456789abcdef" for c in value), "Invalid wrapper/plan SHA256")
        require(value == b_sources[source_key], "Wrapper/plan identity hash differs from source map")


def current_source_evidence(recipe):
    """Check canonical LF fingerprints against current frozen source and plan."""
    evidence = {}
    for name, expected in recipe["identity"]["source_sha256"].items():
        path = (REPO / name if name == "model_evaluation/evaluate.py" else
                REPO / "model_elgin" / name if name in PROVENANCE.values() else
                REPO / "model_elgin/context_reference_v1" / name)
        actual = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        require(actual == expected, f"Current canonical source differs from saved recipe: {name}")
        evidence[path.relative_to(REPO).as_posix()] = dict(raw_sha256=sha256(path), canonical_lf_sha256=actual)
    return evidence


def validate_pairs(data, roots, evidence):
    validate_recipes(data["cap32"]["recipe"], data["cap128"]["recipe"])
    require(data["cap32"]["metrics"]["versions"] == data["cap128"]["metrics"]["versions"],
            "Scorer package versions differ")
    for fold in range(5):
        for key in ("n_sites", "n_positives", "positive_fraction"):
            require(data["cap32"]["rows"][fold][key] == data["cap128"]["rows"][fold][key],
                    "Different outer assessment population")
        audits = [SAVED.read_json(roots[name] / f"none/fold{fold}/split_audit.json",
                                  evidence[name], roots[name]) for name in NAMES]
        require(audits[0] == audits[1], "Gene lists, inner/outer split boundaries or index hashes changed")
        populations = audits[0]["populations"]
        genes = {}
        for name in ("initial_fit", "inner_validation", "refit", "assessment"):
            names = populations[name]["genes"]
            require(isinstance(names, list) and bool(names) and all(isinstance(gene, str) and gene for gene in names)
                    and len(set(names)) == len(names), "Invalid or duplicate genes in split audit")
            genes[name] = set(names)
        require(not genes["initial_fit"] & genes["inner_validation"]
                and not genes["refit"] & genes["assessment"]
                and genes["refit"] == genes["initial_fit"] | genes["inner_validation"],
                "Gene sets do not respect inner/refit/assessment boundaries")


def validate_training_signatures(data, roots, evidence):
    """Reconstruct original run_fit digests, including the same library versions."""
    for name in NAMES:
        recipe = data[name]["recipe"]
        versions = data[name]["metrics"]["versions"]
        require(versions == dict(python=TRAINING_VERSIONS["python"], numpy=TRAINING_VERSIONS["numpy"],
                                 scikit_learn=TRAINING_VERSIONS["sklearn"]),
                "Scorer versions do not match the fixed training environment")
        for fold in range(5):
            audit = SAVED.read_json(roots[name] / f"none/fold{fold}/split_audit.json", evidence[name], roots[name])
            for stage, population in (("inner", "initial_fit"), ("refit", "refit")):
                complete = SAVED.read_json(roots[name] / f"none/fold{fold}/{stage}/complete.json", evidence[name], roots[name])
                expected = dict(config=recipe["config"], seed=recipe["seed"] + fold + (100 if stage == "refit" else 0),
                                max_epochs=recipe["max_epochs"] if stage == "inner" else data[name]["selected_epochs"][fold],
                                patience=recipe["patience"], batch_size=recipe["batch_size"],
                                stage="cv_" + stage, identity=recipe["identity"], threads=recipe["threads"],
                                versions=TRAINING_VERSIONS,
                                fitting=audit["populations"][population]["indices_sha256"],
                                validation=audit["populations"]["inner_validation"]["indices_sha256"] if stage == "inner" else None)
                require(complete["signature"] == fingerprint(expected),
                        f"Saved fit signature differs from exact recipe/environment: {name}/fold{fold}/{stage}")


def attach_resource_provenance(data, roots, evidence):
    """Retain recovery disclosures dropped by the legacy saved-results loader.

    This reads JSON metadata only. A recovered checkpoint fingerprint identifies
    the preserved source of a snapshot; no checkpoint is deserialised here.
    """
    for name in NAMES:
        snapshots = set()
        for row in data[name]["resources"]:
            relative = row["invocation"]
            before = evidence[name].get(relative)
            require(before is not None, "Resource invocation was not validated by the saved-results loader")
            raw = SAVED.read_json(roots[name] / relative, evidence[name], roots[name])
            require(evidence[name][relative] == before, "Resource invocation changed after validation")
            require(raw["status"] == row["status"] and SAVED.resource_record(raw["resources"]) ==
                    {key: row[key] for key in SAVED.resource_record(raw["resources"])},
                    "Resource numbers/status changed after validation")
            kind = raw.get("record_kind", "measured_invocation")
            require(kind in ("measured_invocation", RECOVERED_RESOURCE_KIND), "Unknown resource record kind")
            row.update(record_kind=kind, checkpoint_sha256="", checkpoint_epoch="", resource_snapshot_index="",
                       original_exit_receipt_absent=False, excludes_unfinished_work=False)
            if kind == RECOVERED_RESOURCE_KIND:
                digest = raw["checkpoint_sha256"]
                require(isinstance(digest, str) and len(digest) == 64 and
                        all(char in "0123456789abcdef" for char in digest), "Invalid recovered checkpoint SHA256")
                SAVED.integer(raw["checkpoint_epoch"], "recovered checkpoint epoch", minimum=1)
                SAVED.integer(raw["resource_snapshot_index"], "recovered resource snapshot index")
                require(raw["status"] == "interrupted_or_failed" and
                        raw["original_exit_receipt_absent"] is True and raw["excludes_unfinished_work"] is True,
                        "Recovered snapshot must disclose an absent exit receipt and omitted unfinished work")
                identity = (row["fold_id"], row["fit_stage"], digest, raw["resource_snapshot_index"])
                require(identity not in snapshots, "Duplicate recovered checkpoint resource snapshot")
                snapshots.add(identity)
                row.update({key: raw[key] for key in ("checkpoint_sha256", "checkpoint_epoch", "resource_snapshot_index",
                            "original_exit_receipt_absent", "excludes_unfinished_work")})


def resource_accounting(rows):
    recovered = [dict(row) for row in rows if row.get("record_kind") == RECOVERED_RESOURCE_KIND]
    return dict(recovered_snapshot_count=len(recovered),
                recorded_fitting_totals_include_lower_bounds=bool(recovered),
                recovered_checkpoint_snapshots=recovered,
                disclosure=("Recorded fitting totals include recovered checkpoint snapshot lower bounds. "
                            "Unmeasured work after the identified checkpoint epochs and before interruption is omitted. "
                            "Each recovered snapshot and each resumed invocation is counted once; "
                            "complete.json cumulative snapshots are not added again."
                            if recovered else "No recovered checkpoint lower-bound snapshots were found; totals include the retained per-fit invocation records only."))


def calculate_tables(data):
    metrics = []
    for name in NAMES:
        for row in data[name]["rows"]:
            metrics.append(dict(model=name, evidence="fold", selected_epochs=data[name]["selected_epochs"][row["fold_id"]], **row))
        for evidence, key in (("mean_fold", "mean_fold"), ("sample_sd_fold_ddof1", "sample_sd_fold_ddof1"), ("pooled_oof", "pooled")):
            metrics.append(dict(model=name, evidence=evidence, **data[name]["metrics"][key]))
    paired = []
    for fold in range(5):
        row = dict(fold_id=fold, n_sites=data["cap32"]["rows"][fold]["n_sites"],
                   n_positives=data["cap32"]["rows"][fold]["n_positives"],
                   cap32_selected_epochs=data["cap32"]["selected_epochs"][fold],
                   cap128_selected_epochs=data["cap128"]["selected_epochs"][fold])
        for key in RANKING:
            row["cap32_" + key] = data["cap32"]["rows"][fold][key]
            row["cap128_" + key] = data["cap128"]["rows"][fold][key]
            row["delta_" + key] = row["cap128_" + key] - row["cap32_" + key]
        paired.append(row)
    paired_summary = []
    for key in RANKING:
        values = np.asarray([r["delta_" + key] for r in paired], dtype=float)
        paired_summary.append(dict(metric=key, candidate_minus_control_mean=float(values.mean()),
                                   sample_sd_paired_delta_ddof1=float(values.std(ddof=1)),
                                   min_paired_delta=float(values.min()), max_paired_delta=float(values.max()),
                                   positive_fold_deltas=int((values > 0).sum()),
                                   negative_fold_deltas=int((values < 0).sum()), zero_fold_deltas=int((values == 0).sum())))
    resources = []
    for name in NAMES:
        seen = set()
        for row in data[name]["resources"]:
            require(row["invocation"] not in seen, "Duplicate per-fit resource invocation")
            seen.add(row["invocation"])
            resources.append(dict(model=name, **row))
    return dict(metrics=metrics, paired=paired, paired_summary=paired_summary, resources=resources)


def plot_tables(data, tables, output):
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    files = []
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    x = np.arange(5)
    for name, color in (("cap32", "#325c94"), ("cap128", "#bd5c35")):
        values = [row["selection_score"] for row in data[name]["rows"]]
        axes[0].plot(x, values, marker="o", color=color, label=name)
    axes[0].set(xticks=x, xlabel="Outer gene fold", ylabel="S = (ROC AUC + trapezoidal PR AUC) / 2",
                title="Full data0 development: paired folds")
    axes[0].legend()
    values = [row["delta_selection_score"] for row in tables["paired"]]
    axes[1].bar(x, values, color=["#bd5c35" if v > 0 else "#325c94" for v in values])
    axes[1].axhline(0, color="black", linewidth=.8)
    axes[1].set(xticks=x, xlabel="Outer gene fold", ylabel="Cap128 minus cap32 S",
                title="Paired differences (descriptive)")
    figure.tight_layout()
    files.append(save_figure(figure, output / "paired_fold_scores.png", plt))
    figure, ax = plt.subplots(figsize=(7.3, 4.5))
    keys = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")
    x = np.arange(len(keys))
    for offset, name, color in ((-.18, "cap32", "#325c94"), (.18, "cap128", "#bd5c35")):
        ax.bar(x + offset, [data[name]["metrics"]["mean_fold"][key] for key in keys],
               width=.36, label=name, color=color)
    ax.set(xticks=x, xticklabels=["ROC AUC", "PR AUC\n(trapezoidal)", "AP", "S"],
           ylim=(0, 1), ylabel="Unweighted mean over five outer folds",
           title="Matched data0 development comparison")
    ax.legend()
    figure.tight_layout()
    files.append(save_figure(figure, output / "mean_ranking_metrics.png", plt))
    return files


def save_figure(figure, path, plt):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".cap_", suffix=".png", delete=False) as handle:
            temporary = Path(handle.name)
        figure.savefig(temporary, format="png", dpi=160, bbox_inches="tight")
        os.replace(temporary, path)
    finally:
        plt.close(figure)
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def report_text(data, tables, command):
    delta = next(row for row in tables["paired_summary"] if row["metric"] == "selection_score")
    difference = delta["candidate_minus_control_mean"]
    if abs(difference) <= 1e-12:
        verdict = "The measured mean S is equal within the reporting tolerance (1e-12)."
    else:
        verdict = f"**{'Cap128' if difference > 0 else 'Cap32'} has the higher measured mean data0 development score.**"
    lines = ["# Training read-cap comparison", "", verdict, "",
             f"Cap128 minus cap32 mean S: **{difference:+.10f}**. All completed outcomes are retained, including negative changes. This is a bounded architecture-development experiment, not proof of universal superiority.", "",
             "This report checks completed saved five-fold results, split audits, prediction/artifact byte hashes and resource records. It does not read labels, load weights, fit a model, run inference, or evaluate data1. The figures and tables cover all 121,838 data0 sites and 5,475 positive site labels.", "",
             "## Ranking metrics", "", "The primary criterion is the unweighted mean of five fold-level S values, where S = (ROC AUC + trapezoidal PR AUC) / 2. Average precision (AP) is separate from trapezoidal PR AUC. Pooled OOF values are supplementary.", "",
             "| Training cap | Summary | ROC AUC | Trapezoidal PR AUC | AP | S |",
             "|---|---|---:|---:|---:|---:|"]
    for name in NAMES:
        for label, key in (("Mean fold", "mean_fold"), ("Sample SD, ddof=1", "sample_sd_fold_ddof1"), ("Pooled OOF", "pooled")):
            lines.append(f"| {name} | {label} | " + " | ".join(f"{data[name]['metrics'][key][metric]:.10f}" for metric in RANKING) + " |")
    lines += ["", "## Paired changes", "", "| Metric | Mean cap128−cap32 | Sample SD of paired changes | Folds higher / lower / equal |", "|---|---:|---:|---|"]
    for row in tables["paired_summary"]:
        lines.append(f"| {row['metric']} | {row['candidate_minus_control_mean']:+.10f} | {row['sample_sd_paired_delta_ddof1']:.10f} | {row['positive_fold_deltas']} / {row['negative_fold_deltas']} / {row['zero_fold_deltas']} |")
    lines += ["", "| Outer fold | Cap32 S | Cap128 S | Difference | Selected epochs: cap32 / cap128 |", "|---|---:|---:|---:|---|"]
    for row in tables["paired"]:
        lines.append(f"| {row['fold_id']} | {row['cap32_selection_score']:.10f} | {row['cap128_selection_score']:.10f} | {row['delta_selection_score']:+.10f} | {row['cap32_selected_epochs']} / {row['cap128_selected_epochs']} |")
    lines += ["", "## Decisions at the fixed 0.5 reporting cutoff", "",
              "This cutoff has not been validated or selected here. These are pooled OOF confusion counts and their derived metrics, not averages of counts. Scores remain continuous, and the positive-weighted training loss does not establish probability calibration.", "",
              "| Training cap | TN | FP | FN | TP | Precision | Recall | F1 | Specificity | Accuracy |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in NAMES:
        row = data[name]["metrics"]["pooled"]
        lines.append(f"| {name} | " + " | ".join(str(row[k]) for k in COUNTS) + " | " + " | ".join(f"{row[k]:.8f}" for k in DECISIONS) + " |")
    recipe = data["cap32"]["recipe"]
    lines += ["", "## Controlled model change and gene separation", "",
              "The sequence-aware read network uses a seven-base embedding, an attention-pooled bag of nine-feature reads, and 63 all-read site summaries. Only the maximum sampled reads per training site changes from 32 to 128. Sites with fewer reads retain all their reads; no sites are dropped or relabelled. Summaries, validation and assessment still use all reads. The model receives site labels, not true labels for individual reads.", "",
              f"Both recipes preserve width {recipe['config']['width']}, dropout {recipe['config']['dropout']}, learning rate {recipe['config']['lr']}, weight decay {recipe['config']['weight_decay']}, positive loss weight {recipe['config']['pos_weight']}, seed {recipe['seed']}, batch size {recipe['batch_size']}, {recipe['threads']} CPU threads, maximum {recipe['max_epochs']} inner epochs and patience {recipe['patience']}.", "",
              "The same immutable five gene groups are used in both runs. For assessment fold f, inner validation is (f+1)%5: fit the other three groups, select the duration on the inner group, start fresh weights and refit the four non-assessment groups for that duration, then assess f. Fitted normalisation and references stay inside the fitting boundary. Selected durations may differ because each candidate follows the same inner-selection rule. Existing original-control fits are reused as matched evidence; the reporter does not retrain them.", "",
              "Every saved fitting signature was reconstructed using the exact original recipe and the same declared training library versions: `" + json.dumps(TRAINING_VERSIONS, sort_keys=True) + "`. This checks retained metadata against its digest without loading weights; it does not independently replay training.", "",
              "## Measured computation", "", "| Training cap | Completed fits | Resource records | Interrupted/failed records | Recovered lower-bound snapshots | Recorded fitting wall seconds | Recorded process CPU seconds | Largest sampled process-tree RSS MiB |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in NAMES:
        rows = [row for row in tables["resources"] if row["model"] == name]
        lines.append(f"| {name} | 10 | {len(rows)} | {sum(row['status'] != 'complete' for row in rows)} | {sum(row.get('record_kind') == RECOVERED_RESOURCE_KIND for row in rows)} | {sum(row['wall_seconds'] for row in rows):.3f} | {sum(row['cpu_seconds'] for row in rows):.3f} | {max(row['sampled_peak_process_tree_rss_mib'] for row in rows):.3f} |")
    accounting = resource_accounting(tables["resources"])
    if accounting["recovered_snapshot_count"]:
        lines += ["", "**These recorded fitting totals contain lower bounds.** " + accounting["disclosure"], ""]
        for row in accounting["recovered_checkpoint_snapshots"]:
            lines.append(f"- {row['model']}, outer fold {row['fold_id']} {row['fit_stage']}: recovered the snapshot through checkpoint epoch {row['checkpoint_epoch']} (snapshot index {row['resource_snapshot_index']}; checkpoint SHA256 `{row['checkpoint_sha256']}`). Its original exit receipt is absent. The retained snapshot contributes {row['wall_seconds']:.9f} wall seconds and {row['cpu_seconds']:.9f} process CPU seconds once. Unmeasured work after epoch {row['checkpoint_epoch']} and before the pause is omitted; subsequent resumed invocation records are included separately.")
    lines += ["", "Each per-fit invocation is counted once, including recorded interrupted attempts. A recovered checkpoint snapshot replaces an absent original exit receipt as a disclosed lower bound; it is not a second measurement of a resumed invocation. Cumulative checkpoint/complete.json resource snapshots are not added again. Wall sums measure retained fitting work, rather than end-to-end elapsed time; imports, startup, cache hashing, outer predictions and orchestration outside fit timers are excluded. Memory is the largest retained sampled process-tree RSS, not an additive or exact operating-system peak; any unmeasured peak during omitted work is unknown. Missing unrecorded failures cannot be reconstructed. Sampling intervals/errors, record kinds and checkpoint provenance are retained in resources.csv; reporter resources and the recovery disclosure are separate in the manifest.", "",
              "## Limits and remaining work", "",
              "- Five fold differences share overlapping training data. Their sample SD is descriptive, not a confidence interval or five independent biological experiments. One training seed does not establish seed stability or statistical significance.",
              "- Repeated data0 development and a previously selected architecture limit generalisation claims. Saved hashes and audits corroborate provenance; this reporter is not an independent replay of training or label-based re-evaluation.",
              "- The earlier high-coverage error review motivates this experiment, but these overall results alone do not establish improved high-coverage performance or a biological explanation. No subgroup analysis is silently inferred here.",
              "- No new all-data0 final model, data1 transfer result, validated call threshold, calibrated probability, required published m6Anet benchmark, or genuine SG-NEx prediction is produced by this comparison. data1 has already been exposed and remains outside tuning. This report does not declare a final winner against Samuel's model.", "",
              "## Exact comparison command", "", "Run from the repository root after candidate five-fold CV completes:", "", "```powershell", command, "```", "",
              "The exact executed training arguments and logs remain with each CV run. comparison_manifest.json records roots, exact reporter arguments, source fingerprints and all validated input/output hashes. This tool preserves every saved result rather than altering a score to meet a preferred outcome.", "",
              "![Paired fold scores](paired_fold_scores.png)", "", "![Mean ranking metrics](mean_ranking_metrics.png)", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-cv", type=Path, default=BASELINE_CV)
    parser.add_argument("--candidate-cv", type=Path, default=CANDIDATE_CV)
    parser.add_argument("--output-dir", type=Path, default=CANDIDATE_CV.parent / "comparison")
    args = parser.parse_args(argv)
    roots = dict(cap32=args.baseline_cv.resolve(), cap128=args.candidate_cv.resolve())
    output = args.output_dir.resolve()
    require(roots["cap32"] != roots["cap128"], "Control and candidate CV roots must differ")
    require(all(not output.is_relative_to(path) and not path.is_relative_to(output) for path in roots.values()),
            "Output must not overwrite or contain either CV evidence tree")
    output.mkdir(parents=True, exist_ok=True)
    invocation = dict(working_directory=str(Path.cwd()), arguments=list(sys.argv[1:] if argv is None else argv),
                      baseline_cv=str(roots["cap32"]), candidate_cv=str(roots["cap128"]), output_dir=str(output))
    write_json(output / "analysis_status.json", dict(status="running", invocation=invocation))
    tool_hash, verifier_hash = sha256(__file__), sha256(SAVED.__file__)
    evidence = {name: {} for name in NAMES}
    written = []
    try:
        with Monitor() as monitor:
            data = {name: SAVED.load_mode(roots[name], "none", evidence[name]) for name in NAMES}
            validate_pairs(data, roots, evidence)
            validate_training_signatures(data, roots, evidence)
            attach_resource_provenance(data, roots, evidence)
            source_evidence = current_source_evidence(data["cap128"]["recipe"])
            tables = calculate_tables(data)
            require(all(sha256(roots[name] / rel) == digest for name in NAMES for rel, digest in evidence[name].items()),
                    "Saved evidence changed during comparison")
            fields = ["model", "evidence", "fold_id", "selected_epochs", "n_sites", "n_positives", *RANKING, "threshold", *COUNTS, *DECISIONS]
            for key, filename, csv_fields in (("metrics", "metrics.csv", fields),
                    ("paired", "paired_fold_deltas.csv", list(tables["paired"][0])),
                    ("paired_summary", "paired_delta_summary.csv", list(tables["paired_summary"][0])),
                    ("resources", "resources.csv", list(tables["resources"][0]))):
                path = output / filename
                atomic_text(path, SAVED.csv_text(tables[key], csv_fields))
                written.append(path)
            written += plot_tables(data, tables, output)
            command = "../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_read_cap.py"
            if argv or sys.argv[1:]:
                command += " " + " ".join(powershell_argument(part) for part in invocation["arguments"])
            report = report_text(data, tables, command)
            require(all(sha256(roots[name] / rel) == digest for name in NAMES for rel, digest in evidence[name].items()),
                    "Saved evidence changed while generating the report")
            require(source_evidence == current_source_evidence(data["cap128"]["recipe"])
                    and sha256(__file__) == tool_hash and sha256(SAVED.__file__) == verifier_hash,
                    "Reporter, verifier or training source changed during reporting")
        atomic_text(output / "comparison.md", report)
        written.append(output / "comparison.md")
        manifest = dict(status="complete", scope="Saved full-population data0 cap32 versus cap128 gene-grouped CV development comparison only",
                        reads_labels=False, reads_data1=False, loads_model_weights=False, performs_fitting_or_inference=False,
                        invocation=invocation, reporter_resources=monitor.record,
                        paired_delta_summary=tables["paired_summary"], input_sha256=evidence,
                        fitting_resource_accounting=resource_accounting(tables["resources"]),
                        current_training_source_evidence=source_evidence,
                        output_sha256={path.name: sha256(path) for path in written},
                        reporter_sha256=tool_hash, saved_verifier_sha256=verifier_hash,
                        fit_signature_training_versions=TRAINING_VERSIONS,
                        reporter_versions=dict(python=platform.python_version(), numpy=np.__version__, psutil=psutil.__version__))
        manifest["signature"] = fingerprint(manifest)
        write_json(output / "comparison_manifest.json", manifest)
        write_json(output / "analysis_status.json", dict(status="complete", invocation=invocation,
                    comparison_manifest_sha256=sha256(output / "comparison_manifest.json")))
    except Exception as error:
        write_json(output / "analysis_status.json", dict(status="failed", invocation=invocation,
                    error_type=type(error).__name__, error=str(error),
                    existing_outputs_are_authoritative=False))
        print(f"Comparison refused: {error}. Any older output is not current; see analysis_status.json.", file=sys.stderr)
        return 2
    print(f"Saved verified comparison: {output / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
