# Required benchmarks completed — 22 October 2026

Both course-required references have now run on the actual local data0 input.
All earlier checkpoints/logs and the resumed preparation are preserved.

| Pipeline | Mean ROC | Mean trapezoidal PR | Mean S |
|---|---:|---:|---:|
| Fixed balanced-C1 logistic regression | 0.804056 | 0.149129 | 0.476592 |
| Published m6Anet HCT116_RNA002 | 0.932176 | 0.503257 | 0.717717 |
| Existing Elgin cap128 control | 0.931828 | 0.505601 | 0.718715 |
| Samuel LightGBM | 0.921897 | 0.498996 | 0.710446 |

All rows cover 121,838 sites and 5,475 positives. The primary numbers are
unweighted means over the exact five gene groups. Published m6Anet is a
pretrained reference with possible HCT116 overlap, not five-fold refitting.
Mean-fold and pooled results differ; preserve both rather than changing the
selection rule. See [tables, plots and limits](benchmark_results_2026_10_22/README.md).

The baseline performed five fresh fits with training-only scalers and 18 raw
float64 features. Independent checks verified splits, hashes, scaler statistics
and saved-coefficient prediction parity. Invocation: 93.393 s wall, 90.859 s
CPU, 362.72 MiB sampled process RSS. Models, features and logs remain local.

m6Anet used its unmodified official weights/source/normalization, Python 3.8
installed with Conda, fixed seed and 1,000 sampling iterations. Two repeated
pilots at the final batch size had identical official CSV hashes. Full output
checks verified all 121,838 sites and 11,027,106 ordinal bookkeeping rows,
unchanged sources/assets/inputs and finite scores. Command: 1,303.367 s wall,
1,070.344 s sampled process-tree CPU lower bound, 761.52 MiB sampled tree RSS.
Those scopes differ from baseline training; do not call this a matched speed
comparison or add overlapping timers. Format preparation and pilot/setup costs
are separately retained, outside those command totals.

The earlier pause was explicitly resumed by the user. Source/tests and
preparation/inference/scoring commands are in the two reference subfolders.
The reference model needs a separate legacy environment; the existing neural
training environment is unchanged. No data1/SG-NEx fitting or model selection
was performed in these benchmarks. Clean Ubuntu reproduction remains pending.

Next: explicitly nominate and integrate the selected neural pipeline, verify
its generic prediction interface, fit/save a fresh final all-data0 model, then
perform the exposed data1 diagnostic and actual new-test/SG-NEx predictions.
The separately audited external candidate has not yet replaced the main
pipeline; this benchmark does not create a final submission artifact.
