# Completed required references — 22 October 2026

Actual data0 predictions were checked against the unchanged shared evaluator.
All methods cover 121,838 sites, 5,475 positives and 3,852 genes. Primary values below
are the **unweighted mean of five fold metrics**, not pooled curve areas.

| Pipeline | Mean ROC AUC | Mean trapezoidal PR AUC | Mean S |
|---|---:|---:|---:|
| Logistic regression | 0.804056 | 0.149129 | 0.476592 |
| Samuel LightGBM | 0.921897 | 0.498996 | 0.710446 |
| Elgin cap128 control | 0.931828 | 0.505601 | 0.718715 |
| Published m6Anet | 0.932176 | 0.503257 | 0.717717 |

**The published m6Anet row is a pretrained reference, not gene-held-out
refitting.** Its HCT116 model used SG-NEx HCT116 replicate 2/run 1; exact overlap with
course data0 remains unresolved. Our fold IDs only stratify its scores.
Consequently, this table cannot establish independent superiority over that
published model. The Elgin row is the existing cap128 control; a separate
audited external candidate has not yet been integrated or nominated here.

The simple baseline was fitted afresh on four gene groups per round using
18 raw float64 read means/population SDs, training-only scaling and fixed
balanced-C1 L2 logistic regression. Its historical recipe selection remains
disclosed; no new search was conducted. Models, coefficients/scalers, exact
split audits, OOF scores, logs and resumable completed folds remain local.

Published m6Anet 2.1.0 uses its unmodified HCT116_RNA002 weights and normalization,
CPU/four Torch threads, seed 2026, 1,000 sampling iterations, batch 2048 and one
spawned worker. Module-level seeding makes each pool restart deterministic.
The original nine signals are unchanged; the tenth column is a local row
ordinal used only for output bookkeeping. A fixed large save_per_batch
avoids the vendor's missing-final-batch bug. Both final two-batch pilots had
identical official CSV hashes. No labels were used in preparation/inference.

![Pooled ROC and PR curves](reference_curves.png)

The figure pools site scores; its legend AUCs therefore need not equal the
mean-fold table. Dashed teal is the pretrained reference with possible overlap.
The PR chance line equals the 4.494% positive prevalence. Do not read a site
probability as a measured modified-molecule fraction or a different RNA mark.

## Measured computation

- Logistic replay invocation: 93.393s wall, 90.859s process CPU, 362.72MiB sampled process RSS; 5fresh fits; feature cache reused=False. Includes applicable preparation, verification and scoring.
- Published reference command: 1303.367s wall, 1070.344s sampled process-tree CPU lower bound, 761.52MiB sampled simultaneous tree RSS; includes preflight, inference and output audit, excludes earlier format preparation and later scoring.

These scopes differ; they are not a matched training-speed comparison. CPU
sampling can miss work after the last observation of short-lived workers.
Do not add overlapping parent and process-tree timers. Interrupted preparation
and pilot/setup costs are retained separately and are not included in these
two command totals. Detailed fingerprints/counts are in `summary.json`.

## Reproduce

From the repository root, first obtain the pinned local data0 inputs. Follow
[the baseline commands](../simple_baseline/README.md) and
[the m6Anet setup/preparation/inference/scoring commands](../m6anet_reference/README.md).
Large inputs, environments, weights, checkpoints and site predictions are ignored.
Then, from the main comparison environment:

```text
python -B model_evaluation/report_benchmarks.py
```

Windows execution is checked; clean Ubuntu reproduction remains pending.
This finishes the two required reference comparisons, not the final saved
submission model, data1 diagnostic, new-test predictions or SG-NEx analysis.
Repeated development and possible pretraining overlap limit generalisation
claims. No final threshold or probability calibrator was fitted here.
