"""Samuel's candidate under the shared rules (model_evaluation/SHARED_RULES.md).

Run from model_samuel/:

    python code/train.py --data0 PATH/dataset0.json.gz --labels PATH/data.info.labelled \
        --folds PATH/data0_folds.csv --out outputs --model-dir artifact

1. Five outer rounds on the exact shared gene folds: for fold f, fit the 7-mer
   baseline and the LightGBM model on folds != f only, then score fold f.
   Writes outputs/data0_oof.csv (transcript_id,transcript_position,score,fold_id).
2. Fits the same configuration afresh on all data0, saves it and records its
   SHA256 in artifact/model_card.json. data1 is scored only afterwards, by predict.py.
No hyperparameter search and no early stopping: the configuration is fixed, so
no inner validation fold is needed.
"""
import argparse
import hashlib
import json
import platform
try:
    import resource
except ImportError:  # Windows has no resource module; do not invent a measurement.
    resource = None
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn

from features import BASES, KEY, NUMERIC, KmerBaseline, read_sites

FOLD_SHA256 = "986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0"
MIN_SITES = 50
PARAMS = dict(n_estimators=1500, learning_rate=0.02, num_leaves=31, min_child_samples=50, reg_lambda=5.0,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, deterministic=True, force_row_wise=True,
              verbose=-1)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def peak_ram_mib():
    if resource is None:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(rss / (2**20 if sys.platform == "darwin" else 2**10), 1)


def fit(train, seed, threads):
    baseline = KmerBaseline(MIN_SITES).fit(train)
    x, _ = baseline.transform(train)
    model = lgb.LGBMClassifier(**PARAMS, random_state=seed, n_jobs=threads).fit(x, train.label)
    return baseline, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data0", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--model-dir", default="artifact")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--cv-only", action="store_true", help="out-of-fold run only, e.g. for a repeat-seed check; no final model")
    args = ap.parse_args()
    out, model_dir = Path(args.out), Path(args.model_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    log = []

    if sha256(args.folds) != FOLD_SHA256:
        raise SystemExit("fold file differs from the agreed shared file; restore it from GitHub")
    t0 = time.perf_counter()
    sites = read_sites(args.data0)
    log.append({"stage": "read_data0", "seconds": round(time.perf_counter() - t0, 1), "sites": len(sites)})
    labels = pd.read_csv(args.labels)[KEY + ["label"]]
    folds = pd.read_csv(args.folds)[KEY + ["fold_id"]]
    df = sites.merge(labels, on=KEY, how="outer", validate="one_to_one", indicator=True)
    if not (df._merge == "both").all():
        raise SystemExit(f"sites and labels do not match: {df._merge.value_counts().to_dict()}")
    df = df.drop(columns="_merge").merge(folds, on=KEY, how="left", validate="one_to_one")
    if df.fold_id.isna().any() or sorted(df.fold_id.unique()) != [0, 1, 2, 3, 4]:
        raise SystemExit("every data0 site needs a fold 0-4 from the shared file")
    if set(df.label.unique()) != {0, 1}:
        raise SystemExit("data0 labels must be binary")
    print(f"{len(df)} sites, {df.label.mean():.4f} positive, {len(NUMERIC) + len(BASES)} features", flush=True)

    oof = np.full(len(df), np.nan)
    for fold in range(5):
        t0 = time.perf_counter()
        held = (df.fold_id == fold).values
        baseline, model = fit(df[~held], args.seed, args.threads)
        x, level = baseline.transform(df[held])
        oof[held] = model.predict_proba(x)[:, 1]
        log.append({"stage": f"cv_fold_{fold}", "seconds": round(time.perf_counter() - t0, 1),
                    "train_sites": int((~held).sum()), "assessed_sites": int(held.sum()),
                    "reference_levels": pd.Series(level).value_counts().to_dict(), "peak_ram_mib": peak_ram_mib()})
        print(f"fold {fold} done in {log[-1]['seconds']} s", flush=True)
    assert np.isfinite(oof).all()
    df.assign(score=oof)[KEY + ["score", "fold_id"]].to_csv(out / "data0_oof.csv", index=False, float_format="%.17g")

    if args.cv_only:
        (out / "cv_log.json").write_text(json.dumps({"seed": args.seed, "log": log}, indent=2))
        print(f"out-of-fold scores -> {out / 'data0_oof.csv'} (no final model, --cv-only)")
        return
    t0 = time.perf_counter()
    baseline, model = fit(df, args.seed, args.threads)
    model.booster_.save_model(model_dir / "model.txt")
    baseline.to_frame().to_csv(model_dir / "kmer_baseline.csv", float_format="%.17g")
    log.append({"stage": "final_fit_all_data0", "seconds": round(time.perf_counter() - t0, 1), "peak_ram_mib": peak_ram_mib()})
    card = {
        "model": "LightGBM on 7-mer-relative read-distribution summaries + 7 bases",
        "features": NUMERIC + BASES, "kmer_baseline_min_sites": MIN_SITES,
        "params": PARAMS, "seed": args.seed, "threads": args.threads,
        "model_sha256": sha256(model_dir / "model.txt"), "kmer_baseline_sha256": sha256(model_dir / "kmer_baseline.csv"),
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs_sha256": {"data0": sha256(args.data0), "labels": sha256(args.labels), "folds": sha256(args.folds)},
        "versions": {"python": platform.python_version(), "lightgbm": lgb.__version__, "sklearn": sklearn.__version__,
                     "pandas": pd.__version__, "numpy": np.__version__, "os": platform.platform()},
        "log": log,
    }
    (model_dir / "model_card.json").write_text(json.dumps(card, indent=2))
    print(f"frozen model {card['model_sha256'][:12]}… saved to {model_dir}")


if __name__ == "__main__":
    main()
