"""Reconstruct selected cases from complete original run exports and coverage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from select_biological_cases import ROOT, KEY, PAIR, DEPTHS, LINES, sha, write_json


def aggregate_cases(runs, depth):
    eligible = runs.loc[runs.n_reads.ge(depth) & runs.score.notna()].copy()
    eligible["log_reads"] = np.log(eligible.n_reads)
    groups = eligible.groupby(["case_id"] + KEY + ["cell_line", "biological_replicate"], as_index=False).agg(
        score=("score", "mean"), n_runs=("run_id", "nunique"), run_score_min=("score", "min"),
        run_score_max=("score", "max"), log_reads=("log_reads", "mean"))
    lines = groups.groupby(["case_id"] + KEY + ["cell_line"], as_index=False).agg(
        score=("score", "mean"), n_replicates=("biological_replicate", "nunique"), n_eligible_runs=("n_runs", "sum"),
        score_min=("score", "min"), score_max=("score", "max"), log_reads=("log_reads", "mean"))
    groups["coverage_threshold"] = depth
    lines["coverage_threshold"] = depth
    lines["geometric_mean_reads"] = np.exp(lines.log_reads)
    return groups, lines


def run(selection_dir, out):
    started = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "status.json", {"status": "started"})
    selection = json.loads((selection_dir / "complete.json").read_text(encoding="utf-8"))
    if selection["status"] != "complete":
        raise ValueError("Selection is incomplete")
    inputs = []

    def pin(path, expected=None):
        path = Path(path)
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError(f"Changed input: {path.name}")
        inputs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest, "size_bytes": path.stat().st_size})
        return path

    chosen_path = pin(selection_dir / "selected_cases.csv", selection["outputs"]["selected_cases.csv"]["sha256"])
    chosen = pd.read_csv(chosen_path, float_precision="round_trip")
    keys = chosen[KEY].drop_duplicates()
    manifest_path = ROOT / "sgnex_analysis/manifest.csv"
    analysis_dir = ROOT / "sgnex_analysis/outputs/real_analysis_context_v2"
    report_dir = ROOT / "sgnex_analysis/outputs/task2_report_v2"
    receipt_path = analysis_dir / "analysis_receipt.json"
    report_path = report_dir / "complete.json"
    sp = {p["path"]: p for p in selection["inputs"]}
    receipt = json.loads(pin(receipt_path, sp[receipt_path.relative_to(ROOT).as_posix()]["sha256"]).read_text(encoding="utf-8"))
    report = json.loads(pin(report_path, sp[report_path.relative_to(ROOT).as_posix()]["sha256"]).read_text(encoding="utf-8"))
    pin(selection_dir / "complete.json")
    manifest = pd.read_csv(pin(manifest_path, receipt["manifest_sha256"]), keep_default_na=False)
    if len(manifest) != 23 or manifest.run_id.duplicated().any():
        raise ValueError("Fixed run design changed")
    coverage_path = ROOT / receipt["arguments"]["coverage_matrix"]
    cov = pd.read_csv(pin(coverage_path, receipt["coverage_sha256"]), float_precision="round_trip")
    cov = keys.merge(cov, on=KEY, how="left", validate="one_to_one")
    if cov[manifest.run_id.tolist()].isna().any().any():
        raise ValueError("Selected key missing coverage")
    aliases_path = ROOT / receipt["arguments"]["aliases"]
    aliases = pd.read_csv(pin(aliases_path, receipt["aliases_sha256"]), dtype=str, keep_default_na=False)
    if aliases.duplicated(["run_id", "raw_transcript_id"]).any():
        raise ValueError("Duplicate alias entries")
    prediction_pins = {p["run_id"]: p for p in receipt["predictions"]}
    records = []
    for sample in manifest.itertuples(index=False):
        amap_rows = aliases.loc[aliases.run_id.eq(sample.run_id)]
        amap = dict(zip(amap_rows.raw_transcript_id, amap_rows.transcript_id))
        raw_targets = set(keys.transcript_id) | set(amap_rows.loc[amap_rows.transcript_id.isin(keys.transcript_id), "raw_transcript_id"])
        pp = prediction_pins[sample.run_id]
        path = pin(ROOT / "sgnex_analysis" / sample.prediction_file, pp["sha256"])
        prediction = pd.read_csv(path, float_precision="round_trip", dtype={"transcript_id": str})
        pred = prediction.loc[prediction.transcript_id.isin(raw_targets) & prediction.transcript_position.isin(keys.transcript_position)].copy()
        pred = pred.rename(columns={"transcript_id": "raw_transcript_id"})
        pred["transcript_id"] = pred.raw_transcript_id.map(lambda raw: amap.get(raw, raw))
        pred = keys.merge(pred, on=KEY, how="inner", validate="one_to_one")
        if pred.duplicated(KEY).any():
            raise ValueError("Alias collision in selected original exports")
        current = cov[KEY + [sample.run_id]].rename(columns={sample.run_id: "n_reads"})
        current = chosen[["case_id"] + KEY + ["gene_id", "gene_name", "analysis_sequence_7mer", "training_positive_labels_all_source", "weak_positive_support_lt20"]].merge(current, on=KEY, validate="many_to_one")
        current = current.merge(pred[KEY + ["raw_transcript_id", "score"]], on=KEY, how="left", validate="many_to_one")
        if not current.n_reads.ge(20).equals(current.score.notna()):
            raise ValueError("Original prediction eligibility mismatch at selected site")
        current["run_id"] = sample.run_id
        current["cell_line"] = sample.cell_line
        current["biological_replicate"] = sample.biological_replicate
        current["sequencing_run"] = sample.sequencing_run
        current["alias_applied"] = current.raw_transcript_id.notna() & current.raw_transcript_id.ne(current.transcript_id)
        current["measurement_status"] = np.where(current.n_reads.eq(0), "absent_from_processed_run",
                                         np.where(current.n_reads.lt(20), "below_20_reads_unscored", "scored"))
        records.append(current)
    run_scores = pd.concat(records, ignore_index=True)
    if run_scores.duplicated(["case_id", "run_id"]).any() or len(run_scores) != len(chosen) * 23:
        raise ValueError("Incomplete selected-case/run grid")
    metadata_path = ROOT / "sgnex_analysis/metadata/sample_manifest.csv"
    meta_pin = next(p for p in report["inputs"] if p["name"] == "sample_manifest.csv")
    metadata = pd.read_csv(pin(metadata_path, meta_pin["sha256"]), keep_default_na=False, dtype=str)
    meta_cols = ["run_id", "flowcell", "kit", "Platform", "basecaller_version(ENA)*", "generation_date", "Spike in concentration"]
    run_scores = run_scores.merge(metadata[meta_cols], on="run_id", validate="many_to_one")
    group_frames, line_frames, comparisons = [], [], []
    report_pins = {p["path"]: p for p in report["inputs"]}
    for depth in DEPTHS:
        groups, lines = aggregate_cases(run_scores, depth)
        group_frames.append(groups)
        line_frames.append(lines)
        for case in chosen.itertuples(index=False):
            key_mask = lines.case_id.eq(case.case_id)
            if case.case_id == "shared_high":
                path = analysis_dir / f"all_line_common_scores_cov{depth}.csv.gz"
                expected = pd.read_csv(pin(path, report_pins[path.relative_to(ROOT).as_posix()]["sha256"]), float_precision="round_trip")
                expected = expected.loc[expected.transcript_id.eq(case.transcript_id) & expected.transcript_position.eq(case.transcript_position)]
                if len(expected) != 1:
                    raise ValueError("Shared-high key absent from common panel")
                for line in LINES:
                    actual = lines.loc[key_mask & lines.cell_line.eq(line)]
                    if len(actual) != 1 or actual.n_replicates.iloc[0] < 2 or not np.isclose(actual.score.iloc[0], expected[line].iloc[0], rtol=0, atol=2e-12):
                        raise ValueError("Shared line score differs from independent run reconstruction")
                comparisons.append({"case_id": case.case_id, "coverage_threshold": depth, "pair_available": True,
                                    "minimum_line_score": float(lines.loc[key_mask, "score"].min()), "original_flag": None})
                continue
            a, b = case.cell_line_a, case.cell_line_b
            path = analysis_dir / "pairs" / f"{a}__{b}__cov{depth}.csv.gz"
            expected = pd.read_csv(pin(path, report_pins[path.relative_to(ROOT).as_posix()]["sha256"]), float_precision="round_trip")
            expected = expected.loc[expected.transcript_id.eq(case.transcript_id) & expected.transcript_position.eq(case.transcript_position)]
            actual = lines.loc[key_mask & lines.cell_line.isin([a, b])].set_index("cell_line")
            available = len(actual) == 2 and actual.n_replicates.ge(2).all()
            if available != (len(expected) == 1):
                raise ValueError("Reconstructed pair membership differs")
            if available:
                for side, line in [("a", a), ("b", b)]:
                    for field in ["score", "n_replicates", "n_eligible_runs", "score_min", "score_max", "log_reads", "geometric_mean_reads"]:
                        if not np.isclose(actual.loc[line, field], expected[f"{field}_{side}"].iloc[0], rtol=1e-12, atol=2e-12):
                            raise ValueError(f"Reconstructed {field} mismatch")
                comparisons.append({"case_id": case.case_id, "coverage_threshold": depth, "pair_available": True,
                    "cell_line_a": a, "cell_line_b": b, "score_a": actual.loc[a, "score"], "score_b": actual.loc[b, "score"],
                    "delta_score": actual.loc[a, "score"] - actual.loc[b, "score"], "coverage_ratio": np.exp(abs(actual.loc[a, "log_reads"] - actual.loc[b, "log_reads"])),
                    "group_min_a": actual.loc[a, "score_min"], "group_max_a": actual.loc[a, "score_max"],
                    "group_min_b": actual.loc[b, "score_min"], "group_max_b": actual.loc[b, "score_max"],
                    "original_flag": bool(expected.candidate_large_difference.iloc[0])})
            else:
                comparisons.append({"case_id": case.case_id, "coverage_threshold": depth, "pair_available": False,
                                    "cell_line_a": a, "cell_line_b": b, "original_flag": None})
    run_scores.to_csv(out / "case_run_evidence.csv", index=False)
    pd.concat(group_frames, ignore_index=True).to_csv(out / "case_group_scores.csv", index=False)
    pd.concat(line_frames, ignore_index=True).to_csv(out / "case_line_scores.csv", index=False)
    pd.DataFrame(comparisons).to_csv(out / "case_comparison_checks.csv", index=False)
    # Keep the frozen selected cases byte-identical for easy review.
    (out / "selected_cases.csv").write_bytes(chosen_path.read_bytes())
    outputs = {p.name: {"sha256": sha(p), "size_bytes": p.stat().st_size} for p in sorted(out.iterdir()) if p.name != "status.json"}
    unique_inputs = {p["path"]: p for p in inputs}
    summary = {"cases": len(chosen), "original_run_grid_rows": len(run_scores), "scored_run_rows": int(run_scores.score.notna().sum()),
               "absent_run_rows": int(run_scores.n_reads.eq(0).sum()), "below20_run_rows": int(run_scores.n_reads.between(1, 19).sum()),
               "group_rows": sum(len(t) for t in group_frames), "line_rows": sum(len(t) for t in line_frames),
               "pair_or_shared_depth_checks": len(comparisons)}
    write_json(out / "complete.json", {"status": "complete", "script_sha256": sha(Path(__file__)), "inputs": list(unique_inputs.values()),
               "outputs": outputs, "summary": summary, "no_training_or_inference": True,
               "wall_seconds_internal": time.perf_counter() - started})
    write_json(out / "status.json", {"status": "complete"})
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    cli = parser.parse_args()
    run(cli.selection_dir.resolve(), cli.out.resolve())
