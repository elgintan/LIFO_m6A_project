"""Data0-only positive-loss-weight experiment with the unchanged frozen trainer.

Uses the completed cap128/weight3 control and freshly fits cap128/weight1.
The original checkpoint/RNG recovery and gene-grouped inner/refit procedure are
delegated without changes. No data1 access, final fit, or warm-start is provided.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

import train_read_cap as cap
import report_read_cap as reference

fitting = cap.fitting
Measure, save_json = cap.Measure, cap.save_json
sha256, source_sha256 = cap.sha256, cap.source_sha256
SAVED = reference.SAVED
REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "model_elgin/outputs/loss_weight_v1"
PARENT_CV = REPO / "model_elgin/outputs/read_cap_v1/cv"
PLAN = REPO / "model_elgin/LOSS_WEIGHT_EXPERIMENT.md"
NEW_PROVENANCE = {"loss_weight_entrypoint_sha256": "tools/train_loss_weight.py",
                  "loss_weight_plan_sha256": "LOSS_WEIGHT_EXPERIMENT.md"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configuration(recipe, pos_weight=1.0):
    require(type(pos_weight) in (int, float) and pos_weight in (1., 3.),
            "Only prespecified loss weights1/3 are allowed")
    expected = dict(fitting.BASE, cap=128, context_mode="none", min_sites=30)
    require(recipe["config"] == expected and expected["pos_weight"] == 3.,
            "Comparator must be the unchanged cap128/weight3 original-feature recipe")
    for key, value in dict(max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4, smoke=False).items():
        require(recipe[key] == value, "Unexpected comparator setting: " + key)
    return dict(expected, pos_weight=float(pos_weight))


def runtime_versions():
    return dict(python=fitting.platform.python_version(), torch=str(fitting.torch.__version__),
                numpy=np.__version__, pandas=fitting.pd.__version__, sklearn=fitting.sklearn.__version__)


def check_environment():
    versions = runtime_versions()
    require(versions == reference.TRAINING_VERSIONS, "Runtime differs from the fixed cap128 comparison environment")
    return versions


def parent_sources():
    sources = fitting.source_hashes()
    sources.update({"tools/train_read_cap.py": source_sha256(cap.__file__),
                    "READ_CAP_EXPERIMENT.md": source_sha256(cap.PLAN)})
    return sources


def current_sources():
    sources = parent_sources()
    sources.update({"tools/train_loss_weight.py": source_sha256(__file__),
                    "LOSS_WEIGHT_EXPERIMENT.md": source_sha256(PLAN)})
    return sources


def experiment_identity(parent):
    expected_keys = {"cache_manifest_sha256", "data0_input_sha256", "labels_sha256", "folds_sha256",
                     "source_sha256", "training_entrypoint_sha256", "experiment_plan_sha256"}
    require(set(parent) == expected_keys and len(parent["source_sha256"]) == 9,
            "Expected the exact completed cap128 parent identity")
    require(parent["source_sha256"] == parent_sources(), "Parent source changed")
    require(parent["training_entrypoint_sha256"] == parent["source_sha256"]["tools/train_read_cap.py"] and
            parent["experiment_plan_sha256"] == parent["source_sha256"]["READ_CAP_EXPERIMENT.md"],
            "Parent wrapper/plan identity differs from its source map")
    sources = current_sources()
    return dict(parent, source_sha256=sources,
                loss_weight_entrypoint_sha256=sources["tools/train_loss_weight.py"],
                loss_weight_plan_sha256=sources["LOSS_WEIGHT_EXPERIMENT.md"])


def output_directory(path):
    path = Path(path).resolve()
    require(path.is_relative_to(DEFAULT.resolve()), "Output must stay in the dedicated loss-weight experiment tree")
    return path


def delegate_cv(cache, meta, population, config, args, identity):
    """Call the original implementation; never reuse parent model weights."""
    expected = dict(fitting.BASE, cap=128, context_mode="none", min_sites=30)
    require(config["pos_weight"] in (1., 3.) and config == dict(expected, pos_weight=config["pos_weight"]),
            "Invalid loss-weight experiment config")
    return fitting.run_cv(cache, meta, population, config, args, identity)


def benchmark(cache, meta, config, args, identity):
    """Two isolated fresh one-epoch timings, never promoted into CV."""
    require(config["pos_weight"] == 1. and config["cap"] == 128, "Timing requires cap128/weight1")
    initial, inner, refit, _, audit = fitting.partition(meta, np.arange(len(meta), dtype=np.int64), 0)
    root = args.output_dir / "benchmark"
    save_json(root / "split_audit.json", audit)
    rows = []
    for stage, indices, validation, seed in (("inner", initial, inner, 2026), ("refit", refit, None, 2126)):
        directory = root / ("weight1_" + stage)
        print(f"TIMING ONLY cap128/weight1/{stage}: {len(indices)} fitting sites; one epoch", flush=True)
        fitted = fitting.run_fit(cache, meta.label.to_numpy(), indices, validation,
                    config, seed, directory, 1, 5, 256, "smoke", identity)
        history = json.loads((directory / "history.json").read_text())
        rows.append(dict(pos_weight=1., cap=128, fit_stage=stage, fit_sites=len(indices),
                         validation_sites=0 if validation is None else len(validation),
                         epoch_wall_seconds=history[0]["wall_seconds"], fit_resources=fitted["resources"],
                         artifact_sha256=fitted["best_sha256"],
                         interpretation="Fresh one-epoch timing only; never promoted into CV or a final fit"))
    save_json(root / "timing_summary.json", dict(benchmark=rows,
                maximum_cv_epoch_work_seconds=5 * 20 * sum(row["epoch_wall_seconds"] for row in rows),
                note="Maximum epoch-work extrapolation excludes startup, normalisation, checks and outer inference; not a guaranteed ETA. Early stopping/refit duration may reduce work."))
    print("Saved timing summary; timing scores are not candidate comparison results.", flush=True)


def execute(args):
    versions = check_environment()
    require(args.phase in ("smoke", "benchmark", "cv"), "Unsupported experiment phase")
    print("Checking completed cap128/weight3 parent and unchanged source/data provenance...", flush=True)
    evidence = {}
    parent = SAVED.load_mode(PARENT_CV, "none", evidence)
    config = configuration(parent["recipe"])
    reference.current_source_evidence(parent["recipe"])
    identity = experiment_identity(parent["recipe"]["identity"])
    before = current_sources()
    require(before == identity["source_sha256"] and len(before) == 11, "Wrong experiment source identity")
    cache = fitting.Cache(args.cache)
    require(cache.source == identity["cache_manifest_sha256"], "Wrong data0 cache")
    require(sha256(args.labels) == identity["labels_sha256"], "Changed data0 labels")
    require(sha256(args.folds) == identity["folds_sha256"], "Changed shared gene folds")
    meta = fitting.align_metadata(cache, args.labels, args.folds)
    require(len(meta) == 121838 and int(meta.label.sum()) == 5475, "Unexpected data0 population")
    population = fitting.choose_population(meta, 20 if args.phase == "smoke" else None, 2026)
    if args.phase != "smoke":
        require(fitting.index_hash(population) == parent["recipe"]["population_sha256"], "Population changed")
    args.max_epochs, args.patience, args.seed = (2 if args.phase == "smoke" else 20), 5, 2026
    args.batch_size, args.threads = 256, 4
    args.outer_folds = [0] if args.phase == "smoke" else list(range(5))
    fitting.torch.set_num_threads(4)
    require(before == current_sources(), "Source/plan changed during preflight")
    invocation = dict(phase=args.phase, sites=len(population), genes=int(meta.iloc[population].gene_id.nunique()),
                      identity=identity, configuration=config, runtime_versions=versions,
                      arguments=list(args.executed_arguments), parent_cv=str(PARENT_CV),
                      no_data1=True, no_final_fit=True, no_parent_weight_warm_start=True,
                      parent_full_data0_score=parent["metrics"]["primary_score"])
    save_json(args.output_dir / f"{args.phase}_arguments_{time.time_ns()}.json", invocation)
    audits = []
    for fold in range(5):
        *_, audit = fitting.partition(meta, population, fold)
        if args.phase != "smoke":
            require(audit == json.loads((PARENT_CV / f"none/fold{fold}/split_audit.json").read_text()),
                    "Parent and candidate gene-split audits differ")
        audits.append(audit)
    save_json(args.output_dir / (args.phase + "_split_preflight.json"), audits)
    if args.phase == "benchmark":
        benchmark(cache, meta, config, args, identity)
    else:
        print(f"{args.phase.upper()}: cap128/weight1, {len(population)} data0 sites, folds{args.outer_folds}", flush=True)
        delegate_cv(cache, meta, population, config, args, identity)
        if args.phase == "cv":
            completed = SAVED.load_mode(args.output_dir / "cv", "none", {})
            require(completed["recipe"]["identity"] == identity and completed["recipe"]["config"] == config,
                    "Completed candidate CV differs from the experiment identity")
    require(before == current_sources(), "Source/plan changed during execution")
    require(check_environment() == versions, "Runtime changed during execution")
    require(all(SAVED.sha256(PARENT_CV / relative) == digest for relative, digest in evidence.items()),
            "Parent evidence changed during execution")
    print("Completed requested phase; no data1 or final all-data0 model fit.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("smoke", "benchmark", "cv"), default="smoke")
    parser.add_argument("--cache", type=Path, default=REPO.parent / "advanced_model/cache/data0")
    parser.add_argument("--labels", type=Path, default=REPO.parent / "data0/data.info.labelled")
    parser.add_argument("--folds", type=Path, default=REPO / "eda/received/shared_folds/data0_folds.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    args.executed_arguments = list(sys.argv[1:] if argv is None else argv)
    args.output_dir = output_directory(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Retains the original phase-lock semantics and its documented cross-tool
    # PID-visibility limitation; missing PIDs alone must not authorise duplicates.
    with cap.process_lock(args.output_dir / (args.phase + ".lock")):
        stamp = str(time.time_ns())
        status = args.output_dir / (args.phase + "_status.json")
        save_json(status, dict(status="running", phase=args.phase, invocation=stamp))
        try:
            with Measure() as measured:
                measured.output = args.output_dir / f"{args.phase}_invocation_{stamp}.json"
                execute(args)
        except BaseException as error:
            save_json(status, dict(status="interrupted_or_failed", phase=args.phase, invocation=stamp,
                                   error=type(error).__name__ + ": " + str(error)))
            raise
        save_json(status, dict(status="complete", phase=args.phase, invocation=stamp,
                               resources=measured.record, full_candidate_cv=args.phase == "cv"))


if __name__ == "__main__":
    main()
