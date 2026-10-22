# Published m6Anet reference: fixed benchmark plan

Recorded 22 October 2026 before reference inference. This fulfils the course
requirement to compare with m6Anet; it does not retrain the published model or
change our neural development results.

## Model, environment and input

- Official Bioconda **m6anet 2.1.0**, build `pyhdfd78af_0`, package SHA256
  `5c8d51d0f2d9041863a8e4c1e258144c16f0211bffc8b96cbb484889e4131e1e`.
- Separate Conda environment: Python 3.8.20, CPU PyTorch 1.6.0
  (`py3.8_cpu_0`). This follows the handout's Python 3.8/Conda instruction.
  Keep the existing project training environment unchanged.
- Use the published default **HCT116_RNA002** weights and its bundled
  normalization dictionary. Fingerprint installed source, assets and resolved
  packages before inference. Do not substitute a different organism/chemistry
  to obtain a better result. Do not fit normalization on course labels.
- Start from the original data0 JSONGZ, preserving all nine measured values,
  seven-mer contexts, transcript coordinates and read counts. Reconstruct the
  byte index; do not shift already-processed coordinates. Input preparation
  accepts no labels.
- Version 2.1 expects an additional bookkeeping read-ID column, which the
  course's nine-column JSON does not supply. Add a per-site **row ordinal**
  `0..n_reads-1` solely as explicitly synthetic metadata. Confirm from the
  installed loader that the model receives only the original nine features.
  These ordinals are not biological read identifiers; individual output must
  not be used for molecule tracking. Vendor source and assets remain unchanged.

## Fixed inference and checks

Use CPU, four Torch threads, random seed 2026, the official default sampling
size of 20 and **1,000 pooling iterations**. Run one small, clearly labelled
input-order pilot only to check compatibility and measure cost. Do not select
iterations, weights, seed or a model on pilot or full labels. The same fixed
settings apply to a subsequent full run. Choose the smallest valid worker
count supported by the installed official implementation for Windows; record
it explicitly in every receipt. No biological threshold is fitted here.

Implementation fixed before inference: one worker, batch size256, explicit
`spawn`, and `save_per_batch=2147483647`. The installed official release uses
`if (batch_index+1) % save_per_batch` and lacks a final flush. The large fixed
value makes each batch flush without editing vendor code; check exact site
coverage on a512-site/two-batch pilot. A separate guarded launcher seeds NumPy
at module import, including each spawned pooling child, to make the one-worker
Monte Carlo calculation reproducible. Verify two pilot runs have identical
outputs before accepting this mechanism. These are implementation checks,
not selection on labels. CPU math-library compatibility pins are MKL2020.4
and Intel OpenMP2020.3; newer MKL DLLs did not load with legacy Torch1.6.

### Computation amendment before full scoring

The first two512-site pilots completed with identical official site/read CSV
hashes, all512sites and40969reads. Their measured command wall times were
20.3665s and20.9366s; official inference alone took12.8732s and14.9646s.
No labels were loaded and no pilot performance metric was computed. Repeated
Windows pool startup at batch256 projects roughly an hour for the full input.
Before any full inference or label-based scoring, increase only the execution
batch size to **2048**, retain all other fixed settings, and check memory plus
two-batch reproducibility on the first4096input sites. This amendment is for
computation, not performance selection. Preserve the original batch256 runner
snapshot/hash and both pilot receipts. With seeded worker restarts, different
batch boundaries can change the particular Monte Carlo draws; report the
single final fixed batch2048 run, without choosing between scores. The
published network, normalization and 1000-iteration noisy-OR method are unchanged.

Before the full run, verify site uniqueness, finite nine-feature inputs,
exact feature preservation, valid offsets/counts, vocabulary eligibility and
the installed inference output schema. Report all exclusions or unsupported
contexts; never silently reduce the comparison population. Source data0
SHA256 is `622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e`.
Expected complete population is 121,838 sites. An incompatibility is a finding
to fix or report, not permission to change source measurements.

Retain input receipts, source/model/normalization hashes, exact commands,
stdout/stderr, RNG settings and measured wall time, CPU time and sampled peak
memory. Preparation can resume from verified checkpoints. Official inference
has no optimizer/training checkpoints; retain completed output and run receipts
and never describe a partial run as complete. Keep large inputs, site scores,
environment and weights outside public Git history.

## Scoring and interpretation

Extract the published **site modification probability** from actual output;
do not substitute modification ratio. Align by transcript/site against data0
and the exact shared five gene folds. Use the unchanged shared evaluator and
report mean-fold ROC AUC, trapezoidal PR AUC and their mean S. AP, pooled
metrics and a descriptive 0.5 confusion matrix are supplementary. A common
population comparison is needed if eligibility differs; retain counts and
full-population results separately. No data1/data2 fitting or model selection.

**This is an off-the-shelf published-model reference, not gene-held-out
cross-validation training.** Its pretrained HCT116 model used SG-NEx HCT116
replicate 2/run 1 (PRJEB44348). Exact overlap with course data0 is unconfirmed;
potential pretraining overlap must accompany comparisons. Attaching our fold
IDs for scoring cannot make this an independent test. A reference result does
not alter the predeclared development selection rule for Elgin and Samuel.

Primary sources: [course handout](../../handout_project2_RNAModifications.html),
[official inference guide](https://m6anet.readthedocs.io/en/latest/quickstart.html),
[official source](https://github.com/GoekeLab/m6anet),
[paper](https://doi.org/10.1038/s41592-022-01666-1).
