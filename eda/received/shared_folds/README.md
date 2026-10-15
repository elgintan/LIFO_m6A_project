# LIFO: shared data0 five-fold gene split

Created locally on Windows on 5 October 2026 for all five candidate models.
This is a metadata assignment, not a trained model or a performance result.
The five-fold and seed settings are team conventions.

## What a fold means

A fold is one group held aside for validation. For round 0, train on folds
1, 2, 3 and 4, and validate on fold 0. Repeat with each fold held aside once.
Every site receives one out-of-fold prediction from a model that was not
trained on that site's gene. All transcripts and sites from a gene stay
in one fold. Class stratification attempts to preserve positive prevalence;
fold sizes need not be identical because genes remain intact.

Generation uses `StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=42)`, grouped by `gene_id`, after sorting by transcript ID and
numeric position. Only data0/data.info.labelled is used, with no data1/data2.

## Files to share

Send `LIFO_shared_folds.zip` and the general `TEAM_SHARED_AI_PROMPT.md`.
Extract the ZIP into the project folder alongside `data0`. The ZIP contains:

- `shared_folds/data0_folds.csv`: actual assignments; use this exact file.
- `shared_folds/data0_folds_metadata.json`: source/artifact hashes, settings,
  generating software versions, counts and completed validation checks.
- `shared_folds/data0_fold_summary.csv`: train/validation counts per round.
- `shared_folds/create_shared_folds.py`: generation and read-only verification.
- `shared_folds/fold_generation_requirements.txt`: generation dependencies
  for audits/recreation; not a full model requirements file.
- `shared_folds/README.md`: these instructions.

The CSV header is exactly:

```text
transcript_id,transcript_position,gene_id,fold_id
```

`fold_id` is 0 through 4. Labels stay in each member's data0 metadata.
Gene IDs and fold IDs are metadata, never predictive features.

## Verified counts

All 121,838 unique data0 metadata sites, 5,333 transcripts and 3,852 genes
are assigned. There are 5,475 positives (4.4937%).

| Held-out fold | Validation sites | Genes | Positive sites | Positive % |
|---|---:|---:|---:|---:|
| 0 | 24,358 | 775 | 1,090 | 4.4749 |
| 1 | 24,371 | 770 | 1,097 | 4.5013 |
| 2 | 24,387 | 768 | 1,105 | 4.5311 |
| 3 | 24,378 | 772 | 1,100 | 4.5123 |
| 4 | 24,344 | 767 | 1,083 | 4.4487 |

Checks: complete site coverage, no duplicate keys, correct gene IDs, all
five fold IDs, every gene in exactly one fold, zero training/validation
gene overlap and both classes in every training and validation partition.

CSV SHA256 fingerprint:

```text
986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0
```

A fingerprint checks that file bytes have not changed. Record it in your
experiment metadata. Do not resave in Excel or independently regenerate
the split with seed 42.

## Teammate verification

From your project folder, using your own Python executable:

```text
python shared_folds/create_shared_folds.py --labels data0/data.info.labelled --output-dir shared_folds --verify-only
```

Use `python3` or your environment's Python if appropriate for your OS.
Verification uses Python's standard library only: no scikit-learn install,
regeneration, model training or file writing. It checks local metadata
contents, received file hashes, site coverage, genes and class counts.
Label-file row order/line-ending changes are accepted when sorted records
match exactly. Fold-file byte changes are rejected.

Expected output includes the table above and:

```text
PASS: complete unique site coverage, five folds, no gene leakage, both classes.
No model has been trained.
```

Give your AI agent this note together with the general shared prompt:

> Use shared_folds/data0_folds.csv for our common five-fold data0 validation.
> First verify it against my data0/data.info.labelled with --verify-only.
> Join by BOTH transcript_id and numeric transcript_position, with unique
> and complete coverage checks. For round k, validation is fold_id == k and
> training is fold_id != k; run rounds 0,1,2,3,4. Do not regenerate or change
> assignments. Fit preprocessing, weighting and calibration using training
> data only; inner calibration/early-stopping splits must keep genes separate.
> Save per-fold metrics and out-of-fold probabilities. Tune within data0,
> then refit on all data0 and evaluate the frozen candidate on data1.
> Follow our feature, scoring, cost and output standards. Record the CSV hash.

Report verification failures or signal preparation defects. Do not silently
drop unmatched sites, substitute transcript groups, resplit after filtering,
or select a seed based on model scores.

## Elgin's PowerShell check

From `Team_Project_export/svm`:

```powershell
& .\.venv\Scripts\python.exe ..\shared_folds\create_shared_folds.py --labels ..\data0\data.info.labelled --output-dir ..\shared_folds --verify-only
```

`--labels` locates the data0 metadata. `--output-dir` locates the shared files;
in verification mode it does not write. `--verify-only` prevents regeneration.

## Evidence and limits

Generation: Python 3.12.14, scikit-learn 1.9.1, NumPy 2.5.3, SciPy 1.18.1,
joblib 1.6.0, threadpoolctl 3.7.0. Consuming the frozen CSV does not require
matching generating libraries. Pin model runtime dependencies separately.
Windows creation/verification were tested; an Ubuntu run has not occurred.

This manifest covers metadata sites. Full signal-record quality validation
is still pending. Eligibility defects require a documented team-wide rule
before comparison. No model training or performance scores exist yet.

After CV tuning, final fitting uses all eligible data0. The same artifact
predicts datasets 0, 1 and 2. Final-model data0 predictions are in-sample,
separate from out-of-fold results. data1 is candidate selection data and
shares site IDs with data0; data2 binary scoring remains unresolved.

References: `../TEAM_SHARED_AI_PROMPT.md` and the
[official splitter documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).

AI-use evidence: Codex wrote the generator/instructions, ran generation and
checked outputs. These are assistant-checked until a member verifies their
copy. No Canvas submission, external messages or Ubuntu test were performed.
