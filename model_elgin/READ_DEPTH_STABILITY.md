# Read-depth stability: investigation plan — 20 October 2026

**Completed:** the subsequent full diagnostic retained all 24,533 sites and
found all-read inference performed best. See the
[actual results and plots](read_depth_stability_results/README.md). The design
below was specified before outcomes; no new model was trained or selected.

This is a data0-only diagnostic of the existing original-feature neural
pipeline, using its five completed held-out gene-fold models. No weights,
normalisation, sequence references, labels, fold assignments or calling cutoff
are fitted or changed. Planned tests below are not results until the retained
execution evidence confirms completion.

## Why this follows Member 1's EDA

Member 1 identified changing coverage associations and recommended controlled
read subsampling. Completed data0 diagnostics found weaker ranking and recall
in the original model's >=200-read subgroup than the 100–199 subgroup. Those
groups contain different sites and may differ in motifs, genes and labels;
that association does not prove an effect of read count.

Source inspection adds a concrete mechanism to investigate: training sampled
at most **32 reads for the attention/read branch**, while its 63 summary
features always used all original reads. Saved assessment inference used all
reads in both branches. Read count itself is not a direct model input.

## Fixed population and interventions

Use every data0 site with >=100 original reads: **24,533 sites, 1,204 positive
labels, 1,002 genes**, coverage 100–991. Every condition uses those same sites.
The five assessment populations contain 5,415 / 4,894 / 4,070 / 5,423 / 4,731
sites, with 301 / 225 / 212 / 235 / 231 positives respectively. These counts
were checked against the actual cache and immutable fold manifest.

- Depths: **20, 32, 50, 100**, plus all reads. The additional 32-read level is
  specified before outcomes because it matches the training read-branch cap.
- Sampling seeds: **2026, 2027, 2028**. One deterministic, per-site/per-seed
  permutation without replacement supplies nested depth prefixes. Labels and
  prediction errors do not determine which reads or sites are selected.
- **Primary (`both`):** reduce the read bag and recompute all 63 summaries from
  exactly that same subset. Apply the saved transforms and normalisation.
- **Secondary (`bag-only`):** reduce only attention/read-branch observations,
  retaining the original all-read summaries. This isolates a software mechanism;
  it does not represent a truly low-depth sample and must not be described as
  such or ranked as the primary lower-coverage result.

The pilot uses a deterministic label-free restriction of this population to
check software/timing. Its results are not the full matched-cohort findings.

## Frozen models and numerical controls

Each site is scored only with
`outputs/context_reference_v1/cv/none/fold{fold_id}/refit/best.pt`, which excluded
its gene group. Checkpoint stages, fitting signatures, fitted indices, gene
separation and source/model/cache/fold/label hashes must pass before scoring.
Completed refit epochs are 9 / 20 / 19 / 18 / 17. Inner stopping checkpoints,
historical all-data0 weights and another fold's model cannot substitute.

1. **All-cache control:** original raw read cache plus original cached summaries;
   reproduce the corresponding saved OOF predictions within a recorded small
   numerical tolerance. This is the `bag-only` reference.
2. **All-recomputed control:** all raw cached reads with freshly recomputed
   summaries. This is the primary `both` reference. Measure its score difference
   from all-cache separately: raw reads are stored as float32, whereas the
   original cached summaries were calculated from the source float64 values
   before float32 storage. Avoid attributing tiny rounding differences to depth.

The cached measurements are sampled before nonlinear read transforms.
Summary order/quantiles and read transforms come from the frozen source;
normalisation is reused, never re-estimated from assessment sites.

## Measurements and report interpretation

Retain ROC AUC, explicitly trapezoidal PR AUC, AP and S for each fold/draw;
report mean-fold results and separate fold variation from sampling variation.
Compare each arm with its correct all-read reference on the identical cohort.
Pooled values are supplementary. The matched >=100 cohort is not the full
121,838-site CV population; do not compare its S directly with the full-CV S.

Also measure per-site/class score shifts, repeated-sampling spread and flips
at the existing 0.5 reporting cutoff. Examine the fixed original >=200 group
and motif support descriptively. Do not select a new cutoff or only retain
favourable depths. Sparse/single-class subgroups need counts and undefined
ranking metrics, not fabricated zero AUCs.

Repeated draws and the five reused models are not independent biological
replicates. Computational subsampling does not reproduce independently sequenced
low-depth experiments, resolve molecule-level states, explain label error, or
establish causal biology/significance. Any later modelling change remains
data0 development requiring a separately documented comparison.

## Evidence and interruption recovery

The standalone tools and their tests stay outside fingerprinted production
modules. Predictions, per-condition completion receipts, sampling fingerprints,
logs, resource measurements and plots are retained under ignored
`outputs/read_depth_stability_v1/`. Exact executed commands and measured timing
belong in the generated report. Complete conditions can resume only with
matching source/input/model/configuration fingerprints; partial files remain
evidence and must not be mistaken for complete results.

No data1, data2, SG-NEx application data, retraining, calibration, threshold
tuning or new final model is part of this investigation.

## Run from the repository root

Use the same recorded environment, original cache, exact data0 labels/folds
and completed control CV bundles. The helper verifies their hashes and the
fitting signatures, including package versions. It does not create those
models; see `context_reference_v1/README.md` for original preparation/training.
On the current laptop `python` below is
`../advanced_model/.venv/Scripts/python.exe`.

```text
python -B -m unittest discover -s model_elgin/tools -p test_*read_depth_stability.py -v
python -B -u model_elgin/tools/read_depth_stability.py --trial --trial-genes-per-fold 20 --trial-sites-per-fold 100
python -B model_elgin/tools/report_read_depth_stability.py --run-dir model_elgin/outputs/read_depth_stability_v1/trial --allow-trial
python -B -u model_elgin/tools/read_depth_stability.py --output-dir model_elgin/outputs/read_depth_stability_v1 --depths 20,32,50,100 --seeds 2026,2027,2028 --perturbation both,bag-only --threads 4 --batch-size 64 --max-padded-reads 65536
python -B model_elgin/tools/report_read_depth_stability.py --run-dir model_elgin/outputs/read_depth_stability_v1/full
```

The full command creates `full/`; the small command creates sibling `trial/`.
Rerun the identical inference command to resume completed conditions. There
is no `--resume` flag. An interrupted condition restarts with a new attempt
file while preserving its partial evidence. Changed configuration/source/
inputs need a new experiment parent directory under the isolated output root.
Do not run concurrent writers into one experiment or edit the inference tool
while it is running.

Expected full completeness is **130 conditions, 637,858 score rows**:
24,533 sites x (24 numeric-depth conditions + two all-read controls). These
are repeated diagnostic predictions, not extra independent training examples.
The reporter refuses incomplete or changed receipts and keeps trial metrics
separate. A tiny label-free trial can have a single-class fold; undefined AUCs
are marked unavailable rather than changing the selected sites to obtain a score.
