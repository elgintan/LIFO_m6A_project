"""Small figures and training-key diagnostics for already frozen illustrative cases."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from select_biological_cases import ROOT, KEY, DEPTHS, LINES, sha, write_json

COLORS = dict(zip(LINES, ["#20708c", "#db902a", "#5c9263", "#ae5268", "#7b65a3", "#856c46", "#567db7"]))
ROLES = {"persistent_difference_nontraining_lines": "Persistent contrast: nontraining lines",
         "persistent_difference_training_line": "Persistent contrast: training-line diagnostic",
         "shared_high": "Shared high line averages",
         "overlapping_groups_inconclusive": "Overlapping groups: inconclusive contrast"}


def training_keys(cases, labels):
    if labels.duplicated(KEY).any():
        raise ValueError("Duplicate data0 label keys")
    result = cases[["case_id", "gene_id", "gene_name"] + KEY].merge(labels, on=KEY, how="left", validate="many_to_one", suffixes=("_annotation", "_data0"), indicator=True)
    result["training_key_present"] = result.pop("_merge").eq("both")
    result["gene_id_matches_when_present"] = np.where(result.training_key_present, result.gene_id_annotation.eq(result.gene_id_data0), True)
    if not result.gene_id_matches_when_present.all():
        raise ValueError("Historical gene identity mismatch at matching training key")
    result["independent_validation"] = False
    return result


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=220, bbox_inches="tight")
    fig.savefig(out / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def make_figures(cases, runs, groups, line_scores, train, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
                         "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for ax, case in zip(axes.flat, cases.itertuples(index=False)):
        d = runs[runs.case_id.eq(case.case_id)]
        g = groups[groups.case_id.eq(case.case_id) & groups.coverage_threshold.eq(20)]
        for i, line in enumerate(LINES):
            gg = g[g.cell_line.eq(line)].sort_values("biological_replicate")
            offsets = np.linspace(-.19, .19, len(gg)) if len(gg) > 1 else [0]
            for offset, group in zip(offsets, gg.itertuples(index=False)):
                rr = d[d.cell_line.eq(line) & d.biological_replicate.eq(group.biological_replicate) & d.score.notna()].sort_values("run_id")
                jitter = np.linspace(-.04, .04, len(rr)) if len(rr) > 1 else [0]
                ax.scatter(i + offset + np.array(jitter), rr.score, s=40, facecolors="none", edgecolors="#8b969e", linewidths=.8, zorder=2)
                ax.scatter(i + offset, group.score, marker="D", s=25, color=COLORS[line], edgecolors="white", linewidths=.4, zorder=3)
        t = train[train.case_id.eq(case.case_id)].iloc[0]
        training_text = f"data0 key present; supplied label {int(t.label)}" if t.training_key_present else "key absent from data0 labels"
        support = int(case.training_positive_labels_all_source)
        available = line_scores[(line_scores.case_id == case.case_id) & line_scores.coverage_threshold.eq(20)].set_index("cell_line")
        ticklabels = [line + ("*" if line in available.index and available.loc[line, "n_replicates"] < 2 else "") for line in LINES]
        suffix = "\n* Only one group; blank lines have no >=20-read scores" if any("*" in x for x in ticklabels) else ""
        ax.set(title=f"{case.gene_name} · {case.transcript_id}:{int(case.transcript_position)}\n{ROLES[case.case_id]}",
               xticks=range(7), xticklabels=ticklabels, xlim=(-.6, 6.6), ylim=(-.04, 1.04), ylabel="Predicted m6A site score",
               xlabel=f"Context {case.analysis_sequence_7mer}; {support} positive training-context labels\n{training_text}; not independent assay validation{suffix}")
        ax.tick_params(axis="x", rotation=25)
        ax.axhline(.5, color="#b8bdc2", linestyle="--", lw=.7, zorder=0)
    handles = [Line2D([], [], marker="o", linestyle="none", markerfacecolor="none", color="#8b969e", label="Original run score (>=20 reads)"),
               Line2D([], [], marker="D", linestyle="none", color="#20708c", label="Metadata-group mean (groups may have 1 or 2 runs)")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False)
    fig.suptitle("Four fixed illustrative cases: scores and repeat measurements", fontsize=13)
    save(fig, out, "case_group_score_patterns")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for ax, case in zip(axes.flat, cases.itertuples(index=False)):
        lines = LINES if case.case_id == "shared_high" else [case.cell_line_a, case.cell_line_b]
        d = line_scores[line_scores.case_id.eq(case.case_id)]
        for line in lines:
            series = d[d.cell_line.eq(line)].set_index("coverage_threshold").reindex(DEPTHS)
            values = series.score.where(series.n_replicates.ge(2))
            ax.plot(range(3), values, marker="o", label=line, color=COLORS[line], lw=1.3, markersize=4)
            for i, depth in enumerate(DEPTHS):
                if pd.notna(values.loc[depth]) and case.case_id != "shared_high":
                    ax.annotate(f"g={int(series.loc[depth, 'n_replicates'])}", (i, values.loc[depth]), textcoords="offset points", xytext=(3, 4), fontsize=7, color=COLORS[line])
        if case.case_id == "overlapping_groups_inconclusive":
            for i in [1, 2]:
                ax.text(i, .5, "Pair ineligible:\n<2 groups per line", ha="center", va="center", fontsize=9, color="#6e747b")
        if case.case_id == "shared_high":
            ax.text(.5, .6, "All seven lines: 2-3 groups each\nAll 23 runs remain eligible at every depth", transform=ax.transAxes,
                    ha="center", va="center", fontsize=9, color="#59616a")
        ax.set(title=f"{case.gene_name} · {ROLES[case.case_id]}", xticks=range(3), xticklabels=[">=20", ">=50", ">=100"],
               xlabel="Minimum reads per eligible run", ylabel="Equal-group mean site score", ylim=(0, 1.06), xlim=(-.15, 2.25))
        ax.legend(fontsize=7, loc="best", frameon=False, ncol=2 if len(lines) > 2 else 1)
    fig.suptitle("Nested depth sensitivity: unchanged scores can use the same original runs", fontsize=12)
    save(fig, out, "case_depth_sensitivity")


def run(selection_dir, evidence_dir, out, labels_path):
    started = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "status.json", {"status": "started"})
    inputs = []
    for directory in [selection_dir, evidence_dir]:
        receipt_path = directory / "complete.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["status"] != "complete":
            raise ValueError("Source is incomplete")
        for name, record in receipt["outputs"].items():
            path = directory / name
            if sha(path) != record["sha256"] or path.stat().st_size != record["size_bytes"]:
                raise ValueError(f"Changed completed output: {path.name}")
        inputs.append({"path": receipt_path.relative_to(ROOT).as_posix(), "sha256": sha(receipt_path)})
    cases = pd.read_csv(evidence_dir / "selected_cases.csv", float_precision="round_trip")
    runs = pd.read_csv(evidence_dir / "case_run_evidence.csv", float_precision="round_trip")
    groups = pd.read_csv(evidence_dir / "case_group_scores.csv", float_precision="round_trip")
    line_scores = pd.read_csv(evidence_dir / "case_line_scores.csv", float_precision="round_trip")
    specification_path = ROOT / "model_elgin/artifacts/cap128_weight3_v1/training_specification.json"
    spec = json.loads(specification_path.read_text(encoding="utf-8"))
    if sha(labels_path) != spec["identity"]["labels_sha256"]:
        raise ValueError("Training label fingerprint changed")
    labels = pd.read_csv(labels_path)
    train = training_keys(cases, labels)
    train.to_csv(out / "training_key_diagnostics.csv", index=False)
    # This is post-selection diagnostics; labels never enter selection or ranking.
    write_json(out / "training_key_scope.json", {"selection_unchanged": True, "labels_used_only_after_cases_frozen": True,
        "labels_sha256": sha(labels_path), "training_specification_sha256": sha(specification_path),
        "limits": "Matching literal key is not proof of same sample, assay or historical reference; data0 labels do not validate SG-NEx predictions"})
    make_figures(cases, runs, groups, line_scores, train, out)
    summary_rows = []
    for case in cases.itertuples(index=False):
        t = train[train.case_id.eq(case.case_id)].iloc[0]
        r = runs[runs.case_id.eq(case.case_id)]
        row = {"case_id": case.case_id, "gene_name": case.gene_name, "gene_id": case.gene_id,
               "transcript_id": case.transcript_id, "transcript_position": int(case.transcript_position),
               "sequence_7mer": case.analysis_sequence_7mer, "positive_training_context_labels": int(case.training_positive_labels_all_source),
               "training_key_present": bool(t.training_key_present), "data0_label": t.label,
               "n_scored_runs_20": int(r.score.notna().sum()), "n_below20_runs": int(r.n_reads.between(1, 19).sum())}
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(out / "case_summary.csv", index=False)
    files = {p.name: {"sha256": sha(p), "size_bytes": p.stat().st_size} for p in sorted(out.iterdir()) if p.name != "status.json"}
    inputs.extend([{"path": "../data0/data.info.labelled", "sha256": sha(labels_path)},
                   {"path": specification_path.relative_to(ROOT).as_posix(), "sha256": sha(specification_path)}])
    write_json(out / "complete.json", {"status": "complete", "script_sha256": sha(Path(__file__)), "inputs": inputs,
               "outputs": files, "no_training_or_inference": True, "wall_seconds_internal": time.perf_counter() - started})
    write_json(out / "status.json", {"status": "complete"})
    print(f"Complete: {len(cases)} cases; two PNG/SVG figure pairs; training-key diagnostics")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=ROOT.parent / "data0/data.info.labelled")
    parser.add_argument("--out", type=Path, required=True)
    cli = parser.parse_args()
    run(cli.selection_dir.resolve(), cli.evidence_dir.resolve(), cli.out.resolve(), cli.labels.resolve())
