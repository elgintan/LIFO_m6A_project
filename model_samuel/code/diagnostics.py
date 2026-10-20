"""Subgroup and data2 diagnostics for Samuel's candidate, against the 5 October 18-feature LightGBM.

Run from model_samuel/ after train.py and predict.py:

    python code/diagnostics.py --data0-labels L0 --folds F --old-oof ../team_protocol/lightgbm_out/data0_oof_predictions.csv --data2-labels L2

Writes results/subgroups.csv (out-of-fold, data0) and results/data2_summary.csv. data2 labels are
fractional, so only descriptive summaries are reported for it, no binary metrics.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

from features import KEY

ap = argparse.ArgumentParser()
ap.add_argument("--data0-labels", required=True)
ap.add_argument("--old-oof", required=True)
ap.add_argument("--data2-labels", required=True)
ap.add_argument("--data0-sites", default="../data/cache/sites0.parquet", help="cached 7-mer and read counts")
a = ap.parse_args()

sites = pd.read_parquet(a.data0_sites, columns=KEY + ["kmer", "n_reads"])
df = (sites.merge(pd.read_csv(a.data0_labels)[KEY + ["label"]], on=KEY)
      .merge(pd.read_csv("outputs/data0_oof.csv")[KEY + ["score"]], on=KEY)
      .merge(pd.read_csv(a.old_oof)[KEY + ["score"]].rename(columns={"score": "old"}), on=KEY))
assert len(df) == len(sites)
df["motif"] = df.kmer.str[1:6]
df["reads"] = pd.cut(df.n_reads, [19, 30, 50, 100, 200, 1000], labels=["20-30", "31-50", "51-100", "101-200", "201+"]).astype(str)


def row(g):
    ok = g.label.sum() >= 20
    out = {"n_sites": len(g), "n_positives": int(g.label.sum())}
    for name, col in (("new", "score"), ("old_18_features", "old")):
        out[f"roc_auc_{name}"] = roc_auc_score(g.label, g[col]) if ok else np.nan
        out[f"avg_precision_{name}"] = average_precision_score(g.label, g[col]) if ok else np.nan
        out[f"recall_at_0.5_{name}"] = ((g[col] >= .5) & (g.label == 1)).sum() / max(g.label.sum(), 1)
    return pd.Series(out)


sub = pd.concat([df.groupby("motif").apply(row).assign(group_type="motif"),
                 df.groupby("reads").apply(row).assign(group_type="reads per site")]).rename_axis("group").reset_index()
Path("results").mkdir(exist_ok=True)
sub.to_csv("results/subgroups.csv", index=False)
pd.set_option("display.width", 220)
print(sub.round(3).to_string(index=False))

d2 = pd.read_csv("outputs/data2_predictions.csv").merge(pd.read_csv(a.data2_labels)[KEY + ["label"]], on=KEY)
summary = d2.groupby("label").score.agg(["size", "mean", "median"])
summary.to_csv("results/data2_summary.csv")
print("\ndata2 (descriptive only):\n", summary.round(3), "\nSpearman correlation with supplied fraction:",
      round(spearmanr(d2.label, d2.score)[0], 3))
