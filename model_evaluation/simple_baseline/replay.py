"""Replay the fixed 18-feature balanced-C1 data0 baseline; no tuning/transfer."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time
import warnings

import numpy as np
import psutil
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCORER_PATH = HERE.parent / "evaluate.py"
SPEC = importlib.util.spec_from_file_location("simple_baseline_shared_scorer", SCORER_PATH)
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)
DATA_SHA = "622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e"
LABEL_SHA = "6758f002db36835c188c9d6fb039b4599494ca9dcc816c26cc22a2c04ee42978"
MEASUREMENTS = [m + "_" + p for p in ("minus1", "central", "plus1")
                for m in ("dwell_time", "signal_sd", "signal_mean")]
FEATURES = ["mean_across_reads__" + m for m in MEASUREMENTS] + ["sd_across_reads__" + m for m in MEASUREMENTS]
PARAMETERS = dict(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=1000,
                  tol=1e-4, random_state=42, fit_intercept=True, warm_start=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def atomic_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=str(path.parent), prefix=".lr_", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        for attempt in range(8):
            try:
                os.replace(str(temporary), str(path))
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(.05 * (attempt + 1))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def log(output, message):
    print(message, flush=True)
    with (Path(output) / "training.log").open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


class Meter:
    """This-process wall/CPU/RSS measurement, not a monetary cloud estimate."""
    def __enter__(self):
        self.wall, self.cpu = time.perf_counter(), time.process_time()
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.errors = 0
        self.stop = threading.Event()
        def sample():
            while not self.stop.wait(.1):
                try:
                    self.peak = max(self.peak, self.process.memory_info().rss)
                except psutil.Error:
                    self.errors += 1
        self.worker = threading.Thread(target=sample, daemon=True)
        self.worker.start()
        return self

    def __exit__(self, *unused):
        self.stop.set(); self.worker.join()
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.record = dict(wall_seconds=time.perf_counter()-self.wall,
                           process_cpu_seconds=time.process_time()-self.cpu,
                           sampled_peak_process_rss_mib=self.peak / 1024**2,
                           sampling_interval_seconds=.1, sampling_errors=self.errors)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON object key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def one(mapping, description):
    require(isinstance(mapping, dict) and len(mapping) == 1, "Expected exactly one " + description)
    return next(iter(mapping.items()))


def extract_features(path, keys):
    """All raw reads -> float64 means and population SD; invalid rows abort."""
    index = {key: i for i, key in enumerate(keys)}
    require(len(index) == len(keys), "Duplicate expected site key")
    features = np.full((len(keys), 18), np.nan, dtype=np.float64)
    counts = np.zeros(len(keys), dtype=np.int64)
    seen = set()
    with Path(path).open("rb") as raw:
        magic = raw.read(2)
    opener = gzip.open if magic == b"\x1f\x8b" else open
    blank = 0
    with opener(str(path), "rt", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                blank += 1
                continue
            record = json.loads(line, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
            transcript, positions = one(record, "transcript")
            position, contexts = one(positions, "position")
            context, reads = one(contexts, "sequence context")
            key = SCORER.site_key(dict(transcript_id=transcript, transcript_position=position))
            require(key in index and key not in seen, "Unexpected/duplicate raw site at line " + str(line_number))
            require(isinstance(context, str) and len(context) == 7, "Expected a seven-base context")
            require(isinstance(reads, list) and bool(reads), "Empty or malformed read bag")
            values = np.asarray(reads)
            require(values.ndim == 2 and values.shape[1] == 9 and values.dtype.kind in "fiu",
                    "Every read must contain nine numeric measurements")
            # NumPy promotes mixed booleans/numbers. Check that rare JSON case
            # explicitly without a Python loop over every ordinary numeric read.
            if "true" in line or "false" in line:
                require(not any(isinstance(x, bool) for row in reads for x in row), "Boolean measurement")
            values = values.astype(np.float64, copy=False)
            require(np.isfinite(values).all(), "Non-finite raw measurement")
            at = index[key]
            features[at] = np.concatenate((values.mean(axis=0), values.std(axis=0, ddof=0)))
            counts[at] = len(values)
            seen.add(key)
    require(len(seen) == len(keys) and np.isfinite(features).all(), "Raw data does not cover every expected site")
    return features, counts, dict(n_sites=len(keys), n_reads=int(counts.sum()), blank_lines=blank,
                                 feature_dtype="float64", feature_names=FEATURES,
                                 feature_definition="all nine raw means followed by population SDs, ddof0; no transforms/filtering")


def align_metadata(labels, genes, folds):
    SCORER.same_keys(labels, folds, "Labels/folds")
    require(set(genes) == set(labels), "Every site needs a label gene")
    keys = list(folds)
    require(all(genes[key] == folds[key][0] for key in keys), "Label/fold gene mismatch")
    y = np.asarray([labels[key] for key in keys], dtype=np.int64)
    assigned = np.asarray([folds[key][1] for key in keys], dtype=np.int64)
    gene_values = np.asarray([folds[key][0] for key in keys])
    require(set(assigned) == set(range(5)), "Need all five fixed folds")
    require(all(len(set(assigned[gene_values == gene])) == 1 for gene in set(gene_values)), "A gene crosses folds")
    return keys, y, assigned, gene_values


def partition(y, assigned, genes, fold):
    require(fold in range(5), "Invalid fold")
    train, assessment = np.flatnonzero(assigned != fold), np.flatnonzero(assigned == fold)
    require(len(train) and len(assessment), "Empty training/assessment partition")
    require(not set(genes[train]) & set(genes[assessment]), "Gene leakage")
    require(set(y[train]) == {0, 1} and set(y[assessment]) == {0, 1}, "Both classes required in every partition")
    def describe(indices):
        return dict(sites=len(indices), positives=int(y[indices].sum()), genes=sorted(set(genes[indices])),
                    indices_sha256=hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest())
    return train, assessment, dict(fold_id=fold, zero_gene_overlap=True,
                                    training=describe(train), assessment=describe(assessment))


def model_parameters():
    parameters = dict(PARAMETERS)
    # sklearn1.9 uses l1_ratio=0 for L2; older compatible versions use penalty.
    default = inspect.signature(LogisticRegression).parameters["penalty"].default
    parameters.update(dict(l1_ratio=0.) if default == "deprecated" else dict(penalty="l2"))
    return parameters


def fit_model(features, y, train):
    model = make_pipeline(StandardScaler(), LogisticRegression(**model_parameters()))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(features[train], y[train])
    messages = [type(w.message).__name__ + ": " + str(w.message) for w in caught]
    require(not any(isinstance(w.message, ConvergenceWarning) for w in caught), "Baseline did not converge; no completed fold promoted")
    return model, messages


def export_model(model, identity):
    scaler, classifier = model[0], model[-1]
    require(list(classifier.classes_) == [0, 1], "Wrong classifier classes")
    return dict(kind="fixed18_balancedC1_fold_v1", feature_names=FEATURES, identity=identity,
                scaler_mean=scaler.mean_.tolist(), scaler_scale=scaler.scale_.tolist(),
                scaler_variance=scaler.var_.tolist(), scaler_samples_seen=int(scaler.n_samples_seen_),
                coef=classifier.coef_[0].tolist(), intercept=float(classifier.intercept_[0]),
                classes=classifier.classes_.tolist(), n_iter=int(classifier.n_iter_[0]),
                effective_parameters=model_parameters())


def predict_artifact(artifact, features):
    require(artifact["feature_names"] == FEATURES and artifact["classes"] == [0, 1], "Artifact schema mismatch")
    vectors = [np.asarray(artifact[name], dtype=np.float64) for name in ("scaler_mean", "scaler_scale", "coef")]
    require(all(x.shape == (18,) and np.isfinite(x).all() for x in vectors) and (vectors[1] > 0).all(), "Invalid artifact vectors")
    require(features.ndim == 2 and features.shape[1] == 18 and np.isfinite(features).all()
            and np.isfinite(float(artifact["intercept"])), "Invalid features/intercept")
    z = ((features-vectors[0])/vectors[1]).dot(vectors[2]) + float(artifact["intercept"])
    scores = np.empty_like(z)
    positive = z >= 0
    scores[positive] = 1/(1+np.exp(-z[positive]))
    exp_z = np.exp(z[~positive]); scores[~positive] = exp_z/(1+exp_z)
    return scores


def prediction_text(keys, scores, assigned):
    require(len(keys) == len(scores) == len(assigned), "Prediction lengths differ")
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["transcript_id", "transcript_position", "score", "fold_id"])
    for key, score, fold in zip(keys, scores, assigned):
        require(np.isfinite(score) and 0 <= score <= 1, "Invalid prediction score")
        writer.writerow([key[0], key[1], repr(float(score)), int(fold)])
    return handle.getvalue()


def run_fold(output, features, y, assigned, genes, keys, fold, identity, threads=2):
    train, assessment, split = partition(y, assigned, genes, fold)
    fold_identity = dict(run=identity, split=split)
    signature = fingerprint(fold_identity)
    folder = Path(output) / ("fold" + str(fold))
    folder.mkdir(parents=True, exist_ok=True)
    complete = folder / "complete.json"
    paths = {name: folder / name for name in ("model.json", "predictions.csv", "split_audit.json")}
    if complete.exists():
        receipt = read_json(complete)
        require(receipt["signature"] == signature and receipt["identity"] == fold_identity, "Completed fold identity differs; choose a new output")
        require(all(SCORER.sha256(paths[name]) == digest for name, digest in receipt["output_sha256"].items()), "Completed fold artifact changed")
        require(read_json(paths["split_audit.json"]) == split, "Changed split audit")
        predicted, prediction_folds = SCORER.read_predictions(paths["predictions.csv"], "data0")
        expected_keys = [keys[i] for i in assessment]
        require(set(predicted) == set(expected_keys) and all(prediction_folds[key] == fold for key in expected_keys), "Wrong completed assessment sites")
        scores = np.asarray([predicted[key] for key in expected_keys])
        require(SCORER.metrics(y[assessment], scores) == receipt["metrics"], "Changed completed metrics")
        return scores, receipt, True
    began = time.time_ns()
    invocation_path = folder / ("invocation_" + str(began) + ".json")
    meter = Meter()
    try:
        with meter, threadpool_limits(limits=threads):
            model, messages = fit_model(features, y, train)
            scores = model.predict_proba(features[assessment])[:, 1]
            artifact = export_model(model, fold_identity)
            require(np.max(np.abs(scores-predict_artifact(artifact, features[assessment]))) <= 1e-12, "JSON artifact/pipeline score disagreement")
            metrics = SCORER.metrics(y[assessment], scores)
        write_json(paths["model.json"], artifact)
        write_json(paths["split_audit.json"], split)
        atomic_bytes(paths["predictions.csv"], prediction_text([keys[i] for i in assessment], scores, assigned[assessment]).encode())
        receipt = dict(status="complete", signature=signature, identity=fold_identity, metrics=metrics,
                       fit_warnings=messages, n_iter=artifact["n_iter"], resources=meter.record,
                       output_sha256={name: SCORER.sha256(path) for name, path in paths.items()})
        write_json(invocation_path, dict(status="complete", resources=meter.record, signature=signature))
        write_json(complete, receipt)
        return scores, receipt, False
    except BaseException as error:
        write_json(invocation_path, dict(status="failed_or_interrupted", error=type(error).__name__+": "+str(error),
                                         signature=signature, resources=getattr(meter, "record", None)))
        raise


def prepare_features(data_path, keys, output, identity):
    folder = Path(output) / "features"
    folder.mkdir(parents=True, exist_ok=True)
    arrays_path, receipt_path = folder / "raw18_float64.npz", folder / "complete.json"
    feature_identity = dict(input_sha256=identity["input_sha256"], source_sha256=identity["source_sha256"],
                            feature_names=FEATURES, key_order_sha256=fingerprint(keys), numpy=np.__version__)
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        require(receipt["identity"] == feature_identity and SCORER.sha256(arrays_path) == receipt["arrays_sha256"], "Feature cache identity/hash changed")
        with np.load(str(arrays_path), allow_pickle=False) as saved:
            features, counts = saved["features"], saved["read_counts"]
        require(features.dtype == np.float64 and features.shape == (len(keys), 18) and np.isfinite(features).all()
                and counts.shape == (len(keys),) and (counts > 0).all(), "Invalid cached raw features")
        return features, receipt, True
    with Meter() as meter:
        features, counts, audit = extract_features(data_path, keys)
    buffer = io.BytesIO(); np.savez(buffer, features=features, read_counts=counts)
    atomic_bytes(arrays_path, buffer.getvalue())
    receipt = dict(status="complete", identity=feature_identity, arrays_sha256=SCORER.sha256(arrays_path),
                   audit=audit, resources=meter.record)
    write_json(receipt_path, receipt)
    return features, receipt, False


def versions():
    return dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                scikit_learn=sklearn.__version__, psutil=psutil.__version__)


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def execute(args):
    input_paths = dict(data=args.data, labels=args.labels, folds=args.folds)
    hashes = {name: SCORER.sha256(path) for name, path in input_paths.items()}
    require(hashes == dict(data=DATA_SHA, labels=LABEL_SHA, folds=SCORER.FOLD_SHA256), "Expected exactly the pinned data0 raw signals/labels/folds")
    labels, genes = SCORER.read_labels(args.labels)
    folds = SCORER.read_folds(args.folds)
    keys, y, assigned, gene_values = align_metadata(labels, genes, folds)
    require(len(keys) == 121838 and int(y.sum()) == 5475 and len(set(gene_values)) == 3852, "Wrong full data0 population")
    require(SCORER.canonical_labels_hash(labels, folds) == SCORER.DATA0_LABELS_CANONICAL_SHA256, "Changed canonical labels/genes")
    sources = dict(replay_py=SCORER.sha256(__file__), shared_scorer=SCORER.sha256(SCORER_PATH))
    identity = dict(kind="fixed18_balanced_C1_replay_v1", input_sha256=hashes, source_sha256=sources,
                    versions=versions(), parameters=model_parameters(), threads=args.threads,
                    feature_names=FEATURES, training="fixed configuration; each fresh four-group fit assesses excluded gene group")
    identity_path = args.output_dir / "run_identity.json"
    if identity_path.exists():
        require(read_json(identity_path) == identity, "Run identity changed; use a fresh output directory")
    else:
        write_json(identity_path, identity)
    features, feature_receipt, feature_reused = prepare_features(args.data, keys, args.output_dir, identity)
    require(feature_receipt["audit"]["n_reads"] == 11027106, "Wrong complete data0 read population")
    require(all(SCORER.sha256(path) == hashes[name] for name, path in input_paths.items())
            and SCORER.sha256(__file__) == sources["replay_py"] and SCORER.sha256(SCORER_PATH) == sources["shared_scorer"], "Inputs/source changed during feature preparation")
    log(args.output_dir, "Float64 raw18 features ready: %d sites; reused=%s" % (len(keys), feature_reused))
    if args.phase == "prepare":
        return dict(status="features_prepared_no_fitting", identity=identity, feature_receipt=feature_receipt,
                    feature_cache_reused=feature_reused)
    scores = np.full(len(keys), np.nan)
    receipts = []
    fit_identity = dict(identity, feature_arrays_sha256=feature_receipt["arrays_sha256"])
    for fold in range(5):
        selected, receipt, reused = run_fold(args.output_dir, features, y, assigned, gene_values, keys, fold, fit_identity, args.threads)
        scores[assigned == fold] = selected
        receipts.append(dict(fold_id=fold, reused=reused, complete_sha256=SCORER.sha256(args.output_dir / ("fold%d/complete.json" % fold))))
        log(args.output_dir, "Fold%d: S=%.10f; reused=%s" % (fold, receipt["metrics"]["selection_score"], reused))
    prediction_path = args.output_dir / "data0_oof.csv"
    atomic_bytes(prediction_path, prediction_text(keys, scores, assigned).encode())
    metrics = SCORER.evaluate_files(args.labels, prediction_path, "data0", folds_path=args.folds)
    write_json(args.output_dir / "data0_cv_metrics.json", metrics)
    require(all(SCORER.sha256(path) == hashes[name] for name, path in input_paths.items())
            and SCORER.sha256(__file__) == sources["replay_py"] and SCORER.sha256(SCORER_PATH) == sources["shared_scorer"], "Inputs/source changed during replay")
    return dict(status="complete", identity=fit_identity, feature_cache_reused=feature_reused,
                feature_receipt_sha256=SCORER.sha256(args.output_dir / "features/complete.json"),
                folds=receipts, mean_fold=metrics["mean_fold"], pooled=metrics["pooled"],
                output_sha256={p: SCORER.sha256(args.output_dir / p) for p in ("data0_oof.csv", "data0_cv_metrics.json")},
                no_tuning=True, no_final_all_data0_fit=True, no_data1_or_data2=True,
                limitations=["Previously selected historical B recipe, replayed without a new search.",
                             "Development gene folds; no blind final or transfer result.",
                             "Float64 raw extraction avoids the neural cache's float32 rounding.",
                             "Library/hardware changes can alter final floating-point digits.",
                             "Per-fold timers include scaling, fit, prediction, JSON parity and metrics; exclude file writes."])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "cv"), default="cv")
    parser.add_argument("--data", type=Path, default=REPO.parent / "data0/dataset0.json.gz")
    parser.add_argument("--labels", type=Path, default=REPO.parent / "data0/data.info.labelled")
    parser.add_argument("--folds", type=Path, default=REPO / "eda/received/shared_folds/data0_folds.csv")
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs/replay_v1")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    require(inside(args.output_dir, HERE / "outputs") and args.threads == 2,
            "Output must stay under simple_baseline/outputs; the fixed recipe uses exactly two threads")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = args.output_dir / "run.lock"
    # Never infer stale-lock ownership from a PID in another tool namespace.
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError:
        parser.exit(2, "Run lock exists. Confirm the original session ended before explicitly removing only that lock.\n")
    stamp = str(time.time_ns())
    command = dict(executable=sys.executable, arguments=list(sys.argv[1:] if argv is None else argv), phase=args.phase)
    status_path = args.output_dir / "status.json"
    try:
        write_json(args.output_dir / ("arguments_"+stamp+".json"), command)
        write_json(status_path, dict(status="running", phase=args.phase))
        log(args.output_dir, "Invocation " + stamp + ": " + json.dumps(command))
        with lock, Meter() as meter:
            lock.write(json.dumps(dict(pid=os.getpid(), invocation=stamp))); lock.flush()
            result = execute(args)
        result["invocation_resources"] = meter.record
        result["invocation"] = command
        write_json(args.output_dir / ("invocation_"+stamp+".json"), result)
        write_json(status_path, result)
        print(json.dumps(dict(status=result["status"], resources=meter.record)), flush=True)
        return 0
    except BaseException as error:
        result = dict(status="failed_or_interrupted", error=type(error).__name__+": "+str(error), invocation=command,
                      resources=getattr(locals().get("meter"), "record", None), prior_aggregate_outputs_non_authoritative=True)
        write_json(args.output_dir / ("invocation_"+stamp+".json"), result)
        write_json(status_path, result)
        raise
    finally:
        lock.close()
        lock_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
