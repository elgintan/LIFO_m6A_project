# Published m6Anet reference: preparation and inference

The course handout asks for a published m6Anet comparison using Python 3.8
installed through Conda. Keep that environment separate from our own model's
environment. The parent benchmark plan records the actual package, pretrained
model, normalization, sampling and source fingerprints before inference.

`prepare_input.py` is a **format adapter**, not a new model, data split or
normalization procedure. It accepts the course's already processed JSON/JSON.GZ:
one transcript, one unchanged position, one seven-base context and nine signal
measurements per read on each line. It writes m6Anet 2.1.0 `data.json` and
`data.info`, whose byte offsets, keys and read counts are checked by reading
every output record back. An ordered SHA256 chain of the source's canonical
site keys/context/nine values must also match the independently read-back output
with its metadata column removed. No labels are accepted, and no coordinate offset,
feature scaling, coverage filtering, score calculation or training is done.

The course matrices contain **no read identifiers**. m6Anet 2.1 expects a tenth
column for read-output bookkeeping, while its signal feature columns remain
0–8. The adapter appends a zero-based row ordinal, restarting at each site.
These ordinals are **not biological read IDs** and cannot link molecules across
positions. Use this input only for a site-score benchmark after independently
checking the installed vendor loader/pooling code; never interpret ordinal
outputs as real molecule identities or evidence about individual reads.
The original nine numeric values, site keys and seven-mers are retained.

From the repository root, an explicit small preparation pilot is:

```text
python model_evaluation/m6anet_reference/prepare_input.py --source ../data0/dataset0.json.gz --output model_evaluation/outputs/m6anet_v1/pilot_input --limit-sites 512
```

Use a separate output directory and omit `--limit-sites` for the full source.
A pilot is the first N sites in source order, solely for software/timing checks;
it is not a representative validation sample. The completion receipt labels it
as a subset and refuses silent reuse for a different source or limit.

Preparation saves `.preparing/checkpoint.json` after each 1,000 sites by default.
Rerunning the **same** command resumes: it verifies the source/options/code
identity, truncates uncommitted trailing writes and audits the retained byte
index before continuing. One writer may own an output directory at a time.
Invalid or duplicate sites stop preparation; no valid completion marker is
written. Existing unrelated files are never overwritten.

Both staged and published copies remain on disk after completion to make a
crash during publication recoverable. Only a verified `complete.json` marks an
input ready for inference. Completed reuse rechecks hashes and the whole index;
it does not blindly trust that marker. Signals, staging files and receipts are
local generated outputs, not public repository source.

The published pretrained model may overlap in provenance with the course's
HCT116 development data. Its score is an **off-the-shelf reference**, not a
gene-held-out model retrained on our five folds and not an independent test.
Document pretraining, chemistry, eligible sites, missing predictions and
sampling settings alongside any eventual metric. Preparation alone produces
no performance result.

Run the independent adapter checks from the repository root:

```text
python -B -m unittest discover -s model_evaluation/m6anet_reference -p test_prepare_input.py -v
```

If the execution sandbox denies writes to its default temporary folder, set
`M6ANET_TEST_TMP_ROOT` to a writable local scratch directory before that command.
The test runner creates and cleans its own uniquely named fixture subfolders
inside that location.

Tests cover exact original values, Unicode byte offsets, unchanged coordinates,
explicit ordinal metadata, real interrupted conversion/resume, identity/hash
guards, duplicate/invalid rejection, byte-index and saved-signal tampering. They do not import
vendor models, train, infer or process the full course dataset.

## Seeded official inference launcher

`inference_runner.py` calls the installed official m6Anet 2.1.0 inference entry
point. It does not edit the vendor package, weights or normalization. Run this
launcher using the **separate Python 3.8 Conda environment**, with official
PyTorch 1.6.0. The adapter/tests can run under the project's newer environment,
but that newer environment is not suitable for the published-model launcher.
Installation and artifact pins belong to the parent benchmark plan.

The retained Conda specification is `environment.yml`. For example:

```text
micromamba create -n lifo-m6anet-reference -f model_evaluation/m6anet_reference/environment.yml --strict-channel-priority
micromamba run -n lifo-m6anet-reference python -B model_evaluation/m6anet_reference/inference_runner.py --input-dir model_evaluation/outputs/m6anet_v1/full_input --output-dir model_evaluation/outputs/m6anet_v1/full_run
```

Use a short local prefix on Windows if package extraction exceeds the Windows
path limit. Tested native execution uses the recorded Windows Conda builds;
these commands do not establish a completed clean Ubuntu reproduction.
MKL2020.4/OpenMP2020.3 avoid the newer MKL DLL incompatibility observed with
Torch1.6. The benchmark environment does not replace the main training runtime.

From the repository root, after selecting that environment's `python`:

```text
python -B model_evaluation/m6anet_reference/inference_runner.py --input-dir model_evaluation/outputs/m6anet_v1/pilot_input --output-dir model_evaluation/outputs/m6anet_v1/pilot_run --preflight
python -B model_evaluation/m6anet_reference/inference_runner.py --input-dir model_evaluation/outputs/m6anet_v1/pilot_input --output-dir model_evaluation/outputs/m6anet_v1/pilot_run
```

The first command fingerprints installed source/assets and checks every input
site against the vendor vocabulary and published normalization factors. It also
checks that the vendor loader selects exactly columns 0–8, keeps the ordinal
separate and loads the first site's nine values exactly. It makes no forward
pass and writes no inference files. Successful preflight alone is not a
prediction or performance result.

The second command performs actual model inference. Its fixed settings are:

- HCT116_RNA002 published model and its bundled normalization; CPU execution.
- Seed 2026, 1,000 sampling iterations, batch size 2048, one worker process and
  four Torch threads.
- Explicit `spawn` multiprocessing. NumPy seeding is at module scope, so a
  spawned pooling child also receives the fixed seed; a parent-only seed would
  not be sufficient on Windows.
- `save_per_batch=2147483647`. The installed 2.1.0 vendor code flushes when a
  batch-number remainder is nonzero. A constant larger than the entire batch
  count makes every batch flush, including the final batch. Vendor algorithms
  remain unchanged. The final 4096-site pilot has exactly two batches, exercising the
  even-final-batch case that the vendor's default setting can omit.

This command refuses a nonempty output directory. Before inference it saves a
status receipt, then preserves a failure receipt and partial files if anything
fails or is interrupted. **Official inference is not a resumable training job**:
use a new output directory for a retry; do not concatenate unverified partial
outputs or reuse them as a completed prediction.

Completion requires all of the following: one finite probability in [0,1] for
every input key, no extra/duplicate sites, unchanged read counts and central
contexts, complete local ordinal bookkeeping, and unchanged vendor sources,
weights, normalization, adapter, launcher and input files. The completion receipt
includes hashes, package versions, fixed settings, command arguments, population
and resource scope. Recorded CPU time covers the launcher process only; include
an external process-tree monitor before making a total-computation claim.

For site classification use **`probability_modified` from
`data.site_proba.csv`**. The vendor's read cutoff is used only for its `mod_ratio`
column; it is not a selected site classification threshold. The potentially
large `data.indiv_proba.csv` remains local and uses synthetic row ordinals,
which cannot identify biological molecules. No labelled-data fitting or
threshold choice occurs in this launcher.

Before a full run, compare two independent pilot runs with identical settings
and verify exact output coverage and score reproducibility. The root benchmark
workflow owns this actual execution, timing and later shared scoring. Neither
the source files nor their mocked tests establish a measured m6Anet score.

The first512-site pilots used batch256; their output hashes matched exactly.
Before labels were examined, the computation amendment in the parent plan
fixed batch2048 and4096-site pilots to reduce repeated Windows pool startup.
The final results must use that one fixed execution recipe, with all earlier
pilot receipts retained. Changing batch boundaries can change Monte Carlo
draws; no choice between labelled scores is permitted.

After full inference completes, run the shared scoring adapter from the main
comparison environment (which contains the shared scorer's dependencies):

```text
python -B model_evaluation/m6anet_reference/score_reference.py --reference-dir model_evaluation/outputs/m6anet_v1/full_run --labels ../data0/data.info.labelled --folds eda/received/shared_folds/data0_folds.csv --output-dir model_evaluation/outputs/m6anet_v1/scored
```

It accepts a completed full-source run, checks the site-output fingerprint,
aligns all keys to the exact shared folds and calls the unchanged evaluator.
These folds stratify the published reference's scores; they are not retraining
or proof of pretraining independence. `measure_command.py`, run from the main
environment with psutil, can wrap the inference command to retain stdout,
stderr, sampled memory and a sampled lower bound on process-tree CPU. Its
measurements exclude the monitor and must not be added to overlapping launcher
timers as separate computation.

The unmodified shared scorer mechanically labels data0 metric JSON as
`data0_gene_grouped_oof_development`. For this pretrained reference, that field
does **not** describe its learning history. The scoring receipt, comparison
table and figure captions give the applicable interpretation: fold-stratified
scoring of one published pretrained model, with unresolved pretraining overlap.

Launcher tests use tiny invented fixtures and mocked vendor calls, without
importing Torch, m6Anet or real course signals:

```text
python -B -m unittest discover -s model_evaluation/m6anet_reference -p test_inference_runner.py -v
```
