"""Download only selected runs from the fixed 23-run manifest; no AWS credentials.

This helper was added for handover. It has not downloaded the full signal set
in this preparation. Size is checked against the saved listing; the new local
SHA256 is an audit receipt, not a comparison with an upstream SHA256.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def main(a):
    rows = list(csv.DictReader(Path(a.manifest).open(newline='')))
    if len(rows) != 23 or len({r['run_id'] for r in rows}) != 23:
        raise ValueError('Expected the fixed 23-run metadata/sample_manifest.csv')
    if a.run_id:
        rows = [r for r in rows if r['run_id'] == a.run_id]
        if not rows:
            raise ValueError('Run ID is not in the working scope')
    dest = Path(a.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for row in rows:
        run = row['run_id']
        if Path(run).name != run or run in ('.', '..'):
            raise ValueError('Unsafe run ID')
        path = dest / row['signal_local_path']
        if not path.resolve().is_relative_to(dest):
            raise ValueError('Signal path escapes destination')
        path.parent.mkdir(parents=True, exist_ok=True)
        size = int(row['signal_size_bytes'])
        source = row['signal_download_url']
        receipt = {'run_id': run, 'url': source, 'local_path': str(path),
                   'snapshot_size_bytes': size,
                   'retrieved_or_checked_utc': datetime.now(timezone.utc).isoformat()}
        try:
            reused = path.exists()
            if reused:
                if path.stat().st_size != size:
                    raise ValueError(f'Existing file has wrong size; move it aside: {path}')
            else:
                partial = path.with_name(path.name + '.partial')
                # Restart an interrupted transfer; no unverified resume is claimed.
                with urlopen(source, timeout=120) as response, partial.open('wb') as output:
                    while True:
                        block = response.read(2**20)
                        if not block:
                            break
                        output.write(block)
                if partial.stat().st_size != size:
                    raise ValueError(f'Download size differs from saved inventory: {partial}')
                partial.replace(path)
            receipt.update(status='size_checked_existing' if reused else 'downloaded_size_checked',
                           size_bytes=path.stat().st_size, sha256=sha(path),
                           limitation='No independent upstream SHA256 supplied; size alone is not content validation.')
        except Exception as error:
            receipt.update(status='failed', error=str(error))
            with (dest / 'download_receipts.jsonl').open('a') as f:
                f.write(json.dumps(receipt) + '\n')
            raise
        with (dest / 'download_receipts.jsonl').open('a') as f:
            f.write(json.dumps(receipt) + '\n')
        print(run, receipt['status'], receipt['size_bytes'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', default=str(Path(__file__).resolve().parents[1] / 'metadata/sample_manifest.csv'))
    p.add_argument('--dest', required=True)
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument('--run-id')
    selection.add_argument('--all', action='store_true', help='Download all 23 fixed-scope signal inputs')
    main(p.parse_args())
