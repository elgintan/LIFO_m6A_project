# Member 1 data-exploration package

Start with `Member1_Data_Exploration.html` for the illustrated reading copy, or `MEMBER1_CONTEXT_2026-10-13.md` for the full editable handoff. This is background analysis for Member 1, not the team's final five-page report.

## Completed work

All three supplied JSON/label pairs were fully parsed. Every read contributed to the site summaries. There was no training, model scoring, outlier exclusion, relabelling, regenerated split or new test set. The only plot sampling is the 5,000-point paired-site scatter (seed 42); its associated counts and correlations use all pairs.

The raw signal datasets are not duplicated in this package. Keep the original `Team_Project` directory. Its input hashes are in `tables/source_manifest.json`.

## Run the analysis

Required packages: Python 3, NumPy, pandas, SciPy and matplotlib. Exact versions used are recorded in `requirements-used.txt` and `tables/runtime.json`. No specialised machine-learning library is needed.

From this extracted package's directory, use your own Python executable:

```bash
python scripts/extract_sites.py --data-root /path/to/Team_Project --out .
python scripts/analyse_sites.py --out .
python scripts/render_reading_copy.py --root .
```

Expected source layout:

```text
Team_Project/data0/dataset0.json.gz
Team_Project/data0/data.info.labelled
Team_Project/data1/dataset1.json.gz
Team_Project/data1/data.info
Team_Project/data2/dataset2.json.gz
Team_Project/data2/data.info
```

Re-running replaces the derived EDA tables, figures and HTML in the selected output directory. It does not write to the input datasets. Assertions reject malformed matrices, nonfinite values, duplicate site keys and incomplete joins. Further numeric and sequence checks are recorded in `inventory.json`.

Verify the exact existing folds, without generating anything:

```bash
python shared_folds/create_shared_folds.py --labels /path/to/Team_Project/data0/data.info.labelled --output-dir shared_folds --verify-only
```

Expected CSV SHA256: `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.

## Table guide

| File or column | Meaning |
|---|---|
| `inventory.json` | Full-file record counts, join checks, coverage quantiles, sequence checks and numerical ranges. |
| `dataN_site_summaries.csv.gz` | One row per site; all reads used; supplied labels/metadata retained. |
| `minus1`, `centre`, `plus1` | Event position relative to the candidate site. |
| `dwell`, `event_sd`, `current` | The three supplied event features. |
| `_mean`, `_median`, `_iqr`, `_read_sd` | Aggregation of that supplied feature over reads at a site. IQR is Q75−Q25 using NumPy's default linear interpolation. Read SD uses ddof=0. |
| `coverage` | Actual number of read rows for the site; not a count of biological replicates. |
| `ordered_signal_sha256` | Hash of the numeric read matrix, little-endian float64 in supplied row order. Equality can detect identical full matrices. Inequality cannot exclude partial reuse or different orderings. |
| `within_motif_effects.csv` | Label-1 minus label-0 median of site medians, plus the pooled site IQR and scaled effect, within each motif/dataset. |
| `motif_coverage_effects.csv` | The same raw median differences within motif and coverage bins, with class counts. No inferential tests. |
| `label_signal_summary.csv` | Q25/median/Q75 across sites within each label, for coverage and selected feature summaries. |
| `coverage_label_counts.csv` | Counts by binary label and coverage bin. |
| `metadata_overlap.json` | Site/transcript overlap and data1 gene-mapping coverage from data0. Unmapped does not mean unseen gene. |
| `signal_overlap.json` | Paired-site sequence/full-matrix equality checks and descriptive correlations. |
| `paired_label_counts.csv` | Observed label concordance, not prediction performance. |
| `discordant_sites.csv` | Shared IDs with opposite supplied labels; original labels retained. |
| `data2_template_check.csv` | Number of labels and sequences per matched numeric position. |
| `data2_matched_deltas.csv` | Differences versus the label-0 row at each matched position, then quartiles over the 189 positions. |
| `unusual_sites_review.csv` | Maximum central-current and central-dwell IQR per dataset/motif; descriptive review candidates, not verified faults. |

## Plot conventions and interpretation

Each site has equal weight. No pooled read-level significance test is used. Label groups remain imbalanced. The heatmap hides groups with fewer than 20 sites in either class, while the complete effects remain in the tables. Heatmap colour is capped at ±1.5 IQR units. Data2 bands are IQRs across matched positions, not confidence intervals. Current and dwell axes use the numbers as stored in the inputs.

Do not use exploratory tables calculated across all data as fitted training transformations. Refit every learned normaliser, feature-selection step, class weight, or calibration model within training partitions.

## Handoff boundaries

Member 1 owns the data-quality and interpretation findings. Members 2 and 3 decide and test candidate modelling changes. Member 4 verifies the full SG-NEx sample scope and application findings. Member 5 owns the researcher interface and integration support. No messages, public repository changes, cloud jobs or submissions were sent or initiated here.

The context file separates verified findings, hypotheses, proposed splits and pending work. It includes report wording and references. Read those limitations before reusing a figure or claim.
