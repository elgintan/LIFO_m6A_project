"""Copy the completed full-score explorer and add the verified biological cases.

Run from the repository root. This performs file validation/copying only, never
rebuilds scores, and refuses any nonempty destination. A successful result has
integration_complete.json, written only after every copy and hash check passes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import time

REPO = Path(__file__).resolve().parents[3]
MODEL_SHA256 = "b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668"
FRONTEND_FILES = ("app.html", "index.html", "case_logic.js", "case_view.js")
ANALYSIS_BASELINE = "fd76aa46254a4bee61bb22d557c4a585a57e6476"
ANALYSIS_SUPPORT_README = (
    "# Wider Task 2 analysis\n\n"
    "This local file supports the original casebook README's relative link. "
    "The wider Task 2 analysis lives online at the fixed public baseline below; "
    "its recursive files are not bundled in this explorer artifact.\n\n"
    "[Read the published Task 2 analysis at the fixed public baseline]("
    "https://github.com/elgintan/LIFO_m6A_project/blob/" + ANALYSIS_BASELINE
    + "/sgnex_analysis/task2_results_2026_10_23/README.md).\n\n"
    "The original casebook files and their scores are copied unchanged. "
    "This support file is navigation only and adds no scientific result.\n"
)
CASES = {
    "persistent_difference_nontraining_lines": ("ENST00000340913", 177),
    "persistent_difference_training_line": ("ENST00000311481", 1947),
    "shared_high": ("ENST00000331925", 607),
    "overlapping_groups_inconclusive": ("ENST00000359707", 2510),
}


@dataclass(frozen=True)
class SourceContract:
    """Production counts are fixed; tiny unit fixtures supply their own counts."""
    runs: int = 23
    lines: int = 7
    groups: int = 17
    kept_sites: int = 451352
    scored_observations: int = 2983948
    data_json_files: int = 132
    validation_passes: int = 190


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fingerprint(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Not a regular file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return {"sha256": h.hexdigest(), "size_bytes": path.stat().st_size}


def load_json(path: Path) -> dict:
    def invalid_constant(value: str):
        raise ValueError(f"Non-finite JSON constant {value} in {path}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid_constant)


def child(root: Path, name: str) -> Path:
    """Only portable relative public paths; reject traversal before reading."""
    relative = PurePosixPath(name)
    require(bool(name) and "\\" not in name and ":" not in name
            and not relative.is_absolute() and ".." not in relative.parts,
            f"Unsafe manifest path: {name}")
    result = root.joinpath(*relative.parts)
    require(result.resolve().is_relative_to(root.resolve()), f"Path escapes root: {name}")
    require(not any(p.is_symlink() for p in [result, *result.parents]
                    if p == root or p.is_relative_to(root)), f"Symbolic link: {name}")
    require(result.suffix.lower() != ".pem", "Private-key files cannot enter the artifact")
    return result


def inventory(root: Path) -> dict[str, dict]:
    require(root.is_dir() and not root.is_symlink(), f"Missing directory: {root}")
    found = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Symbolic link in source: {path}")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            found[name] = fingerprint(child(root, name))
    return found


def check_source(source: Path, contract: SourceContract) -> tuple[dict, dict, dict]:
    overview = load_json(source / "data/overview.json")
    build, totals, runs = overview["build"], overview["totals"], overview["runs"]
    require(build["mode"] == "scores" and build["score_status"] == "final",
            "Source must be the completed real-score explorer")
    require(build["n_runs_with_predictions"] == contract.runs == len(runs), "Wrong source run scope")
    require(len({r["id"] for r in runs}) == contract.runs, "Repeated source run ID")
    require(len(overview["lines"]) == contract.lines
            and len({r["line"] for r in runs}) == contract.lines, "Wrong source cell-line scope")
    require(len({r["group"] for r in runs}) == contract.groups, "Wrong source metadata-group scope")
    require(totals["kept_sites"] == contract.kept_sites
            == totals["union_sites"]["20"], "Source is not the complete scoreable population")
    require(sum(r["n_scored"] for r in runs) == contract.scored_observations,
            "Wrong source scored-observation total")
    require(build["keep_min_reads"] == 20, "Unexpected source read threshold")
    require(build["model_versions"] == ["elgin-cap128-weight3-18epoch-b2d38ff29a91"], "Wrong source model")
    qc = build["context_qc"]
    require(qc["n_keys"] == contract.kept_sites and qc["policy"]["primary"] == "all_source_consistent"
            and qc["policy"]["sensitivity"] == "scored_consistent", "Wrong context-QC scope/policy")
    receipts = {}
    parent = source.parent
    for name in ("validation.json", "qa/utf8_check.json", "qa/overview_report_audit.json", "qa/browser_qa.json"):
        receipts[name] = fingerprint(child(parent, name))
    validation = load_json(parent / "validation.json")
    require(validation["require_complete"] is True and validation["counts"]["FAIL"] == 0
            and validation["counts"]["WARN"] == 0
            and validation["counts"]["PASS"] >= contract.validation_passes, "Source validation did not pass")
    require({r["run_id"]: r["n_scored"] for r in validation["runs"]}
            == {r["id"]: r["n_scored"] for r in runs}, "Source validation run counts differ")
    require(validation["context_qc"]["receipt_sha256"] == qc["receipt_sha256"], "Context receipt mismatch")
    audit = load_json(parent / "qa/overview_report_audit.json")
    require(audit["numerical_status"] == "PASS" and audit["n_fraction_mismatches"] == 0,
            "Source aggregate numerical audit did not pass")
    overview_pins = [sha for name, sha in audit["inputs"].items()
                     if name.replace("\\", "/").endswith("/site/data/overview.json")]
    require(overview_pins == [fingerprint(source / "data/overview.json")["sha256"]], "Stale overview audit")
    browser = load_json(parent / "qa/browser_qa.json")
    require(browser["status"] == "desktop QA completed", "Source desktop QA receipt missing")
    require(browser["source_app_sha256"] == fingerprint(source / "app.html")["sha256"]
            and browser["packaged_index_sha256"] == fingerprint(source / "index.html")["sha256"],
            "Source frontend differs from its completed browser-QA receipt")
    utf8 = load_json(parent / "qa/utf8_check.json")
    require(utf8["status"] == "complete" and utf8["files_checked"] == contract.data_json_files,
            "Wrong completed source JSON scope")
    expected = {}
    for item in utf8["files"]:
        name = "data/" + item["path"]
        child(source, name)
        require(name not in expected, "Duplicate source UTF8 receipt path")
        expected[name] = {"sha256": item["after_sha256"], "size_bytes": item["size_bytes"]}
    current = inventory(source)
    require("integration_complete.json" not in current,
            "Source must be the original completed real-score site, not an already integrated copy")
    actual_data = {name: pin for name, pin in current.items() if name.startswith("data/")}
    require(len(expected) == contract.data_json_files and expected == actual_data,
            "Source data changed since the completed UTF8/JSON audit")
    require(all(name.endswith(".json") for name in actual_data), "Unexpected source data file")
    return overview, current, receipts


def finite_score(value) -> bool:
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1


def check_payload(package: Path, overview: dict) -> tuple[dict, dict, dict]:
    manifest = load_json(package / "publication_manifest.json")
    require(manifest["status"] == "complete", "Case publication is not complete")
    pins = {}
    for item in manifest["files"]:
        name = item["file"]
        require(name not in pins, "Duplicate case publication path")
        pin = {"sha256": item["sha256"], "size_bytes": item["size_bytes"]}
        require(fingerprint(child(package, name)) == pin, f"Case publication hash/size mismatch: {name}")
        pins[name] = pin
    for name in ("explorer_cases.json", "selection_receipt.json", "independent_selection_audit.json",
                 "persistent_difference_ranked.csv.gz", "shared_high_ranked.csv.gz", "inconclusive_ranked.csv.gz"):
        require(name in pins, f"Missing published case evidence: {name}")
    payload = load_json(package / "explorer_cases.json")
    require(payload["schema_version"] == 1 and payload["model_sha256"] == MODEL_SHA256, "Wrong case schema/model")
    require(payload["selection_receipt_sha256"] == pins["selection_receipt.json"]["sha256"], "Wrong case selection binding")
    selection = load_json(package / "selection_receipt.json")
    require(selection["status"] == "complete" and selection["no_training_or_inference"] is True,
            "Case selection receipt is not complete")
    independent = load_json(package / "independent_selection_audit.json")
    require(independent.get("status") == "PASS", "Independent case selection audit did not pass")
    plan = [p for p in selection["inputs"] if p["path"].replace("\\", "/").endswith("/BIOLOGICAL_CASE_SELECTION_PLAN.md")]
    require(len(plan) == 1, "Missing unique frozen selection-plan pin")
    runs = {r["id"]: r for r in overview["runs"]}
    seen = set()
    statuses = Counter()
    require(len(payload["cases"]) == len(CASES), "Expected exactly four case roles")
    for record in payload["cases"]:
        case = record["case"]
        case_id = case["case_id"]
        key = (case["transcript_id"], case["transcript_position"])
        require(case_id not in seen and CASES.get(case_id) == key, "Wrong, duplicate, or missing exact case key")
        seen.add(case_id)
        require(type(case["transcript_position"]) is int, "Case position must remain an integer")
        require(len(record["original_runs"]) == len(runs), "Case is missing an original run")
        seen_runs = set()
        for row in record["original_runs"]:
            run_id = row["run_id"]
            require(run_id in runs and run_id not in seen_runs, "Unexpected or duplicate case run ID")
            seen_runs.add(run_id)
            require(row["case_id"] == case_id and (row["transcript_id"], row["transcript_position"]) == key,
                    "Case run key mismatch")
            require(row["cell_line"] == runs[run_id]["line"], "Case run cell-line mismatch")
            reads = row["n_reads"]
            require(type(reads) is int and reads >= 0, "Invalid source read count")
            status = row["measurement_status"]
            if reads >= 20:
                require(status == "scored" and finite_score(row["score"]) and bool(row["raw_transcript_id"]),
                        "Eligible case run lacks a finite original score/identifier")
            else:
                expected = "absent_from_processed_run" if reads == 0 else "below_20_reads_unscored"
                require(status == expected and row["score"] is None and row["raw_transcript_id"] is None,
                        "Missing/low-read case measurement must remain unscored, not zero")
            statuses[status] += 1
        for row in record["line_scores"]:
            require(row["case_id"] == case_id and (row["transcript_id"], row["transcript_position"]) == key,
                    "Case line key mismatch")
            require(row["coverage_threshold"] in (20, 50, 100) and row["n_replicates"] >= 1
                    and finite_score(row["score"]), "Invalid diagnostic/qualified line score")
    return payload, pins, {"plan": plan[0], "run_measurement_status_counts": dict(statuses)}


def check_case_scores(source: Path, overview: dict, payload: dict) -> None:
    """Read only the four relevant gene buckets, not all score JSON again."""
    index = load_json(source / "data/genes_index.json")
    fields = index["fields"]
    entries = {row[fields.index("key")]: row[fields.index("bucket")] for row in index["rows"]}
    cache = {}
    run_order = [r["id"] for r in overview["runs"]]
    for record in payload["cases"]:
        case = record["case"]
        gene = case["gene_id"]
        require(gene in entries, "Case gene absent from the completed full explorer")
        bucket = int(entries[gene])
        if bucket not in cache:
            cache[bucket] = load_json(source / f"data/genes/b{bucket:03d}.json")
        data = cache[bucket][gene]
        sites = [site for tx in data["tx"] if tx["id"] == case["transcript_id"]
                 for site in tx["sites"] if site[0] == case["transcript_position"]]
        require(len(sites) == 1, "Exact case site missing or repeated in the completed full explorer")
        site = sites[0]
        reads, scores = site[1].split(","), site[2].split(",")
        require(len(reads) == len(scores) == len(run_order), "Wrong source case run-vector length")
        original = {row["run_id"]: row for row in record["original_runs"]}
        for run_id, n, score in zip(run_order, reads, scores):
            row = original[run_id]
            require((int(n) if n else 0) == row["n_reads"], "Case/source original read-count disagreement")
            require((float(score) if score else None) == row["score"], "Case/source original-score disagreement")
        require(site[3]["all_source_consistent"] is True
                and site[3]["encoded7mer_all_source"] == case["analysis_sequence_7mer"], "Case/source context disagreement")


def integrate(source_site: Path, frontend: Path, case_package: Path, out: Path,
              plan_path: Path, *, include_evidence: bool = True,
              contract: SourceContract = SourceContract(), require_tracked_frontend: bool = True) -> dict:
    started, cpu_started = time.perf_counter(), time.process_time()
    source_site, frontend, case_package, out, plan_path = [p.resolve() for p in
        (source_site, frontend, case_package, out, plan_path)]
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())),
            "Output already exists and is nonempty; choose a fresh output. Nothing was removed.")
    for source in (source_site, frontend, case_package):
        require(not out.is_relative_to(source) and not source.is_relative_to(out), "Output/source directories overlap")
    overview, source_pins, receipts = check_source(source_site, contract)
    payload, package_pins, case_checks = check_payload(case_package, overview)
    plan_pin = fingerprint(plan_path)
    require(plan_pin == {k: case_checks["plan"][k] for k in ("sha256", "size_bytes")}, "Frozen selection plan changed")
    check_case_scores(source_site, overview, payload)
    frontend_pins = {name: fingerprint(frontend / name) for name in FRONTEND_FILES}
    for name in FRONTEND_FILES:
        (frontend / name).read_text(encoding="utf-8")
        if require_tracked_frontend:
            relative = (frontend / name).relative_to(REPO).as_posix()
            result = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative],
                                    cwd=REPO, capture_output=True, text=True)
            require(result.returncode == 0, f"Frontend file is not tracked in Git: {relative}")
    app = (frontend / "app.html").read_text(encoding="utf-8")
    index = (frontend / "index.html").read_text(encoding="utf-8")
    split = app.index("</style>") + len("</style>")
    require(app[:split] in index and app[split:] in index, "Frontend index.html is stale; package the current app first")
    require("case_logic.js" in app and "case_view.js" in app and "biological_cases.json" in app,
            "Frontend does not load the biological case panel")
    manifest_pin = fingerprint(case_package / "publication_manifest.json")
    script_pin = fingerprint(Path(__file__))

    # From here failures leave a partial directory without a completion receipt.
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_site, out, dirs_exist_ok=True)
    for name in FRONTEND_FILES:
        shutil.copyfile(frontend / name, out / name)
    shutil.copyfile(case_package / "explorer_cases.json", out / "data/biological_cases.json")
    if include_evidence:
        evidence = out / "evidence/biological_cases"
        evidence.mkdir(parents=True)
        for name in package_pins:
            target = child(evidence, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(child(case_package, name), target)
        shutil.copyfile(case_package / "publication_manifest.json", evidence / "publication_manifest.json")
        shutil.copyfile(plan_path, evidence / "BIOLOGICAL_CASE_SELECTION_PLAN.md")
        # The frozen casebook README links to siblings in its original repo.
        # Add portable support paths without rewriting any published case file.
        shutil.copyfile(plan_path, out / "evidence/BIOLOGICAL_CASE_SELECTION_PLAN.md")
        analysis_support = out / "evidence/task2_results_2026_10_23/README.md"
        analysis_support.parent.mkdir()
        analysis_support.write_bytes(ANALYSIS_SUPPORT_README.encode("utf-8"))
    output_pins = inventory(out)
    for name, pin in source_pins.items():
        if name not in FRONTEND_FILES:
            require(output_pins.get(name) == pin, f"Original explorer file changed during copy: {name}")
    require(output_pins["data/biological_cases.json"] == package_pins["explorer_cases.json"], "Copied payload changed")
    for name, pin in frontend_pins.items():
        require(output_pins[name] == pin, "Copied frontend changed")
    if include_evidence:
        for name, pin in package_pins.items():
            require(output_pins["evidence/biological_cases/" + name] == pin, "Copied public evidence changed")
        require(output_pins["evidence/biological_cases/publication_manifest.json"] == manifest_pin, "Copied publication manifest changed")
        require(output_pins["evidence/biological_cases/BIOLOGICAL_CASE_SELECTION_PLAN.md"] == plan_pin, "Copied selection plan changed")
        require(output_pins["evidence/BIOLOGICAL_CASE_SELECTION_PLAN.md"] == plan_pin,
                "Copied compatibility selection plan changed")
        support_bytes = ANALYSIS_SUPPORT_README.encode("utf-8")
        require(output_pins["evidence/task2_results_2026_10_23/README.md"]
                == {"sha256": hashlib.sha256(support_bytes).hexdigest(), "size_bytes": len(support_bytes)},
                "Wider-analysis navigation support changed")
    require(inventory(source_site) == source_pins, "Source explorer changed during integration")
    require({name: fingerprint(frontend / name) for name in FRONTEND_FILES} == frontend_pins, "Frontend changed during integration")
    require(fingerprint(case_package / "publication_manifest.json") == manifest_pin
            and all(fingerprint(child(case_package, name)) == pin for name, pin in package_pins.items())
            and fingerprint(plan_path) == plan_pin, "Case evidence changed during integration")
    require(fingerprint(Path(__file__)) == script_pin, "Integration script changed during execution")
    require({name: fingerprint(child(source_site.parent, name)) for name in receipts} == receipts,
            "Source validation receipts changed during integration")
    receipt = {
        "status": "complete", "schema_version": 1,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Incremental byte copy of audited full-score site; tracked frontend overlay; exact published case payload",
        "script": script_pin,
        "inputs": {"source_site": str(source_site), "source_files": source_pins,
                   "source_validation_receipts": receipts, "frontend": frontend_pins,
                   "case_publication_manifest": manifest_pin, "case_files": package_pins,
                   "selection_plan": plan_pin},
        "counts": {"runs": len(overview["runs"]), "cell_lines": len(overview["lines"]),
                   "metadata_groups": contract.groups, "scoreable_site_keys": overview["totals"]["kept_sites"],
                   "scored_run_site_observations": sum(r["n_scored"] for r in overview["runs"]),
                   "source_data_json_files_preserved": contract.data_json_files, "cases": len(payload["cases"]),
                   "case_original_run_records": sum(len(c["original_runs"]) for c in payload["cases"]),
                   "case_run_measurement_status_counts": case_checks["run_measurement_status_counts"],
                   "output_files_excluding_this_receipt": len(output_pins)},
        "model_sha256": MODEL_SHA256, "all_original_score_json_bytes_unchanged": True,
        "case_payload_bytes_unchanged": True, "evidence_included": include_evidence,
        "wider_analysis_navigation_baseline": ANALYSIS_BASELINE if include_evidence else None,
        "no_training_inference_download_or_score_rebuild": True,
        "outputs": output_pins,
        "resources": {"wall_seconds": time.perf_counter() - started,
                      "process_cpu_seconds": time.process_time() - cpu_started,
                      "scope": "Function entry through validation, hashing, byte copying, and final hash checks; excludes imports and completion JSON write; child git CPU excluded",
                      "rss_measured": False, "peak_rss_bytes": None},
        "limits": ["Source prior browser QA applies to the old frontend; integrated frontend still needs fresh browser/responsive QA",
                   "All data stay local unless this fresh artifact is separately published",
                   "Illustrative selected cases and uncalibrated model scores are not independent biological validation"],
    }
    # Completion last: a partial/failed output must never look like a completed build.
    with (out / "integration_complete.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-site", type=Path, default=REPO / "data_visualisation/outputs/real_scores_v1/site")
    parser.add_argument("--frontend", type=Path, default=REPO / "data_visualisation/task2_viz/site")
    parser.add_argument("--case-package", type=Path, default=REPO / "sgnex_analysis/biological_case_results_2026_10_23")
    parser.add_argument("--selection-plan", type=Path, default=REPO / "sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md")
    parser.add_argument("--out", type=Path, default=REPO / "data_visualisation/outputs/biological_cases_v1/site")
    parser.add_argument("--without-evidence", action="store_true", help="Omit linked casebook files; normal publication should retain them")
    args = parser.parse_args()
    receipt = integrate(args.source_site, args.frontend, args.case_package, args.out,
                        args.selection_plan, include_evidence=not args.without_evidence)
    print(json.dumps({"status": receipt["status"], "counts": receipt["counts"],
                      "resources": receipt["resources"], "output": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
