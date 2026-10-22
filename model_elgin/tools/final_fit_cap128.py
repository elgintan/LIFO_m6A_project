"""Stage: nominate/check, then final-fit the original cap128/weight3 data0 model.

Delegates the frozen trainer's run_final unchanged. No new search, warm-start,
data1 access, inference or external-candidate integration is implemented here.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

import train_read_cap as cap
import report_read_cap as reference

fitting, SAVED = cap.fitting, reference.SAVED
REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "model_elgin/outputs/read_cap_v1"
CV_ROOT = DEFAULT / "cv"
PLAN = REPO / "model_elgin/FINAL_MODEL_SELECTION.md"
require, sha256 = cap.require, cap.sha256


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def versions():
    return dict(python=fitting.platform.python_version(), torch=str(fitting.torch.__version__),
                numpy=np.__version__, pandas=fitting.pd.__version__, sklearn=fitting.sklearn.__version__)


def configuration(recipe):
    expected = dict(fitting.BASE, cap=128, context_mode="none", min_sites=30)
    require(recipe["config"] == expected and expected["pos_weight"] == 3.,
            "Only the original cap128/weight3/none candidate is nominated")
    for key, value in dict(seed=2026, max_epochs=20, patience=5, batch_size=256, threads=4, smoke=False).items():
        require(recipe[key] == value, "Changed nominated recipe: " + key)
    return dict(expected)


def check_cv_identity(identity):
    expected_keys = {"cache_manifest_sha256", "data0_input_sha256", "labels_sha256", "folds_sha256",
                     "source_sha256", "training_entrypoint_sha256", "experiment_plan_sha256"}
    sources = fitting.source_hashes()
    sources.update({"tools/train_read_cap.py": cap.source_sha256(cap.__file__),
                    "READ_CAP_EXPERIMENT.md": cap.source_sha256(cap.PLAN)})
    require(set(identity) == expected_keys and len(identity["source_sha256"]) == 9
            and identity["source_sha256"] == sources, "Nominated CV identity/source map changed")
    require(identity["training_entrypoint_sha256"] == sources["tools/train_read_cap.py"]
            and identity["experiment_plan_sha256"] == sources["READ_CAP_EXPERIMENT.md"],
            "Legacy CV wrapper/plan provenance differs from source map")
    return sources


def validate_fit_signatures(parent, evidence):
    recipe = parent["recipe"]
    for fold in range(5):
        directory = CV_ROOT / ("none/fold%d" % fold)
        audit = SAVED.read_json(directory / "split_audit.json", evidence, CV_ROOT)
        for stage, population in (("inner", "initial_fit"), ("refit", "refit")):
            completed = SAVED.read_json(directory / stage / "complete.json", evidence, CV_ROOT)
            expected = dict(config=recipe["config"], seed=2026+fold+(100 if stage == "refit" else 0),
                            max_epochs=20 if stage == "inner" else parent["selected_epochs"][fold],
                            patience=5, batch_size=256, stage="cv_"+stage, identity=recipe["identity"],
                            threads=4, versions=reference.TRAINING_VERSIONS,
                            fitting=audit["populations"][population]["indices_sha256"],
                            validation=audit["populations"]["inner_validation"]["indices_sha256"] if stage == "inner" else None)
            require(completed["signature"] == fitting.fingerprint(expected), "CV fit signature mismatch")


def immutable_json(path, value):
    if path.exists():
        require(read_json(path) == value, "Frozen final wrapper/selection specification changed")
    else:
        cap.save_json(path, value)


@contextmanager
def phase_lock(path):
    """Refuse existing locks; PID absence in another namespace proves nothing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = dict(pid=os.getpid(), token=str(time.time_ns()))
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(owner, handle)
    except FileExistsError as error:
        raise ValueError("Final phase lock exists. Confirm its original session ended before explicitly clearing that lock; do not launch a duplicate.") from error
    try:
        yield
    finally:
        if path.exists() and read_json(path) == owner:
            path.unlink()


def nomination_guard():
    require(PLAN.is_file(), "The root-owned FINAL_MODEL_SELECTION.md must exist before checking")
    return dict(final_entrypoint_sha256=cap.source_sha256(__file__),
                selection_plan_sha256=cap.source_sha256(PLAN))


def epoch_choice(parent):
    epochs = list(parent["selected_epochs"])
    require(len(epochs) == 5 and all(type(epoch) is int and 1 <= epoch <= 20 for epoch in epochs),
            "Invalid completed inner epoch choices")
    return epochs, int(np.median(epochs))


def preflight(args):
    require(versions() == reference.TRAINING_VERSIONS, "Use the exact completed-CV training environment")
    evidence = {}
    parent = SAVED.load_mode(CV_ROOT, "none", evidence)
    config = configuration(parent["recipe"])
    check_cv_identity(parent["recipe"]["identity"])
    reference.current_source_evidence(parent["recipe"])
    validate_fit_signatures(parent, evidence)
    epochs, selected = epoch_choice(parent)
    cache = fitting.Cache(args.cache)
    identity = parent["recipe"]["identity"]
    require(cache.source == identity["cache_manifest_sha256"] and sha256(args.labels) == identity["labels_sha256"]
            and sha256(args.folds) == identity["folds_sha256"], "Final fit inputs differ from evaluated CV")
    meta = fitting.align_metadata(cache, args.labels, args.folds)
    require(len(meta) == 121838 and int(meta.label.sum()) == 5475 and int(meta.gene_id.nunique()) == 3852,
            "Final fit needs the full unchanged data0 population")
    population = np.arange(len(meta), dtype=np.int64)
    require(fitting.index_hash(population) == parent["recipe"]["population_sha256"], "Changed final population order")
    for fold in range(5):
        *_, actual = fitting.partition(meta, population, fold)
        expected = read_json(CV_ROOT / ("none/fold%d/split_audit.json" % fold))
        require(actual == expected, "Actual data0 gene groups differ from saved assessment boundaries")
    cache_manifest = read_json(args.cache / "manifest.json")
    cache_hashes = dict(cache_manifest["cache_sha256"], **{"manifest.json": sha256(args.cache / "manifest.json")})
    guard = nomination_guard()
    frozen = dict(kind="original_cap128_weight3_final_wrapper_v1", wrapper_and_selection=guard,
                  cv_identity=identity, config=config, selected_epochs=selected, inner_selected_epochs=epochs,
                  seed=2026, batch_size=256, threads=4, patience=5,
                  full_data0_sites=len(meta), positives=int(meta.label.sum()), genes=int(meta.gene_id.nunique()),
                  all_data0_indices_sha256=fitting.index_hash(population), cv_evidence_sha256=evidence,
                  data0_cache_sha256=cache_hashes,
                  runtime_versions=versions(), final_destination="model_elgin/outputs/read_cap_v1/final/none",
                  rule="median of five inner-selected epochs; fresh all-data0 weights, no validation/stopping search",
                  provenance_note="training_entrypoint_sha256 in cv_identity is legacy CV provenance; actual final wrapper/plan are guarded separately")
    return cache, meta, config, identity, frozen, evidence


def unchanged(frozen, evidence, args):
    require(nomination_guard() == frozen["wrapper_and_selection"], "Final wrapper/selection plan changed during execution")
    check_cv_identity(frozen["cv_identity"])
    require(all(sha256(CV_ROOT / path) == digest for path, digest in evidence.items()), "Completed CV evidence changed")
    require(all(sha256(args.cache / name) == digest for name, digest in frozen["data0_cache_sha256"].items()),
            "Data0 cache changed during final phase")
    require(sha256(args.labels) == frozen["cv_identity"]["labels_sha256"]
            and sha256(args.folds) == frozen["cv_identity"]["folds_sha256"]
            and versions() == frozen["runtime_versions"], "Final inputs/environment changed")


def delegate_final(cache, meta, config, args, identity):
    require(config == dict(fitting.BASE, cap=128, context_mode="none", min_sites=30), "Invalid final config")
    return fitting.run_final(cache, meta, config, args, identity)


def execute(args):
    cache, meta, config, identity, frozen, evidence = preflight(args)
    directory = DEFAULT / "final_phase"
    specification = directory / "frozen_wrapper_specification.json"
    if args.fit:
        require(specification.exists(), "Run --check-only and review its frozen specification before --fit")
    immutable_json(specification, frozen)
    unchanged(frozen, evidence, args)
    print("Project stage: FINAL MODEL CHECK — original cap128/weight3; selected epochs %s -> %d." %
          (frozen["inner_selected_epochs"], frozen["selected_epochs"]), flush=True)
    if args.check_only:
        return dict(status="checked_no_fitting", frozen_specification_sha256=sha256(specification),
                    selected_epochs=frozen["selected_epochs"], wrapper_and_selection=frozen["wrapper_and_selection"])
    args.output_dir, args.seed, args.batch_size, args.threads = DEFAULT, 2026, 256, 4
    args.max_epochs, args.patience = 20, 5
    fitting.torch.set_num_threads(4)
    print("Project stage: FINAL ALL-DATA0 FIT — fresh seed2026, fixed %d epochs; no data1/inference." % frozen["selected_epochs"], flush=True)
    delegate_final(cache, meta, config, args, identity)
    unchanged(frozen, evidence, args)
    final = DEFAULT / "final/none"
    completed, promoted = read_json(final / "complete.json"), read_json(final / "frozen_model.json")
    require(completed["epochs_completed"] == frozen["selected_epochs"] and completed["best_epoch"] == frozen["selected_epochs"]
            and completed["config"] == config and completed["seed"] == 2026 and completed["train_sites"] == 121838
            and completed["validation_sites"] == 0 and completed["fit_indices_sha256"] == frozen["all_data0_indices_sha256"],
            "Final completion metadata differs from the frozen nomination")
    require(sha256(final / "model.pt") == promoted["model_sha256"]
            and sha256(final / "best.pt") == completed["best_sha256"]
            and sha256(final / "frozen_specification.json") == promoted["specification_sha256"], "Final artifact/promotion fingerprint mismatch")
    return dict(status="final_model_complete_no_predictions", selected_epochs=frozen["selected_epochs"],
                model_sha256=promoted["model_sha256"], wrapper_and_selection=frozen["wrapper_and_selection"],
                frozen_specification_sha256=sha256(specification), cv_evidence_sha256=evidence,
                no_data1=True, no_prediction=True, no_external_candidate=True,
                final_files_sha256={name: sha256(final / name) for name in
                    ("model.pt", "best.pt", "last.pt", "history.json", "training.log", "complete.json", "frozen_model.json", "frozen_specification.json")})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--fit", action="store_true")
    parser.add_argument("--cache", type=Path, default=REPO.parent / "advanced_model/cache/data0")
    parser.add_argument("--labels", type=Path, default=REPO.parent / "data0/data.info.labelled")
    parser.add_argument("--folds", type=Path, default=REPO / "eda/received/shared_folds/data0_folds.csv")
    args = parser.parse_args(argv)
    directory = DEFAULT / "final_phase"
    directory.mkdir(parents=True, exist_ok=True)
    with phase_lock(directory / "final.lock"):
        stamp = str(time.time_ns())
        invocation = dict(arguments=list(sys.argv[1:] if argv is None else argv),
                          phase="check_only" if args.check_only else "final_fit", no_data1=True)
        cap.save_json(directory / ("arguments_"+stamp+".json"), invocation)
        status = directory / "status.json"
        cap.save_json(status, dict(status="running", invocation=invocation))
        try:
            with cap.Measure() as measured:
                measured.output = directory / ("resources_"+stamp+".json")
                result = execute(args)
            result.update(invocation=invocation, wrapper_resources=measured.record,
                          resource_scope="Wrapper invocation, including preflight/core delegation; overlaps core fit timers, do not add totals")
            cap.save_json(directory / ("result_"+stamp+".json"), result)
            cap.save_json(status, result)
        except BaseException as error:
            result = dict(status="failed_or_interrupted", invocation=invocation, error=type(error).__name__+": "+str(error),
                          old_results_not_current=True)
            cap.save_json(directory / ("result_"+stamp+".json"), result)
            cap.save_json(status, result)
            raise
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    main()
