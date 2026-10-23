"""Predeclared illustrative cases from immutable completed Task2 tables."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

KEY = ["transcript_id", "transcript_position"]
PAIR = ["cell_line_a", "cell_line_b"]
META = ["gene_id", "gene_name", "analysis_sequence_7mer", "context_motif_5mer"]
DEPTHS = [20, 50, 100]
LINES = ["A549", "H9", "HEYA8", "Hct116", "HepG2", "K562", "MCF7"]
ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def strict_bool(series):
    if series.dtype == bool:
        return series
    values = series.astype(str).str.lower()
    if not values.isin(["true", "false"]).all():
        raise ValueError("Malformed Boolean flag")
    return values.eq("true")


def validate_pair(frame):
    if frame.duplicated(KEY).any():
        raise ValueError("Duplicate pair keys")
    for column in ["coverage_balanced", "replicate_separated", "candidate_large_difference"]:
        frame[column] = strict_bool(frame[column])
    if not frame[["n_replicates_a", "n_replicates_b"]].ge(2).all().all():
        raise ValueError("Ineligible group count")
    if not frame[["score_a", "score_b"]].apply(lambda col: col.between(0, 1)).all().all():
        raise ValueError("Invalid score")
    delta = frame.score_a - frame.score_b
    ratio = np.exp(abs(frame.log_reads_a - frame.log_reads_b))
    separated = (frame.score_min_a > frame.score_max_b) | (frame.score_max_a < frame.score_min_b)
    balanced = ratio.le(2)
    candidate = delta.abs().ge(.2) & separated & balanced
    if not np.allclose(delta, frame.delta_score, rtol=0, atol=2e-12):
        raise ValueError("Delta mismatch")
    if not np.allclose(ratio, frame.coverage_ratio, rtol=1e-12, atol=1e-12):
        raise ValueError("Depth ratio mismatch")
    for observed, expected in [(frame.replicate_separated, separated),
                               (frame.coverage_balanced, balanced),
                               (frame.candidate_large_difference, candidate)]:
        if not observed.equals(expected):
            raise ValueError("Original candidate/range/depth flag mismatch")
    return frame


def stable_pool(tables):
    """Same keys, same pair, original flag true at every depth; never relax."""
    merged = None
    for depth in DEPTHS:
        selected = tables[depth].loc[tables[depth].candidate_large_difference].copy()
        selected = selected.rename(columns={c: f"{c}_{depth}" for c in selected if c not in KEY + PAIR + META})
        if merged is None:
            merged = selected
        else:
            # Metadata included in join so any changing annotation cannot silently pass.
            merged = merged.merge(selected, on=KEY + PAIR + META, validate="one_to_one")
    signs = merged[[f"delta_score_{d}" for d in DEPTHS]].apply(np.sign)
    merged = merged.loc[signs.ne(0).all(axis=1) & signs.eq(signs.iloc[:, 0], axis=0).all(axis=1)].copy()
    merged["minimum_abs_delta"] = merged[[f"delta_score_{d}" for d in DEPTHS]].abs().min(axis=1)
    merged["minimum_group_count"] = merged[[f"n_replicates_{side}_{d}" for d in DEPTHS for side in ["a", "b"]]].min(axis=1)
    return merged


def rank_differences(frame, magnitude="minimum_abs_delta"):
    return frame.sort_values([magnitude, "minimum_group_count"] + PAIR + KEY,
                             ascending=[False, False, True, True, True, True], kind="stable").reset_index(drop=True)


def shared_pool(tables, cutoff):
    merged = None
    for depth in DEPTHS:
        table = tables[depth][KEY + LINES].copy()
        if table.duplicated(KEY).any() or table[LINES].isna().any().any():
            raise ValueError("Invalid all-line common keys/scores")
        table = table.rename(columns={c: f"{c}_{depth}" for c in LINES})
        merged = table if merged is None else merged.merge(table, on=KEY, validate="one_to_one")
    cols = [f"{c}_{d}" for d in DEPTHS for c in LINES]
    merged["minimum_line_depth_score"] = merged[cols].min(axis=1)
    merged = merged.loc[merged.minimum_line_depth_score.ge(cutoff)].copy()
    return merged.sort_values(["minimum_line_depth_score"] + KEY, ascending=[False, True, True], kind="stable").reset_index(drop=True)


def run(analysis, qc_dir, reporter, out):
    started = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "status.json", {"status": "started", "no_training_or_inference": True})
    report = json.loads((reporter / "complete.json").read_text(encoding="utf-8"))
    qc_receipt = json.loads((qc_dir / "complete.json").read_text(encoding="utf-8"))
    receipt = json.loads((analysis / "analysis_receipt.json").read_text(encoding="utf-8"))
    if report["status"] != "complete" or qc_receipt["status"] != "complete" or receipt["status"] != "complete":
        raise ValueError("Source not complete")
    if sha(analysis / "analysis_receipt.json") != report["analysis_receipt_sha256"] or sha(qc_dir / "complete.json") != report["qc_complete_sha256"]:
        raise ValueError("Source receipt binding mismatch")
    if receipt["context_qualification"]["policy"] != "all-source-consistent":
        raise ValueError("Expected primary context policy")
    args = receipt["arguments"]
    if args["coverage"] != "20,50,100" or args["min_replicates"] != 2 or args["max_coverage_ratio"] != 2 or args["min_delta"] != .2:
        raise ValueError("Source design changed")
    pins = {Path(x["path"]).as_posix(): x for x in report["inputs"]}
    used = []

    def checked_read(path, **kwargs):
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        pin = pins[relative]
        if sha(path) != pin["sha256"] or path.stat().st_size != pin["size_bytes"]:
            raise ValueError(f"Saved source table changed: {relative}")
        used.append(pin)
        return pd.read_csv(path, float_precision="round_trip", **kwargs)

    stable, uncertain, counts = [], [], []
    for a, b in itertools.combinations(LINES, 2):
        tables = {}
        for depth in DEPTHS:
            frame = validate_pair(checked_read(analysis / "pairs" / f"{a}__{b}__cov{depth}.csv.gz"))
            if not frame.cell_line_a.eq(a).all() or not frame.cell_line_b.eq(b).all():
                raise ValueError("Wrong pair label")
            tables[depth] = frame
            counts.append({"cell_line_a": a, "cell_line_b": b, "coverage_threshold": depth,
                           "n_pair_sites": len(frame), "n_original_candidates": int(frame.candidate_large_difference.sum())})
        persistent = stable_pool(tables)
        stable.append(persistent)
        frame = tables[20]
        ambiguous = frame.loc[frame.delta_score.abs().ge(.2) & frame.coverage_balanced & ~frame.replicate_separated].copy()
        ambiguous["absolute_delta_20"] = ambiguous.delta_score.abs()
        ambiguous["minimum_group_count"] = ambiguous[["n_replicates_a", "n_replicates_b"]].min(axis=1)
        uncertain.append(ambiguous)
        print(f"Checked {a}/{b}: {len(persistent)} persistent candidate pair-sites", flush=True)
    stable = rank_differences(pd.concat(stable, ignore_index=True))
    uncertain = rank_differences(pd.concat(uncertain, ignore_index=True), "absolute_delta_20")
    commons = {d: checked_read(analysis / f"all_line_common_scores_cov{d}.csv.gz") for d in DEPTHS}
    shared = shared_pool(commons, .7)
    n_shared_07 = len(shared)
    shared_cutoff = .7 if n_shared_07 else .5
    if not n_shared_07:
        shared = shared_pool(commons, .5)

    qc_path = qc_dir / "key_context_qc.csv.gz"
    qpin = qc_receipt["outputs"][qc_path.name]
    if sha(qc_path) != qpin["sha256"] or qc_path.stat().st_size != qpin["size_bytes"]:
        raise ValueError("QC table changed")
    qc = pd.read_csv(qc_path, usecols=KEY + ["all_source_consistent", "encoded7mer_all_source", "training_positive_labels_all_source", "weak_positive_support_lt20", "zero_positive_support"], float_precision="round_trip")
    if qc.duplicated(KEY).any():
        raise ValueError("Duplicate QC keys")
    support = qc.drop(columns="all_source_consistent")
    for pool in [stable, uncertain, shared]:
        checked = pool[KEY].merge(qc[KEY + ["all_source_consistent"]], on=KEY, how="left", validate="many_to_one")
        if checked.all_source_consistent.isna().any() or not strict_bool(checked.all_source_consistent).all():
            raise ValueError("Selected-pool context not qualified")
    stable = stable.merge(support, on=KEY, how="left", validate="many_to_one")
    uncertain = uncertain.merge(support, on=KEY, how="left", validate="many_to_one")
    shared = shared.merge(support, on=KEY, how="left", validate="one_to_one")
    # Shared annotations are looked up by exact key; no symbol-driven selection.
    # Every all-seven-common site must also occur in the last checked pair.
    # That complete pair table has a reporter input hash; cell-line cache does not.
    annotation = tables[100][KEY + META].drop_duplicates()
    if annotation.duplicated(KEY).any():
        raise ValueError("Conflicting saved gene annotation")
    shared = shared.merge(annotation, on=KEY, how="left", validate="one_to_one")
    if shared[["gene_id", "analysis_sequence_7mer"]].isna().any().any():
        raise ValueError("Shared key lacks pinned pair-table annotation")
    for pool in [stable, uncertain, shared]:
        pool.insert(0, "rank", range(1, len(pool) + 1))
    selected = []
    has_hct = stable[PAIR].eq("Hct116").any(axis=1)
    uncertain_hct = uncertain[PAIR].eq("Hct116").any(axis=1)
    for role, pool in [("persistent_difference_nontraining_lines", stable.loc[~has_hct]),
                       ("persistent_difference_training_line", stable.loc[has_hct]),
                       ("shared_high", shared),
                       ("overlapping_groups_inconclusive", uncertain.loc[~uncertain_hct])]:
        if len(pool):
            record = pool.iloc[0].to_dict()
            record["case_id"] = role
            record["selection_population_size"] = len(pool)
            selected.append(record)
    chosen = pd.DataFrame(selected)
    stable.to_csv(out / "persistent_difference_ranked.csv.gz", index=False)
    uncertain.to_csv(out / "inconclusive_ranked.csv.gz", index=False)
    shared.to_csv(out / "shared_high_ranked.csv.gz", index=False)
    pd.DataFrame(counts).to_csv(out / "pair_population_counts.csv", index=False)
    chosen.to_csv(out / "selected_cases.csv", index=False)
    summary = {"n_persistent_pair_sites": len(stable), "n_persistent_unique_sites": len(stable[KEY].drop_duplicates()),
               "n_persistent_nontraining_pair_sites": int((~has_hct).sum()), "n_persistent_training_pair_sites": int(has_hct.sum()),
               "n_inconclusive_pair_sites": len(uncertain), "n_inconclusive_nontraining_pair_sites": int((~uncertain_hct).sum()),
               "n_shared_high_at_07": n_shared_07, "shared_cutoff_used": shared_cutoff, "n_shared_high_used": len(shared),
               "n_selected_cases": len(chosen), "selection_is_tail_illustration_not_inference": True}
    write_json(out / "summary.json", summary)
    inputs = used + [{"path": str(qc_path.relative_to(ROOT)), "sha256": sha(qc_path), "size_bytes": qc_path.stat().st_size}]
    for path in [PLAN, reporter / "complete.json", qc_dir / "complete.json", analysis / "analysis_receipt.json"]:
        inputs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "size_bytes": path.stat().st_size})
    outputs = {p.name: {"sha256": sha(p), "size_bytes": p.stat().st_size} for p in sorted(out.iterdir()) if p.name != "status.json"}
    write_json(out / "complete.json", {"status": "complete", "script_sha256": sha(Path(__file__)),
               "inputs": inputs, "outputs": outputs, "summary": summary, "no_training_or_inference": True,
               "wall_seconds_internal": time.perf_counter() - started})
    write_json(out / "status.json", {"status": "complete"})
    print(json.dumps(summary), flush=True)
    print(chosen[["case_id"] + KEY + ["gene_name", "selection_population_size"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/real_analysis_context_v2")
    parser.add_argument("--qc-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/context_qc_v1")
    parser.add_argument("--reporter-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/task2_report_v2")
    parser.add_argument("--out", type=Path, required=True)
    cli = parser.parse_args()
    run(cli.analysis_dir.resolve(), cli.qc_dir.resolve(), cli.reporter_dir.resolve(), cli.out.resolve())
