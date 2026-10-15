# Data and local environments

## Included evidence

`eda/received/` contains the supplied derived site summaries, figures, analysis
code and historical shared folds. The SHA256 receipt identifies unchanged
copies. These summaries cannot reconstruct individual read matrices.

`model_elgin/baseline_2026_10_07/examples/input_10_sites.json` is a small real
prediction example. It is not the full training set or a new biological test.
`data_visualisation/prototype/data/` contains received coverage/metadata and
simulated scores, not raw signal inputs for Task 2 prediction.

## Raw inputs outside Git

Obtain the supplied course data through the official course release and retain
the original files locally:

```text
data0/dataset0.json.gz
data0/data.info.labelled
data1/dataset1.json.gz
data1/data.info
data2/dataset2.json.gz
data2/data.info
```

Dataset identity/provenance matters; names alone do not identify a cell line,
run or experimental design. Compare hashes with
`eda/received/tables/source_manifest.json`. Do not replace original labels or
regenerate historical folds. New shared assignments, if selected, need a
separate filename and documented generation method.

Member 1's extraction code accepts `--data-root` and `--out`; see her received
README for the exact workflow. New candidate training entry points and their
data paths will be documented after the protocol is agreed. Do not copy a
virtual environment from another computer; install each candidate's recorded
dependencies in a local environment when needed.

## SG-NEx application inputs

Use [official SG-NEx access information](https://github.com/GoekeLab/sg-nex-data)
and the course handout to identify all required direct-RNA JSONs. Record source,
release, cell line, biological replicate, run, reference and preprocessing.
The prototype's 23 processed runs are a starting inventory, not independent
verification of the full required scope. Its missing build/download scripts
and provenance need obtaining from Member 5.

The selected model must generate a separate real prediction CSV for each
application run. Keep full precision and join coverage from the matched input
metadata. Preserve the required three score columns; keep sample/model
information in a separate manifest.
