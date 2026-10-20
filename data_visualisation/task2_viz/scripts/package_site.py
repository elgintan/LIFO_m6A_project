"""Turn site/app.html into deployable pages.

  site/index.html          full HTML document (for GitHub Pages or `python -m http.server`)
  <artifact-dir>/          optional copy for a host that adds its own document wrapper:
                           index.html is the bare fragment, plus the data/ folder

Usage:
  python scripts/package_site.py [--artifact-dir PATH]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", type=Path, default=ROOT / "site")
    ap.add_argument("--artifact-dir", type=Path, default=None)
    args = ap.parse_args()
    if args.artifact_dir:
        dest = args.artifact_dir.resolve()
        if dest.exists():
            raise SystemExit("Artifact directory already exists; choose a new directory. Nothing was removed.")
        if dest.is_relative_to(args.site.resolve()):
            raise SystemExit("Artifact directory must be outside the source site directory.")
        if not (args.site / "data").is_dir():
            raise SystemExit("Build or restore site/data before exporting an artifact.")
    fragment = (args.site / "app.html").read_text(encoding="utf-8")
    split = fragment.index("</style>") + len("</style>")
    page = HEAD + fragment[:split] + "\n</head>\n<body>\n" + fragment[split:] + "\n</body>\n</html>\n"
    (args.site / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote {args.site / 'index.html'} ({len(page) / 1e3:.0f} kB)")
    if args.artifact_dir:
        dest = args.artifact_dir
        shutil.copytree(args.site / "data", dest / "data")
        (dest / "index.html").write_text(fragment, encoding="utf-8")
        n = sum(1 for _ in (dest / "data").rglob("*.json"))
        size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
        print(f"wrote {dest} ({n} data files, {size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
