"""Audit and summarise the first complete frozen-model SG-NEx run.

No training, model inference, source-signal transformation or biological-label
scoring. Per-site inputs stay local; only aggregate report evidence is exported.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RUN = "SGNex_Hct116_directRNA_replicate3_run4"
MODEL = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
VERSION = "elgin-cap128-weight3-18epoch-b2d38ff29a91"
PREDICTIONS = REPO / "sgnex_analysis/outputs/predictions"
PREFLIGHT = REPO / "sgnex_analysis/outputs/preflight"
RECEIVED = REPO / "sgnex_analysis/outputs/received_member4_20261019"
THRESHOLDS = (0.5, 0.7, 0.9)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(2 ** 20), b""):
            digest.update(block)
    return digest.hexdigest()


def code_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, payload):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def table(rows, columns):
    lines = ["| " + " | ".join(title for _key, title in columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        values = []
        for key, _title in columns:
            value = row[key]
            values.append("{:.6f}".format(value) if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def score_summary(name, scores):
    scores = np.asarray(scores, dtype=np.float64)
    if not len(scores):
        raise ValueError("Empty reported score population: " + name)
    result = {"population": name, "n_scored_sites": len(scores), "mean_score": float(scores.mean()),
              "median_score": float(np.median(scores)), "minimum_score": float(scores.min()),
              "maximum_score": float(scores.max())}
    for threshold in THRESHOLDS:
        suffix = str(threshold).replace(".", "p")
        count = int((scores >= threshold).sum())
        result["n_score_ge" + suffix] = count
        result["fraction_score_ge" + suffix] = count / len(scores)
    return result


def build(output):
    started, cpu = time.perf_counter(), time.process_time()
    paths = {"receipt": PREDICTIONS / (RUN + ".receipt.json"),
             "predictions": PREDICTIONS / (RUN + ".csv"),
             "metadata": PREDICTIONS / (RUN + ".site_metadata.csv.gz"),
             "input_qc": PREDICTIONS / (RUN + ".input_qc.json"),
             "core_manifest": PREDICTIONS / (RUN + ".model_export.csv.manifest.json"),
             "audit": PREFLIGHT / "first_full_input_audit.json",
             "depth_profile": PREFLIGHT / "first_depth_context_profile.json",
             "probe": PREFLIGHT / "first_real_probe_20261023/probe_verification.json",
             "inventory": REPO / "sgnex_analysis/metadata/sample_manifest.csv",
             "coverage": RECEIVED / "results/coverage_matrix_ge20_union.csv.gz",
             "aliases": RECEIVED / "metadata/transcript_aliases_checked.csv",
             "training_7mer": REPO / "sgnex_analysis/training_context_support/training_7mer_support.csv",
             "training_motif": REPO / "sgnex_analysis/training_context_support/training_motif_support.csv",
             "model": REPO / "model_elgin/artifacts/cap128_weight3_v1/model.pt",
             "model_metadata": REPO / "model_elgin/artifacts/cap128_weight3_v1/metadata.json"}
    receipt, qc, core = (load(paths[key]) for key in ("receipt", "input_qc", "core_manifest"))
    audit, profile, probe = (load(paths[key]) for key in ("audit", "depth_profile", "probe"))
    if (receipt.get("status") != "complete" or receipt.get("model_version") != VERSION
            or receipt.get("final_model_selected") is not True or receipt["identity"]["run_id"] != RUN
            or receipt["identity"]["model_sha256"] != MODEL or receipt["identity"]["min_reads"] != 20
            or receipt.get("no_training_or_calibration") is not True):
        raise ValueError("Expected the complete selected-model first run")
    for name, expected in receipt["files_sha256"].items():
        if Path(name).name != name or sha(PREDICTIONS / name) != expected:
            raise ValueError("Changed prediction artifact: " + name)
    if sha(paths["model"]) != MODEL or load(paths["model_metadata"])["epochs"] != 18:
        raise ValueError("The selected final model changed")
    adapter = REPO / "sgnex_analysis/scripts/predict_elgin_run.py"
    if code_sha(adapter) != receipt["identity"]["adapter_sha256"]:
        raise ValueError("Adapter source differs from the completed inference")
    for name, expected in receipt["identity"]["core_source_sha256"].items():
        if code_sha(REPO / "model_elgin/context_reference_v1" / name) != expected:
            raise ValueError("Core prediction code changed: " + name)
    if (core["status"] != "complete" or core["model_sha256"] != MODEL or core["stage"] != "final_data0"
            or core["all_reads_used"] is not True or core["labels_read"] is not False
            or core["output_sha256"] != sha(paths["predictions"])
            or core["code_sha256"] != receipt["identity"]["core_source_sha256"]):
        raise ValueError("Core inference receipt differs")
    if any(item.get("status") != "complete" for item in (qc, audit, profile, probe)):
        raise ValueError("Completed source/profile/probe checks are required")
    if (audit["coverage_key_and_count_match"] is not True or audit["fitting_or_inference"] is not False
            or probe["model_sha256"] != MODEL or probe["adapter_sha256"] != receipt["identity"]["adapter_sha256"]
            or probe["maximum_absolute_score_difference"] > probe["absolute_tolerance"]):
        raise ValueError("Independent input/probe evidence differs")
    for field, key in (("inventory_sha256", "inventory"), ("coverage_sha256", "coverage"), ("aliases_sha256", "aliases")):
        if audit[field] != sha(paths[key]):
            raise ValueError("Member 4 evidence changed: " + key)
    with paths["inventory"].open(newline="", encoding="utf-8-sig") as handle:
        inventory = list(csv.DictReader(handle))
    if len(inventory) != 23 or len({row["run_id"] for row in inventory}) != 23:
        raise ValueError("Expected the agreed 23-run scope")
    sample = next(row for row in inventory if row["run_id"] == RUN)
    source = REPO / "sgnex_analysis/outputs/signals" / sample["signal_local_path"]
    paths["source"] = source
    if (source.stat().st_size != int(sample["signal_size_bytes"])
            or sha(source) != receipt["identity"]["input_sha256"]
            or audit["source_sha256"] != receipt["identity"]["input_sha256"]
            or qc["original_input_sha256"] != receipt["identity"]["input_sha256"]):
        raise ValueError("Original public signal content differs")
    fingerprints = {name: {"path": str(path.relative_to(REPO)).replace("\\", "/"), "sha256": sha(path)}
                    for name, path in paths.items()}
    predictions = {}
    with paths["predictions"].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["transcript_id", "transcript_position", "score"]:
            raise ValueError("Three-column prediction contract changed")
        for row in reader:
            key, score = (row["transcript_id"], int(row["transcript_position"])), float(row["score"])
            if None in row or any(value is None for value in row.values()) or key in predictions or not np.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Malformed/duplicate prediction key or invalid score")
            predictions[key] = score
    sevenmers = pd.read_csv(paths["training_7mer"])
    motifs = pd.read_csv(paths["training_motif"])
    if (len(sevenmers) != 288 or len(motifs) != 18 or sevenmers.sequence_7mer.duplicated().any()
            or motifs.motif_5mer.duplicated().any() or int(sevenmers.training_sites.sum()) != 121838
            or int(sevenmers.positive_labels.sum()) != 5475):
        raise ValueError("Training-context evidence differs")
    support7 = sevenmers.set_index("sequence_7mer").to_dict("index")
    support5 = motifs.set_index("motif_5mer").to_dict("index")
    observed, seen, eligible_records = {}, set(), []
    counts = Counter(input_sites=0, input_reads=0, finite_reads=0, eligible_sites=0,
                     eligible_reads=0, below_minimum_source_reads=0, reads_discarded_nonfinite=0)
    depth_counts = Counter({depth: 0 for depth in (1, 5, 10, 20, 50, 100)})
    minimum, maximum = None, 0
    with gzip.open(paths["metadata"], "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["transcript_id", "transcript_position", "sequence_7mer", "motif_5mer", "n_reads_input", "n_reads_finite", "prediction_status"]:
            raise ValueError("Source QC metadata contract changed")
        for row in reader:
            key = row["transcript_id"], int(row["transcript_position"])
            n, finite = int(row["n_reads_input"]), int(row["n_reads_finite"])
            if key in seen or n < 1 or n != finite:
                raise ValueError("Duplicate/malformed source key or dropped nonfinite reads")
            seen.add(key)
            canonical = row["sequence_7mer"].upper().replace("U", "T")
            motif = row["motif_5mer"].upper().replace("U", "T")
            if len(canonical) != 7 or canonical[1:6] != motif or any(base not in "ACGT" for base in canonical):
                raise ValueError("Unexpected context or motif")
            eligible = n >= 20
            if row["prediction_status"] != ("eligible" if eligible else "below_minimum_source_reads"):
                raise ValueError("Source eligibility reason differs from read count")
            counts.update(input_sites=1, input_reads=n, finite_reads=finite,
                          eligible_sites=int(eligible), eligible_reads=n if eligible else 0,
                          below_minimum_source_reads=int(not eligible))
            for depth in depth_counts:
                depth_counts[depth] += int(n >= depth)
            minimum, maximum = n if minimum is None else min(minimum, n), max(maximum, n)
            if eligible:
                if key not in predictions or canonical not in support7 or motif not in support5:
                    raise ValueError("Eligible score missing or unseen training context")
                observed[key] = n
                positive = int(support7[canonical]["positive_labels"])
                support_group = "0 positive training labels" if positive == 0 else ("1-19 positive training labels" if positive < 20 else ">=20 positive training labels")
                eligible_records.append({"sequence_7mer": canonical, "motif_5mer": motif,
                    "n_reads": n, "score": predictions[key], "support_group": support_group})
            elif key in predictions:
                raise ValueError("Below-minimum site was incorrectly scored")
    del seen
    if predictions.keys() != observed.keys() or len(predictions) != receipt["counts"]["scored_sites"]:
        raise ValueError("Prediction and eligible source keys differ")
    if dict(counts) != qc["counts"] or any(receipt["counts"][key] != value for key, value in counts.items()):
        raise ValueError("Full-source QC counts differ")
    if counts["input_sites"] != int(sample["n_candidate_site_rows"]) or any(depth_counts[d] != int(sample["n_sites_ge" + str(d)]) for d in depth_counts):
        raise ValueError("Member 4 source coverage denominators differ")
    if (depth_counts != Counter({int(key): value for key, value in audit["sites_at_least_reads"].items()})
            or counts["input_reads"] != audit["n_reads"] or profile["metadata_sha256"] != sha(paths["metadata"])
            or maximum != profile["maximum_source_reads"] or minimum != profile["minimum_source_reads"]):
        raise ValueError("Independent depth/source profile differs")
    aliases = {}
    with paths["aliases"].open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["run_id"] == RUN:
                if row["raw_transcript_id"] in aliases:
                    raise ValueError("Ambiguous run-specific alias")
                aliases[row["raw_transcript_id"]] = row["transcript_id"]
    expected = {}
    with gzip.open(paths["coverage"], "rt", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            n = int(row[RUN])
            if n >= 20:
                key = row["transcript_id"], int(row["transcript_position"])
                if key in expected:
                    raise ValueError("Duplicate Member 4 coverage key")
                expected[key] = n
    mapped = {(aliases.get(key[0], key[0]), key[1]): n for key, n in observed.items()}
    if len(mapped) != len(observed) or mapped != expected:
        raise ValueError("Member 4 and genuine-source eligible keys/read counts differ")
    data = pd.DataFrame(eligible_records)
    distinct7 = data.sequence_7mer.nunique()
    if distinct7 != profile["distinct_model_encoded_eligible_7mers"] or distinct7 != 288:
        raise ValueError("Actual observed seven-mer count differs")
    if data.groupby("motif_5mer").size().to_dict() != audit["eligible_central5_counts"]:
        raise ValueError("Eligible motif counts differ from independent source audit")
    above = int((data.n_reads > int(sevenmers.training_reads_max.max())).sum())
    if above != profile["eligible_sites_above_training_max991"]:
        raise ValueError("Training-range boundary flag differs")
    coverage_rows = []
    for name, low, high in (("20-49 reads", 20, 49), ("50-99 reads", 50, 99),
                            ("100-199 reads", 100, 199), (">=200 reads", 200, np.inf)):
        selected = data[data.n_reads.between(low, high)]
        coverage_rows.append(score_summary(name, selected.score))
    sensitivity_rows = [score_summary(">=" + str(depth) + " reads", data.loc[data.n_reads >= depth, "score"])
                        for depth in (20, 50, 100)]
    motif_rows = []
    for motif, group in data.groupby("motif_5mer", sort=True):
        item = score_summary(motif, group.score)
        item.update(data0_training_sites=int(support5[motif]["training_sites"]),
                    data0_positive_labels=int(support5[motif]["positive_labels"]))
        motif_rows.append(item)
    support_rows = [score_summary(name, group.score) for name, group in data.groupby("support_group", sort=True)]
    summary = {"status": "complete", "scope": "First of 23 runs only: source/input-support and predicted-score QC",
        "run_id": RUN, "cell_line": sample["cell_line"], "replicate_group": sample["replicate_group"],
        "model_version": VERSION, "model_sha256": MODEL, "model_epochs": 18,
        "input_counts": dict(counts), "source_depth_thresholds": dict(depth_counts),
        "source_depth_minimum": minimum, "source_depth_maximum": maximum,
        "training_depth_minimum": int(sevenmers.training_reads_min.min()),
        "training_depth_maximum": int(sevenmers.training_reads_max.max()),
        "eligible_above_training_maximum_retained": above, "actual_observed_eligible_7mers": int(distinct7),
        "actual_observed_eligible_central_motifs": int(data.motif_5mer.nunique()),
        "unseen_model_encoded_7mers": 0, "unseen_central_motifs": 0,
        "member4_complete_key_and_count_match": True, "run_specific_aliases_applied_for_comparison_only": len(aliases),
        "coverage_bins": coverage_rows, "depth_sensitivity": sensitivity_rows, "motifs": motif_rows,
        "sevenmer_training_positive_support": support_rows,
        "working_score_cutoffs_not_calibrated_biological_calls": list(THRESHOLDS),
        "core_inference_resources": receipt["core_inference_resources"],
        "adapter_resources": receipt["adapter_resources"], "inference_resource_scope": receipt["resource_scope"],
        "source_input_audit_resources": audit["resources"], "probe_software_check": probe,
        "source_sha256": fingerprints, "reporter_sha256": sha(__file__),
        "limitations": ["One sequencing run, not a cell-line or replicate comparison.",
            "No compatible independent assay labels supplied: no SG-NEx accuracy/ROC/PR claim.",
            "Scores/cutoff fractions are not chemical prevalence, modified-read fractions or other RNA marks.",
            "Raw-source schema/count agreement does not prove historical preprocessing/reference/event-coordinate identity.",
            "Sparse training labels are evidence limits, not a calibrated per-site uncertainty estimate.",
            "Depth/context comparisons are descriptive and confounded; no causal or significance claim."]}
    for filename, rows in (("coverage_bins.csv", coverage_rows), ("depth_sensitivity.csv", sensitivity_rows),
                           ("motif_summary.csv", motif_rows), ("training_support_summary.csv", support_rows)):
        pd.DataFrame(rows).to_csv(output / filename, index=False, lineterminator="\n")
    os.environ.setdefault("MPLCONFIGDIR", str(REPO / "sgnex_analysis/outputs/report_mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    population = [("All source candidates", counts["input_sites"]), (">=20 reads: scored", depth_counts[20]),
                  (">=50 reads", depth_counts[50]), (">=100 reads", depth_counts[100])]
    fig, ax = plt.subplots(figsize=(8.2, 3.2), constrained_layout=True)
    ax.barh(range(4), [n for _name, n in population], color=["#8c9aa5", "#176b7a", "#388e8e", "#72b3a5"])
    ax.set(yticks=range(4), yticklabels=[name for name, _n in population], xscale="log",
           xlabel="Candidate sites (log scale)", title="First HCT116 run: coverage defines the scored population")
    ax.invert_yaxis()
    ax.set_xlim(10000, counts["input_sites"] * 2)
    for index, (_name, n) in enumerate(population):
        ax.text(n * 1.035, index, "{:,}".format(n), va="center", fontsize=9)
    ax.grid(axis="x", alpha=.18)
    for extension in ("png", "svg"):
        fig.savefig(output / ("coverage_population." + extension), dpi=220)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.1, 4), constrained_layout=True)
    grid = np.linspace(0, 1, 101)
    for item, color in zip(coverage_rows, ("#176b7a", "#bf6a38", "#6976a5", "#49936b")):
        name = item["population"]
        low, high = {"20-49 reads": (20, 49), "50-99 reads": (50, 99),
                     "100-199 reads": (100, 199), ">=200 reads": (200, np.inf)}[name]
        sorted_scores = np.sort(data.loc[data.n_reads.between(low, high), "score"].to_numpy())
        cdf = np.searchsorted(sorted_scores, grid, side="right") / len(sorted_scores)
        ax.plot(grid, cdf, lw=1.6, color=color, label="{} (n={:,})".format(name, len(sorted_scores)))
    ax.axvline(.5, color="grey", lw=1, ls=":", label="Working score cutoff 0.5")
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Model score", ylabel="Fraction of group with score <= x",
           title="First HCT116 run: cumulative scores by read depth")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=.18)
    for extension in ("png", "svg"):
        fig.savefig(output / ("score_depth_cdf." + extension), dpi=220)
    plt.close(fig)
    fraction = counts["eligible_sites"] / counts["input_sites"]
    sparse5 = int(data.motif_5mer.isin(motifs.loc[motifs.positive_labels.lt(20), "motif_5mer"]).sum())
    contents = """# First genuine SG-NEx prediction: coverage and score QC

**Task 2: one complete run out of the agreed 23.** The frozen selected neural
model has generated real scores for `{run}`. This is a sequencing-run QC and
predicted-score report, not a completed seven-cell-line analysis or a new
accuracy evaluation. No model fitting, calibration or threshold tuning occurs.

## What actually completed

All **{source_sites:,} source sites and {source_reads:,} reads** were checked by
the strict input workflow. Member 4's >=20-read rule retained **{eligible:,}
sites ({fraction:.3%})**, comprising **{eligible_reads:,} reads**. All those reads
were used by the unchanged predictor. **{below:,} below-20-read sites remain
unscored**, with an explicit QC reason; they are not labelled unmodified or
silently turned into zero scores. No nonfinite read was removed or imputed.

The model is `elgin-cap128-weight3-18epoch-b2d38ff29a91`, fitted only on data0;
SHA256 `{model}`. The original three-column export is preserved locally with
full-precision scores, original transcript IDs/positions and no coordinate
shift. Exact source, source-metadata, model, adapter, predictor and output
hashes were checked again for this report.

## How Member 4's findings affect this result

Her run inventory fixes the dataset identity and source population. Every one
of the **{eligible:,} scored keys and its read count** matches her received
coverage matrix exactly. The >=20-read population, the {ge50:,} sites with
>=50 reads and {ge100:,} sites with >=100 reads for sensitivity analysis, and the retention of missing/low-depth
observations as unscored all come directly from the agreed analysis design.
These checks make Member 4's work part of actual model-application eligibility
and verification.

![Coverage populations for this run](coverage_population.png)

These populations are nested. Their sizes describe observed processed
candidate sites, not modified-site counts. Cross-run comparisons still need
eligible matching sites and equal replicate-group weighting after all runs
are available. A single run cannot establish a cell-line effect.

## Actual continuous scores and fixed-cutoff sensitivity

{depth_table}

The fractions above mean **fraction of scored sites whose model score meets or exceeds
the stated cutoff**. They are not assay-validated m6A prevalence or measured
modified-molecule fractions. Cutoffs 0.5/0.7/0.9 are fixed reporting/sensitivity
rules; none was selected from these distributions. The >=50/100 rows change
the analysed population, so differences cannot be assigned to coverage alone.

![Cumulative model scores by coverage group](score_depth_cdf.png)

The CDF is evaluated at 101 fixed score-grid points; its groups are disjoint
20-49, 50-99, 100-199 and >=200 reads. It shows score behaviour rather than
classification accuracy. Motif composition, abundance, technical processing
and other differences can confound this descriptive coverage comparison.

## Context support and unusual valid inputs

The actual eligible metadata enumerates **{contexts} seven-mers and 18 central
motifs**, with U encoded as T. All occur in data0, so there are no unseen
canonical contexts in this run. This actual enumeration is distinct from the
earlier audit-only training-support deduction, whose distinct-count field was
left null.

Seen context does not guarantee strong positive-label evidence. **{sparse5:,}
eligible sites** use AAACC/TAACA/TAACC, whose data0 central-motif positive-label
support is 11/1/2 respectively. The companion `motif_summary.csv` and
`training_support_summary.csv` preserve the full aggregate counts and scores;
sparse support is an evidence limit, not a calibrated uncertainty score or a
reason to remove valid sites. The model shares parameters across contexts.

{support_table}

Training depths span 20-991 reads. This run spans {minimum}-{maximum}; exactly
**{above} eligible site exceeds the training maximum**. It was retained and
flagged for interpretation, not deleted or used to retrain the frozen model.
All low-depth input records and their QC reasons remain in local metadata.

## Computation and verification

The full adapter measured **{adapter_wall:.3f}s wall** and
**{adapter_cpu:.3f}s parent-process CPU excluding the predictor child**. It
includes complete source QC, eligible-input construction, child inference and
export audit. Core inference measured **{core_wall:.3f}s wall,
{core_cpu:.3f}s process CPU and {core_rss:.2f}MiB sampled peak process-tree RSS**.
Its wall overlaps the adapter wall: **do not add them**. The separate earlier
full-input audit measured {audit_wall:.3f}s wall; the small 1,024-source-site probe
passed numeric parity with maximum difference {probe_difference:.3g}. The probe
is a software check, not an accuracy test. Resource scopes and all source
fingerprints are retained in `summary.json`.

No model inference was repeated by this reporter. It verified all adapter
receipt files, selected model/core identity, original input hash, full CSV
contents, complete QC metadata, training-support joins and Member 4's exact
eligible key/count population. No compatible independent SG-NEx assay labels
were supplied, so accuracy, ROC/PR, calibration, biological modification
fractions, other RNA marks or differential cell-line conclusions are not
claimed. Exact reference/event offsets remain unverified; literal coordinates
are preserved and no genomic/UTR mapping is performed.

## Reproduce from the repository root

The actual interpreter on this laptop is
`../advanced_model/.venv/Scripts/python.exe`; use `python` in the pinned model
environment on another machine. The first-run commands were:

```text
python -B sgnex_analysis/scripts/download_signal_inputs.py --dest sgnex_analysis/outputs/signals --run-id {run}
python -B sgnex_analysis/scripts/audit_elgin_input.py --input sgnex_analysis/outputs/signals/{run}/data.json --run-id {run} --output sgnex_analysis/outputs/preflight/first_full_input_audit.json
python -B -u sgnex_analysis/scripts/predict_elgin_run.py --input sgnex_analysis/outputs/signals/{run}/data.json --run-id {run} --output sgnex_analysis/outputs/predictions/{run}.csv --min-reads 20 --threads 4
python -B sgnex_analysis/scripts/report_first_prediction.py
```

The report command requires the completed local evidence and refuses an
existing nonempty output directory. Use `--output-dir` with a fresh path for a
later check. The first download/input-audit/prediction commands describe real
prior work and should not overwrite retained outputs. Per-site CSVs, all-site
QC metadata, eligible original JSON, raw signal and logs remain under ignored
`sgnex_analysis/outputs/`; the public report contains aggregates only.

**Still pending:** completion of the remaining agreed runs, replicate-aware
common-site analyses and coverage/context sensitivity, supported biological
interpretation, genuine-score Explorer integration and final scientific report.
""".format(run=RUN, model=MODEL, source_sites=counts["input_sites"], source_reads=counts["input_reads"],
        eligible=counts["eligible_sites"], fraction=fraction, eligible_reads=counts["eligible_reads"],
        below=counts["below_minimum_source_reads"], ge50=depth_counts[50], ge100=depth_counts[100],
        depth_table=table(sensitivity_rows, [("population", "Population"), ("n_scored_sites", "Sites"),
            ("median_score", "Median score"), ("fraction_score_ge0p5", "Fraction score >=0.5"),
            ("fraction_score_ge0p7", "Fraction score >=0.7"), ("fraction_score_ge0p9", "Fraction score >=0.9")]),
        contexts=distinct7, sparse5=sparse5, support_table=table(support_rows, [("population", "Seven-mer support in data0"),
            ("n_scored_sites", "Eligible sites"), ("median_score", "Median score"),
            ("fraction_score_ge0p5", "Fraction score >=0.5")]),
        minimum=minimum, maximum=maximum, above=above,
        adapter_wall=receipt["adapter_resources"]["wall_seconds"],
        adapter_cpu=receipt["adapter_resources"]["process_cpu_seconds_excluding_child"],
        core_wall=receipt["core_inference_resources"]["wall_seconds"],
        core_cpu=receipt["core_inference_resources"]["cpu_seconds"],
        core_rss=receipt["core_inference_resources"]["sampled_peak_process_tree_rss_mib"],
        audit_wall=audit["resources"]["wall_seconds"],
        probe_difference=probe["maximum_absolute_score_difference"])
    (output / "README.md").write_text(contents, encoding="utf-8")
    for name, evidence in fingerprints.items():
        if sha(paths[name]) != evidence["sha256"]:
            raise ValueError("Input evidence changed during report generation: " + name)
    summary["report_generation_resources"] = {"wall_seconds": time.perf_counter()-started,
        "process_cpu_seconds": time.process_time()-cpu, "scope": "Receipt/source hashes, stored CSV/QC metadata, joins and figure/report generation; no inference"}
    save(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "sgnex_analysis/first_prediction_qc")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve previous reports; use a fresh output directory")
    output.mkdir(parents=True, exist_ok=True)
    save(output / "status.json", {"status": "running"})
    try:
        summary = build(output)
        receipt = {"status": "complete", "reporter_sha256": sha(__file__), "files_sha256": {
            str(path.relative_to(output)): sha(path) for path in sorted(output.iterdir()) if path.name != "status.json"}}
        save(output / "status.json", receipt)
        save(output / "complete.json", receipt)
    except BaseException as error:
        save(output / "status.json", {"status": "failed_partial_outputs_preserved", "error": type(error).__name__ + ": " + str(error)})
        raise
    print(json.dumps({"status": "complete", "run_id": RUN,
        "eligible_sites": summary["input_counts"]["eligible_sites"], "actual_contexts": summary["actual_observed_eligible_7mers"],
        "member4_key_and_count_match": summary["member4_complete_key_and_count_match"]}, indent=2))


if __name__ == "__main__":
    main()
