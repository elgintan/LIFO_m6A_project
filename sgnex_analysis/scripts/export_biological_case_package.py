"""Copy compact verified case evidence and prepare a future explorer payload."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from select_biological_cases import ROOT, KEY, DEPTHS, LINES, PLAN, sha, write_json


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if pd.isna(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


def run(selection, evidence, report, audit_dir, out):
    out.mkdir(parents=True, exist_ok=True)
    if not all((out / name).exists() for name in ["README.md", "LITERATURE.md", "REPORT_PARAGRAPH.md", "EXPLORER_INTEGRATION.md"]):
        raise ValueError("Reviewed narrative documents must exist before packaging")
    for directory in [selection, evidence, report]:
        receipt = json.loads((directory / "complete.json").read_text(encoding="utf-8"))
        if receipt["status"] != "complete":
            raise ValueError("Incomplete source")
        for name, pin in receipt["outputs"].items():
            path = directory / name
            if sha(path) != pin["sha256"] or path.stat().st_size != pin["size_bytes"]:
                raise ValueError(f"Completed output changed: {path.name}")
    audit = json.loads((audit_dir / "audit_result.json").read_text(encoding="utf-8"))
    if audit["status"] != "PASS" or audit["selection_complete_sha256"] != sha(selection / "complete.json"):
        raise ValueError("Independent audit does not bind this selection")
    if audit["production_selection_imported"] or audit["fitting_or_inference"]:
        raise ValueError("Unexpected independent-audit scope")
    for directory, names in [(selection, ["selected_cases.csv", "summary.json", "pair_population_counts.csv", "persistent_difference_ranked.csv.gz", "inconclusive_ranked.csv.gz", "shared_high_ranked.csv.gz"]),
                              (evidence, ["case_run_evidence.csv", "case_group_scores.csv", "case_line_scores.csv", "case_comparison_checks.csv"]),
                              (report, ["case_summary.csv", "training_key_diagnostics.csv", "training_key_scope.json", "case_group_score_patterns.png", "case_group_score_patterns.svg", "case_depth_sensitivity.png", "case_depth_sensitivity.svg"])]:
        for name in names:
            shutil.copyfile(directory / name, out / name)
    for directory, name in [(selection, "selection_receipt.json"), (evidence, "evidence_receipt.json"), (report, "report_receipt.json")]:
        shutil.copyfile(directory / "complete.json", out / name)
    shutil.copyfile(audit_dir / "audit_result.json", out / "independent_selection_audit.json")
    shutil.copyfile(audit_dir / "audit_cases.py", out / "independent_audit_cases.py")
    cases = pd.read_csv(evidence / "selected_cases.csv", float_precision="round_trip")
    run_scores = pd.read_csv(evidence / "case_run_evidence.csv", float_precision="round_trip")
    groups = pd.read_csv(evidence / "case_group_scores.csv", float_precision="round_trip")
    lines = pd.read_csv(evidence / "case_line_scores.csv", float_precision="round_trip")
    checks = pd.read_csv(evidence / "case_comparison_checks.csv", float_precision="round_trip")
    training = pd.read_csv(report / "training_key_diagnostics.csv", float_precision="round_trip")
    cutoffs, payload = [], []
    for case in cases.to_dict("records"):
        case_id = case["case_id"]
        d = lines[lines.case_id.eq(case_id)]
        for depth in DEPTHS:
            for line in LINES:
                found = d[d.coverage_threshold.eq(depth) & d.cell_line.eq(line)]
                score = float(found.score.iloc[0]) if len(found) else None
                n_groups = int(found.n_replicates.iloc[0]) if len(found) else 0
                for cutoff in [.5, .7, .9]:
                    cutoffs.append({"case_id": case_id, "coverage_threshold": depth, "cell_line": line,
                                    "n_eligible_groups": n_groups, "score": score, "cutoff": cutoff,
                                    "qualified_at_least_two_groups": n_groups >= 2,
                                    "at_or_above_cutoff": score >= cutoff if n_groups >= 2 else None})
        payload.append(clean({"case": case, "training_key": training[training.case_id.eq(case_id)].to_dict("records")[0],
                              "line_scores": d.to_dict("records"), "groups": groups[groups.case_id.eq(case_id)].to_dict("records"),
                              "original_runs": run_scores[run_scores.case_id.eq(case_id)].to_dict("records"),
                              "comparison_checks": checks[checks.case_id.eq(case_id)].to_dict("records")}))
    pd.DataFrame(cutoffs).to_csv(out / "case_cutoff_sensitivity.csv", index=False)
    tech = []
    for (case, line), frame in run_scores.groupby(["case_id", "cell_line"]):
        tech.append({"case_id": case, "cell_line": line, "n_runs": len(frame),
                     "basecallers": " | ".join(sorted(frame["basecaller_version(ENA)*"].astype(str).unique())),
                     "platforms": " | ".join(sorted(frame.Platform.astype(str).unique())),
                     "dates": " | ".join(sorted(frame.generation_date.astype(str).unique())),
                     "min_reads": int(frame.n_reads.min()), "max_reads": int(frame.n_reads.max())})
    pd.DataFrame(tech).to_csv(out / "case_technical_metadata_summary.csv", index=False)
    write_json(out / "explorer_cases.json", {"schema_version": 1, "selection_receipt_sha256": sha(selection / "complete.json"),
        "model_sha256": "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668",
        "warnings": ["Illustrative tail-selected cases; not independent discoveries", "Predicted site scores are not molecule fractions",
                     "Literal transcript coordinates retained; reference/offset and orthogonal-site identity unverified",
                     "Metadata groups may not be independent laboratory preparations; technical effects confounded",
                     "Training-key labels are not SG-NEx validation"], "cases": payload})
    commands = []
    for role, folder in [("selection first attempt: failed annotation-pin guard", "biological_case_selection_20261023"),
                         ("completed selection retry", "biological_case_selection_retry_20261023"),
                         ("original23run evidence reconstruction", "biological_case_evidence_20261023"),
                         ("figure/report first layout", "biological_case_figures_20261023"),
                         ("figure/report layout repair", "biological_case_figures_layout_20261023")]:
        path = ROOT / "sgnex_analysis/outputs/checks" / folder / "measurement.json"
        m = json.loads(path.read_text(encoding="utf-8"))
        commands.append({"role": role, "source": path.relative_to(ROOT).as_posix(), **{key: m[key] for key in
            ["status", "exit_code", "wall_seconds", "sampled_process_tree_cpu_seconds_lower_bound", "sampled_peak_tree_rss_mib", "cpu_scope", "rss_scope"]}})
    write_json(out / "resources.json", {"separate_command_scopes_do_not_sum_overlapping_timers": True,
               "commands": commands, "independent_audit": audit.get("resources", {}),
               "independent_audit_scope": audit.get("resource_scope")})
    records = [{"file": path.name, "sha256": sha(path), "size_bytes": path.stat().st_size}
               for path in sorted(out.iterdir()) if path.is_file() and path.name != "publication_manifest.json"]
    write_json(out / "publication_manifest.json", {"status": "complete", "files": records,
               "plan_sha256": sha(PLAN), "export_script_sha256": sha(Path(__file__)), "no_training_or_inference": True})
    print(f"Exported {len(records)} compact evidence files, four exact-key explorer cases and252cutoff rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/biological_case_selection_v2")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/biological_case_evidence_v1")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/biological_case_report_v2")
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "sgnex_analysis/outputs/checks/biological_case_independent_20261023")
    parser.add_argument("--out", type=Path, default=ROOT / "sgnex_analysis/biological_case_results_2026_10_23")
    cli = parser.parse_args()
    run(cli.selection_dir.resolve(), cli.evidence_dir.resolve(), cli.report_dir.resolve(), cli.audit_dir.resolve(), cli.out.resolve())
