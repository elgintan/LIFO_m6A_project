"""Check a Task 2 prediction hand-off before it goes into the visualisation.

Expected layout (team format; see docs/data_contract.md):
  <inputs>/manifest.csv     run_id,cell_line,biological_replicate,sequencing_run,prediction_file,
                            coverage_file,min_reads,reference_version,model_version
  <inputs>/MODEL_INFO.md
  <inputs>/<prediction_file> one CSV per run: transcript_id,transcript_position,score

Each prediction file is compared with the public SG-NEx read counts for its run
(raw IDs against raw IDs), so a file made from the wrong run, a truncated file
or a file with shifted positions is caught here rather than in a plot. Problems
are reported, never silently fixed.

Usage:
  python scripts/validate_task2_inputs.py --inputs task2_inputs --public public_data
Exit code 0 = no FAIL (WARN lines still need reading), 1 = at least one FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task2lib as lib  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, scope: str, check: str, detail: str = "") -> None:
        self.items.append({"level": level, "scope": scope, "check": check, "detail": detail})

    def counts(self) -> dict:
        return {lvl: sum(i["level"] == lvl for i in self.items) for lvl in ("PASS", "WARN", "FAIL")}


def model_info_placeholders(text: str) -> list[str]:
    """Find unfinished model markers, while allowing honest pending-status prose."""
    patterns = [
        r"\bPENDING_[A-Z0-9_]+\b",
        r"(?:\*\*|__|`|\[|<)\s*(?:PENDING|TBD|TODO)\s*(?:\*\*|__|`|\]|>)",
        r"(?im)^\s*(?:[-*]\s*)?(?:model(?:\s+(?:id|identifier|version|checkpoint|sha256))?|"
        r"identifier|artifact|sha256|selected\s+model[^:\n]{0,60})\s*[:=]\s*[`*_\s]*(?:PENDING|TBD|TODO)\b",
    ]
    return sorted({match.group(0).strip() for pattern in patterns
                   for match in re.finditer(pattern, text, re.IGNORECASE)})


def check_file(row: pd.Series, inputs: Path, public: Path, rep: Report, require_complete: bool = False) -> dict | None:
    run_id = row.run_id
    incomplete = "FAIL" if require_complete else "WARN"
    rel = str(row.prediction_file).strip()
    try:
        path = lib.prediction_path(inputs, rel)
    except ValueError as exc:
        rep.add("FAIL", run_id, "prediction_file is a relative CSV path", str(exc))
        return None
    if not rel or not path.exists():
        rep.add("FAIL", run_id, "prediction_file exists", f"not found: {rel or '(blank)'}")
        return None
    if run_id not in path.name:
        rep.add("WARN", run_id, "prediction file name contains the run_id", path.name)
    pred = lib.read_predictions(path)
    if list(pred.columns) != lib.PRED_COLUMNS:
        rep.add("FAIL", run_id, "header is transcript_id,transcript_position,score", f"got {list(pred.columns)}")
        return None
    rep.add("PASS", run_id, "header", path.name)

    dups = int(pred.duplicated(["transcript_id", "transcript_position"]).sum())
    rep.add("FAIL" if dups else "PASS", run_id, "each site appears once", f"{dups:,} duplicate sites" if dups else "")
    empty = int((pred == "").any(axis=1).sum())
    pos = pd.to_numeric(pred.transcript_position, errors="coerce")
    score = pd.to_numeric(pred.score, errors="coerce")
    bad_pos = int((pos.isna() | ~np.isfinite(pos) | (pos < 0) | (pos >= 2**63) | (pos != np.floor(pos))).sum())
    bad_score = int((score.isna() | ~np.isfinite(score) | (score < 0) | (score > 1)).sum())
    for name, n in (("no empty cells", empty), ("positions are whole numbers >= 0", bad_pos),
                    ("scores are numbers between 0 and 1", bad_score)):
        rep.add("FAIL" if n else "PASS", run_id, name, f"{n:,} bad rows" if n else "")
    if empty or bad_pos or bad_score:
        return None
    pred = pd.DataFrame({"transcript_id": pred.transcript_id, "transcript_position": pos.astype("int64"), "score": score})
    normalised_dups = int(pred.duplicated(["transcript_id", "transcript_position"]).sum())
    if normalised_dups > dups:
        rep.add("FAIL", run_id, "numeric site keys are unique",
                f"{normalised_dups:,} duplicate sites after normalising positions")
    if dups or normalised_dups:
        return None

    if "n_sites_scored" in row.index and str(row.n_sites_scored).strip():
        declared = int(float(row.n_sites_scored))
        rep.add("FAIL" if declared != len(pred) else "PASS", run_id, "row count matches manifest n_sites_scored",
                f"manifest {declared:,}, file {len(pred):,}")

    rc_path = public / "readcount" / f"{run_id}.readcount.csv"
    if not rc_path.exists():
        rep.add(incomplete, run_id, "public read counts available", "not downloaded; site checks skipped")
        return {"run_id": run_id, "n_scored": len(pred)}
    rc = pd.read_csv(rc_path, dtype={"transcript_id": "string", "transcript_position": "int64", "n_reads": "int64"})
    merged = pred.merge(rc, on=["transcript_id", "transcript_position"], how="left")
    unknown = merged[merged.n_reads.isna()]
    if len(unknown):
        ex = ", ".join(f"{t}:{p}" for t, p in unknown[["transcript_id", "transcript_position"]].head(3).itertuples(index=False))
        rep.add("FAIL", run_id, "every scored site exists in this run's SG-NEx data",
                f"{len(unknown):,} sites not found (e.g. {ex}); wrong run, changed IDs or shifted positions?")
    else:
        rep.add("PASS", run_id, "every scored site exists in this run's SG-NEx data")

    mr_txt = str(row.min_reads).strip()
    if mr_txt:
        mr_number = pd.to_numeric(mr_txt, errors="coerce")
        if not np.isfinite(mr_number) or mr_number < 1 or mr_number != np.floor(mr_number):
            rep.add("FAIL", run_id, "min_reads is a positive whole number", mr_txt)
            return None
        mr = int(mr_number)
        below = int((merged.n_reads < mr).sum())
        rep.add(incomplete if below else "PASS", run_id, f"scored sites have >= {mr} reads (manifest min_reads)",
                f"{below:,} scored sites below it" if below else "")
        eligible = int((rc.n_reads >= mr).sum())
        missing = eligible - int((merged.n_reads >= mr).sum())
        rep.add(incomplete if missing else "PASS", run_id, f"every site with >= {mr} reads has a score",
                f"{missing:,} of {eligible:,} eligible sites have no score (shown as 'missing prediction')"
                if missing else f"{eligible:,} eligible sites")
    else:
        rep.add(incomplete, run_id, "manifest states min_reads",
                "blank, so 'too few reads' and 'missing prediction' cannot be told apart")
    return {"run_id": run_id, "n_scored": len(pred), "score_mean": float(pred.score.mean())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--public", type=Path, default=Path("public_data"))
    ap.add_argument("--report", type=Path, default=Path("reports/input_validation.json"))
    ap.add_argument("--require-complete", action="store_true",
                    help="Final hand-off: missing runs/sites/readcounts or incomplete provenance are FAIL")
    ap.add_argument("--aliases", type=Path,
                    help="Authoritative explicit per-run aliases; identifiers are never inferred")
    ap.add_argument("--context-qc", type=Path,
                    help="Completed cross-run audit directory; required for final comparisons")
    args = ap.parse_args(argv)
    rep = Report()
    incomplete = "FAIL" if args.require_complete else "WARN"

    man_path = args.inputs / "manifest.csv"
    if not man_path.exists():
        print(f"FAIL: {man_path} not found")
        return 1
    man = lib.read_manifest(man_path)
    missing_cols = [c for c in lib.MANIFEST_COLUMNS if c not in man.columns]
    rep.add("FAIL" if missing_cols else "PASS", "manifest", "has the nine team columns",
            f"missing {missing_cols}" if missing_cols else "")
    if missing_cols:
        man = man.reindex(columns=list(man.columns) + missing_cols, fill_value="")

    dup_runs = man.run_id[man.run_id.duplicated()].tolist()
    rep.add("FAIL" if dup_runs else "PASS", "manifest", "each run listed once", ", ".join(dup_runs))
    bad_rows = []
    for row in man.itertuples():
        try:
            p = lib.parse_run_id(row.run_id)
        except ValueError:
            bad_rows.append(f"{row.run_id}: not an SG-NEx run name")
            continue
        if (row.cell_line, str(row.biological_replicate).strip(), str(row.sequencing_run).strip()) != \
                (p["cell_line"], str(p["replicate"]), str(p["run"])):
            bad_rows.append(f"{row.run_id}: cell_line/replicate/run columns disagree with the run name")
    rep.add("FAIL" if bad_rows else "PASS", "manifest", "run columns match run names", "; ".join(bad_rows))

    versions = sorted(set(man.model_version))
    pending = [v for v in versions if "PENDING" in v.upper() or not v.strip()]
    if len(versions) != 1:
        rep.add("FAIL", "manifest", "one model_version for every run", " | ".join(versions))
    elif pending:
        rep.add("FAIL", "manifest", "model_version names a selected model", f"still '{versions[0]}'")
    else:
        rep.add("PASS", "manifest", "one model_version for every run", versions[0])
    mins = sorted(set(m.strip() for m in man.min_reads))
    if len(mins) > 1:
        rep.add(incomplete, "manifest", "one min_reads rule for every run", ", ".join(mins))
    if args.require_complete:
        references = sorted(set(man.reference_version))
        if len(references) != 1 or not references[0].strip():
            rep.add("FAIL", "manifest", "one nonempty reference_version for every run", " | ".join(references))
        if any(not str(value).strip() for value in man.coverage_file):
            rep.add("FAIL", "manifest", "coverage_file is documented for every run")

    info = args.inputs / "MODEL_INFO.md"
    if not info.exists():
        rep.add(incomplete, "manifest", "MODEL_INFO.md present", "missing: the site cannot describe the model")
    else:
        placeholders = model_info_placeholders(info.read_text())
        if placeholders:
            rep.add(incomplete, "manifest", "MODEL_INFO.md complete",
                    "unfinished model placeholders: " + " | ".join(placeholders))

    public_runs = set(pd.read_csv(args.public / "runs_discovered.csv").run_id)
    if args.require_complete:
        from fetch_public_data import read_pinned_inventory
        expected_runs = set(read_pinned_inventory())
        if public_runs != expected_runs:
            rep.add("FAIL", "manifest", "public inventory matches the agreed 23-run scope",
                    f"{len(expected_runs-public_runs)} missing, {len(public_runs-expected_runs)} extra")
    not_delivered = sorted(public_runs - set(man.run_id))
    not_public = sorted(set(man.run_id) - public_runs)
    if not_delivered:
        rep.add(incomplete, "manifest", "every public m6Anet run delivered", f"{len(not_delivered)} missing: {', '.join(not_delivered)}")
    if not_public:
        rep.add(incomplete, "manifest", "runs match the public m6Anet listing", f"not in public listing: {', '.join(not_public)}")

    summaries = []
    for _, row in man.iterrows():
        if lib.RUN_PATTERN.match(row.run_id):
            s = check_file(row, args.inputs, args.public, rep, args.require_complete)
            if s:
                summaries.append(s)

    context_info = None
    if args.require_complete and (args.aliases is None or args.context_qc is None):
        rep.add("FAIL", "context", "final delivery includes explicit aliases and completed context QC",
                "Supply --aliases and --context-qc; raw prediction completeness remains a separate requirement")
    if args.aliases is not None or args.context_qc is not None:
        try:
            aliases = lib.load_aliases(args.aliases, man.run_id)
            rep.add("PASS", "context", "aliases are explicit per-run mappings",
                    f"{sum(len(a) for a in aliases.values()):,} documented mappings; unlisted IDs stay literal")
            if args.context_qc is not None:
                if args.aliases is None:
                    raise ValueError("Context QC requires its explicit alias table")
                qc, context_info = lib.load_context_qc(args.context_qc, man_path, args.aliases, args.inputs)
                expected_keys = set()
                for row in man.itertuples():
                    pred = lib.read_predictions(lib.prediction_path(args.inputs, row.prediction_file))
                    positions = pd.to_numeric(pred.transcript_position, errors="raise").astype("int64")
                    amap = aliases.get(row.run_id, {})
                    tx = pred.transcript_id.map(lambda value: amap.get(value, value))
                    expected_keys.update(zip(tx.astype(str), positions))
                actual_keys = set(zip(qc.transcript_id.astype(str), qc.transcript_position))
                if expected_keys != actual_keys:
                    raise ValueError(f"Context QC key set differs from complete predictions: "
                                     f"{len(expected_keys-actual_keys)} missing, {len(actual_keys-expected_keys)} extra")
                rep.add("PASS", "context", "completed context QC covers every scored canonical key",
                        f"{len(qc):,} keys; {int(qc.all_source_consistent.sum()):,} primary context eligible; "
                        "conflicting scores remain in their original files")
        except (OSError, KeyError, ValueError, TypeError) as exc:
            rep.add("FAIL", "context", "completed context QC and current predictions agree", str(exc))

    counts = rep.counts()
    width = max(len(i["scope"]) for i in rep.items)
    for i in rep.items:
        if i["level"] != "PASS":
            print(f"{i['level']:4s}  {i['scope']:{width}s}  {i['check']}" + (f" -- {i['detail']}" if i["detail"] else ""))
    print(f"\n{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL "
          f"across {len(man)} runs (model_version: {', '.join(versions)})")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"inputs": str(args.inputs), "require_complete": args.require_complete,
                                       "counts": counts, "model_versions": versions,
                                       "context_qc": context_info,
                                       "runs": summaries, "items": rep.items}, indent=1))
    print(f"Report: {args.report}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
