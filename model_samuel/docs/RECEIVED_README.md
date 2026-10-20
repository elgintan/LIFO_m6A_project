# Samuel's model: LightGBM on sequence-relative read summaries

Owner: Samuel (Member 3). Built 18 October 2026 under `model_evaluation/SHARED_RULES.md`.

**Status:** trained, frozen and scored with the official `model_evaluation/evaluate.py`
(Python 3.12.15, numpy 2.5.3, scikit-learn 1.9.1, as pinned). Outputs:
`results/data0_cv_metrics.json` and `results/data1_metrics.json`. The fold file passed the
shared `--verify-only` check.

## Results

| Measure | data0, mean of 5 gene folds (sample SD) | data1 (frozen model, HEK293T transfer) |
|---|---:|---:|
| ROC AUC | 0.9219 (0.0059) | 0.8218 |
| Trapezoidal PR AUC | 0.4990 (0.0176) | 0.3829 |
| Average precision | 0.4996 (0.0175) | 0.3831 |
| S = (ROC AUC + PR AUC) / 2 | **0.7104** (0.0105) | **0.6023** |

Per fold, S ranges from 0.6997 to 0.7224. Repeating the five-fold run with seeds 7 and
2026 gives S 0.7093 and 0.7083 (`results/seed_check/`), so seed-to-seed variation is about
0.002, smaller than the fold-to-fold SD of 0.0105.

For reference, Elgin's archived 7 October neural model reports data0 ROC AUC 0.9330 and
PR AUC 0.5039 (S about 0.718), and data1 S 0.6046. The two candidates are within about
0.01 on every measure; neither is a fresh run under identical conditions yet.

## Method

1. **Site features.** For each site, the mean, population SD and 10th, 25th, 50th, 75th
   and 90th percentiles across reads of all 9 measurements (dwell time, signal SD, mean
   current at positions -1, 0, +1): 63 numbers. Read count is not a feature.
2. **Sequence-relative signal.** Each of the 63 numbers is replaced by its difference from
   the training-set average for the site's 7-mer. A 7-mer with fewer than 50 training sites
   falls back to its central 5-mer, then to the global training mean. In each fold the
   averages come from the four training folds only, without labels; between 59 and 100
   assessed sites per fold used the 5-mer fallback. Test files are never standardised
   against themselves.
3. **Sequence.** The 7 bases as categorical features.
4. **Classifier.** LightGBM, 1,500 trees, learning rate 0.02, 31 leaves, minimum 50 sites
   per leaf, L2 penalty 5, 80% row and column subsampling, seed 42, log loss. No class
   weights, no early stopping, no hyperparameter search in this run.
5. **Evaluation.** Exact shared folds (SHA256 checked by `train.py`). For fold f, the
   7-mer averages and the model are fitted on folds other than f, then fold f is scored.
   The same configuration is then fitted afresh on all of data0, saved and hashed
   (`artifact/model_card.json`) before data1 was scored.

**Why these choices** (Member 1's findings and our own exploration):

- The 7-mer explains about 98% of between-site variation in central current, and pooled
  comparisons can reverse within-motif signal directions. Measuring signal relative to
  the sequence context addresses both.
- Modified sites differ in the spread of their reads, not only the average, and the
  synthetic data2 shows the signal tracks the modified fraction. Quantiles capture spread.
- Sparse 7-mers need a fallback, so the 50-site minimum with 5-mer and global fallbacks.

## How this configuration was chosen (disclosure)

- The LightGBM settings were selected on 5 October from five configurations by data0
  cross-validation on these same folds, using the earlier 18 features.
- The feature set was chosen on 12 October from five variants
  (`../experiments/feature_ablation/`, in Samuel's local project). That comparison also
  printed data1 scores, so **data1 was seen during development**. The chosen variant also
  had the best data0 S of the five, so the choice does not depend on data1, but data1 is
  not an untouched test for this model.
- A variant that standardised each dataset against itself was dropped: it breaks on data2
  (scores collapse when most sites are modified) and the shared rules forbid it.

## Where it improves and where it does not

Compared with the 5 October 18-feature LightGBM on the same folds (`results/subgroups.csv`):

- Better in 12 of the 15 motifs with at least 20 positives, by ROC AUC; equal in AGACT. The largest gains
  are in TAACT (0.751 to 0.832), TGACA (0.721 to 0.793) and GAACC (0.757 to 0.806).
- Still weak where positives are rare: AAACA ROC AUC 0.648, TGACC 0.604; AAACA and AGACC
  are slightly worse than before. None of the modified sites in GAACA, GAACC or TAACT
  reaches a score of 0.5.
- Better at every coverage level, but sites with more than 200 reads remain the weakest
  stratum (ROC AUC 0.857 against 0.91 to 0.94 elsewhere). Not yet explained.
- data2 (descriptive only, fractional labels): mean score rises from 0.027 at fraction 0
  to about 0.27 at fractions 0.95 and 1, Spearman correlation 0.316. Scores are not
  modified-fraction estimates.

## Run it

From this folder, with Python 3.11 or 3.12. Prediction needs only
`requirements-predict.txt`; training and diagnostics need `requirements.txt`.
On Ubuntu, `pip install -r requirements-predict.txt` should suffice (LightGBM also needs
the system OpenMP library, `sudo apt install libgomp1`, if missing). On macOS, install
LightGBM from conda-forge, since pip's build needs a separate OpenMP library.

    # Predict any m6Anet-format data.json or .json.gz; no labels needed
    python code/predict.py --input examples/input_10_sites.json --output predictions.csv

    # Retrain (about 2 minutes on 4 threads; peak memory about 950 MB)
    python code/train.py --data0 PATH/dataset0.json.gz --labels PATH/data.info.labelled \
        --folds ../eda/received/shared_folds/data0_folds.csv --out outputs --model-dir artifact

The example is 10 real sites from the public SG-NEx sample
`SGNex_Hct116_directRNA_replicate3_run4`; `examples/predictions.csv` is the expected output.

## Files

| Path | Content |
|---|---|
| `code/features.py` | JSON parsing, site summaries, 7-mer baseline with fallback |
| `code/train.py` | five-fold out-of-fold run and the frozen all-data0 fit |
| `code/predict.py` | prediction script; checks the model hashes first |
| `code/score_local.py` | local mirror of the shared scorer (gives identical numbers) |
| `code/diagnostics.py` | subgroup comparison and data2 summary |
| `artifact/` | `model.txt`, `kmer_baseline.csv`, `model_card.json` (hashes, versions, timings) |
| `outputs/` | `data0_oof.csv` (with fold_id), `data1_predictions.csv`, `data2_predictions.csv` |
| `results/` | official metrics JSON, local-mirror JSON, repeat-seed metrics, subgroup table, data2 summary |

## Limitations

- data1 was seen during feature selection (above), and 74% of its sites are also in data0.
- Computation was measured on one macOS laptop only (Apple silicon, 4 threads).
- `predict.py` reproduced `examples/predictions.csv` byte for byte in a fresh, minimal
  conda environment (`requirements-predict.txt`), run from another folder. It has not yet
  been run on Ubuntu.
- The trapezoidal PR AUC in S rewards tied scores: a constant prediction gets 0.536 on
  data1 by this measure. It does not affect this model (PR AUC and AP agree to 0.001), but
  it can flatter coarse-scoring models. Raised for discussion, not changed.

## Still to do

- Run `predict.py` on a clean Ubuntu machine (the student evaluation uses AWS Ubuntu).
