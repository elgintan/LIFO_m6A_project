"""Restore received coverage evidence locally; no download, prediction or analysis.

Only listed metadata/results/figures and two reading guides are copied. The
received SHA256 inventory is checked before each copy. Model artifacts and
development predictions are deliberately excluded. Existing differing files
are refused so historical evidence is never silently replaced.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ROOT = ROOT / 'outputs'
REQUIRED = {
    'results/coverage_matrix_ge20_union.csv.gz',
    'results/site_annotations.csv.gz',
    'metadata/transcript_aliases_checked.csv',
}
GUIDES = {'Member4_Analysis.html', 'Member4_Analysis.ipynb'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def safe_relative(value):
    path = PurePosixPath(value)
    if (not value or '\\' in value or ':' in value or path.is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))
            or path.suffix.lower() in ('.pem', '.key', '.keys', '.p12', '.pfx')):
        raise ValueError('Unsafe or credential path in received inventory')
    return path


def restore(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == LOCAL_ROOT.resolve() or not output.is_relative_to(LOCAL_ROOT.resolve()):
        raise ValueError('Destination must be a subfolder of sgnex_analysis/outputs')
    inventory = source / 'PACKAGE_MANIFEST.json'
    entries = json.loads(inventory.read_text(encoding='utf-8'))['files']
    selected = []
    names = set()
    for entry in entries:
        relative = safe_relative(entry['path'])
        if relative.as_posix() in names:
            raise ValueError('Duplicate received inventory entry')
        names.add(relative.as_posix())
        if relative.parts[0] in ('metadata', 'results', 'figures') or str(relative) in GUIDES:
            selected.append((relative, entry))
    if not REQUIRED.issubset({str(path) for path, _ in selected}):
        raise ValueError('Required coverage/annotation/alias files absent from source inventory')
    # Check all sources and existing targets before beginning any copy.
    for relative, entry in selected:
        original, target = source.joinpath(*relative.parts), output.joinpath(*relative.parts)
        if not original.resolve().is_relative_to(source) or not target.resolve().is_relative_to(output):
            raise ValueError('Received or destination path escapes its root')
        if not original.is_file() or original.stat().st_size != entry['bytes'] or sha(original) != entry['sha256']:
            raise ValueError('Received size/SHA256 mismatch: ' + str(relative))
        if target.exists() and (not target.is_file() or sha(target) != entry['sha256']):
            raise ValueError('Existing evidence differs; use a new destination: ' + str(relative))
    records = []
    for relative, entry in selected:
        original, target = source.joinpath(*relative.parts), output.joinpath(*relative.parts)
        reused = target.exists()
        if not reused:
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + '.partial')
            if partial.exists():
                raise ValueError('Previous partial copy exists; inspect it before retrying: ' + str(relative))
            shutil.copyfile(original, partial)
            if sha(partial) != entry['sha256']:
                raise ValueError('Copied SHA256 mismatch: ' + str(relative))
            partial.replace(target)
        records.append({'path': str(relative), 'bytes': entry['bytes'],
                        'sha256': entry['sha256'], 'reused': reused})
    now = datetime.now(timezone.utc)
    receipt = {'status': 'restored_received_evidence_only', 'utc': now.isoformat(),
               'source_package_manifest_sha256': sha(inventory), 'files': records,
               'limitations': ['Copy/integrity verification is not independent reconstruction.',
                              'No signals, model artifacts or new biological results were generated.']}
    receipts = output / 'restore_receipts'
    receipts.mkdir(parents=True, exist_ok=True)
    record = receipts / (now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    record.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(f'Restored/verified {len(records)} received files; receipt: {record}')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Extracted Member4_Analysis package folder')
    parser.add_argument('--output-dir', default=str(LOCAL_ROOT / 'received_member4_20261019'))
    args = parser.parse_args()
    restore(args.source, args.output_dir)
