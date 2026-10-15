"""Build the final evidence report only from completed, fingerprinted outputs.

This script never trains, opens dataset labels, or changes the saved predictor.
Missing/inconsistent required evidence raises an error before results.md exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shlex
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RANKING = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")
TITLES = ("ROC AUC", "Trapezoidal PR AUC", "AP", "Selection score")
LIGHTGBM = {
    "roc_auc": .818, "pr_auc_trapezoid": .362, "average_precision": .362,
    "selection_score": .590, "tn": 83355, "fp": 862, "fn": 5360, "tp": 1233,
}
LIGHTGBM.update(
    precision=1233/(1233+862), recall=1233/(1233+5360),
    f1=2*1233/(2*1233+862+5360), specificity=83355/(83355+862),
)
LIGHTGBM_CV = {"roc_auc": .910, "pr_auc_trapezoid": .443,
               "average_precision": .444, "selection_score": (.910+.443)/2}


def read_json(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Required evidence missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8*1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_text(path, text):
    path = Path(path)
    temporary = path.with_name(path.name+".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def number(value, digits=8):
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{float(value):.{digits}f}"


def link(path, base=ROOT):
    path = Path(path).resolve()
    target = os.path.relpath(path, base.resolve()).replace("\\", "/")
    return f"[{path.name}]({target})"


def metric_table(rows):
    lines = ["| Evidence stage | ROC AUC | Trapezoidal PR AUC | AP | Selection score |",
             "|---|---:|---:|---:|---:|"]
    for label, values in rows:
        lines.append("| "+label+" | "+" | ".join(number(values.get(k)) for k in RANKING)+" |")
    return "\n".join(lines)


def validate_cv(report, location):
    folds = report.get("folds", [])
    if len(folds) != 5 or sorted(r["fold_id"] for r in folds) != list(range(5)):
        raise ValueError(f"Expected five complete shared folds: {location}")
    for metric in RANKING:
        values = [float(r[metric]) for r in folds]
        if any(not math.isfinite(v) for v in values):
            raise ValueError(f"Nonfinite CV metric: {location}")
        if not math.isclose(statistics.mean(values), report["mean"][metric], abs_tol=1e-12):
            raise ValueError(f"CV mean differs from fold arithmetic: {location}")
        if not math.isclose(statistics.stdev(values), report["sample_sd"][metric], abs_tol=1e-12):
            raise ValueError(f"CV sample SD differs from fold arithmetic: {location}")
    if sum(r["n_sites"] for r in folds) != report["pooled_oof"]["n_sites"]:
        raise ValueError(f"OOF/fold counts differ: {location}")


def validate_predictions(path, manifest, model_hash):
    if manifest.get("status") != "complete" or manifest["model_sha256"] != model_hash:
        raise ValueError(f"Prediction is not from the same frozen final model: {path}")
    if manifest["output_sha256"] != sha256(path) or not manifest.get("exact_input_key_coverage"):
        raise ValueError(f"Prediction hash/coverage evidence differs: {path}")
    seen = set()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["transcript_id", "transcript_position", "score"]:
            raise ValueError(f"Wrong prediction header: {path}")
        for row in reader:
            key = row["transcript_id"], int(row["transcript_position"])
            p = float(row["score"])
            if not key[0] or key in seen or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError(f"Invalid prediction row: {path}")
            seen.add(key)
    if len(seen) != manifest["n_sites"]:
        raise ValueError(f"Prediction row count differs: {path}")


def parallel_worker_evidence(runs, cvs):
    """Audit completed disjoint worker ownership; these workers do no scoring."""
    records, ownership = [], set()
    configs = {cv["config"]["id"]: cv["config"] for cv in cvs}
    for path in sorted(runs.glob("worker_*.json")):
        record = read_json(path)
        candidate = record.get("candidate", record.get("config", {}).get("id"))
        folds = record.get("folds", [])
        if record.get("status") != "complete" or candidate not in configs \
                or not folds or len(set(folds)) != len(folds) \
                or any(type(f) is not int or f not in range(5) for f in folds):
            raise ValueError("Incomplete/invalid parallel CV worker: "+str(path))
        if "config" in record and record["config"] != configs[candidate]:
            raise ValueError("Worker configuration differs from finalist: "+str(path))
        started, finished = record.get("started_unix"), record.get("finished_unix")
        if not isinstance(started, (int, float)) or not isinstance(finished, (int, float)) \
                or not math.isfinite(started) or not math.isfinite(finished) or finished < started:
            raise ValueError("Missing/invalid worker timestamps: "+str(path))
        if not isinstance(record.get("command"), list) or not record["command"] \
                or not all(isinstance(arg, str) for arg in record["command"]):
            raise ValueError("Missing actual worker invocation arguments: "+str(path))
        if record.get("worker_source_sha256") != sha256(ROOT/"cv_worker.py"):
            raise ValueError("Worker source changed after recorded execution: "+str(path))
        if not record.get("resources"):
            raise ValueError("Worker measurement missing: "+str(path))
        for fold in folds:
            key = candidate, fold
            if key in ownership:
                raise ValueError("Parallel workers overlap candidate/fold ownership: "+str(key))
            ownership.add(key)
        records.append((path, record))
    if records and ownership != {(candidate, f) for candidate in configs for f in range(5)}:
        raise ValueError("Recorded parallel workers do not cover every finalist/shared fold")
    return records


def parallel_worker_summary(records):
    if not records:
        return "No parallel worker record exists; no parallel-stage elapsed measurement is claimed."
    started = min(record["started_unix"] for _, record in records)
    finished = max(record["finished_unix"] for _, record in records)
    lines = [f"Recorded parallel CV fit-stage span: **{finished-started:.3f} seconds**, calculated as latest worker finish minus earliest worker start, from **{len(records)}** disjoint worker records. This is the measured calendar span of this stage, including launch gaps and the pause in agent coordination caused by the account usage limit. Local Python workers continued during that pause; the three remaining fits were launched after the user's continuation. This span is not an uninterrupted hardware speed benchmark. It excludes subsequent `train.py --phase cv` holdout inference/aggregation and final fitting.", "",
             "| Worker evidence | Candidate | Shared folds owned | PID | Recorded start-to-finish seconds | Timer wall seconds | Timer CPU seconds | Individual sampled RSS MiB |",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for path, record in records:
        resource = record["resources"]
        lines.append(f"| {link(path)} | {record.get('candidate', record.get('config', {}).get('id'))} | "
                     f"{', '.join(map(str, record['folds']))} | {record['pid']} | "
                     f"{record['finished_unix']-record['started_unix']:.3f} | {resource['wall_seconds']:.3f} | "
                     f"{resource['cpu_seconds']:.3f} | {resource['sampled_peak_process_tree_rss_mib']:.3f} |")
    lines += ["", "Worker resource timers begin after cache/input checks; their timestamp spans include those checks. They overlap saved fit components and whole-worker invocation timers. Worker wall durations sum to cumulative process work, not calendar completion time. Individual RSS peaks occurred at unknown times and must not be summed into a combined RAM peak."]
    return "\n".join(lines)


def resource_rows(runs, cvs, prediction_evidence, evaluations, audit, cache_dir, workers):
    rows = []

    def add(scope, path, record, index=0, additive=True):
        if not record:
            return
        rss = record.get("sampled_peak_process_tree_rss_mib")
        rss_scope = "sampled Python process tree"
        if rss is None and "sampled_peak_process_rss_bytes" in record:
            rss = record["sampled_peak_process_rss_bytes"]/(1024**2)
            rss_scope = "sampled preparation Python process only"
        rows.append({
            "scope": scope, "evidence_path": str(path.resolve()), "segment": index,
            "wall_seconds": record["wall_seconds"],
            "cpu_seconds": record.get("cpu_seconds", record.get("process_cpu_seconds")),
            "sampled_peak_rss_mib": rss,
            "memory_scope": rss_scope, "additive_component": additive,
        })

    add("data0_cache_preparation", cache_dir/"audit.json", audit["measurements"])
    for path in sorted(runs.rglob("complete.json")):
        evidence = read_json(path)
        name = path.parent.name
        scope = ("screen_training" if name.startswith("screen_") else
                 "repeat_seed_training" if name.startswith("repeat_") else
                 "outer_inner_epoch_selection" if name.endswith("_inner") else
                 "outer_training_refit" if name.endswith("_refit") else
                 "final_all_data0_fit" if name == "final_fit" else "other_completed_fit")
        resources = evidence.get("resources", [])
        if isinstance(resources, dict):
            resources = [resources]
        for index, record in enumerate(resources):
            add(scope, path, record, index)
    for cv in cvs:
        config = cv["config"]["id"]
        for fold in cv["folds"]:
            add("outer_holdout_inference", runs/config/"cv_metrics.json",
                fold.get("inference_resources"), fold["fold_id"])
    for index, (path, manifest) in enumerate(prediction_evidence):
        add(f"raw_data{index}_prediction", path.with_suffix(".csv.manifest.json"), manifest.get("resources"))
    for stage, (path, evidence) in evaluations.items():
        add(f"evaluate_{stage}", path, evidence.get("resources"))
    diagnostic = ROOT/"diagnostics/diagnostics_manifest.json"
    if diagnostic.is_file():
        evidence = read_json(diagnostic)
        if evidence.get("status") == "complete":
            add("post_training_data0_diagnostics", diagnostic, evidence.get("resources"))
    # Whole trainer timers include and overlap the fit/inference components.
    # Keep their recorded overhead-inclusive totals separately, never add them.
    for path in sorted(runs.glob("trainer_invocation_*.json")):
        evidence = read_json(path)
        add("whole_trainer_invocation_"+evidence.get("status", "unknown"), path,
            evidence.get("resources"), additive=False)
    for path, evidence in workers:
        add("parallel_worker_fit_stage", path, evidence.get("resources"), additive=False)
    return rows


def save_costs(rows, target):
    temporary = target.with_name(target.name+".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, target)


def cost_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row["additive_component"]:
            grouped[row["scope"]].append(row)
    lines = ["| Measured scope | Components | Cumulative component wall seconds | CPU seconds | Largest individual sampled RSS MiB |",
             "|---|---:|---:|---:|---:|"]
    for scope, components in grouped.items():
        cpu_values = [r["cpu_seconds"] for r in components]
        rss_values = [r["sampled_peak_rss_mib"] for r in components if r["sampled_peak_rss_mib"] is not None]
        lines.append(f"| {scope} | {len(components)} | "
                     f"{sum(r['wall_seconds'] for r in components):.3f} | "
                     f"{sum(cpu_values):.3f} | "
                     f"{max(rss_values):.3f} |")
    components = [r for r in rows if r["additive_component"]]
    total = sum(r["wall_seconds"] for r in components)
    cpu = sum(r["cpu_seconds"] for r in components)
    lines.append(f"| Sum of recorded distinct component work | {len(components)} | {total:.3f} | {cpu:.3f} | — |")
    return "\n".join(lines)


def whole_trainer_summary(rows):
    records = [r for r in rows if r["scope"].startswith("whole_trainer_invocation_")]
    if not records:
        raise ValueError("Required whole-trainer invocation measurement missing")
    lines = ["| Separate overlapping whole-trainer scope | Invocation wall seconds | CPU seconds | Individual sampled process-tree RSS MiB |",
             "|---|---:|---:|---:|"]
    for row in records:
        lines.append(f"| {row['scope']} ({link(row['evidence_path'])}) | {row['wall_seconds']:.3f} | "
                     f"{row['cpu_seconds']:.3f} | {row['sampled_peak_rss_mib']:.3f} |")
    lines.append(f"| Cumulative saved invocation work, separate from components | "
                 f"{sum(r['wall_seconds'] for r in records):.3f} | "
                 f"{sum(r['cpu_seconds'] for r in records):.3f} | — |")
    return "\n".join(lines)


def plot_links(evaluations):
    sections = []
    for stage, (path, _) in evaluations.items():
        plots = [path.parent/name for name in ("roc_curve.png", "pr_curve.png", "confusion_matrix.png", "reliability.png")]
        available = [link(p) for p in plots if p.is_file()]
        if available:
            sections.append(f"- {stage}: "+", ".join(available))
    return "\n".join(sections) or "No evaluation plots found; figure generation remains pending."


def final_verification(model_hash):
    candidates = []
    for path in sorted((ROOT/"verification").glob("*.json")):
        evidence = read_json(path)
        checked = evidence.get("frozen_final_fresh_process", evidence.get("final_model_fresh_process", {}))
        if evidence.get("status") == "passed" and checked.get("status") == "passed" \
                and checked.get("model_sha256") == model_hash:
            candidates.append((path, evidence, checked))
    if not candidates:
        raise ValueError("Required passing fresh-process final-model verification is missing or has a different model fingerprint")
    path, evidence, checked = candidates[-1]
    for name, expected in evidence.get("source_sha256", {}).items():
        if (ROOT/name).is_file() and sha256(ROOT/name) != expected:
            raise ValueError("Final correctness verification refers to changed source: "+name)
    return path, evidence, checked


def diagnostic_section(runs):
    directory = ROOT/"diagnostics"
    path = directory/"diagnostics_manifest.json"
    if not path.is_file():
        return ["## Data0 diagnostic plots and read-sampling sensitivity", "",
                "Post-training diagnostics are pending; run plot_diagnostics.py after training. No sensitivity result is invented.", ""]
    record = read_json(path)
    if record.get("status") != "complete" or record.get("data1_or_data2_accessed") is not False \
            or record.get("training_or_tuning_performed") is not False:
        raise ValueError("Post-training diagnostic manifest is incomplete or has an invalid scope")
    if record["signature"]["frozen_specification_sha256"] != sha256(runs/"frozen_specification.json"):
        raise ValueError("Diagnostics refer to a different frozen specification")
    for name, expected in record["output_sha256"].items():
        if sha256(directory/name) != expected:
            raise ValueError("Diagnostic evidence fingerprint changed: "+name)
    robustness = read_json(directory/"read_sampling_robustness.json")
    coverage = read_json(directory/"oof_coverage_deciles.json")
    lines = ["## Data0 diagnostic plots and read-sampling sensitivity", "",
             "These completed supplementary analyses use data0 only and change no trained model, selected configuration, epoch count or final inference procedure.", "",
             "Plots: "+", ".join(link(directory/name) for name in (
                 "screen_learning_curves.png", "repeat_learning_curves.png", "cv_fold_scores.png",
                 "oof_coverage_deciles.png", "read_sampling_robustness.png"))+".", "",
             f"Saved selected **outer-fold0** model: all-read inference versus **{robustness['cap']}** uniformly sampled reads with seeds **{robustness['seeds']}**. Full-bag summaries are identical in every comparison. A mean of sampled probabilities is shown only as a diagnostic; it is not the saved final predictor. Read branch active: **{robustness['read_branch_active']}**.", "",
             metric_table([(r["inference"]+(f" seed{r['seed']}" if r.get("seed") is not None else ""), r)
                           for r in robustness["rows"]]), "",
             "| Sampling procedure | Mean absolute score change | Largest score change | Decisions differing at 0.5 |",
             "|---|---:|---:|---:|"]
    for row in robustness["rows"][1:]:
        name = row["inference"]+(f" seed{row['seed']}" if row.get("seed") is not None else "")
        lines.append(f"| {name} | {row['mean_absolute_probability_difference_from_all_reads']:.8f} | "
                     f"{row['max_absolute_probability_difference_from_all_reads']:.8f} | {row['decision_disagreements_at_0_5']:,} |")
    lines += ["", f"Across repeated samples, mean sitewise probability SD **{robustness['across_sample_probability_sd']['mean']:.8f}**, maximum **{robustness['across_sample_probability_sd']['max']:.8f}**. These are sensitivity measurements on one held-out fold, not independent performance uncertainty or a five-fold training-cap ablation. For a summary-only selected model the sampling branch is inactive and the comparison is expected to be identical by design; the actual equality check remains retained.", "",
              f"OOF coverage analysis produced **{coverage['bins_actual']}** quantile bins; equal coverage values were kept together. No sites were removed. Evidence: {link(directory/'oof_coverage_deciles.csv')}, {link(directory/'read_sampling_robustness.json')}, {link(path)}.", "",
              "| OOF coverage bin | Reads range | Sites | Positives | Positive fraction | ROC AUC | Trapezoidal PR AUC |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for row in coverage["rows"]:
        lines.append(f"| {row['coverage_bin']} | {row['min_reads']}–{row['max_reads']} | {row['n_sites']:,} | "
                     f"{row['n_positives']:,} | {row['positive_fraction']:.6f} | "
                     f"{number(row['roc_auc'])} | {number(row['pr_auc_trapezoid'])} |")
    lines += ["", "Coverage subgroup differences are descriptive. Their positive prevalence and gene/context composition differ, so this analysis does not prove that coverage caused a score difference or justify filtering the main score.", ""]
    return lines


def powershell_arguments(arguments):
    # Single quotes preserve every saved argument without shell expansion.
    return " ".join("'"+str(arg).replace("'", "''")+"'" for arg in arguments)


def local_script_arguments(arguments):
    """Translate only the entry-point path to the documented advanced cwd."""
    return [Path(arguments[0]).name, *arguments[1:]]


def commands(plan, workers):
    threads, epochs, patience = plan["threads"], plan["max_epochs"], plan["patience"]
    lines = [
        "```powershell",
        "Set-Location 'PATH_TO_MODEL_DIRECTORY'",
        "Set-Location './advanced_model'",
        "$advancedPython = '.\\.venv\\Scripts\\python.exe'",
        "& $advancedPython prepare.py --input ../data0/dataset0.json.gz --output-dir cache/data0",
    ]
    if workers:
        lines.append("& $advancedPython "+powershell_arguments(local_script_arguments(plan["command"])))
        for _, record in workers:
            lines.append("& $advancedPython "+powershell_arguments(local_script_arguments(record["command"])))
        lines += [
            f"& $advancedPython train.py --phase cv --max-epochs {epochs} --patience {patience} --threads {threads}",
            f"& $advancedPython train.py --phase final --max-epochs {epochs} --patience {patience} --threads {threads}",
        ]
    else:
        lines.append(f"& $advancedPython train.py --phase all --max-epochs {epochs} --patience {patience} --threads {threads}")
    lines.append("& $advancedPython plot_diagnostics.py --runs runs --cache cache/data0 --threads 4")
    for n in range(3):
        batch_size = 8 if n == 2 else 32
        lines.append(f"& $advancedPython predict.py --input ../data{n}/dataset{n}.json.gz --model runs/final_model.pt --output predictions/LIFO_dataset{n}.csv --threads {threads} --batch-size {batch_size}")
    for n, stage in ((0, "data0_in_sample"), (1, "data1_frozen_selection"), (2, "data2_pending")):
        name = "data.info.labelled" if n == 0 else "data.info"
        lines.append(f"& $advancedPython evaluate.py --labels ../data{n}/{name} --predictions predictions/LIFO_dataset{n}.csv --output-dir evaluations/{stage} --stage {stage}")
    lines += [
        "& $advancedPython verify.py --model runs/final_model.pt --output verification/final_verification.json",
        "& $advancedPython report.py --runs runs --predictions-dir predictions",
        "```",
        "These are the command forms for the retained scripts/settings. The screen and parallel-worker options reproduce their saved actual invocation arguments when workers exist; only the script path is translated to the documented advanced_model working directory. The original argument arrays remain in search_manifest.json and each linked worker record. Each worker owns disjoint candidate/fold directories; to reproduce parallel execution, launch those worker commands concurrently in separate PowerShell terminals after screen completion, wait for every worker to finish, then run the CV aggregator and final phase. The block lists arguments and dependencies, not an invented shell launch schedule. `--phase all` performs the same experiment serially and reuses completed unchanged checkpoints. Shell redirection can retain terminal logs. Prediction reuses a matching completed CSV after checking its fingerprints.",
        "",
        "Ubuntu CPU reproduction is **unverified on Ubuntu/RONIN** in this run. From the copied `Team_Project_export/advanced_model` folder:",
        "",
        "```bash",
        "python3.12 -m venv .venv",
        "source .venv/bin/activate",
        "python -m pip install -r requirements.lock.txt",
        "python prepare.py --input ../data0/dataset0.json.gz --output-dir cache/data0",
        f"python train.py --phase all --max-epochs {epochs} --patience {patience} --threads {threads}",
        f"python predict.py --input ../data1/dataset1.json.gz --model runs/final_model.pt --output predictions/LIFO_dataset1.csv --threads {threads}",
        "python evaluate.py --labels ../data1/data.info --predictions predictions/LIFO_dataset1.csv --output-dir evaluations/data1_frozen_selection --stage data1_frozen_selection",
        "python report.py --runs runs --predictions-dir predictions",
        "```",
        "Use the analogous dataset0/dataset2 prediction/evaluation commands above, then the model verification and data0 diagnostics commands. The peer prediction path requires only JSON plus the saved artifact, without labels, folds, online annotation or retraining. The model executes explicitly on CPU. A compatible ordinary Linux PyTorch build can also execute on CPU; no particular wheel index is asserted to be verified here. Installation and dependency compatibility still need Ubuntu verification.",
    ]
    if workers:
        lines += ["", "Retained actual worker argument lists (Unix quoting for reference; Ubuntu execution remains unverified):", "", "```bash"]
        for _, record in workers:
            lines.append("python "+" ".join(shlex.quote(arg) for arg in local_script_arguments(record["command"])))
        lines += ["```", "These are alternative disjoint fit commands, not extra fits to add after the serial `--phase all` command. Run the CV aggregator after all workers if using this alternative."]
    return "\n".join(lines)


def actual_pipeline_commands():
    path = ROOT/"pipeline_status.json"
    if not path.is_file():
        return "No automated continuation invocation record was found."
    evidence = read_json(path)
    commands = evidence.get("commands", [])
    if not commands or not all(isinstance(command, list) and command for command in commands):
        raise ValueError("Automated continuation commands are missing or malformed")
    lines = ["### Recorded continuation commands", "",
             "The following arguments were actually invoked by finish_pipeline.py, in recorded order, from the advanced_model folder. They include the prediction batch sizes, real example prediction, selected out-of-fold evaluation and diagnostics. The original executable path and argument arrays remain in "+link(path)+"; stage console logs are saved as pipeline_<stage>.log. Re-running finish_pipeline.py reuses matching completed stages and stops on a failed stage.", "", "```powershell"]
    for command in commands:
        lines.append("& "+powershell_arguments(command))
    lines += ["```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT/"runs")
    parser.add_argument("--predictions-dir", type=Path, default=ROOT/"predictions")
    parser.add_argument("--evaluations-dir", type=Path, default=ROOT/"evaluations")
    parser.add_argument("--cache", type=Path, default=ROOT/"cache/data0")
    args = parser.parse_args()
    runs, predictions_dir = args.runs.resolve(), args.predictions_dir.resolve()
    plan = read_json(runs/"search_manifest.json")
    screen = read_json(runs/"screen_results.json")
    finalists = read_json(runs/"finalists.json")
    cvs = read_json(runs/"cv_results.json")
    frozen = read_json(runs/"frozen_specification.json")
    final = read_json(runs/"final_model_manifest.json")
    audit = read_json(args.cache/"audit.json")
    if audit.get("status") != "completed" or len(cvs) != len(finalists):
        raise ValueError("Preparation or full finalist CV is incomplete")
    if {r["config"]["id"] for r in screen} != {c["id"] for c in plan["configs"]}:
        raise ValueError("Screen results do not include every planned configuration")
    if {r["config"]["id"] for r in cvs} != {c["id"] for c in finalists}:
        raise ValueError("CV candidates differ from saved finalists")
    model_path = runs/"final_model.pt"
    if final["model_sha256"] != sha256(model_path):
        raise ValueError("Final model fingerprint differs")
    selected_id = frozen["config"]["id"]
    selected = next(r for r in cvs if r["config"]["id"] == selected_id)
    if frozen["config"] != final["config"] or frozen["epochs"] != final["epochs"]:
        raise ValueError("Final artifact configuration differs from frozen specification")
    if frozen["cv_metrics_sha256"] != sha256(runs/selected_id/"cv_metrics.json"):
        raise ValueError("Selected CV evidence changed after freezing")
    for cv in cvs:
        config_id = cv["config"]["id"]
        validate_cv(cv, runs/config_id/"cv_metrics.json")
        if read_json(runs/config_id/"cv_metrics.json") != cv:
            raise ValueError("Aggregate and candidate CV evidence differ")
        read_json(runs/f"repeat_{config_id}"/"complete.json")
        for f in range(5):
            for step in ("inner", "refit"):
                read_json(runs/f"{config_id}_fold{f}_{step}"/"complete.json")
    for config in plan["configs"]:
        read_json(runs/f"screen_{config['id']}"/"complete.json")
    read_json(runs/"final_fit"/"complete.json")
    workers = parallel_worker_evidence(runs, cvs)

    prediction_evidence = []
    for n in range(3):
        path = predictions_dir/f"LIFO_dataset{n}.csv"
        manifest = read_json(path.with_suffix(".csv.manifest.json"))
        validate_predictions(path, manifest, final["model_sha256"])
        prediction_evidence.append((path, manifest))
    evaluations = {}
    for path in sorted(args.evaluations_dir.rglob("metrics.json")):
        evidence = read_json(path)
        stage = evidence.get("stage")
        if stage:
            if stage in evaluations:
                raise ValueError(f"Duplicate evaluation stage: {stage}")
            evaluations[stage] = (path, evidence)
    required = ("data0_in_sample", "data1_frozen_selection", "data2_pending")
    for n, stage in enumerate(required):
        if stage not in evaluations:
            raise ValueError(f"Required final evaluation missing: {stage}")
        path, evidence = evaluations[stage]
        manifest = prediction_evidence[n][1]
        if evidence["predictions_sha256"] != manifest["output_sha256"] or evidence["n_sites"] != manifest["n_sites"]:
            raise ValueError(f"Evaluation/prediction provenance differs: {stage}")
        label_hash = evidence.get("labels_sha256")
        if not isinstance(label_hash, str) or len(label_hash) != 64 \
                or any(c not in "0123456789abcdef" for c in label_hash):
            raise ValueError(f"Evaluation label-source fingerprint missing/invalid: {stage}")
        if n == 0 and label_hash != plan["labels_sha256"]:
            raise ValueError("In-sample data0 evaluation label source differs from training labels")
    data1 = evaluations["data1_frozen_selection"][1]
    data0 = evaluations["data0_in_sample"][1]
    data2 = evaluations["data2_pending"][1]
    if data1.get("status") != "complete" or data0.get("status") != "complete":
        raise ValueError("Binary final evaluations are incomplete")
    if data2.get("status") != "coverage_passed_scoring_pending":
        raise ValueError("Expected data2 coverage-only evaluation")
    evaluation_log_path = runs/"data1_evaluation_log.json"
    evaluation_log = read_json(evaluation_log_path)
    if not isinstance(evaluation_log, list):
        raise ValueError("Invalid data1 evaluation log")
    completed_data1 = [entry for entry in evaluation_log if entry.get("status") == "complete"]
    if len(completed_data1) != 1:
        raise ValueError("Report requires exactly one completed frozen data1 evaluation; do not conceal repeated evaluation")
    entry = completed_data1[0]
    if entry.get("model_sha256") != final["model_sha256"] \
            or entry.get("predictions_sha256") != prediction_evidence[1][1]["output_sha256"] \
            or entry.get("metrics_sha256") != sha256(evaluations["data1_frozen_selection"][0]):
        raise ValueError("Completed data1 exposure record fingerprints differ from actual outputs")
    verification_path, verification_evidence, final_check = final_verification(final["model_sha256"])
    diagnostics = diagnostic_section(runs)
    supplemental_checks = []
    independent_path = ROOT/"verification/final_outputs_audit.json"
    if independent_path.is_file():
        independent = read_json(independent_path)
        if independent.get("status") != "passed" or independent["final_model"]["sha256"] != final["model_sha256"]:
            raise ValueError("Independent output audit is incomplete or refers to another model")
        if independent["audit_script_sha256"] != sha256(ROOT/"verification/final_outputs_audit.py"):
            raise ValueError("Independent audit script changed after execution")
        for n, (path, _) in enumerate(prediction_evidence):
            if independent["prediction_coverage"][f"data{n}"]["csv_sha256"] != sha256(path):
                raise ValueError("Independent audit refers to changed predictions")
        supplemental_checks.append("Read-only independent output audit **passed**: "+link(independent_path)+". It reproduced selected OOF/fold and data1 metric arithmetic directly with sklearn, checked all three complete metadata key sets and source/fold/model/input/output fingerprints, and performed no new model fitting or inference. Exact audit command, from advanced_model: `& '.venv/Scripts/python.exe' 'verification/final_outputs_audit.py'`.")
    figure_path = ROOT/"verification/figure_review_manifest.json"
    if figure_path.is_file():
        figure_review = read_json(figure_path)
        if figure_review.get("status") != "complete" or figure_review["review_sha256"] != sha256(ROOT/"verification/figure_review.md"):
            raise ValueError("Figure-review evidence changed or is incomplete")
        for figure in figure_review["figures"]:
            if figure["sha256"] != sha256(ROOT/figure["path"]):
                raise ValueError("An inspected figure changed after review")
        supplemental_checks.append(f"Original-resolution visual review completed for **{figure_review['inspected_pngs']} figures**: "+link(ROOT/"verification/figure_review.md")+" and "+link(figure_path)+". Displayed AUC values/counts matched the metric records; no confirmed clipping or missing labels remained.")
    score = float(data1["selection_score"])
    if score > .5905:
        verdict = "The advanced candidate has the better measured selection score relative to the supplied LightGBM report; it exceeds the conditional rounding range. Prefer this advanced candidate on predictive performance, subject to reproducibility checks."
    elif score < .5895:
        verdict = "LightGBM is the better of the two on the supplied selection evidence: its reported score exceeds this measured advanced candidate, even allowing the stated rounding range. Retain LightGBM as the preferred candidate."
    else:
        verdict = "The precise ordering is unresolved from the rounded LightGBM evidence: the advanced score falls inside its conditional rounding range. Obtain exact LightGBM scores before claiming a winner."

    costs = resource_rows(runs, cvs, prediction_evidence, evaluations, audit, args.cache.resolve(), workers)
    cost_path = ROOT/"compute_costs.csv"
    save_costs(costs, cost_path)
    config = frozen["config"]
    hardware = plan.get("hardware", {})
    lines = [
        "# Advanced model: actual training, validation and frozen evaluation",
        "",
        "All scores below come from completed saved local runs, unless explicitly labelled teammate-reported. No expected/pilot score is substituted for a completed result.",
        "",
        verdict,
        "",
        f"Advanced data1 selection score **{score:.10f}** versus LightGBM approximately **0.590**; point difference versus its rounded centre **{score-.590:+.10f}**. The criterion is `(ROC AUC + trapezoidal PR AUC) / 2`. Under conventional three-decimal rounding of both LightGBM components its score is approximately **[0.5895, 0.5905]**. This is a rounding bound, not a confidence interval or significance test.",
        "",
        "## Completed output and provenance",
        "",
        f"- Final selected configuration: **{selected_id}**, refitted on all **{audit['n_sites']:,}** eligible data0 sites for **{frozen['epochs']}** fixed epochs. No early stopping or tuning uses data1/data2.",
        f"- One frozen artifact: {link(model_path)}; {final['bytes']:,} bytes, {final['parameters']:,} stored trainable parameters. SHA256 `{final['model_sha256']}`. Parameter count includes modules instantiated by the shared class, including any unused by the selected pooling mode.",
        f"- Shared five-gene-fold CSV fingerprint: `{plan['shared_fold_sha256']}`.",
        f"- Prepared data0: **{audit['n_reads_total']:,} reads**, all retained; read count minimum **{audit['read_count']['min']}**, maximum **{audit['read_count']['max']}**, mean **{audit['read_count']['mean']:.4f}**. {link(args.cache/'audit.json')} contains the actual strict audit and input/cache fingerprints.",
        f"- Selection/freeze records: {link(runs/'search_manifest.json')}, {link(runs/'frozen_specification.json')}, {link(runs/'final_model_manifest.json')}. Final data1 metrics: {link(evaluations['data1_frozen_selection'][0])}.",
        f"- Recorded data1 exposure: **{len(completed_data1)} completed evaluation**, **{len(evaluation_log)} recorded attempt(s)**, with matching model/prediction/metric hashes in {link(evaluation_log_path)}. This does not erase the team's earlier data1 exposure.",
        f"- Evaluation label-source fingerprints: data0 `{data0['labels_sha256']}`; data1 `{data1['labels_sha256']}`; data2 `{data2['labels_sha256']}`. Evaluation reuse requires unchanged label and prediction bytes.",
        f"- Fresh-process CPU verification passed for this exact model hash: {link(verification_path)}. Real example sites **{final_check.get('sites')}**; largest probability difference between processes **{final_check.get('fresh_process_max_probability_difference'):.12g}**. This verifies local reload/prediction consistency, not clean Ubuntu execution.",
    ]
    for n, (path, manifest) in enumerate(prediction_evidence):
        lines.append(f"- Dataset{n}: {link(path)}, **{manifest['n_sites']:,}** unique sites; CSV SHA256 `{manifest['output_sha256']}`; input SHA256 `{manifest['input_sha256']}`. Manifest confirms complete actual JSON-key coverage and the identical model hash.")
    lines += [
        "",
        "## Actual held-out and data1 metrics",
        "",
        metric_table([
            ("Selected data0 five-fold development mean", selected["mean"]),
            ("LightGBM data0 five-fold mean (rounded teammate report)", LIGHTGBM_CV),
            ("Selected data0 sample SD (ddof=1)", selected["sample_sd"]),
            ("Selected data0 pooled OOF development", selected["pooled_oof"]),
            ("Final model data0 in-sample", data0),
            ("Frozen advanced model data1 selection", data1),
            ("LightGBM data1 (rounded teammate report)", LIGHTGBM),
        ]),
        "",
        "OOF means each data0 site's score came from a model that excluded its shared held-out gene fold. The pooled OOF score combines all these predictions; it differs from averaging five fold metrics. Architecture selection used these outer scores, so this is **development validation**, not an untouched confirmation of the search procedure. Each fold's epochs were selected using only a further gene-separated partition inside its outer training portion; it was then refitted on the complete outer training portion before scoring held-out genes.",
        "",
        "| Shared fold | Sites | Positives | Selected epochs | ROC AUC | Trapezoidal PR AUC | AP | Selection score |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(selected["folds"], key=lambda r: r["fold_id"]):
        lines.append(f"| {row['fold_id']} | {row['n_sites']:,} | {row['n_positives']:,} | {row['selected_epochs']} | "+" | ".join(number(row[k]) for k in RANKING)+" |")
    lines += [
        "",
        f"data0 positive fraction is **{selected['pooled_oof']['positive_fraction']:.6%}**; data1 is **{data1['positive_fraction']:.6%}**. PR AUC depends on positive prevalence. AP is separately named and is not substituted for trapezoidal PR AUC.",
        "",
        "## Fixed threshold 0.5 and reliability",
        "",
        "| Predictor on data1 | TN | FP | FN | TP | Precision | Recall | F1 | Specificity |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in (("Advanced (actual)", data1), ("LightGBM (reported counts; checked arithmetic)", LIGHTGBM)):
        lines.append("| "+name+" | "+" | ".join(number(row[k]) for k in ("tn", "fp", "fn", "tp", "precision", "recall", "f1", "specificity"))+" |")
    lines += [
        "",
        f"At 0.5 the advanced model detects {data1['tp']:,} of {data1['n_positives']:,} labelled positive sites and misses {data1['fn']:,}. Ranking quality and decision-cutoff recall answer different questions. No data1-derived cutoff or calibration was fitted. Actual data1 Brier score **{data1['brier']:.10f}** and log loss **{data1['log_loss']:.10f}** describe probability reliability; lower is better. The reliability plot is descriptive, without refitting.",
        f"Compared with LightGBM's reported counts, this cutoff detects **{data1['tp']-LIGHTGBM['tp']:,} more positives** and produces **{data1['fp']-LIGHTGBM['fp']:,} more false positives**. Recall and F1 improve; precision and specificity decrease. The model preference uses the agreed ROC/PR criterion, rather than choosing a data1-specific cutoff.",
        "",
        "## Search, repeat seed and alternative finalists",
        "",
        "The search screens all configurations on the same inner gene holdout within shared folds 1–4. It sends the highest-ranked screen candidate and at least one genuinely read-level candidate to full five-fold development evaluation, and repeats the two finalists with seed 43 on the screen split. This procedure does not evaluate every screened candidate across all five folds.",
        "",
        "| Configuration | Pooling | Summary inputs | Screen seed42 score | Best screen epoch | Repeat seed43 score | Full five-fold mean score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    cv_lookup = {r["config"]["id"]: r for r in cvs}
    for row in screen:
        c = row["config"]
        repeat_path = runs/f"repeat_{c['id']}"/"complete.json"
        repeat = read_json(repeat_path) if repeat_path.is_file() else None
        cv = cv_lookup.get(c["id"])
        lines.append(f"| {c['id']} | {c['pool']} | {c['summary_n']} | {row['inner_score']:.8f} | {row['best_epoch']} | {number(repeat['best_score']) if repeat else 'not run'} | {number(cv['mean']['selection_score']) if cv else 'not run'} |")
    lines += [
        "",
        "These are unequal scopes: screen/repeat scores are inner development evidence, while finalist scores use all five shared folds. The second seed is not a full five-fold multi-seed experiment. The same screen split is reused, so repeat results test optimisation variability on that split rather than create a new independent dataset. Quantile/context/read-branch configurations test whole-pipeline changes; they do not isolate architecture alone. BCE loss magnitudes on learning curves must not be ranked across different positive weights: attention_weighted uses 3, while the other candidates use 1. Their common ROC/PR selection scores can be compared.",
        "",
    ]
    for cv in cvs:
        lines += [f"**Finalist {cv['config']['id']}** — {link(runs/cv['config']['id']/'cv_metrics.json')}", "",
                  metric_table([("Five-fold mean", cv["mean"]), ("Sample SD", cv["sample_sd"]), ("Pooled OOF", cv["pooled_oof"])]), ""]
    failure_files = []
    for path in runs.rglob("*.json"):
        evidence = read_json(path)
        if isinstance(evidence, dict) and (evidence.get("status") in ("failed", "interrupted", "interrupted_or_failed") or evidence.get("error")):
            failure_files.append((path, evidence.get("error", evidence.get("status"))))
    lines += diagnostics
    lines += ["**Failed configurations and interruptions:** "+(
        "; ".join(f"{link(path)}: {error}" for path, error in failure_files)
        if failure_files else "No failed/interrupted fit JSON record was found in the retained runs directory. This does not prove no unrecorded process failure occurred; terminal logs and epoch checkpoints are retained separately."), "",
        "## Model and reusable workflow", "",
        "`JSON site → strict nine-column all-read bag + context → deterministic summaries/sequence encoding → fit-partition scaling → neural predictor → site probability → exact three-column CSV`. A bag is all reads aligned to one site. Site labels train the site probability only; positive sites do not give every read a positive label.", "",
        f"Selected configuration (actual): `{json.dumps(config, sort_keys=True)}`. The read encoder concatenates nine transformed signals with a seven-position, four-dimensional nucleotide embedding (28 context numbers), then uses two shared SiLU hidden layers. The site head concatenates context, the chosen summary branch, and any learned pooled read branch. Width **{config['width']}**, dropout **{config['dropout']}**, AdamW learning rate **{config['lr']}**, weight decay **{config['weight_decay']}**, BCE positive weight **{config['pos_weight']}**. Gradient norm is capped at 5.", "",
        "Summary features are nine arithmetic means, nine population SDs (ddof=0), and nine each of the .10/.25/.50/.75/.90 linear quantiles, calculated over every read. The 18-summary control uses only the first 18. Read transforms apply signed log1p to dwell ×1000 and signal SD; read mean currents remain unchanged before train-only affine scaling. Summary transforms use signed log1p, with dwell units ×1000, before train-only scaling. Fitted means/SDs are learned exclusively from each fit's eligible training indices and saved as model buffers. No per-bag centring erases absolute current shifts. No motif-specific normalisation, external pretraining, learned test-data transform or synthetic read labels are used.", "",
        "Deep Sets pools masked learned mean, SD and max. Gated attention pools a learned masked weighted sum plus learned mean/SD. The noisy-OR candidate pools a geometric survival mean at a fixed reference count of 20 and feeds its logit to the site head; this is a coverage-normalised **adaptation**, not a reproduction of published m6Anet or pum6a. Mean/SD summaries are controls with context; larger summary candidates add quantiles.", "",
        f"Training read-level branches sample at most **{config['cap']}** reads uniformly without replacement when a bag is larger; the reproducible seed varies by epoch. Validation and final prediction use all supplied reads. All summaries use all reads even while the neural read branch trains on a sampled subset. Padding is masked in attention, mean/variance, maximum and noisy-OR pooling. Read order does not have biological meaning; nucleotide/event-position order is preserved. T/U share a code; recognised ambiguous IUPAC bases use a fifth code; unsupported symbols fail. IDs, coordinates, gene IDs, folds, labels and offsets are excluded predictive inputs.", "",
        f"Final epochs are the median of the selected candidate's five training-side epoch choices (**{frozen['epochs']}**). The full data0 fit has fixed epochs and no holdout/early stopping. It learns fresh weights with seed 2026. Final dataset0 CSV predictions are in-sample and cannot serve as held-out evidence.", "",
        "Checkpoint recovery: each fit writes `last.pt` after an epoch, with optimiser, model, torch RNG, preprocessing, history and signature; `best.pt`, `history.json`, `training.log` and `complete.json` retain the chosen/completed state. The next invocation checks input/configuration/source signatures before reuse. An unfinished current epoch restarts from the last saved epoch. Preparation restarts its incomplete scan; completed cache reuse verifies fingerprints. Existing final prediction reuse checks input/model/output hashes. The saved specification must not be changed after data1 evaluation.", "",
        "## Computation measured in this run", "",
        f"Hardware/version evidence: `{json.dumps(hardware, sort_keys=True)}`. A separate read-only Windows registry check confirmed **AMD Ryzen AI 9 365 w/ Radeon 880M**. Installed torch **2.14.1+cpu**, with no available training acceleration in this environment; the retained implementation executes explicitly on CPU. Configured threads **{plan['threads']} per training process**; concurrent workers therefore use multiple process allocations.", "",
        cost_summary(costs), "",
        whole_trainer_summary(costs), "",
        f"Retained whole-worker invocation timers: **{len(list(runs.glob('trainer_invocation_worker_*.json')))}** for **{len(workers)}** worker records. All worker records have their own fit-stage resource measurements and start-to-finish timestamps. A missing whole-invocation CPU/RSS measurement is not reconstructed; supplemental whole-invocation totals cover only retained records.", "",
        parallel_worker_summary(workers), "",
        f"Detailed actual component records: {link(cost_path)}. The sum counts cache creation once, each saved fit segment once, each held-out inference once, raw prediction once per dataset and each recorded evaluation once. These are distinct work scopes that can occur concurrently; summed wall seconds represent cumulative component work, not calendar elapsed completion time. The final manifest repeats fit resources and is intentionally not added again. Largest sampled RSS values are maxima of individual sampled components, not exact continuous peaks or a combined memory total. Preparation samples one process; the other stages sample each process tree at 0.2-second intervals.", "",
        "The **separate whole-trainer invocation timer** covers cache loading/fingerprint checks, setup, training-partition normalisation, screen/CV/final work and their orchestration within each saved invocation. Worker whole-invocation timers also include their input checks and fit setup. These timers overlap fit/holdout components and the worker fit-stage records, and must never be added to component totals. `compute_costs.csv` marks all such rows `additive_component=False`; the whole-invocation table excludes worker fit-stage records to avoid repeating their subset. Its summed wall durations are cumulative process work when invocations overlap. Per-fit timers cover epochs plus inner validation and exclude preceding normalisation/setup; those costs are captured by invocation timers. Preparation, raw prediction, evaluation and post-training diagnostics are outside trainer invocations.", "",
        "The component and invocation tables do not claim end-to-end elapsed session time. Only the explicitly timestamped parallel-stage span measures that stage's calendar elapsed time. Installation/environment setup, interpreter imports before timers, correctness verification processes without recorded measurements, report generation, shell waiting and any missing/unrecorded failed work remain outside saved timer scopes. Saved interrupted/failed whole-trainer invocations are shown separately when available. Measured CPU is process CPU time and sampled memory is approximate. No cloud billing or monetary cost is invented.", "",
        "LightGBM's teammate-reported Apple-silicon/macOS/two-thread figures are approximately 13 s extraction, 132 s for 25 CV fits, 7 s final fit, 20/14/1.4 s dataset0/1/2 prediction, 5.3 MB model and 450 MiB process high-water RSS. These are rounded report-only costs on different hardware/scopes, not a controlled efficiency comparison. Baseline audit: "+link(ROOT/"docs/lightgbm_evidence.md")+".", "",
        "## Plots and retained files", "", plot_links(evaluations), "",
        "\n\n".join(supplemental_checks), "",
        "Training curves/epoch metrics are retained in each fit's `history.json` and `training.log`; no curve or score is fabricated for an uncompleted stage. Models/checkpoints are under `runs`; candidate OOF/fold probabilities, screen/repeat evidence and configs remain there. The three submission-shaped candidate CSVs are under `predictions`, separate from existing team candidates. No file was submitted or published by these scripts.", "",
        "Code: "+", ".join(link(ROOT/name) for name in ("train.py", "cv_worker.py", "model.py", "data.py", "prepare.py", "predict.py", "evaluate.py", "common.py", "report.py", "plot_diagnostics.py", "verify.py"))+". Research: "+link(ROOT/"docs/research.md")+".", "",
        "## Limitations and pending work", "",
        "- data1 was already used to rank the original five team pipelines, and this experiment was motivated by that visible ranking. Frozen evaluation prevents new fitting on it but does not make it an independent final test. Shared data0/data1 site identifiers do not establish identical signals or biological independence.",
        "- LightGBM precise scores/model/code were absent from the audited local evidence. Its ranking metrics are rounded teammate reports; its threshold measures were calculated from reported counts. An exact paired same-site comparison, significance test and gene-cluster uncertainty interval cannot be produced from those reports. Do not infer significance from fold SD.",
        "- Configuration selection from outer development scores introduces selection optimism. The screen is restricted to one inner split, and repeated seed evidence covers only that split. Complete nested selection-procedure evaluation, repeated five-fold seeds, dedicated context/read-cap ablations and broader independent transfer validation remain pending.",
        f"- The planned inner training limit was {plan['max_epochs']} epochs with patience {plan['patience']}. Some fits can select the last permitted epoch; this is a finite search budget, not evidence that optimisation has converged or that longer training cannot help. The six configurations and two five-fold finalists do not establish a global optimum.",
        "- Site labels are experimental assay observations and can be imperfect. Attention/latent read scores are not experimentally verified read labels; site probabilities are not stoichiometric fractions. Missing waveforms/alignment features cannot be reconstructed from nine values.",
        f"- Sigmoid scores are not guaranteed calibrated biological probabilities. The selected BCE positive weight is {config['pos_weight']}; a weight above 1 changes the loss's emphasis and can shift the probability scale. No calibration or cutoff adjustment was learned from data1. Reliability/Brier/log-loss measurements are descriptive checks of the frozen outputs.",
        f"- data2 has {data2['n_sites']:,} predicted sites and labels {data2.get('label_values')}. Its output coverage passed; binary scoring is deliberately pending official label interpretation.",
        "- Clean Ubuntu/RONIN installation and prediction have not been verified in this local Windows run. A published m6Anet benchmark, wider SG-NEx cell-line analysis, interactive visualisation, publication and official submission are separate project work and are not claimed completed here.", "",
        "## AI use and errors/fixes", "",
        "AI assisted primary-source research, pipeline design, code generation, execution, validation and this evidence report. The source papers informed freshly trained models; no externally trained weights or external training/pretraining data were used. Verify and acknowledge this assistance under the official project AI-use requirements.", "",
        "Environment issues reported during this execution: the Windows CIM hardware query was denied, so accessible platform/psutil evidence was used; the initial pip network request failed inside the restricted sandbox and installation later succeeded using an authorised escalation; access to the root/shared environment was unavailable, so a dedicated `advanced_model/.venv` was used. These were setup issues, not evidence of model failure. Package installation overhead is outside all measured training timers. Retain the original terminal/install logs rather than infer their duration.", "",
        "A supplementary diagnostic originally used two CPU threads against the four-thread CV reference and stopped at an overly strict 1e-12 metric-reproduction guard. Preserved evidence is in diagnostics_attempts/thread2_strict_guard_failure/failure_audit.json. Per-site probabilities differed by at most 1.1920928955078125e-7, mean 1.3441327656054331e-9, with zero decisions changed at 0.5; ROC AUC differed by −1.9714440302465164e-8. The check was rerun with the original four threads, retaining the original strict guard. The pipeline resumed only missing diagnostics/report stages; trained weights, selected configuration, final predictions and the single frozen data1 evaluation were retained. The failed diagnostic's resource duration was not recorded and is not invented.", "",
        "## Exact commands", "", commands(plan, workers), "", actual_pipeline_commands(), "",
        "The report is generated only after all finalist metrics, the frozen model, three fingerprinted CSV manifests and all three final evaluation records are present and consistent. It contains completed evidence; pending items are labelled above.", "",
    ]
    target = ROOT/"results.md"
    save_text(target, "\n".join(lines))
    print(f"Created {target}")
    print(verdict)


if __name__ == "__main__":
    main()
