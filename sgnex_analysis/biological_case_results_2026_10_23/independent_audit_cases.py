"""Independent saved-evidence audit; never imports production case selection."""
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ANALYSIS = ROOT / "sgnex_analysis/outputs/real_analysis_context_v2"
SELECTION = ROOT / "sgnex_analysis/outputs/biological_case_selection_v2"
REPORT = ROOT / "sgnex_analysis/outputs/task2_report_v2"
QC = ROOT / "sgnex_analysis/outputs/context_qc_v1"
DEPTHS = [20, 50, 100]
KEY = ["transcript_id", "transcript_position"]
META = ["gene_id", "gene_name", "analysis_sequence_7mer", "context_motif_5mer"]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def read(path, **kwargs):
    return pd.read_csv(path, float_precision="round_trip", dtype={"transcript_id": str}, **kwargs)


def boolean(values):
    values = values.astype(str)
    if not values.isin(["True", "False"]).all():
        raise AssertionError("Invalid literal Boolean")
    return values.eq("True")


if (OUT / "audit_result.json").exists():
    raise FileExistsError("Preserve completed independent audit")
start, cpu = time.perf_counter(), time.process_time()
selection = json.loads((SELECTION / "complete.json").read_text(encoding="utf-8"))
report = json.loads((REPORT / "complete.json").read_text(encoding="utf-8"))
qc_receipt = json.loads((QC / "complete.json").read_text(encoding="utf-8"))
assert selection["status"] == report["status"] == qc_receipt["status"] == "complete"
assert selection["script_sha256"] == sha(ROOT / "sgnex_analysis/scripts/select_biological_cases.py")
input_pins = {}
for item in selection["inputs"]:
    path = ROOT / item["path"]
    assert path.stat().st_size == item["size_bytes"] and sha(path) == item["sha256"], item["path"]
    input_pins[item["path"].replace("\\", "/")] = item
for name, item in selection["outputs"].items():
    path = SELECTION / name
    assert path.stat().st_size == item["size_bytes"] and sha(path) == item["sha256"], name
report_pins = {item["path"]: item for item in report["inputs"]}
for path in [ANALYSIS / "analysis_receipt.json", QC / "complete.json"]:
    relative = path.relative_to(ROOT).as_posix()
    assert sha(path) == report_pins[relative]["sha256"]
manifest = pd.read_csv(ROOT / "sgnex_analysis/manifest.csv", dtype=str)
lines = sorted(manifest.cell_line.unique())
assert len(lines) == 7 and len(manifest) == 23

persistent, uncertain, per_pair_counts = [], [], []
max_delta_error = max_ratio_error = 0.0
full_pair_rows_checked = 0
for a, b in itertools.combinations(lines, 2):
    by_depth = {}
    for depth in DEPTHS:
        path = ANALYSIS / f"pairs/{a}__{b}__cov{depth}.csv.gz"
        relative = path.relative_to(ROOT).as_posix()
        assert relative in input_pins
        assert input_pins[relative]["sha256"] == report_pins[relative]["sha256"]
        frame = read(path)
        assert not frame.duplicated(KEY).any()
        assert frame.cell_line_a.eq(a).all() and frame.cell_line_b.eq(b).all()
        assert np.isfinite(frame[["score_a", "score_b", "log_reads_a", "log_reads_b"]].to_numpy()).all()
        assert frame[["score_a", "score_b"]].ge(0).all().all() and frame[["score_a", "score_b"]].le(1).all().all()
        assert frame[["n_replicates_a", "n_replicates_b"]].ge(2).all().all()
        delta = frame.score_a - frame.score_b
        ratio = np.exp((frame.log_reads_a - frame.log_reads_b).abs())
        sep = frame.score_min_a.gt(frame.score_max_b) | frame.score_max_a.lt(frame.score_min_b)
        balanced = ratio.le(2)
        candidate = delta.abs().ge(.2) & sep & balanced
        delta_error = float((delta - frame.delta_score).abs().max())
        ratio_error = float((ratio - frame.coverage_ratio).abs().max())
        max_delta_error = max(max_delta_error, delta_error)
        max_ratio_error = max(max_ratio_error, ratio_error)
        assert np.allclose(delta, frame.delta_score, atol=1e-14, rtol=0)
        assert np.allclose(ratio, frame.coverage_ratio, atol=1e-12, rtol=1e-12)
        assert boolean(frame.replicate_separated).equals(sep)
        assert boolean(frame.coverage_balanced).equals(balanced)
        assert boolean(frame.candidate_large_difference).equals(candidate)
        full_pair_rows_checked += len(frame)
        selected = frame.loc[candidate]
        by_depth[depth] = {(row.transcript_id, int(row.transcript_position)): row for row in selected.itertuples()}
        per_pair_counts.append({"cell_line_a": a, "cell_line_b": b, "coverage_threshold": depth,
                                "n_pair_sites": len(frame), "n_original_candidates": int(candidate.sum())})
        if depth == 20:
            for row in frame.loc[delta.abs().ge(.2) & balanced & ~sep].itertuples():
                uncertain.append({"cell_line_a": a, "cell_line_b": b, "transcript_id": row.transcript_id,
                                  "transcript_position": int(row.transcript_position), "absolute_delta_20": abs(row.delta_score),
                                  "minimum_group_count": min(row.n_replicates_a, row.n_replicates_b)})
    common = set(by_depth[20]) & set(by_depth[50]) & set(by_depth[100])
    n_this_pair = 0
    for key in common:
        values = [by_depth[d][key] for d in DEPTHS]
        signs = [np.sign(row.delta_score) for row in values]
        if 0 in signs or len(set(signs)) != 1:
            continue
        assert len({tuple(getattr(row, field) for field in META) for row in values}) == 1
        persistent.append({"cell_line_a": a, "cell_line_b": b, "transcript_id": key[0], "transcript_position": key[1],
                           "minimum_abs_delta": min(abs(row.delta_score) for row in values),
                           "minimum_group_count": min(getattr(row, field) for row in values for field in ["n_replicates_a", "n_replicates_b"])})
        n_this_pair += 1
    print(f"Independently checked {a}/{b}: {n_this_pair} persistent pair-site rows", flush=True)

sort_tail = ["cell_line_a", "cell_line_b", "transcript_id", "transcript_position"]
persistent = pd.DataFrame(persistent).sort_values(["minimum_abs_delta", "minimum_group_count"] + sort_tail,
                                                ascending=[False, False, True, True, True, True], kind="stable").reset_index(drop=True)
uncertain = pd.DataFrame(uncertain).sort_values(["absolute_delta_20", "minimum_group_count"] + sort_tail,
                                              ascending=[False, False, True, True, True, True], kind="stable").reset_index(drop=True)
for name, expected, metric in [("persistent_difference_ranked.csv.gz", persistent, "minimum_abs_delta"),
                               ("inconclusive_ranked.csv.gz", uncertain, "absolute_delta_20")]:
    saved = read(SELECTION / name)
    assert len(saved) == len(expected)
    assert list(saved[sort_tail].itertuples(index=False, name=None)) == list(expected[sort_tail].itertuples(index=False, name=None))
    assert np.array_equal(saved[metric].to_numpy(), expected[metric].to_numpy())
    assert np.array_equal(saved.minimum_group_count.to_numpy(), expected.minimum_group_count.to_numpy())
    assert np.array_equal(saved["rank"].to_numpy(), np.arange(1, len(saved)+1))

common_by_depth = {}
for depth in DEPTHS:
    path = ANALYSIS / f"all_line_common_scores_cov{depth}.csv.gz"
    relative = path.relative_to(ROOT).as_posix()
    assert input_pins[relative]["sha256"] == report_pins[relative]["sha256"]
    common = read(path)
    assert not common.duplicated(KEY).any() and not common[lines].isna().any().any()
    common_by_depth[depth] = common.set_index(KEY)
site_keys = set(common_by_depth[20].index) & set(common_by_depth[50].index) & set(common_by_depth[100].index)
all_shared = []
for key in site_keys:
    scores = [float(common_by_depth[d].loc[key, line]) for d in DEPTHS for line in lines]
    all_shared.append({"transcript_id": key[0], "transcript_position": int(key[1]), "minimum_line_depth_score": min(scores)})
all_shared = pd.DataFrame(all_shared)
n_shared_07 = int(all_shared.minimum_line_depth_score.ge(.7).sum())
cutoff = .7 if n_shared_07 else .5
shared = all_shared[all_shared.minimum_line_depth_score.ge(cutoff)].sort_values(["minimum_line_depth_score"]+KEY, ascending=[False, True, True]).reset_index(drop=True)
saved_shared = read(SELECTION / "shared_high_ranked.csv.gz")
assert list(saved_shared[KEY].itertuples(index=False, name=None)) == list(shared[KEY].itertuples(index=False, name=None))
assert np.array_equal(saved_shared.minimum_line_depth_score.to_numpy(), shared.minimum_line_depth_score.to_numpy())

counts = read(SELECTION / "pair_population_counts.csv")
pd.testing.assert_frame_equal(counts, pd.DataFrame(per_pair_counts), check_dtype=False)
expected_cases = {}
for role, table in [
    ("persistent_difference_nontraining_lines", persistent[~persistent[sort_tail[:2]].eq("Hct116").any(axis=1)]),
    ("persistent_difference_training_line", persistent[persistent[sort_tail[:2]].eq("Hct116").any(axis=1)]),
    ("shared_high", shared),
    ("overlapping_groups_inconclusive", uncertain[~uncertain[sort_tail[:2]].eq("Hct116").any(axis=1)])]:
    if len(table): expected_cases[role] = table.iloc[0]
chosen = read(SELECTION / "selected_cases.csv").set_index("case_id")
assert set(chosen.index) == set(expected_cases)
qc = read(QC / "key_context_qc.csv.gz", keep_default_na=False).set_index(KEY)
for role, expected in expected_cases.items():
    saved = chosen.loc[role]
    assert (saved.transcript_id, int(saved.transcript_position)) == (expected.transcript_id, int(expected.transcript_position))
    if role != "shared_high":
        assert (saved.cell_line_a, saved.cell_line_b) == (expected.cell_line_a, expected.cell_line_b)
    support = qc.loc[(saved.transcript_id, int(saved.transcript_position))]
    assert str(support.all_source_consistent) == "True"
    assert support.encoded7mer_all_source == saved.encoded7mer_all_source == saved.analysis_sequence_7mer
    assert int(support.training_positive_labels_all_source) == int(saved.training_positive_labels_all_source)
    for flag in ["weak_positive_support_lt20", "zero_positive_support"]:
        assert str(support[flag]) == str(saved[flag])
    for field in expected.index:
        if field in sort_tail + ["minimum_abs_delta", "minimum_group_count", "absolute_delta_20", "minimum_line_depth_score"]:
            assert saved[field] == expected[field]

for item in selection["inputs"]:
    assert sha(ROOT / item["path"]) == item["sha256"], "Concurrent input mutation"
result = {
    "status": "PASS", "production_selection_imported": False, "fitting_or_inference": False,
    "selection_complete_sha256": sha(SELECTION / "complete.json"), "reporter_complete_sha256": sha(REPORT / "complete.json"),
    "qc_complete_sha256": sha(QC / "complete.json"), "script_sha256": sha(Path(__file__)),
    "n_input_pins_checked": len(selection["inputs"]), "n_output_hashes_checked": len(selection["outputs"]),
    "n_full_pair_tables_checked": 63, "n_full_pair_rows_checked": full_pair_rows_checked,
    "n_persistent_pair_rows": len(persistent), "n_persistent_unique_keys": len(persistent[KEY].drop_duplicates()),
    "n_persistent_nontraining_pair_rows": int((~persistent[sort_tail[:2]].eq("Hct116").any(axis=1)).sum()),
    "n_persistent_training_pair_rows": int(persistent[sort_tail[:2]].eq("Hct116").any(axis=1).sum()),
    "n_inconclusive_pair_rows": len(uncertain), "n_shared_high_07": n_shared_07, "shared_cutoff": cutoff,
    "all_rank_orders_and_selected_keys_match": True,
    "max_pair_delta_recompute_difference": max_delta_error, "max_pair_depth_ratio_recompute_difference": max_ratio_error,
    "selected": [{"role": role, "transcript_id": row.transcript_id, "transcript_position": int(row.transcript_position),
                  "gene_name": chosen.loc[role, "gene_name"], "training_positive_context_count": int(chosen.loc[role, "training_positive_labels_all_source"])} for role, row in expected_cases.items()],
    "resources": {"wall_seconds": time.perf_counter()-start, "process_cpu_seconds": time.process_time()-cpu},
    "resource_scope": "Current process after imports through input/output fingerprint checks and independent reconstruction; excludes final evidence writes. No peak memory claim",
    "limitations": "Selection and saved source-table audit only. Original23run score/group reconstruction and biological literature interpretation are separate root tasks; no chemical truth or significance test established",
}
persistent.to_csv(OUT / "independent_persistent_ranking.csv", index=False)
uncertain.to_csv(OUT / "independent_inconclusive_ranking.csv", index=False)
shared.to_csv(OUT / "independent_shared_high_ranking.csv", index=False)
(OUT / "audit_result.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
print(json.dumps(result, indent=2), flush=True)
