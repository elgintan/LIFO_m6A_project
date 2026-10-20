"""Local mirror of model_evaluation/evaluate.py, for use until the official scorer is run.

Same metric definitions (ROC AUC, trapezoidal PR AUC from precision_recall_curve
with drop_intermediate=False, average precision, S = (ROC + PR) / 2, threshold 0.5).
Results written here are marked "local_mirror"; the official JSON comes from the
shared scorer.

    python code/score_local.py --dataset data0 --labels L --predictions outputs/data0_oof.csv --folds F --output results/data0_local.json
    python code/score_local.py --dataset data1 --labels L --predictions outputs/data1_predictions.csv --output results/data1_local.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import auc, average_precision_score, precision_recall_curve, roc_auc_score

KEY = ["transcript_id", "transcript_position"]


def metrics(y, s):
    p, r, _ = precision_recall_curve(y, s, drop_intermediate=False)
    roc, pr = roc_auc_score(y, s), auc(r, p)
    tp = int(((s >= .5) & (y == 1)).sum()); fp = int(((s >= .5) & (y == 0)).sum())
    return {"n_sites": int(len(y)), "n_positives": int(y.sum()), "roc_auc": float(roc), "pr_auc_trapezoid": float(pr),
            "average_precision": float(average_precision_score(y, s)), "selection_score": float((roc + pr) / 2),
            "precision_at_0.5": tp / (tp + fp) if tp + fp else 0.0, "recall_at_0.5": tp / int(y.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=("data0", "data1"), required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--folds")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    labels = pd.read_csv(a.labels)[KEY + ["label"]]
    pred = pd.read_csv(a.predictions)
    df = labels.merge(pred, on=KEY, how="outer", validate="one_to_one", indicator=True)
    assert (df._merge == "both").all(), df._merge.value_counts().to_dict()
    assert df.score.between(0, 1).all()
    out = {"scorer": "local_mirror", "dataset": a.dataset, "pooled": metrics(df.label.values, df.score.values)}
    if a.dataset == "data0":
        folds = pd.read_csv(a.folds)[KEY + ["fold_id"]]
        df = df.merge(folds, on=KEY, suffixes=("", "_shared"))
        assert (df.fold_id == df.fold_id_shared).all(), "prediction fold_id differs from the shared folds"
        per = [{"fold_id": f, **metrics(g.label.values, g.score.values)} for f, g in df.groupby("fold_id")]
        names = ("roc_auc", "pr_auc_trapezoid", "average_precision", "selection_score")
        out["per_fold"] = per
        out["mean_fold"] = {n: float(np.mean([r[n] for r in per])) for n in names}
        out["sample_sd_fold"] = {n: float(np.std([r[n] for r in per], ddof=1)) for n in names}
        out["primary_score"] = out["mean_fold"]["selection_score"]
    else:
        out["primary_score"] = out["pooled"]["selection_score"]
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k in ("mean_fold", "sample_sd_fold", "primary_score")} or out["pooled"], indent=1))


if __name__ == "__main__":
    main()
