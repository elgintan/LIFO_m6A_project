"""Build the data files the Task 2 visualisation reads.

Inputs
  --public            public SG-NEx files from fetch_public_data.py (read counts, annotation)
  --sample-metadata   run metadata from the official SG-NEx sample sheet
                      (Member 4's sample_manifest.csv)
  --predictions       optional: a hand-off folder that passed validate_task2_inputs.py
                      (team manifest.csv, MODEL_INFO.md, one CSV per run). Without it the
                      site is built in coverage-only mode: real read counts, no m6A scores.
  --score-status      exploratory | final, required with --predictions; controls how the
                      page labels the scores
  --member4-support   optional: Member 4's replicate_coverage_support.csv, compared with
                      this pipeline's own counts as an independent cross-check
  --member4-aliases   optional: Member 4's transcript_aliases_checked.csv, compared with
                      this pipeline's alias table

Outputs
  <out>/overview.json, genes_index.json, tx_index.json, genes_lowcov.json, genes/bNNN.json
  <reports>/transcript_aliases.csv   explicit raw -> joined transcript IDs, with Ensembl 91 checks
  <reports>/crosscheck_member4.json  agreement with Member 4's independent counts

Sites shipped to the browser: every site with at least --keep-min-reads reads in at
least one run (default 20, the training data's minimum). Summary numbers use all sites.

Usage (coverage-only):
  python scripts/build_site_data.py --public public_data \
      --sample-metadata team_inputs/member4_2026-10-19/sample_manifest.csv --out site/data
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import shutil
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task2lib as lib  # noqa: E402

PIPELINE_VERSION = "0.2.0"
LADDER_EDGES = [2, 5, 10, 20, 50, 100, 200, 500]          # bins: 1 | 2-4 | 5-9 | ... | 500+
LADDER_LABELS = ["1", "2–4", "5–9", "10–19", "20–49", "50–99", "100–199", "200–499", "500+"]
COVER_THRESHOLDS = [1, 5, 10, 20, 50, 100]
SHARE_THRESHOLDS = [5, 10, 20, 50]
OVERLAP_THRESHOLDS = [5, 10, 20, 50]
SUPPORT_THRESHOLDS = [20, 50, 100]
COMPARE_THRESHOLDS = [20, 50, 100]
AGREE_BINS = [(20, 50, "20–49"), (50, 100, "50–99"), (100, 10**9, "100+")]
HIGH_SCORE = 0.5
EXAMPLE_CANDIDATES = ["ACTB", "EEF1A1", "MALAT1", "GAPDH", "MYC", "HSP90AB1", "FTL", "EEF2",
                      "RPLP0", "TPT1", "NCL", "HNRNPA1", "TP53", "KRT18"]
N_BUCKETS = 128
SPIKE_LABELS = {"spike_SIRV": "SIRV spike-in controls", "spike_ERCC": "ERCC spike-in controls",
                "spike_sequin": "Sequin spike-in controls"}
KIND_NAMES = ["annotated", "alt_haplotype", "spike_SIRV", "spike_ERCC", "spike_sequin", "other"]
POS_BITS = 24


def site_key(tx_code: np.ndarray, pos: np.ndarray) -> np.ndarray:
    return (tx_code.astype(np.int64) << POS_BITS) | pos.astype(np.int64)


def bucket_of(key: str) -> int:
    return zlib.crc32(key.encode()) % N_BUCKETS


def upset(masks: pd.Series, lines: list[str], top: int = 15) -> list[dict]:
    vc = masks[masks > 0].value_counts().head(top)
    return [{"lines": [lines[i] for i in range(len(lines)) if m >> i & 1], "n": int(n)} for m, n in vc.items()]


def alias_table(aliases: dict, ann: pd.DataFrame) -> pd.DataFrame:
    """Explicit alias rows with an Ensembl 91 check for each one."""
    ver = dict(zip(ann.transcript_id, ann.tx_version))
    rows = []
    for run_id, amap in aliases.items():
        for raw, base in sorted(amap.items()):
            in_table = base in ver
            match = in_table and ver[base] == raw
            evidence = ("version equals the Ensembl 91 primary annotation" if match else
                        "transcript in Ensembl 91 with a different version; not joined" if in_table else
                        "not in the Ensembl 91 primary annotation; joined by ID, shown as unannotated")
            rows.append({"run_id": run_id, "raw_transcript_id": raw, "transcript_id": base,
                         "in_ensembl91_primary": in_table, "version_matches_ensembl91": match, "evidence": evidence})
    return pd.DataFrame(rows, columns=["run_id", "raw_transcript_id", "transcript_id",
                                       "in_ensembl91_primary", "version_matches_ensembl91", "evidence"])


def load_predictions(pred_dir: Path, runs: pd.DataFrame, aliases: dict, tx_cats: pd.Index, key_index: pd.Index,
                     site_codes: np.ndarray, run_idx: np.ndarray, nreads: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Long table of scored (site, run) pairs with read counts, read through the team manifest."""
    man = lib.read_manifest(pred_dir / "manifest.csv").set_index("run_id")
    versions = sorted(set(man.model_version))
    if len(versions) != 1 or "PENDING" in versions[0].upper():
        raise SystemExit(f"manifest model_version is {versions}; run validate_task2_inputs.py first")
    frames = []
    for r in runs.itertuples():
        if r.run_id not in man.index or not (pred_dir / man.loc[r.run_id, "prediction_file"]).exists():
            print(f"  note: no predictions for {r.run_id}; it will show read counts only")
            continue
        path = pred_dir / man.loc[r.run_id, "prediction_file"]
        pred = pd.read_csv(path, dtype={"transcript_id": "string", "transcript_position": "int64", "score": "float64"})
        if list(pred.columns) != lib.PRED_COLUMNS or not pred.score.between(0, 1).all():
            raise SystemExit(f"{path}: failed basic checks; run validate_task2_inputs.py first")
        amap = aliases.get(r.run_id, {})
        tx = pred.transcript_id.map(lambda t: amap.get(t, t)) if amap else pred.transcript_id
        codes = pd.Categorical(tx, categories=tx_cats).codes.astype(np.int64)
        sc = key_index.get_indexer(site_key(codes, pred.transcript_position.to_numpy()))
        if (codes < 0).any() or (sc < 0).any():
            raise SystemExit(f"{path}: sites missing from SG-NEx read counts; run validate_task2_inputs.py first")
        m = run_idx == r.idx
        n = pd.Series(nreads[m], index=site_codes[m]).reindex(sc).to_numpy()
        if np.isnan(n.astype(float)).any():
            raise SystemExit(f"{path}: scored sites not present in this run; run validate_task2_inputs.py first")
        frames.append(pd.DataFrame({"site": sc, "run_idx": np.int16(r.idx), "score": pred.score.to_numpy(np.float64),
                                    "n": n.astype(np.int32)}))
    pr = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["site", "run_idx", "score", "n"])
    info = {"model_versions": versions,
            "min_reads": sorted({int(float(x)) for x in man.min_reads if str(x).strip()}),
            "n_runs_with_predictions": len(frames),
            "model_info": (pred_dir / "MODEL_INFO.md").read_text()[:4000] if (pred_dir / "MODEL_INFO.md").exists() else ""}
    return pr, info


def group_mean(pr: pd.DataFrame, runs: pd.DataFrame, min_reads: int) -> pd.DataFrame:
    """Score per (site, replicate group): mean over the group's runs with enough reads."""
    meta = runs.set_index("idx")
    q = pr[pr.n >= min_reads]
    return (q.assign(gidx=meta.gidx.reindex(q.run_idx).to_numpy())
             .groupby(["site", "gidx"]).score.mean().rename("score").reset_index())


def compare_lines(pr: pd.DataFrame, runs: pd.DataFrame, lines: list[str]) -> dict:
    """Cell-line scores: mean over eligible runs within each replicate group, then equal weight per group."""
    meta = runs.drop_duplicates("gidx").set_index("gidx")
    out = {}
    for T in COMPARE_THRESHOLDS:
        gm = group_mean(pr, runs, T)
        gm["line"] = meta.cell_line.reindex(gm.gidx).map({c: i for i, c in enumerate(lines)}).to_numpy()
        per = gm.groupby(["site", "line"]).agg(score=("score", "mean"), n_groups=("score", "size")).reset_index()
        for rule, need in (("ge1", 1), ("ge2", 2)):
            ls = per[per.n_groups >= need].pivot(index="site", columns="line", values="score").reindex(columns=range(len(lines)))
            common = ls.dropna()
            per_line = {}
            for i, line in enumerate(lines):
                v = common[i].to_numpy() if len(common) else np.array([])
                hist, _ = np.histogram(v, bins=20, range=(0, 1))
                per_line[line] = {"hist": [int(x) for x in hist], "n": int(len(v)),
                                  "frac_high": round(float((v >= HIGH_SCORE).mean()), 4) if len(v) else None,
                                  "median": round(float(np.median(v)), 3) if len(v) else None}
            hi = (pd.Series(sum((common[i].to_numpy() >= HIGH_SCORE).astype(np.int64) << i for i in range(len(lines))),
                            index=common.index) if len(common) else pd.Series(dtype=np.int64))
            out[f"{T}_{rule}"] = {"common_sites": int(len(common)), "lines": per_line,
                                  "high_combos": upset(hi, lines) if len(common) else [],
                                  "high_in_none": int((hi == 0).sum()) if len(common) else 0}
    return out


def agreement(pr: pd.DataFrame, runs: pd.DataFrame, lines: list[str], min_reads: int) -> list[dict]:
    """Correlation of scores between replicate groups and between runs of one group, by read band."""
    meta = runs.set_index("idx")
    pr = pr[pr.n >= min_reads].assign(line=meta.cell_line.reindex(pr.run_idx).to_numpy(),
                                      rep=meta.replicate.reindex(pr.run_idx).to_numpy())
    out = []
    for line in lines:
        sub = pr[pr.line == line]
        units = {}
        reps = sorted(sub.rep.unique())
        rep_tab = sub.groupby(["rep", "site"]).agg(score=("score", "mean"), n=("n", "sum"))
        for a, b in itertools.combinations(reps, 2):
            units.setdefault("between replicate groups", []).append((rep_tab.loc[a], rep_tab.loc[b], f"rep{a} vs rep{b}"))
        for rep in reps:
            rr = sorted(sub[sub.rep == rep].run_idx.unique())
            for a, b in itertools.combinations(rr, 2):
                ta = sub[sub.run_idx == a].set_index("site")[["score", "n"]]
                tb = sub[sub.run_idx == b].set_index("site")[["score", "n"]]
                units.setdefault("between runs of one group", []).append(
                    (ta, tb, f"rep{rep}: run{meta.run[a]} vs run{meta.run[b]}"))
        for kind, pairs in units.items():
            for lo, hi, label in AGREE_BINS:
                rs, ns = [], []
                for ta, tb, _ in pairs:
                    j = ta.join(tb, lsuffix="_a", rsuffix="_b", how="inner")
                    mn = np.minimum(j.n_a, j.n_b)
                    j = j[(mn >= lo) & (mn < hi)]
                    if len(j) >= 30 and j.score_a.nunique() > 1 and j.score_b.nunique() > 1:
                        rs.append(float(np.corrcoef(j.score_a, j.score_b)[0, 1]))
                        ns.append(len(j))
                out.append({"line": line, "kind": kind, "bin": label, "n_pairs": len(rs), "n_sites": int(sum(ns)),
                            "r": round(float(np.mean(rs)), 3) if rs else None, "pairs": [p[2] for p in pairs]})
    return out


def replicate_support(nreads, site_codes, run_idx, runs, lines, site_is_annotated) -> dict:
    """Per cell line: sites measured in >=1, >=2 or every replicate group; and the all-line intersections."""
    gidx_of_run = runs.gidx.to_numpy(np.int64)
    line_groups = {c: sorted(set(runs.gidx[runs.cell_line == c])) for c in lines}
    out = {}
    for T in SUPPORT_THRESHOLDS:
        m = nreads >= T
        bits = pd.Series(np.left_shift(np.int64(1), gidx_of_run[run_idx[m]])).groupby(site_codes[m]).agg(np.bitwise_or.reduce)
        sites = bits.index.to_numpy()
        mv = bits.to_numpy(np.int64)
        for pop, keep in (("all_reference_types", np.ones(len(sites), bool)), ("annotated_human", site_is_annotated[sites])):
            v = mv[keep]
            counts = {c: sum((v >> g) & 1 for g in gs) for c, gs in line_groups.items()}
            rows = {}
            for c, gs in line_groups.items():
                k = counts[c]
                rows[c] = {"groups": len(gs), "ge1": int((k >= 1).sum()), "ge2": int((k >= 2).sum()),
                           "all": int((k == len(gs)).sum())}
            all7 = {"ge1": int(np.logical_and.reduce([counts[c] >= 1 for c in lines]).sum()),
                    "ge2": int(np.logical_and.reduce([counts[c] >= 2 for c in lines]).sum()),
                    "all": int(np.logical_and.reduce([counts[c] == len(line_groups[c]) for c in lines]).sum())}
            out[f"{T}_{pop}"] = {"lines": rows, "all_lines": all7}
    return out


def crosscheck_member4(support: dict, path: Path) -> dict:
    m4 = pd.read_csv(path)
    checks, mismatches = 0, []
    for r in m4.itertuples():
        key = f"{r.coverage_threshold}_{r.population}"
        if key not in support:
            continue
        mine = support[key]["all_lines"] if r.cell_line == "ALL_7_INTERSECTION" else support[key]["lines"].get(r.cell_line)
        if mine is None:
            mismatches.append({"row": r._asdict(), "reason": "cell line not found"})
            continue
        for col, k in (("sites_ge1_replicate", "ge1"), ("sites_ge2_replicates", "ge2"), ("sites_all_replicates", "all")):
            checks += 1
            if int(getattr(r, col)) != mine[k]:
                mismatches.append({"threshold": int(r.coverage_threshold), "population": r.population,
                                   "cell_line": r.cell_line, "column": col, "member4": int(getattr(r, col)), "pipeline": mine[k]})
    return {"source": str(path), "values_compared": checks, "mismatches": mismatches, "all_match": not mismatches}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--public", type=Path, default=Path("public_data"))
    ap.add_argument("--sample-metadata", type=Path, required=True)
    ap.add_argument("--predictions", type=Path, default=None)
    ap.add_argument("--score-status", choices=["exploratory", "final"], default=None)
    ap.add_argument("--member4-support", type=Path, default=None)
    ap.add_argument("--member4-aliases", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("site/data"))
    ap.add_argument("--reports", type=Path, default=Path("reports"))
    ap.add_argument("--keep-min-reads", type=int, default=20)
    args = ap.parse_args()
    if args.predictions and not args.score_status:
        raise SystemExit("--score-status exploratory|final is required with --predictions")
    t0 = dt.datetime.now()
    args.reports.mkdir(parents=True, exist_ok=True)
    if args.predictions:
        from validate_task2_inputs import main as validate_inputs
        validation_args = ["--inputs", str(args.predictions), "--public", str(args.public),
                           "--report", str(args.reports / "prediction_validation.json")]
        if args.score_status == "final":
            validation_args.append("--require-complete")
        status = validate_inputs(validation_args)
        if status:
            raise SystemExit("Prediction validation failed; no site data was built. Fix the hand-off first.")

    runs = lib.load_runs(args.public)
    R = len(runs)
    lines = [c for c in lib.CELL_LINE_ORDER if c in set(runs.cell_line)]
    lines += sorted(set(runs.cell_line) - set(lines))
    line_of_run = np.array([lines.index(c) for c in runs.cell_line], dtype=np.int64)
    meta = lib.load_sample_metadata(args.sample_metadata).set_index("run_id")
    missing_meta = sorted(set(runs.run_id) - set(meta.index))
    if missing_meta:
        raise SystemExit(f"sample metadata lacks runs: {missing_meta}")
    group_conflict = [r.run_id for r in runs.itertuples() if meta.loc[r.run_id, "group"] != r.group]
    if group_conflict:
        raise SystemExit(f"replicate groups disagree with the sample metadata for {group_conflict}")

    print("Loading read counts ...")
    aliases: dict[str, dict] = {}
    rc = lib.load_readcounts(args.public, runs, aliases=aliases)
    tx_cats = rc.transcript_id.cat.categories
    tx_code = rc.transcript_id.cat.codes.to_numpy(np.int64)
    pos = rc.transcript_position.to_numpy(np.int64)
    if pos.max() >= 2 ** POS_BITS:
        raise SystemExit("transcript position too large for site keys")
    site_codes, uniq_keys = pd.factorize(site_key(tx_code, pos))
    site_codes = site_codes.astype(np.int64)
    key_index = pd.Index(uniq_keys)
    run_idx = rc.run_idx.to_numpy(np.int64)
    nreads = rc.n_reads.to_numpy(np.int64)
    S = len(uniq_keys)
    del rc

    ann = lib.load_annotation(args.public / "annotation" / "Homo_sapiens.GRCh38.91.annotations-transcripts.txt")
    annotated = set(ann.transcript_id)
    tx_kind = lib.transcript_kind(pd.Series(tx_cats), annotated).to_numpy()
    tx_kind_code = np.array([KIND_NAMES.index(k) for k in tx_kind], dtype=np.int8)
    site_tx = (uniq_keys >> POS_BITS).astype(np.int64)
    site_pos = (uniq_keys & (2 ** POS_BITS - 1)).astype(np.int64)
    site_is_annotated = tx_kind_code[site_tx] == 0

    alias_df = alias_table(aliases, ann)
    alias_df.to_csv(args.reports / "transcript_aliases.csv", index=False)
    wrong_version = alias_df[alias_df.in_ensembl91_primary & ~alias_df.version_matches_ensembl91]
    if len(wrong_version):
        raise SystemExit(f"{len(wrong_version)} aliased transcripts have a different Ensembl 91 version; review "
                         f"{args.reports / 'transcript_aliases.csv'} before joining")
    alias_summary = {run: {"aliased_ids": int((alias_df.run_id == run).sum()),
                           "version_matches_ensembl91": int(((alias_df.run_id == run) & alias_df.version_matches_ensembl91).sum()),
                           "not_in_primary_annotation": int(((alias_df.run_id == run) & ~alias_df.in_ensembl91_primary).sum())}
                     for run in aliases}

    print("Run and coverage summaries ...")
    run_rows = []
    for r in runs.itertuples():
        m = run_idx == r.idx
        n = nreads[m]
        ladder = np.bincount(np.searchsorted(LADDER_EDGES, n, side="right"), minlength=len(LADDER_LABELS))
        md = meta.loc[r.run_id]
        run_rows.append({
            "id": r.run_id, "line": r.cell_line, "rep": int(r.replicate), "run": int(r.run), "group": r.group,
            "n_sites": int(m.sum()), "ge": {str(t): int((n >= t).sum()) for t in COVER_THRESHOLDS},
            "median": float(np.median(n)), "p90": float(np.percentile(n, 90)), "max": int(n.max()),
            "n_tx": int(len(np.unique(tx_code[m]))), "ladder": [int(x) for x in ladder],
            "date": md.date, "basecaller": md.basecaller, "kit": md.kit, "flowcell": md.flowcell,
            "platform": md.platform, "spike_in": md.spike_in,
        })
    site_max = pd.Series(nreads).groupby(site_codes).max().reindex(range(S)).to_numpy()
    union = {str(t): int((site_max >= t).sum()) for t in COVER_THRESHOLDS}

    kinds = []
    row_kind = tx_kind_code[tx_code]
    for ki, k in enumerate(KIND_NAMES):
        m = row_kind == ki
        if m.any():
            kinds.append({"kind": k, "site_rows": int(m.sum()), "site_rows_ge20": int((m & (nreads >= 20)).sum()),
                          "sites_ge20": int(len(np.unique(site_codes[m & (nreads >= 20)]))),
                          "transcripts": int(len(np.unique(tx_code[m]))), "runs": int(len(np.unique(run_idx[m])))})

    print("Cell-line sharing, replicate support and run overlap ...")
    line_of_row = line_of_run[run_idx]
    sharing = {}
    for T in SHARE_THRESHOLDS:
        m = nreads >= T
        df = pd.DataFrame({"s": site_codes[m], "l": line_of_row[m]}).drop_duplicates()
        masks = pd.Series(np.left_shift(1, df.l.to_numpy(np.int64))).groupby(df.s.to_numpy()).sum()
        mv = masks.to_numpy(np.int64)
        full = (1 << len(lines)) - 1
        n_set = sum((mv >> i) & 1 for i in range(len(lines)))
        sharing[str(T)] = {"n_sites": int(len(mv)), "all_lines": int((mv == full).sum()),
                           "line_totals": {lines[i]: int(((mv >> i) & 1).sum()) for i in range(len(lines))},
                           "n_lines_hist": [int(x) for x in np.bincount(n_set, minlength=len(lines) + 1)],
                           "combos": upset(masks, lines)}
    support = replicate_support(nreads, site_codes, run_idx, runs, lines, site_is_annotated)
    overlap = {}
    for T in OVERLAP_THRESHOLDS:
        m = nreads >= T
        u, inv = np.unique(site_codes[m], return_inverse=True)
        M = np.zeros((len(u), R), dtype=np.float32)
        M[inv, run_idx[m]] = 1.0
        inter = (M.T @ M).astype(np.float64)
        size = np.diag(inter)
        overlap[str(T)] = [[round(float(x), 3) for x in row] for row in inter / (size[:, None] + size[None, :] - inter)]
        del M

    cross = {}
    if args.member4_support:
        cross["replicate_support"] = crosscheck_member4(support, args.member4_support)
    if args.member4_aliases:
        m4 = pd.read_csv(args.member4_aliases, dtype=str)
        mine = alias_df.set_index(["run_id", "raw_transcript_id"])
        theirs = m4.set_index(["run_id", "raw_transcript_id"])
        both = mine.join(theirs, how="inner", rsuffix="_m4")
        cross["aliases"] = {
            "pipeline_rows": int(len(mine)), "member4_rows": int(len(theirs)), "rows_in_both": int(len(both)),
            "same_joined_id": int((both.transcript_id == both.transcript_id_m4).sum()),
            "member4_verified": int((theirs.primary_annotation_version_verified == "True").sum()),
            "pipeline_version_matches": int(mine.version_matches_ensembl91.sum()),
            "member4_verified_but_pipeline_not": int(((both.primary_annotation_version_verified == "True")
                                                      & ~both.version_matches_ensembl91.astype(bool)).sum()),
        }

    print("Kept sites and predictions ...")
    kept_ids = np.flatnonzero(site_max >= args.keep_min_reads)
    K = len(kept_ids)
    kept_pos_of_site = np.full(S, -1, dtype=np.int64)
    kept_pos_of_site[kept_ids] = np.arange(K)
    row_k = kept_pos_of_site[site_codes]
    sel = row_k >= 0
    READS = np.zeros((K, R), dtype=np.int32)
    READS[row_k[sel], run_idx[sel]] = nreads[sel]

    mode = "coverage_only"
    SCORES = None
    pinfo = {"model_versions": [], "min_reads": [], "n_runs_with_predictions": 0, "model_info": ""}
    compare, agree = None, None
    if args.predictions:
        pr, pinfo = load_predictions(args.predictions, runs, aliases, tx_cats, key_index, site_codes, run_idx, nreads)
        if len(pr):
            mode = "scores"
            SCORES = np.full((K, R), np.nan, dtype=np.float32)
            pk = kept_pos_of_site[pr.site.to_numpy(np.int64)]
            ok = pk >= 0
            SCORES[pk[ok], pr.run_idx.to_numpy(np.int64)[ok]] = pr.score.to_numpy()[ok]
            per_run = pr.groupby("run_idx").size().reindex(range(R), fill_value=0).to_numpy()
            for i, row in enumerate(run_rows):
                row["n_scored"] = int(per_run[i])
            min_reads = min(pinfo["min_reads"]) if pinfo["min_reads"] else args.keep_min_reads
            print("Cell-line comparison ...")
            compare = compare_lines(pr, runs, lines)
            agree = agreement(pr, runs, lines, min_reads)

    print("Grouping sites by gene ...")
    ann_idx = ann.set_index("transcript_id")
    kept_tx = site_tx[kept_ids]
    kept_pos = site_pos[kept_ids]
    order = np.lexsort((kept_pos, kept_tx))
    genes: dict[str, dict] = {}
    tx_rows: dict[int, list[int]] = {}
    for k in order:
        tx_rows.setdefault(int(kept_tx[k]), []).append(int(k))
    line_masks_per_run = np.array([1 << int(line_of_run[i]) for i in range(R)], dtype=np.int64)
    for tc, ks in tx_rows.items():
        tid = str(tx_cats[tc])
        kind = tx_kind[tc]
        if kind == "annotated":
            a = ann_idx.loc[tid]
            gkey, label = a.gene_id, (a.symbol or a.gene_id)
            gmeta = {"label": label, "gene_id": a.gene_id, "kind": kind, "biotype": a.biotype,
                     "desc": a.description, "loc": f"chr{a.chromosome}:{a.gene_start:,}-{a.gene_end:,} ({a.strand})"}
            tlen, tver, nex, known = int(a.tx_len), a.tx_version, int(a.n_exons), True
        elif kind.startswith("spike_"):
            gkey, label = kind.upper(), SPIKE_LABELS[kind]
            gmeta = {"label": label, "gene_id": "", "kind": kind, "biotype": "synthetic spike-in",
                     "desc": "Synthetic RNA added to the sample; expected to carry no m6A", "loc": ""}
            tlen, tver, nex, known = int(kept_pos[ks].max()) + 60, tid, None, False
        else:
            gkey, label = tid, tid
            gmeta = {"label": label, "gene_id": "", "kind": kind, "biotype": "",
                     "desc": "Transcript not in the primary-assembly annotation (likely an alternative haplotype or patch copy of a gene)",
                     "loc": ""}
            tlen, tver, nex, known = int(kept_pos[ks].max()) + 60, tid, None, False
        g = genes.setdefault(gkey, {**gmeta, "tx": []})
        sites = []
        lm = 0
        for k in ks:
            reads = READS[k]
            lm |= int(np.bitwise_or.reduce(line_masks_per_run[reads >= args.keep_min_reads]))
            site = [int(kept_pos[k]), ",".join("" if v == 0 else str(int(v)) for v in reads)]
            if SCORES is not None:
                site.append(",".join("" if np.isnan(v) else f"{float(v):.4f}".rstrip("0").rstrip(".") for v in SCORES[k]))
            sites.append(site)
        g["tx"].append({"id": tid, "ver": tver, "len": tlen, "len_known": known, "n_exons": nex, "sites": sites})
        g["_lines"] = g.get("_lines", 0) | lm

    print("Writing files ...")
    out = args.out
    if (out / "genes").exists():
        raise SystemExit("Output genes directory already exists. Build into a new output directory; nothing was removed.")
    (out / "genes").mkdir(parents=True, exist_ok=True)
    buckets: list[dict] = [{} for _ in range(N_BUCKETS)]
    index_rows, tx_index = [], []
    for gkey, g in genes.items():
        g["tx"].sort(key=lambda t: (-len(t["sites"]), t["id"]))
        b = bucket_of(gkey)
        n_lines = bin(g.pop("_lines")).count("1")
        buckets[b][gkey] = g
        row = len(index_rows)
        index_rows.append([gkey, g["label"], g["gene_id"], g["kind"], sum(len(t["sites"]) for t in g["tx"]),
                           b, g["biotype"], n_lines])
        tx_index.extend([t["id"], row] for t in g["tx"])
    for b, content in enumerate(buckets):
        (out / "genes" / f"b{b:03d}.json").write_text(json.dumps(content, separators=(",", ":"), ensure_ascii=False))
    (out / "genes_index.json").write_text(json.dumps(
        {"fields": ["key", "label", "gene_id", "kind", "n_sites", "bucket", "biotype", "n_lines"], "rows": index_rows},
        separators=(",", ":"), ensure_ascii=False))
    (out / "tx_index.json").write_text(json.dumps(tx_index, separators=(",", ":")))

    # Genes seen in the data but with no site reaching --keep-min-reads, so a search
    # can explain why they have no data on the page instead of reporting them as absent.
    gene_codes, gene_names = pd.factorize(ann.gene_id)
    tx_gene = pd.Series(gene_codes, index=ann.transcript_id).reindex(pd.Index(tx_cats.astype(str))).fillna(-1).to_numpy(np.int64)
    sg = tx_gene[site_tx]
    has = sg >= 0
    n_sites_any = np.bincount(sg[has], minlength=len(gene_names))
    max_reads = pd.Series(site_max[has]).groupby(sg[has]).max().reindex(range(len(gene_names)), fill_value=0).to_numpy()
    rg = tx_gene[tx_code]
    pair = np.unique(rg[rg >= 0] * R + run_idx[rg >= 0])
    n_runs_any = np.bincount(pair // R, minlength=len(gene_names))
    symbol_of = ann.drop_duplicates("gene_id").set_index("gene_id").symbol
    indexed = {r[2] for r in index_rows if r[3] == "annotated"}
    lowcov = [[symbol_of[g] or g, g, int(n_sites_any[i]), int(max_reads[i]), int(n_runs_any[i])]
              for i, g in enumerate(gene_names) if n_sites_any[i] > 0 and g not in indexed]
    (out / "genes_lowcov.json").write_text(json.dumps({"fields": ["label", "gene_id", "n_sites", "max_reads", "n_runs"],
                                                       "rows": lowcov}, separators=(",", ":")))

    by_label = {r[1]: r for r in index_rows if r[3] == "annotated"}
    examples = [g for g in EXAMPLE_CANDIDATES if g in by_label and by_label[g][7] == len(lines)][:5]
    if len(examples) < 5:
        extra = sorted((r for r in index_rows if r[3] == "annotated" and r[7] == len(lines) and r[1] not in examples),
                       key=lambda r: -r[4])
        examples += [r[1] for r in extra[: 5 - len(examples)]]

    (args.reports / "crosscheck_member4.json").write_text(json.dumps(cross, indent=1, default=str))
    overview = {
        "build": {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                  "pipeline_version": PIPELINE_VERSION, "mode": mode, "score_status": args.score_status if mode == "scores" else None,
                  "predictions_dir": args.predictions.name if args.predictions else None,
                  "keep_min_reads": args.keep_min_reads, "high_score": HIGH_SCORE, **pinfo,
                  "public_download_utc": pd.read_csv(args.public / "download_manifest.csv").checked_utc.max(),
                  "annotation": "Ensembl release 91 transcript table from the SG-NEx bucket",
                  "sample_metadata": "official SG-NEx sample sheet (samples.tsv, via Member 4, received 19 Oct 2026)",
                  "aliases": alias_summary,
                  "crosscheck": {k: {kk: vv for kk, vv in v.items() if kk != "mismatches"} | {"n_mismatches": len(v.get("mismatches", []))}
                                 if k == "replicate_support" else v for k, v in cross.items()}},
        "lines": [{"name": c, "info": lib.CELL_LINE_INFO.get(c, ""), "n_runs": int((runs.cell_line == c).sum()),
                   "n_reps": int(runs[runs.cell_line == c].replicate.nunique())} for c in lines],
        "runs": run_rows, "ladder_labels": LADDER_LABELS, "cover_thresholds": COVER_THRESHOLDS,
        "totals": {"site_rows": int(len(site_codes)), "union_sites": union, "kept_sites": int(K),
                   "genes_searchable": int(sum(r[3] == "annotated" for r in index_rows)), "index_rows": len(index_rows)},
        "kinds": kinds,
        "sharing": {"thresholds": SHARE_THRESHOLDS, "by_T": sharing},
        "support": {"thresholds": SUPPORT_THRESHOLDS, "by_key": support},
        "overlap": {"thresholds": OVERLAP_THRESHOLDS, "by_T": overlap},
        "compare": None if compare is None else {"thresholds": COMPARE_THRESHOLDS, "by_key": compare,
                                                 "agreement": agree, "agree_bins": [b[2] for b in AGREE_BINS]},
        "examples": examples,
    }
    (out / "overview.json").write_text(json.dumps(overview, separators=(",", ":"), ensure_ascii=False))
    sizes = sorted(p.stat().st_size for p in (out / "genes").glob("*.json"))
    total = sum(sizes) + sum(p.stat().st_size for p in out.glob("*.json"))
    print(f"Done in {(dt.datetime.now() - t0).seconds}s ({mode}): {K:,} sites in {len(genes):,} groups; "
          f"{total / 1e6:.1f} MB; largest bucket {sizes[-1] / 1e6:.2f} MB; examples {examples}")
    if cross:
        rs = cross.get("replicate_support")
        if rs:
            print(f"Member 4 replicate-support cross-check: {rs['values_compared']} values, {len(rs['mismatches'])} mismatches")
        if "aliases" in cross:
            print(f"Alias comparison: {cross['aliases']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
