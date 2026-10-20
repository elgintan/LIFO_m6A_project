"""Download the public SG-NEx files the visualisation needs (standard library only).

What it fetches (no AWS account or credentials needed; the bucket is public):
  * data.readcount for every run under data/processed_data/m6Anet/
    (one row per candidate DRACH site: transcript_id, transcript_position, n_reads)
  * Homo_sapiens.GRCh38.91.annotations-transcripts.txt
    (transcript -> gene symbol, biotype, chromosome, transcript length)

Every file is checked against the size S3 reports and fingerprinted with
SHA-256. Results go to public_data/download_manifest.csv. Re-running skips files
that are already complete, so an interrupted download can simply be restarted.

Usage:
  python scripts/fetch_public_data.py --out public_data
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BUCKET_URL = "https://sg-nex-data.s3.amazonaws.com"
M6ANET_PREFIX = "data/processed_data/m6Anet/"
ANNOTATION_KEY = "data/annotations/txt_file/Homo_sapiens.GRCh38.91.annotations-transcripts.txt"
RUN_PATTERN = re.compile(r"^SGNex_(?P<cell_line>.+?)_directRNA_replicate(?P<replicate>\d+)_run(?P<run>\d+)$")
DEFAULT_RUN_INVENTORY = Path(__file__).resolve().parents[1] / "public_data/runs_discovered.csv"
PINNED_RUN_SET_SHA256 = "58688a918fd962da470ebf7ac906ef42de085d4ba58566a3d44ea87f2b501ac6"


def read_pinned_inventory(path: Path = DEFAULT_RUN_INVENTORY) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        runs = [row["run_id"] for row in csv.DictReader(handle)]
    digest = hashlib.sha256(("\n".join(sorted(runs)) + "\n").encode()).hexdigest()
    if len(runs) != 23 or digest != PINNED_RUN_SET_SHA256:
        raise ValueError("Run inventory differs from the agreed 23-run set; restore the versioned file")
    return runs


def select_pinned_runs(discovered: list[str], pinned: list[str]) -> list[str]:
    """Keep the agreed inventory; live discovery can only check its availability."""
    if not pinned or len(pinned) != len(set(pinned)) or any(not RUN_PATTERN.fullmatch(r) for r in pinned):
        raise ValueError("Run inventory must contain unique valid SG-NEx run IDs")
    missing = sorted(set(pinned) - set(discovered))
    if missing:
        raise ValueError(f"Required runs are absent from the public listing: {missing}")
    return sorted(pinned)


def list_objects(prefix: str, delimiter: str | None = None) -> tuple[list[str], list[dict]]:
    """Return (common prefixes, objects) for one S3 listing, following pagination."""
    prefixes, objects, token = [], [], None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if delimiter:
            params["delimiter"] = delimiter
        if token:
            params["continuation-token"] = token
        url = f"{BUCKET_URL}/?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            xml = resp.read().decode("utf-8")
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix></CommonPrefixes>", xml)
        for block in re.findall(r"<Contents>(.*?)</Contents>", xml, re.S):
            objects.append({
                "key": re.search(r"<Key>([^<]+)</Key>", block).group(1),
                "size": int(re.search(r"<Size>(\d+)</Size>", block).group(1)),
                "etag": re.search(r"<ETag>([^<]+)</ETag>", block).group(1).replace("&quot;", "").strip('"'),
            })
        if "<IsTruncated>true</IsTruncated>" not in xml:
            return prefixes, objects
        token = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml).group(1)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(key: str, size: int, dest: Path) -> str:
    """Download one object unless a complete copy exists; return 'downloaded' or 'kept'."""
    if dest.exists() and dest.stat().st_size == size:
        return "kept"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    url = f"{BUCKET_URL}/{urllib.parse.quote(key)}"
    with urllib.request.urlopen(url, timeout=120) as resp, tmp.open("wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
    if tmp.stat().st_size != size:
        raise RuntimeError(f"{key}: expected {size} bytes, got {tmp.stat().st_size}")
    tmp.replace(dest)
    return "downloaded"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("public_data"))
    ap.add_argument("--run-inventory", type=Path, default=DEFAULT_RUN_INVENTORY,
                    help="Versioned 23-run inventory; live discovery never expands this scope")
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    run_prefixes, _ = list_objects(M6ANET_PREFIX, delimiter="/")
    discovered = sorted(p[len(M6ANET_PREFIX):].strip("/") for p in run_prefixes)
    pinned = read_pinned_inventory(args.run_inventory)
    runs = select_pinned_runs(discovered, pinned)
    extras = sorted(set(discovered) - set(runs))
    print(f"Using {len(runs)} pinned m6Anet-processed runs; {len(extras)} additional listed folders excluded")

    with (out / "runs_discovered.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "cell_line", "replicate", "run", "s3_prefix", "listed_utc"])
        for r in runs:
            m = RUN_PATTERN.match(r)
            w.writerow([r, m["cell_line"], m["replicate"], m["run"], f"s3://sg-nex-data/{M6ANET_PREFIX}{r}/", now])

    targets = []
    for r in runs:
        _, objs = list_objects(f"{M6ANET_PREFIX}{r}/data.readcount")
        obj = next((o for o in objs if o["key"].endswith("/data.readcount")), None)
        if obj is None:
            raise SystemExit(f"{r}: data.readcount not found")
        targets.append((obj, out / "readcount" / f"{r}.readcount.csv"))
    _, objs = list_objects(ANNOTATION_KEY)
    targets.append((objs[0], out / "annotation" / Path(ANNOTATION_KEY).name))

    rows = []
    for i, (obj, dest) in enumerate(targets, 1):
        status = download(obj["key"], obj["size"], dest)
        digest = sha256_of(dest)
        rows.append([f"s3://sg-nex-data/{obj['key']}", str(dest.relative_to(out)), obj["size"],
                     obj["etag"], digest, status, now])
        print(f"[{i:2d}/{len(targets)}] {status:10s} {obj['size'] / 1e6:7.1f} MB  {dest.name}", flush=True)

    with (out / "download_manifest.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "local_path", "bytes", "s3_etag", "sha256", "status", "checked_utc"])
        w.writerows(rows)
    print(f"Done: {sum(r[2] for r in rows) / 1e9:.2f} GB in {len(rows)} files; manifest written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
