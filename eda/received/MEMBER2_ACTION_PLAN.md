# Member 2 action plan: turning Member 1 findings into experiments

Revision 2, 14 October 2026. Read alongside MEMBER2_AI_HANDOFF.md.

## Status and ownership

Completed: full-file quality checks, all-read site summaries, six exploratory figures, overlap checks and verification of the exact data0 gene folds. Newly added in this revision: this detailed plan and an explicit feature specification. **The follow-up analyses below have not been run. There are no new performance results.**

Member 1 can perform the descriptive follow-ups. Member 2 translates their evidence into model experiments, with Member 3 checking evaluation. This plan does not require Member 2 to complete every exploratory idea before proceeding with development on data0. Resolve the separate provenance blockers before pooling datasets.

## First: inspect what is already implemented

Inspect the current feature extraction, preprocessing, model configuration, split loading and saved results. Match the existing features against `feature_specification.csv`. The 36 mean/median/IQR/across-read-SD features listed there already exist in the supplied EDA tables; whether the current model uses them is unknown. Do not present adding an existing feature as a new improvement. Preserve current code and results for comparison.

## A. Controlled signal comparisons — highest priority

Question: do label-related differences persist among sites with comparable sequence and coverage?

Use data0 for development, and describe data1 separately as an exposed diagnostic. Start with the existing `motif_coverage_effects.csv`. Compare labels within the same central 5-mer and coverage bins (20–49, 50–99, 100–199, 200–499, 500+). Then repeat within the exact seven-base sequence where support allows. Do not silently combine sparse groups or present their unstable estimates as established effects.

For each feature/group, report class counts, distinct gene counts when available, label-specific medians and their difference. Display groups with at least 20 sites per label, retaining all groups and counts in the evidence table. This is a display convention, not proof of adequate independent sample size or a filtering rule for training. Show whether the effect direction is consistent across the existing data0 gene folds; that is a descriptive stability check, not a new independent test. If estimating uncertainty, resample genes rather than individual reads.

Expected future outputs: a comparison table and a plot contrasting pooled, motif-controlled and exact-context/coverage-controlled differences. These outputs are not included yet.

Decision for Member 2: nominate signal/context interactions that remain plausible after these comparisons. Test predictive benefit on unchanged gene folds. Do not use all-data EDA reference statistics as fitted model normalisers or call EDA-driven feature selection independent evaluation.

## B. Read-subsampling stability — highest priority

Question: how sensitive is each site summary to the number of available reads?

Use a fixed set of data0 sites with at least 100 reads. Save the selected site IDs and report representation by label, motif and coverage. If sampling sites to control cost, use seed 42 and publish the sampling rule/counts; do not choose sites based on favourable results. Keep the same sites at every depth. For each site, sample 20, 50 and 100 reads without replacement, repeating 100 times with seed 42. Reads may recur across repetitions. Document RNG/library versions and sorted input order.

Recalculate central-current median/IQR, central event-SD median and central dwell-time median. Compare each result with that site's all-read summary. Summarise median absolute deviation from the all-read reference and variation across repeats, separately by feature and label/motif where supported. Keep units separate; if scaling deviations, document the denominator and zero-denominator handling. The all-read value is a reference estimate, not ground truth.

Expected future outputs: a site/feature/depth stability table and error-versus-depth curves. These outputs are not included yet.

Decision for Member 2: identify summaries that are particularly noisy with fewer reads. Compare the current handling of reads with a proposed sampling/aggregation change on identical gene folds. Do not automatically discard lower-coverage sites. This experiment covers high-coverage source sites and finite-read sensitivity; it does not establish behaviour of genuinely low-expression sites or biological replicates.

## C. Unusual-case review

Question: are broad site summaries driven by a few extremes, broad variation or apparently separated read groups?

Begin with the three sites in the handoff and select 5–10 documented cases from `unusual_sites_review.csv`, plus ordinary sites of the same motif and similar coverage. Use raw read matrices; the compressed site summaries alone cannot reconstruct read distributions. Plot central-current distributions and scatterplots against neighbouring current and dwell measurements. Record selection rules and counts. If a site occurs in both data0 and data1, compare it without assuming the files are biological replicates.

Expected future output: a small case sheet containing site ID, original label, coverage, motif, plots, observed pattern, competing explanations, and evidence still needed. No such case sheet has been completed yet.

Decision for Member 2: consider robust summaries or a documented quality flag. Do not delete or relabel sites solely because they are unusual or a model disagrees. Apparent clusters do not identify modified molecules; technical explanations need alignment/provenance evidence.

## D. Precise candidate feature definitions

Let X be a site's n-by-9 matrix with zero-based columns. Columns 0/1/2 are minus1 dwell/event SD/current; 3/4/5 are centre; 6/7/8 are plus1. Features below are candidates, not proven improvements.

| Feature/group | Exact definition | Existing EDA output? | Training requirement |
|---|---|---|---|
| `{position}_{measurement}_mean` | Mean of the corresponding X column | Yes, all nine measurements | Any subsequent scaling uses training only |
| `{position}_{measurement}_median` | Median of that X column | Yes, all nine | Same |
| `{position}_{measurement}_iqr` | Q75 minus Q25, linear quantile interpolation | Yes, all nine | Same |
| `{position}_{measurement}_read_sd` | Population SD across reads, ddof=0 | Yes, all nine | Same; distinct from supplied event SD |
| `coverage` | Number of rows of X | Yes | Treat inclusion as an experiment |
| `log_coverage` | Natural log of 1 + coverage | No new column computed | Fixed transform; subsequent scaling training only |
| `log_centre_dwell_median` | Natural log of median(X[:,3]) | No new column computed | Require positive finite inputs; subsequent scaling training only |
| `motif` | sequence[1:6] | Yes, text category | Fit category encoding/vocabulary in training; define unknown handling |
| `sequence` | Complete seven-base context | Yes, text category | Same; may add sparsity |
| `centre_current_motif_residual` | Site central-current median minus the training-site median of that feature within its motif | No; proposed | Fit reference per training partition only; define sparse/unknown fallback before evaluation |

The CSV provides all 36 numeric feature names individually, alongside coverage and categorical/proposed features. Labels, transcript/gene identifiers, fold IDs, dataset/sample identity and start/end offsets are metadata, not input features in these proposed experiments. Preserve dataset identity for joining and auditing distinct samples.

## E. First three controlled model comparisons

Use the current pipeline as the reference, and hold eligible sites, gene folds, metric definitions and other settings fixed where practicable. Match tuning budgets if a change requires tuning. Early stopping and learned preprocessing belong inside outer-training data.

1. **Sequence use:** assess whether the current pipeline uses sequence adequately. Compare explicit sequence/signal conditioning or a training-fitted residual with the current implementation. If equivalent functionality exists, test its contribution by removing it rather than duplicating it.
2. **Read-distribution summaries:** test a missing robust-summary group, or remove an existing group to measure its contribution. Record exactly which columns changed. Use stability findings when available to motivate the choice.
3. **Coverage dependence:** compare inclusion/exclusion of coverage under the same pipeline. Evaluate subgroup counts and behaviour across coverage ranges. If the existing model already samples reads, document that before proposing a sampling change.

For each comparison retain: question; supporting observation; exact change; input/fold hashes; seed; preprocessing/tuning scope; per-fold ROC AUC and precisely defined PR metric; out-of-fold predictions; subgroup counts; runtime; result and decision. Use existing logs rather than inventing a new team-wide administration system. Report failures and trade-offs, not just improvements. Data1 remains a diagnostic; data2 is not an ordinary binary test.

## F. Dataset questions that block pooling

Obtain answers from the course release notes, source metadata or teaching team:

- Which cell line, sample/run and label assay generated data1? Are its coordinates and preprocessing compatible with data0?
- What exactly do data2 fractions represent? How were the seven groups constructed, were reads reused, and what evaluation metric is intended?
- Which transcript annotation/version maps all data1 transcripts to genes? Unmapped transcripts are not proven unseen genes.

These questions are documented, not resolved. Do not regenerate data0 folds while investigating them. After complete mapping, a data1 row from a data0 gene must inherit that gene's existing fold before any augmentation comparison.

## Communicating each result

For every new plot or experiment, state: **question → observation → possible explanation → limitation → modelling action**. Keep the original six plots and source numbers labelled as completed EDA; retain A–C as pending until actual outputs exist. Biological explanations remain hypotheses unless supporting evidence is supplied.

## Instruction for the receiving AI

Read the handoff first, then inventory actual uploaded files. Report current pipeline features versus proposed additions, missing inputs, and the first three controlled comparisons. Use the existing scripts/tables where they suffice. Request raw matrices for B/C and current model code for model experiments. Do not claim the new analyses ran just because this plan describes them. Do not claim improved performance until supported by saved results.
