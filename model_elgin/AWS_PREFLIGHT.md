# Prepared direct Ubuntu/AWS prediction check

Status: commands prepared; no direct AWS-host execution receipt yet. This is a
recommended software preflight, not a new fit, accuracy experiment or bulk job.

## Before launching

Use the course-managed RONIN project if taking this route. For this ten-site
check, our suggested small CPU target is Ubuntu24.04 LTS, x86_64/AMD64,2vCPUs,
4GB RAM and about20GB root storage. This is a practical allowance, not a measured
minimum or a full new-test sizing claim. The actual offered image/architecture,
machine type, displayed hourly price and project budget must be checked on the
current page before launch. A GPU is not used by this predictor.

The [official RONIN guide](https://blog.ronin.cloud/create-a-machine/) explains
the general New Machine/software/hardware/storage/launch flow; its screenshots
are older, so current course-page options take precedence.
[Canonical documents separate AMD64 and ARM64 Ubuntu images](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/).
AMD64 matches the architecture of our passed hosted check; an ARM configuration
would be an additional untested platform.

Estimated total setup/check time:15–30minutes, mostly image startup and package
installation/network transfer. This is an estimate, not a guaranteed runtime or
cost quote. The example itself is tiny. Keep SSH key material private and use the
course's existing secure connection procedure. No key contents, machine address
or private URL belongs in public evidence.

## 1. Open the machine's Ubuntu terminal

The following commands belong in the remote Ubuntu terminal, not Windows
PowerShell. First inspect the operating system, architecture and Python:

```bash
cat /etc/os-release
uname -m
python3 --version
```

Expected target:Ubuntu24.04, x86_64 and Python3.12. If the offered image differs,
check compatibility before changing version pins or installing another OS.

If Git or the Python venv module is missing on this new machine, install those
standard tools:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends -y git python3-venv ca-certificates
```

## 2. Clone into a fresh folder and install the exact CPU environment

```bash
git clone https://github.com/elgintan/LIFO_m6A_project.git LIFO_m6A_submission_check
cd LIFO_m6A_submission_check
git rev-parse HEAD
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r model_elgin/context_reference_v1/requirements.txt
python -m pip check
```

`git clone` obtains only the public repository; it does not copy laptop signals,
labels, unpublished checkpoints or credentials. The selected public `model.pt`
is included. The virtual environment keeps the exact
model packages separate from the machine's system Python. Do not install legacy
m6Anet or start training for this prediction check. If the clone folder already
exists, preserve it and choose a fresh folder rather than deleting its contents.

## 3. Predict the ten public example sites

```bash
python -c "from pathlib import Path; Path('model_elgin/outputs/aws_preflight_20261023').mkdir(parents=True, exist_ok=False)"
python -B model_elgin/context_reference_v1/predict.py --input model_elgin/artifacts/cap128_weight3_v1/example/input.json --model model_elgin/artifacts/cap128_weight3_v1/model.pt --output model_elgin/outputs/aws_preflight_20261023/predictions.csv --threads 4
```

Expected success message:10sites/1887reads, stage final_data0, all-read prediction.
This is expected output, not a receipt that the command has already run here.
Preserve the CSV and its `.manifest.json`. If the output folder already exists,
use another fresh name consistently in both commands and the check below.

## 4. Independently verify keys, scores and fingerprints

Copy this entire block into the same activated Ubuntu terminal:

```bash
python - <<'PY'
import csv, hashlib, json, math, platform, subprocess
from importlib.metadata import version
from pathlib import Path
root = Path.cwd()
pkg = root / 'model_elgin/artifacts/cap128_weight3_v1'
out = root / 'model_elgin/outputs/aws_preflight_20261023'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['transcript_id', 'transcript_position', 'score']
        result = {}
        for r in reader:
            assert None not in r and all(v is not None for v in r.values())
            key = (r['transcript_id'], int(r['transcript_position']))
            score = float(r['score'])
            assert key not in result and math.isfinite(score) and 0 <= score <= 1
            result[key] = score
        return result
release = json.loads((pkg / 'complete.json').read_text())
assert release['status'] == 'complete'
for name, expected_sha in release['files_sha256'].items():
    assert sha(pkg / name) == expected_sha, name
actual = rows(out / 'predictions.csv')
expected = rows(pkg / 'example/expected.csv')
assert actual.keys() == expected.keys() and len(actual) == 10
maximum = max(abs(actual[k] - expected[k]) for k in actual)
assert maximum <= 3e-6
m = json.loads((out / 'predictions.csv.manifest.json').read_text())
assert m['status'] == 'complete' and m['stage'] == 'final_data0'
assert m['n_sites'] == 10 and m['n_reads'] == 1887
assert m['all_reads_used'] is True and m['exact_input_key_coverage'] is True
assert m['labels_read'] is False
assert m['model_sha256'] == sha(pkg / 'model.pt') == 'b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668'
assert m['input_sha256'] == sha(pkg / 'example/input.json')
assert m['output_sha256'] == sha(out / 'predictions.csv')
for name, expected_sha in m['code_sha256'].items():
    assert sha(root / 'model_elgin/context_reference_v1' / name) == expected_sha
os_text = Path('/etc/os-release').read_text()
assert 'ID=ubuntu' in os_text and 'VERSION_ID="24.04"' in os_text
assert platform.machine() == 'x86_64'
versions = {p: version(p) for p in ['numpy', 'pandas', 'scikit-learn', 'psutil', 'torch']}
assert versions == {'numpy':'2.5.3', 'pandas':'3.0.6', 'scikit-learn':'1.9.1', 'psutil':'7.2.2', 'torch':'2.14.1+cpu'}
receipt = {'status':'complete', 'kind':'direct_host_example_prediction_check',
    'provider_not_automatically_verified': True,
    'git_commit':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
    'os_release':os_text, 'architecture':platform.machine(), 'python':platform.python_version(),
    'versions':versions, 'model_sha256':m['model_sha256'], 'n_sites':10, 'n_reads':1887,
    'maximum_absolute_score_difference':maximum, 'absolute_tolerance':3e-6,
    'prediction_sha256':m['output_sha256'], 'inference_resources':m['resources'],
    'scope':'Software parity on data0 examples; not independent accuracy or new-test submission'}
target = out / 'verification.json'
with target.open('x', encoding='utf-8') as f:
    json.dump(receipt, f, indent=2, allow_nan=False)
print('PASS: ten keys,1887 reads, exact package/source pins and score parity')
PY
```

The receipt verifies Ubuntu/runtime/software facts. AWS provenance comes from
the actual machine being launched in the course RONIN project; this code does
not query cloud credentials or infer a provider from a filename. Retain the
three result files and terminal success/error evidence locally for review.
If any assertion fails, preserve outputs and diagnose that specific mismatch.

## 5. End the bounded session

After results have been copied/reviewed, stop the machine using RONIN's normal
Stop control and confirm its state. Preserve its disk/results; no deletion or
termination is part of this check. A stopped machine can still incur storage
charges ([AWS explanation](https://repost.aws/knowledge-center/ebs-charge-stopped-instance));
check the displayed project costs. Do not start full-data training or
the completed23-run batch. Actual new-test inference is a separate later run.
