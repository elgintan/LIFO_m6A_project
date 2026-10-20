"""Score any m6Anet-format data.json (or .json.gz) with the frozen model. No labels needed.

Run from model_samuel/:

    python code/predict.py --input examples/input_10_sites.json --output predictions.csv

Writes transcript_id,transcript_position,score (one row per site, in input order).
"""
import argparse
import hashlib
import json
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from features import KEY, KmerBaseline, read_sites

HERE = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model-dir", default=HERE / "artifact")
    args = ap.parse_args()
    model_dir = Path(args.model_dir)
    output = Path(args.output)
    protected = [Path(args.input), *(model_dir / name for name in
                 ("model.txt", "kmer_baseline.csv", "model_card.json"))]
    if output.resolve() in {path.resolve() for path in protected}:
        raise SystemExit("output must not overwrite the input or saved model")
    card = json.loads((model_dir / "model_card.json").read_text())
    for name in ("model", "kmer_baseline"):
        path = model_dir / ("model.txt" if name == "model" else "kmer_baseline.csv")
        if hashlib.sha256(path.read_bytes()).hexdigest() != card[f"{name}_sha256"]:
            raise SystemExit(f"{path.name} does not match model_card.json")
    booster = lgb.Booster(model_file=str(model_dir / "model.txt"))
    baseline = KmerBaseline.from_frame(pd.read_csv(model_dir / "kmer_baseline.csv", index_col=[0, 1]),
                                       card["kmer_baseline_min_sites"])
    sites = read_sites(args.input)
    x, _ = baseline.transform(sites)
    sites["score"] = booster.predict(x[card["features"]])
    output.parent.mkdir(parents=True, exist_ok=True)
    sites[KEY + ["score"]].to_csv(output, index=False, float_format="%.17g")
    print(f"{len(sites)} sites scored -> {args.output}")


if __name__ == "__main__":
    main()
