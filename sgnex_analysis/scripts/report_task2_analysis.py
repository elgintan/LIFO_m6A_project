"""Scientific figures from completed context QC and saved Task2 comparisons.

No raw signals, labels, fitting or inference. This reporter validates and
summarises all21 pairs and the separate all-seven-line matched populations.
Different read-depth populations are never interpreted as a within-site effect.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
KEYS = ["transcript_id", "transcript_position"]
DEPTHS = (20, 50, 100)
CUTOFFS = (0.5, 0.7, 0.9)
COLORS = ["#246A86", "#DA8C33", "#568D5C", "#AA526B", "#7A66A5", "#5675B1", "#867148"]
RELATIONS = ["Runs: same metadata group", "Runs: different group, same line", "Runs: different lines",
             "Group means: same line", "Group means: different lines"]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path):
    path = Path(path).resolve()
    try:
        public_path = path.relative_to(REPO).as_posix()
    except ValueError:
        public_path = path.name
    return {"name": path.name, "path": public_path, "sha256": sha(path), "size_bytes": path.stat().st_size}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def boolean(values, name):
    text = values.astype(str)
    if not text.isin(["True", "False"]).all():
        raise ValueError(f"{name}: expected literal True/False")
    return text.eq("True")


def validate_scores(values, name):
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all() or not ((array >= 0) & (array <= 1)).all():
        raise ValueError(f"{name}: scores must be finite in[0,1]")


def classify_agreement(table, manifest):
    """Relate agreement estimates using metadata, without calling groups independent."""
    runs = manifest.set_index("run_id")
    group_lookup = {}
    for row in manifest.itertuples():
        group_lookup[f"{row.cell_line}:rep{row.biological_replicate}"] = row.cell_line
    result = table.copy()
    labels = []
    for row in table.itertuples():
        if row.unit == "run_id":
            if row.a not in runs.index or row.b not in runs.index:
                raise ValueError("Agreement contains an unknown run")
            a, b = runs.loc[row.a], runs.loc[row.b]
            if a.cell_line != b.cell_line:
                label = RELATIONS[2]
            elif str(a.biological_replicate) == str(b.biological_replicate):
                label = RELATIONS[0]
            else:
                label = RELATIONS[1]
        elif row.unit == "replicate_id":
            if row.a not in group_lookup or row.b not in group_lookup:
                raise ValueError("Agreement contains an unknown metadata group")
            label = RELATIONS[3] if group_lookup[row.a] == group_lookup[row.b] else RELATIONS[4]
        else:
            raise ValueError("Unknown agreement unit")
        labels.append(label)
    result["metadata_relationship"] = labels
    return result


def agreement_summary(table):
    rows = []
    for depth in DEPTHS:
        for relationship in RELATIONS:
            subset = table[(table.coverage_threshold == depth) & (table.metadata_relationship == relationship)]
            defined = subset.spearman.dropna()
            rows.append({"coverage_threshold": depth, "metadata_relationship": relationship,
                         "n_pair_estimates": len(subset), "n_defined_correlations": len(defined),
                         "median_spearman": float(defined.median()) if len(defined) else np.nan,
                         "minimum_spearman": float(defined.min()) if len(defined) else np.nan,
                         "maximum_spearman": float(defined.max()) if len(defined) else np.nan,
                         "median_shared_site_count": float(subset.n_common_sites.median()) if len(subset) else np.nan,
                         "median_absolute_score_difference": float(subset.median_absolute_delta.median()) if len(subset) else np.nan})
    return pd.DataFrame(rows)


def common_summaries(wide, depth):
    rows, cdf = [], []
    grid = np.linspace(0, 1, 501)
    for line in wide:
        values = np.asarray(wide[line], dtype=float)
        validate_scores(values, "all-line common")
        ordered = np.sort(values)
        for cutoff in CUTOFFS:
            high = int((values >= cutoff).sum())
            rows.append({"coverage_threshold": depth, "cell_line": line, "score_cutoff": cutoff,
                         "n_common_sites": len(values), "mean_score": float(values.mean()) if len(values) else np.nan,
                         "median_score": float(np.median(values)) if len(values) else np.nan,
                         "n_high": high, "fraction_high": high / len(values) if len(values) else np.nan})
        for value, count in zip(grid, np.searchsorted(ordered, grid, side="right")):
            cdf.append({"coverage_threshold": depth, "cell_line": line, "score_grid": value,
                        "n_sites_le_score": int(count), "n_common_sites": len(values),
                        "empirical_fraction_le_score": count / len(values) if len(values) else np.nan})
    return pd.DataFrame(rows), pd.DataFrame(cdf)


def validate_pair_summary(pair, summary_rows):
    """Recompute actual pair denominators/effects/flags from saved full pair rows."""
    if pair[KEYS].duplicated().any():
        raise ValueError("Duplicate pair site keys")
    for column in ["score_a", "score_b"]:
        validate_scores(pair[column], column)
    delta = pair.score_a - pair.score_b
    if not np.allclose(pair.delta_score, delta, atol=1e-14, rtol=1e-14):
        raise ValueError("Pair delta is inconsistent with saved scores")
    balanced = boolean(pair.coverage_balanced, "coverage_balanced")
    flags = boolean(pair.candidate_large_difference, "candidate_large_difference")
    if (not np.isfinite(pair.coverage_ratio).all() or (pair.coverage_ratio < 1-1e-14).any()
            or not balanced.eq(pair.coverage_ratio.le(2)).all()):
        raise ValueError("Pair coverage-balance flag is inconsistent")
    separated = (pair.score_min_a > pair.score_max_b) | (pair.score_max_a < pair.score_min_b)
    if not flags.eq(delta.abs().ge(.2) & separated & balanced).all():
        raise ValueError("Candidate flags differ from the declared descriptive screen")
    if pair.n_replicates_a.lt(2).any() or pair.n_replicates_b.lt(2).any():
        raise ValueError("Pair lacks two metadata groups per line")
    for row in summary_rows.itertuples():
        mask = np.ones(len(pair), dtype=bool) if row.population == "all_pairwise_common" else balanced.to_numpy()
        d = delta[mask]
        actual = [len(d), int(flags[mask].sum())]
        if actual != [int(row.n_sites), int(row.n_large_replicate_separated)]:
            raise ValueError("Pair summary counts differ from full pair table")
        median = float(d.median()) if len(d) else np.nan
        if not np.isclose(median, row.median_delta_a_minus_b, atol=1e-14, rtol=1e-14, equal_nan=True):
            raise ValueError("Pair summary median differs from full pair table")


def save_figure(fig, path):
    fig.savefig(path.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def figures(output, populations, common, cdf, agreements, pair_summary):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12,
                         "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    all_lines = populations[populations.population_type.eq("all_lines")].sort_values("coverage_threshold")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1, 1.3]})
    x = np.arange(3)
    for offset, column, label, color in [(-.25, "n_annotated_coverage_qualified", "Before context gate", "#B7C0C6"),
                                         (0, "n_primary_all_source_consistent", "Primary: all-source agreement", COLORS[0]),
                                         (.25, "n_scored_only_consistent", "Sensitivity: scored-only agreement", COLORS[1])]:
        bars = axes[0].bar(x + offset, all_lines[column], width=.23, label=label, color=color)
        for bar in bars:
            axes[0].annotate(f"{int(bar.get_height()):,}", (bar.get_x() + bar.get_width()/2, bar.get_height()),
                             ha="center", va="bottom", fontsize=8, rotation=90, xytext=(0, 3), textcoords="offset points")
    axes[0].set(xticks=x, xticklabels=DEPTHS, xlabel="Minimum reads per eligible run", ylabel="Sites common to all seven lines",
                title="A  Coverage and context define the population")
    axes[0].set_ylim(0, max(1, all_lines.n_annotated_coverage_qualified.max())*1.28)
    axes[0].legend(fontsize=8, loc="upper right")
    pairs = populations[(populations.population_type == "pairwise") & (populations.coverage_threshold == 20)].copy()
    pairs["excluded_fraction"] = np.where(pairs.n_annotated_coverage_qualified > 0,
                                           pairs.n_excluded_primary_context / pairs.n_annotated_coverage_qualified, np.nan)
    axes[1].barh(pairs.cell_lines.str.replace("|", " / ", regex=False), pairs.excluded_fraction * 100, color=COLORS[3])
    # A zero-width bar is invisible: explicitly show valid zero exclusions.
    axes[1].scatter(pairs.excluded_fraction * 100, np.arange(len(pairs)), color=COLORS[3], s=18, zorder=3)
    if pairs.excluded_fraction.eq(0).all():
        axes[1].set_xlim(-.05, .25)
        axes[1].set_xticks([0, .1, .2], ["0%", "0.1%", "0.2%"])
        axes[1].text(.97, .5, "No context exclusions\nin any of the 21 pairs", transform=axes[1].transAxes,
                     ha="right", va="center", fontsize=10)
    axes[1].invert_yaxis(); axes[1].tick_params(axis="y", labelsize=8)
    axes[1].set(xlabel="Excluded from primary population by context QC (%)", title="B  All 21 pairwise populations at >=20 reads")
    fig.suptitle("Matching sequence context is a prerequisite for score comparison", y=1.03, fontsize=13)
    fig.tight_layout(); save_figure(fig, output / "context_population_consequences")

    lines = sorted(common.cell_line.unique())
    n20 = common.loc[common.coverage_threshold.eq(20), "n_common_sites"].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.7))
    for color, line in zip(COLORS, lines):
        d = cdf[(cdf.coverage_threshold == 20) & (cdf.cell_line == line)]
        axes[0].plot(d.score_grid, d.empirical_fraction_le_score, label=line, color=color, lw=1.6)
    axes[0].set(xlabel="Replicate-aware predicted site score", ylabel="Fraction of matched sites with score <= x",
                title=f"A  Same {n20:,} sites in every line (>=20 reads)", xlim=(0, 1), ylim=(0, 1))
    axes[0].legend(fontsize=8)
    x = np.arange(len(lines))
    for offset, cutoff, color in [(-.24, .5, COLORS[0]), (0, .7, COLORS[1]), (.24, .9, COLORS[3])]:
        d = common[(common.coverage_threshold == 20) & (common.score_cutoff == cutoff)].set_index("cell_line").loc[lines]
        axes[1].bar(x + offset, d.fraction_high*100, width=.23, color=color, label=f"Score >= {cutoff}")
    axes[1].set(xticks=x, xticklabels=lines, xlabel="Cell line", ylabel="Matched sites above descriptive cutoff (%)",
                title="B  Cutoff sensitivity on the same population")
    axes[1].tick_params(axis="x", rotation=30); axes[1].legend(fontsize=8)
    fig.suptitle("Scores are model outputs, not measured modification fractions", y=1.03, fontsize=13)
    fig.tight_layout(); save_figure(fig, output / "matched_site_score_patterns")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    for ax, depth in zip(axes, DEPTHS):
        for i, relationship in enumerate(RELATIONS):
            values = agreements[(agreements.coverage_threshold == depth) & (agreements.metadata_relationship == relationship)].spearman.dropna().to_numpy()
            if len(values):
                ax.boxplot([values], positions=[i], widths=.5, patch_artist=True,
                           boxprops={"facecolor": COLORS[i], "alpha": .6}, medianprops={"color": "black"}, showfliers=True)
            ax.text(i, .06, f"n={len(values)}", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=8)
        ax.set(xticks=range(5), xticklabels=["Run same\ngroup", "Run same line,\nother group", "Run other\nline", "Group mean\nsame line", "Group mean\nother line"],
               ylim=(-1, 1), title=f"Minimum {depth} reads")
        ax.tick_params(axis="x", labelsize=8, rotation=25); ax.axhline(0, color="#AAAAAA", lw=.7)
    axes[0].set_ylabel("Spearman rank agreement on shared sites")
    fig.suptitle("Descriptive run/group concordance; each pair has its own shared-site denominator", y=1.08, fontsize=12)
    fig.tight_layout(); save_figure(fig, output / "run_group_agreement")

    pair_data = pair_summary[pair_summary.population == "all_pairwise_common"].copy()
    order = list(pair_data.loc[pair_data.coverage_threshold.eq(20), ["cell_line_a", "cell_line_b"]].itertuples(index=False, name=None))
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 8), sharey=True, gridspec_kw={"width_ratios": [1, 1]})
    positions = np.arange(len(order))
    labels = []
    for a, b in order:
        rows = pair_data[(pair_data.cell_line_a == a) & (pair_data.cell_line_b == b)].set_index("coverage_threshold")
        labels.append(f"{a} - {b}  [{int(rows.loc[20, 'n_sites']):,} / {int(rows.loc[50, 'n_sites']):,} / {int(rows.loc[100, 'n_sites']):,}]")
    for offset, depth, color in [(-.2, 20, COLORS[0]), (0, 50, COLORS[1]), (.2, 100, COLORS[2])]:
        values = pair_data[pair_data.coverage_threshold == depth].set_index(["cell_line_a", "cell_line_b"]).loc[order]
        axes[0].scatter(values.median_delta_a_minus_b, positions + offset, label=f">={depth} reads", color=color, s=22)
        axes[1].scatter(values.n_large_replicate_separated, positions + offset, label=f">={depth} reads", color=color, s=22)
    axes[0].set(yticks=positions, yticklabels=labels, xlabel="Median paired score difference (A minus B)", title="A  Continuous effects, all 21 pairs")
    axes[0].tick_params(axis="y", labelsize=8); axes[0].axvline(0, color="#777777", lw=.8); axes[0].invert_yaxis()
    axes[1].set(xlabel="Descriptive candidate count", title="B  Large, separated, depth-balanced flags")
    axes[0].legend(fontsize=8); axes[1].legend(fontsize=8)
    fig.suptitle("Pair-specific denominators in brackets: >=20 / >=50 / >=100 reads\nCandidate: |delta|>=0.2, separated group ranges, depth ratio<=2; no significance/FDR claim", y=1.02, fontsize=11)
    fig.tight_layout(); save_figure(fig, output / "all_pairwise_effects")


def run_report(qc_dir, analysis_dir, output, manifest_path, metadata_path):
    qc_dir, analysis_dir, output = Path(qc_dir), Path(analysis_dir), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    source_hash = sha(Path(__file__))
    write_json(output / "status.json", {"status": "running"})
    input_files = {}
    def read_csv(path, **kwargs):
        path = Path(path); input_files[str(path.resolve())] = record(path)
        return pd.read_csv(path, float_precision="round_trip", **kwargs)
    def read_json(path):
        path = Path(path); input_files[str(path.resolve())] = record(path)
        return json.loads(path.read_text(encoding="utf-8"))
    qc = read_json(qc_dir / "complete.json")
    receipt = read_json(analysis_dir / "analysis_receipt.json")
    if qc.get("status") != "complete" or receipt.get("status") != "complete":
        raise ValueError("Both source analyses must be complete")
    info = receipt["context_qualification"]
    if info["policy"] != "all-source-consistent" or info["qc_complete_sha256"] != sha(qc_dir / "complete.json"):
        raise ValueError("Reporter requires the primary all-source context-qualified comparison linked to this QC")
    args = receipt["arguments"]
    if ([int(x) for x in args["coverage"].split(",")] != list(DEPTHS)
            or [float(x) for x in args["cutoffs"].split(",")] != list(CUTOFFS)
            or args["min_replicates"] != 2 or args["require_all_replicates"] or args["allow_missing_predictions"]
            or args["max_coverage_ratio"] != 2 or args["min_delta"] != .2):
        raise ValueError("Comparison differs from the declared primary design")
    manifest = read_csv(manifest_path, keep_default_na=False, dtype=str)
    if len(manifest) != 23 or manifest.run_id.duplicated().any() or manifest.cell_line.nunique() != 7:
        raise ValueError("Fixed23-run/seven-line manifest required")
    if sha(manifest_path) != receipt["manifest_sha256"] or sha(manifest_path) != qc["inputs"]["manifest"]["sha256"]:
        raise ValueError("Manifest changed since source analysis")
    if len(receipt["predictions"]) != 23 or len({item["run_id"] for item in receipt["predictions"]}) != 23:
        raise ValueError("Expected23 unique prediction receipts")
    pred_by_run = {item["run_id"]: item["sha256"] for item in receipt["predictions"]}
    qc_pred = {item["run_id"]: item["sha256"] for item in qc["inputs"]["predictions"]}
    if pred_by_run != qc_pred or set(pred_by_run) != set(manifest.run_id):
        raise ValueError("Comparison/QC prediction fingerprints differ")
    for item in receipt["predictions"]:
        path = (Path(manifest_path).parent / item["path"]).resolve()
        input_files[str(path)] = record(path)
        if sha(path) != item["sha256"]:
            raise ValueError("Original prediction changed after comparison")
    for name in ["population_effects.csv", "summary.json", "key_context_qc.csv.gz", "run_qc_counts.csv"]:
        if sha(qc_dir / name) != qc["outputs"][name]["sha256"]:
            raise ValueError(f"QC output changed: {name}")
    population = read_csv(qc_dir / "population_effects.csv")
    summary = read_json(qc_dir / "summary.json")
    key_qc = read_csv(qc_dir / "key_context_qc.csv.gz", keep_default_na=False, dtype={"transcript_id": str})
    if key_qc[KEYS].duplicated().any(): raise ValueError("Duplicate context-QC key")
    key_qc["all_source_consistent"] = boolean(key_qc.all_source_consistent, "all_source_consistent")
    availability = read_csv(analysis_dir / "prediction_availability.csv")
    if len(availability) != 23 or availability.missing_predictions.any() or not availability.expected_sites.eq(availability.predicted_sites).all():
        raise ValueError("Comparison lacked complete predictions")
    original_common = read_csv(analysis_dir / "all_line_summary.csv")
    common_tables, cdf_tables, supports = [], [], []
    lines = sorted(manifest.cell_line.unique())
    for depth in DEPTHS:
        wide = read_csv(analysis_dir / f"all_line_common_scores_cov{depth}.csv.gz", dtype={"transcript_id": str})
        if wide[KEYS].duplicated().any() or set(wide.columns) != set(KEYS + lines):
            raise ValueError("Invalid all-line common-score table")
        context = wide[KEYS].merge(key_qc, on=KEYS, how="left", validate="one_to_one")
        if context.all_source_consistent.isna().any() or not context.all_source_consistent.all() or not context.kind.eq("annotated").all():
            raise ValueError("All-line common table contains an unqualified context/annotation")
        expected = population[(population.population_type == "all_lines") & (population.coverage_threshold == depth)].iloc[0]
        if len(wide) != int(expected.n_primary_all_source_consistent):
            raise ValueError("All-line denominator disagrees with context-QC population")
        table, cdf = common_summaries(wide[lines], depth)
        old = original_common[original_common.coverage_threshold == depth]
        joined = table.merge(old, on=["coverage_threshold", "cell_line", "score_cutoff"], validate="one_to_one", suffixes=("_new", "_old"))
        if len(joined) != 21:
            raise ValueError("Missing all-line threshold summary rows")
        for column in ["n_common_sites", "mean_score", "median_score", "fraction_high"]:
            if not np.allclose(joined[column+"_new"], joined[column+"_old"], equal_nan=True, rtol=1e-13, atol=1e-14):
                raise ValueError("Recomputed all-line summary differs")
        common_tables.append(table); cdf_tables.append(cdf)
        pos = pd.to_numeric(context.training_positive_labels_all_source.replace("", np.nan))
        for label, mask in [("zero positive labels", pos.eq(0)), ("1-19 positive labels", pos.ge(1)&pos.lt(20)),
                            (">=20 positive labels", pos.ge(20)), ("unknown support", pos.isna())]:
            supports.append({"coverage_threshold": depth, "training_context_support": label, "n_common_sites": len(wide),
                             "n_sites": int(mask.sum()), "fraction": float(mask.mean()) if len(wide) else np.nan})
    common, cdf = pd.concat(common_tables, ignore_index=True), pd.concat(cdf_tables, ignore_index=True)
    pair_summary = read_csv(analysis_dir / "pair_summary.csv")
    expected_pairs = set(itertools.combinations(lines, 2))
    for depth in DEPTHS:
        for a, b in sorted(expected_pairs):
            rows = pair_summary[(pair_summary.coverage_threshold == depth) & (pair_summary.cell_line_a == a) & (pair_summary.cell_line_b == b)]
            if len(rows) != 2 or set(rows.population) != {"all_pairwise_common", "coverage_balanced"}:
                raise ValueError("Missing/duplicated pair-population summary")
            pair = read_csv(analysis_dir / f"pairs/{a}__{b}__cov{depth}.csv.gz", dtype={"transcript_id": str})
            validate_pair_summary(pair, rows)
            context_join = pair[KEYS].merge(key_qc[KEYS+["all_source_consistent", "kind"]], on=KEYS, how="left", validate="one_to_one")
            if context_join.all_source_consistent.isna().any() or not context_join.all_source_consistent.all() or not context_join.kind.eq("annotated").all():
                raise ValueError("Pair includes nonprimary context")
            expected = population[(population.population_type == "pairwise") & (population.coverage_threshold == depth) & (population.cell_lines == f"{a}|{b}")].iloc[0]
            if len(pair) != int(expected.n_primary_all_source_consistent):
                raise ValueError("Pair denominator differs from context-QC population")
        print(f"Report verified21 full pair tables at >={depth} reads", flush=True)
    if len(pair_summary) != 126:
        raise ValueError("Expected21pairs x3depths x2populations")
    agreements = classify_agreement(read_csv(analysis_dir / "agreement.csv"), manifest)
    agreement_stats = agreement_summary(agreements)
    coverage = read_csv(analysis_dir / "score_coverage_dependence.csv")
    metadata = read_csv(metadata_path, keep_default_na=False, dtype=str)
    if set(metadata.run_id) != set(manifest.run_id) or metadata.run_id.duplicated().any():
        raise ValueError("Technical metadata differs from23runs")
    metadata_identity = metadata.set_index("run_id").loc[manifest.run_id, ["cell_line", "biological_replicate"]].reset_index(drop=True)
    if not metadata_identity.equals(manifest[["cell_line", "biological_replicate"]].reset_index(drop=True)):
        raise ValueError("Technical metadata line/group identities differ from manifest")
    technical_columns = ["run_id", "cell_line", "biological_replicate", "replicate_status", "flowcell", "kit", "Platform", "basecaller_version(ENA)*", "generation_date", "Spike in concentration"]
    technical = metadata[technical_columns].copy()
    technical = technical.rename(columns={"basecaller_version(ENA)*": "basecaller_version", "Spike in concentration": "spike_in_description"})
    technical_counts = []
    for line, rows in technical.groupby("cell_line", sort=True):
        for column in ["flowcell", "kit", "Platform", "basecaller_version", "generation_date", "spike_in_description"]:
            for value, count in rows[column].replace("", "not supplied").value_counts().items():
                technical_counts.append({"cell_line": line, "metadata_field": column, "value": value, "n_runs": int(count)})
    for filename, frame in [("context_population_effects.csv", population), ("all_line_score_summary.csv", common),
                            ("all_line_score_cdf_grid.csv", cdf), ("all_pair_summary.csv", pair_summary),
                            ("agreement_by_metadata_relationship.csv", agreements), ("agreement_summary.csv", agreement_stats),
                            ("score_coverage_dependence.csv", coverage), ("common_site_training_context_support.csv", pd.DataFrame(supports)),
                            ("technical_run_metadata.csv", technical), ("technical_metadata_counts.csv", pd.DataFrame(technical_counts))]:
        frame.to_csv(output / filename, index=False)
    figures(output, population, common, cdf, agreements, pair_summary)
    c20 = common[(common.coverage_threshold == 20) & (common.score_cutoff == .5)]
    allpop = population[population.population_type == "all_lines"].sort_values("coverage_threshold")
    counts = summary["counts"]
    s20 = pd.DataFrame(supports); s20 = s20[s20.coverage_threshold == 20]
    weak = int(s20[s20.training_context_support.isin(["zero positive labels", "1-19 positive labels"])].n_sites.sum())
    n20 = int(c20.n_common_sites.iloc[0])
    rows_text = "\n".join(f"| {row.cell_line} | {row.mean_score:.4f} | {row.median_score:.4f} | {100*row.fraction_high:.2f}% |" for row in c20.itertuples())
    text = f"""# Task2: context-qualified predicted-score patterns

This is assistant-executed descriptive analysis of the selected frozen model,
not an independent m6A assay, calibrated prevalence estimate or causal cell-line test.
All23 original prediction exports remain complete and unchanged. Metadata groups
follow sample names; separate laboratory preparations are not independently proven.

## Context determines which site keys can be compared

The audit streamed {summary['source_totals']['source_sites']:,} saved source-site
observations. It compared all source contexts at the {counts['coverage_union_keys']:,}
coverage-union keys, including low-read observations. There were
{counts.get('encoded_conflict_all_source_keys', 0):,} keys with conflicting model-encoded
contexts across those source observations and {counts.get('encoded_conflict_scored_keys', 0):,}
with conflicts among >=20-read scored observations. Contexts outside the complete
scoreable union were not compared; those observations were never scored by this application.
Conflicts remain in the QC evidence and original exports. No majority sequence was substituted.

Across all seven lines, before-context / primary-context / scored-only-sensitivity
common populations are: {', '.join(f">={int(r.coverage_threshold)} reads: {int(r.n_annotated_coverage_qualified):,} / {int(r.n_primary_all_source_consistent):,} / {int(r.n_scored_only_consistent):,}" for r in allpop.itertuples())}.
Every comparison additionally requires annotated human keys and >=2 metadata groups
per cell line. Eligible runs are averaged within group, then groups receive equal weights.

## Patterns on one explicitly matched population

At >=20 reads, each line uses the same {n20:,} common sites:

| Cell line | Mean score | Median score | Score >=0.5 |
|---|---:|---:|---:|
{rows_text}

The 0.5/0.7/0.9 cutoffs are descriptive conventions. Continuous distributions
and cutoff counts are provided together; none of these percentages measures
chemical modification prevalence or the fraction of modified molecules.
The >=50 and >=100 populations contain different subsets of sites. Changes
between their summaries mix population selection and coverage, and are not a
controlled within-site read-depth experiment.

## Concordance and pair-specific effects

`agreement_summary.csv` separates same-group sequencing runs, other groups in the
same cell line, and cross-line comparisons. Its correlations describe score ranks
on the sites shared by each pair; each estimate has its own denominator. Shared
sequence/context structure can contribute to agreement. A high correlation is not
prediction accuracy or evidence that groups are independent biological replicates.

All21 line pairs are retained at all three read thresholds. Each pair uses its own
common population, separately from the all-seven-line panel. Full pair files remain
with the comparator outputs, including small effects, overlapping group ranges and
valid extremes. Candidate flags require |mean-score difference|>=0.2, non-overlapping
group ranges and depth ratio<=2. They are exploratory screens, without a significance
test or false-discovery control. `all_pair_summary.csv` reports their denominators.

## Support, negative evidence and limits

Of the {n20:,} common >=20-read sites, {weak:,} have a seven-base context with fewer
than20 positive data0 training labels. They remain in every applicable analysis;
support counts are warnings, not calibrated uncertainty or an exclusion rule.
`common_site_training_context_support.csv` retains zero, sparse, well-supported and
unknown support separately. The context gate, conflicting cases, undefined correlations
and all21 pair outcomes are preserved rather than selected for favourable results.

`score_coverage_dependence.csv` records observed score/read-count associations.
`technical_metadata_counts.csv` records basecaller, platform, kit, date and spike-in
composition by line. Coverage balancing does not fully adjust expression or batch;
technical factors can be confounded with cell line. Matching seven bases does not
prove exact historical FASTA identity or nucleotide/event offsets. No genomic-region,
pathway, chemical-type, stoichiometry or causal lineage claim follows from this analysis.

## Reproduction and figures

Run `sgnex_analysis/scripts/report_task2_analysis.py --qc-dir ... --analysis-dir ...
--out NEW_DIRECTORY` from the repository root with the documented Python environment.
The reporter rechecks source completion, context-policy/input binding, complete
prediction availability, all-seven-line summaries, all63 full pair tables and QC
population denominators before writing its own completion receipt last.
PNG and editable-text SVG figures accompany the aggregate CSVs. CDF plots use an
explicit501-point grid of the empirical distribution; the score summaries use all sites.
"""
    (output / "findings.md").write_text(text, encoding="utf-8")
    # Recheck every consumed file after computation, so a concurrent update fails.
    for path, saved in input_files.items():
        if sha(path) != saved["sha256"]:
            raise ValueError("A consumed analysis input changed during reporting")
    if sha(Path(__file__)) != source_hash:
        raise ValueError("Reporter source changed during execution")
    outputs = {path.name: record(path) for path in output.iterdir() if path.name not in {"status.json", "complete.json"}}
    complete = {"status": "complete", "script_sha256": source_hash, "inputs": list(input_files.values()),
                "qc_complete_sha256": sha(qc_dir / "complete.json"), "analysis_receipt_sha256": sha(analysis_dir / "analysis_receipt.json"),
                "outputs": outputs, "no_training_or_inference": True,
                "resources": {"wall_seconds": time.perf_counter()-start, "process_cpu_seconds": time.process_time()-cpu},
                "resource_scope": "Current process after new-directory creation through validation/analysis/plots/input-rehash; excludes final completion/status writes and imports. External monitor may record peak memory separately",
                "software": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__}}
    write_json(output / "complete.json", complete)
    write_json(output / "status.json", {"status": "complete", "complete_sha256": sha(output / "complete.json")})
    return complete


def main():
    p = argparse.ArgumentParser(description=__doc__)
    base = REPO / "sgnex_analysis"
    p.add_argument("--qc-dir", type=Path, default=base / "outputs/context_qc_v1")
    p.add_argument("--analysis-dir", type=Path, default=base / "outputs/real_analysis_context_v2")
    p.add_argument("--out", type=Path, default=base / "outputs/task2_report_v1")
    p.add_argument("--manifest", type=Path, default=base / "manifest.csv")
    p.add_argument("--metadata", type=Path, default=base / "metadata/sample_manifest.csv")
    args = p.parse_args(); existed = args.out.exists()
    try:
        result = run_report(args.qc_dir, args.analysis_dir, args.out, args.manifest, args.metadata)
        print(json.dumps({"status": result["status"], "n_output_files": len(result["outputs"]), "resources": result["resources"]}), flush=True)
    except BaseException as exc:
        if not existed and args.out.exists() and not (args.out / "complete.json").exists():
            write_json(args.out / "status.json", {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
        raise


if __name__ == "__main__": main()
