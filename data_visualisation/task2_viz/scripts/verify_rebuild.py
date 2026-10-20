"""Check that a rebuilt explorer matches a reference copy.

Every file in site/data must be byte-identical, except overview.json, where only
the build time and the public-download check time may differ. Optionally the
reports (alias table, Member 4 cross-check) are compared byte for byte too.

Usage:
  python scripts/verify_rebuild.py --reference site/data --rebuilt REBUILT/site/data
  python scripts/verify_rebuild.py --reference site/data --rebuilt REBUILT/site/data --reference-reports reports --rebuilt-reports REBUILT/reports
Exit code 0 = everything matches, 1 = at least one difference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VOLATILE = {"generated_utc", "public_download_utc"}   # keys inside overview["build"]
REPORT_FILES = ["transcript_aliases.csv", "crosscheck_member4.json"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def overview_without_times(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["build"] = {k: v for k, v in data["build"].items() if k not in VOLATILE}
    return data


def compare_dirs(ref: Path, new: Path) -> list[str]:
    problems = []
    for name, path in (("reference", ref), ("rebuilt", new)):
        if not path.is_dir():
            problems.append(f"{name} directory does not exist: {path}")
    if problems:
        return problems
    ref_files = {p.relative_to(ref).as_posix() for p in ref.rglob("*") if p.is_file()}
    new_files = {p.relative_to(new).as_posix() for p in new.rglob("*") if p.is_file()}
    if not ref_files or not new_files:
        return ["Reference and rebuilt directories must both contain data files"]
    problems += [f"missing from rebuild: {f}" for f in sorted(ref_files - new_files)]
    problems += [f"extra in rebuild: {f}" for f in sorted(new_files - ref_files)]
    for f in sorted(ref_files & new_files):
        a, b = ref / f, new / f
        if f == "overview.json":
            if overview_without_times(a) != overview_without_times(b):
                problems.append("overview.json differs beyond the build timestamps")
        elif sha256(a) != sha256(b):
            problems.append(f"content differs: {f}")
    print(f"{len(ref_files & new_files)} files compared in {new}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--rebuilt", type=Path, required=True)
    ap.add_argument("--reference-reports", type=Path)
    ap.add_argument("--rebuilt-reports", type=Path)
    args = ap.parse_args()
    problems = compare_dirs(args.reference, args.rebuilt)
    if args.reference_reports and args.rebuilt_reports:
        for name in REPORT_FILES:
            a, b = args.reference_reports / name, args.rebuilt_reports / name
            if not a.exists() or not b.exists():
                problems.append(f"report missing: {name}")
            elif sha256(a) != sha256(b):
                problems.append(f"report differs: {name}")
        print(f"{len(REPORT_FILES)} reports compared")
    for p in problems:
        print(f"FAIL  {p}")
    print("PASS: the rebuild reproduces the reference exactly (apart from build timestamps)." if not problems
          else f"{len(problems)} difference(s) found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
