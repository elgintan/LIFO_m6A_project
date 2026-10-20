# LIFO integration notes — 20 October 2026

Source: `Member5_Explorer_Package_2026-10-19/task2_viz`. The original package
contains 160 files (48,425,200 bytes); all 159 entries in its supplied checksum
list matched during import. `IMPORT_RECEIPT.json` preserves the source hashes.
The original package remains outside this active checkout. Its `CHECKSUMS.sha256`
describes the original delivery, not the modified files below or the smaller
public checkout.

## Narrow changes to the imported copy

- Existing artifact directories are no longer recursively deleted by
  `package_site.py`; choose a new destination. The builder similarly refuses
  an existing generated `genes/` directory instead of deleting it.
- `verify_rebuild.py` rejects nonexistent and empty directories instead of
  claiming they reproduce a reference.
- Prediction validation rejects infinite/fractional positions, duplicates
  such as position `1` versus `1.0`, and CSV paths escaping the hand-off folder.
  Existing raw duplicate and bad-score checks remain.
- A score-enabled build now invokes the supplied validator. Final builds also
  require complete delivery: missing eligible predictions, missing public
  readcounts/runs, incorrect run scope and incomplete model provenance fail.
  Exploratory builds retain explicit warnings for incomplete delivery.
- The downloader is pinned to the versioned set of 23 run IDs, checked by a
  canonical run-set hash. Live listings check availability without silently
  adding new runs. A missing required run fails rather than changing scope.
- Constant-score agreement is reported unavailable rather than producing
  nonstandard JSON NaN; an empty alias map retains its column schema.
- Source/frontend documentation now records the user's chosen 23-run scope.
  No scientific counts or prediction values were changed.
- Generated data and large CSV alias tables are ignored in Git. Small public
  manifests and code remain. No private credentials are required or included.

## Checks actually run

Windows, existing Python 3.12 environment with NumPy 2.5.3/pandas 3.0.6:

```text
python -B -m unittest discover -s tests -v
```

**18 tests passed.** All fixtures are synthetic and generated temporarily under
ignored `tests/.tmp/`. Checks cover known valid/invalid joins, score errors,
numeric duplicates, unsafe paths, pending models, rebuild comparisons,
non-destructive packaging, equal biological-replicate weighting and undefined
correlation. Further checks cover fixed download scope and complete/incomplete
final delivery, including a synthetic 23-run passing fixture. A printed
`PENDING_TEAM_SELECTION` failure is an intentionally
rejected test fixture, not a new problem in actual predictions. The actual
execution log is retained locally under `data_visualisation/outputs/`.

These checks do not establish full rebuild equivalence, browser correctness,
Ubuntu compatibility, model quality or biological findings. No download,
full-data regeneration, real inference, server or hosting was run here.

## Remaining work

Run-level signal JSONs and downloaded readcount/annotation files are not
included. The downloader obtains public readcounts/annotation only, not the
large signal JSONs needed by the model. Freeze a selected model and preserve
original run transcript IDs when predicting. The builder applies a documented
alias map for versioned IDs and checks primary-annotation version matches.

Finish actual per-run predictions and model provenance, resolve every FAIL,
pass the strict final-delivery gate, build fresh data, compare the intended populations,
verify the browser and final deployment, and write evidence-based conclusions.
Coverage or replicate agreement alone does not validate a prediction or prove
the cause of a cell-line difference. Scores are not modification fractions.
