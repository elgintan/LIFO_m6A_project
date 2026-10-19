# Historical reference checked on 19 October 2026

This is the selected October 7 neural model's saved data0 out-of-fold
predictions, checked against the common evaluation contract. No new fitting,
inference, data1 evaluation or SG-NEx prediction occurred in this reference
check. The generated files listed below are retained **locally and ignored
by Git**; a public clone contains this explanation and the exporter code.

- `data0_oof.csv`: 121,838 original score strings in original order, with the
  immutable `fold_id` added. These are not final-model submission predictions.
- `reference_receipt.json`: exporter/input/model fingerprints, completed-fit
  checks, population counts and provenance limitations.
- `data0_cv_metrics.json`: actual output of the team's shared scorer.

Mean across the five folds:

| Metric | Reproduced historical value |
|---|---:|
| ROC AUC | 0.9330102728 |
| Trapezoidal PR AUC | 0.5038813521 |
| Combined score | 0.7184458125 |

The exact values remain in the JSON. These are development results: the
original architecture was selected using data0 results. A new feature-effect
claim also needs controlled modelling settings, not just matching folds.

The exporter verifies source/raw-data/label/cache/fold fingerprints, candidate
selection records, agreement between each saved fold prediction and combined
OOF output, and completed refit configuration/count/epoch/model hashes. Hashes
and logs corroborate provenance; they do not independently prove every action
in a training process. Original raw inputs and checkpoints are kept locally.

See [the first-step guide](../FIRST_STEPS.md) for the exact checking commands.
The [new implementation](../context_reference_v1/README.md) has passed small
software/data0 checks; its full performance comparison remains pending.
