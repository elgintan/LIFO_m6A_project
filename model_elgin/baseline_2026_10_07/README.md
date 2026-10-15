# Archived neural starting point — 7 October 2026

This is retained evidence from the completed earlier local run, copied into
the team repository on 15 October. The weights, training core and results are
unchanged. One personal directory literal in the archived report generator was
replaced with a portable placeholder, explicitly recorded in the source receipt.
New documentation is not a new
training run. Original full local checkpoints/caches/audits remain outside this
clean repository. `../../SOURCE_RECEIPT.json` at repository root records copies.

Contents: `code/`, `artifact/final_model.pt`, `examples/`, `metrics/`,
`predictions/`, `figures/`, `training_history.json` and `training.log`.

| Historical measure | Actual value |
|---|---:|
| Data0 development mean ROC AUC | 0.9330102728024183 |
| Data0 development mean trapezoidal PR AUC | 0.5038813521143567 |
| Frozen data1 ROC AUC | 0.8278541802156597 |
| Frozen data1 trapezoidal PR AUC | 0.3813786812981725 |
| Frozen data1 mean ROC/PR | 0.6046164307569161 |

The final model used all 121,838 data0 sites for 19 fixed epochs. Model SHA256:
`5f543342a8fde2ae25e44c364c342a55f1b7dc587cb4e88cfb00fa592fddc5f9`.
The three CSVs are predictions from that same model. Data0 final predictions
are in-sample, not the held-out development result. The small example contains
ten real sites and historical predictions, not an independent performance test.

Architecture selection used development folds. Data1 was previously exposed
and has overlapping identifiers. Exact raw LightGBM probabilities were absent;
its historical approximately 0.590 score was teammate-reported and rounded.
No blind independent or universal-superiority claim follows.

## Using the snapshot

The historical source is preserved for inspection; some trainer/orchestrator
paths assume its original surrounding layout. Do not launch a new training
run from these archived commands while the next methodology is pending. The
new candidate will get explicit portable data/split arguments when developed.

The prediction script has explicit paths. With a compatible environment and
from repository root, the small example can be run as:

```bash
python model_elgin/baseline_2026_10_07/code/predict.py --input model_elgin/baseline_2026_10_07/examples/input_10_sites.json --model model_elgin/baseline_2026_10_07/artifact/final_model.pt --output model_elgin/outputs/baseline_example.csv --threads 4 --batch-size 32
```

This copied layout has not yet undergone a fresh prediction or Ubuntu check.
The original local artifact had a successful fresh-process CPU example check.
Do not warm-start new data0 partition evaluations from these all-data0 weights.
