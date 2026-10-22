# Data and local environments

## Included evidence

`eda/received/` contains the supplied derived site summaries, figures, analysis
code and historical shared folds. The SHA256 receipt identifies unchanged
copies. These summaries cannot reconstruct individual read matrices.

`model_elgin/baseline_2026_10_07/examples/input_10_sites.json` is a small real
prediction example. It is not the full training set or a new biological test.
`data_visualisation/prototype/data/` is an archival simulated demonstration.
The current `data_visualisation/task2_viz` pipeline has a coverage-only handoff;
its small display JSONs cannot replace Task 2 signal inputs either.

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

Official intermediate leaderboard slides identify data0 as HCT116, data1 as
HEK293T and data2 as synthetic sequences. Exact run/preprocessing provenance
and fractional-label scoring are separate questions. Compare hashes with
`eda/received/tables/source_manifest.json`. Do not replace original labels or
regenerate historical folds. New shared assignments, if selected, need a
separate filename and documented generation method.

Member 1's extraction code accepts `--data-root` and `--out`; see her received
README for the exact workflow. New candidate training entry points and their
data paths will be documented as those models are implemented. The accepted
outer assignments and shared scoring commands are in
[minimum shared rules](model_evaluation/SHARED_RULES.md). Do not copy a
virtual environment from another computer; install each candidate's recorded
dependencies in a local environment when needed.

## SG-NEx application inputs

Elgin selected the **23 available processed direct-RNA runs** as the working
scope on 20 October. The canonical run list is `sgnex_analysis/manifest.csv`;
the delivered source inventory and download helper are documented in that
folder. Total processed signal size is approximately 33.37 GB. No full signal
download was performed during the original integration. On23October the first
1.5-GB full input passed strict validation and exact inherited coverage checks;
the full23-run sequential download/audit/prediction workflow is now running.
See [the run guide](sgnex_analysis/ELGIN_TASK2_RUNNER.md). Download/process into
local ignored storage and retain source/size/hash receipts. Broader metadata
entries do not automatically expand this agreed subset.

Member 5 has now supplied its download/build/validation scripts; follow
`data_visualisation/task2_viz/README.md`. A fresh clone needs documented public
inputs or the original local handover to rebuild the full coverage explorer.
Large handover-derived coverage/annotation/alias data are retained locally,
not added again as generated site tables in this integration.

Use [official SG-NEx access information](https://github.com/GoekeLab/sg-nex-data)
to verify source release, cell line, replicate group, run, reference and event
preprocessing. Exact coordinate/reference uncertainties remain documented in
the received MODEL_INFO.md. Preserve original prediction identifiers and
positions; do not blindly strip transcript versions or shift coordinates.

The selected model must generate a separate real prediction CSV for each
application run. Keep full precision and join coverage from the matched input
metadata. Preserve the required three score columns; keep sample/model
information in a separate manifest.
