# Training-context support for Task 2

**Task 2 preparation: this report summarises existing data0 support.** It does
not train, predict, change classifier inputs or exclude sites.

All 121,838 training sites contain 18 central DRACH motifs and every one of the
288 canonical seven-base contexts. Training read depth ranges from 20 to 991.
The seven-mer tables contain 5,475 positive and 116,363 negative labels in total.
The 18-motif counts exactly reproduce
[Member 1's supplied motif summary](../../eda/received/tables/motif_summary.csv).

Seen context is different from sufficient positive-label evidence: 56 seven-mers
have zero positive labels; 211 have fewer than 20; 77 have at least 20 examples
of each class. At the central-motif level AAACC has 11 positives, TAACA 1 and
TAACC 2. These motifs were included in training, despite sparse subgroup
evaluation support. The model shares learned parameters across contexts;
zero positives within a seven-mer does not prohibit a positive prediction.

The first run's existing input audit supports zero unseen **model-encoded**
canonical contexts among its 135,870 eligible sites, with U mapped to T.
Its distinct observed seven-mer count was not enumerated. 15,708 sites
(11.561%) have one of the three sparse-positive central motifs. This is
an input-support deduction, not a completed-prediction or accuracy result.

Use `training_7mer_support.csv` for a companion metadata join after canonicalising
sequence to uppercase and U to T. `training_motif_support.csv` supports the
central-five-base join. Preserve the required three-column prediction CSVs.
For genuinely unseen contexts in later inputs, record zero training support
and a separate unseen flag. Never silently remove them or alter thresholds.
Sites below 20 reads lie outside the observed training depth range and outside
the primary Member 4 analysis population. Retain the unchanged raw input and
all-source QC metadata; these low-coverage sites remain explicitly unscored.
The core model export covers all eligible sites only.
Sparse labels are an evidence limitation, not a calibrated uncertainty score.

From the repository root, using the pinned model environment:

```text
python -B sgnex_analysis/scripts/report_training_context_support.py
```

The command reads local cache/labels and the completed first-run audit. Use
`--skip-first-input-audit` for a training-only report, and `--output-dir` with a
fresh directory for a repeated check. Exact input and reporter fingerprints,
counts and measured timing are in `provenance.json`; `complete.json` is written
last. No complete 23-run predictions or biological conclusions are claimed.
