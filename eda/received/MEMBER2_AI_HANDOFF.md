# DSA4262: Member 1 → Member 2 AI handoff

Revision 2 — updated 14 October 2026. Summarises the Member 1 analysis completed on 13 October 2026.

## Read this first: instructions for the receiving AI

You are helping **Member 2 with model development and training**, working with Member 3 on evaluation. Use the findings below to propose controlled experiments. Explain unfamiliar concepts simply. Keep the model family open and inspect the team's current code before suggesting changes already implemented.

This file is self-contained for understanding the findings and recommended next steps. It does **not** contain raw data, fold assignments, code, figures or trained models. Do not assume you can access the previous AI conversation or files merely because they are named here. Obtain missing computational inputs before running experiments. Treat the numbers below as findings documented by Member 1, not checks you have independently performed.

**Status:** all three supplied datasets underwent full signal/metadata exploration. No model was trained, evaluated or selected in that analysis. No prediction files or model-performance claims were used. Feature improvements and alternative splits below remain proposals. Preserve the distinction between observations, hypotheses and completed modelling results.

**Immediate recommendation:** retain the exact shared data0 gene folds for development; use data1 as an already-exposed diagnostic dataset; keep data2 separate until its fractional labels are explained. Do not silently pool all three files.

## 1. Project and role boundaries

The team predicts site-level m6A RNA modification from nanopore direct RNA sequencing. Member 1 owns data exploration and biological context; Member 2 owns model development/training; Member 3 checks evaluation and robustness; Member 4 owns SG-NEx application/biology; Member 5 owns interactive visualisation and integration support.

The supplied handout requires a simple-baseline and m6Anet comparison, ROC AUC and PR AUC assessment, separate training/prediction scripts, reproducible public code with a small prediction example runnable on AWS Ubuntu, and application to all required SG-NEx direct-RNA datasets. The report is limited to five pages excluding permitted front matter/references and includes AI-use/error-verification documentation. The supplied deadline is 28 October 2026, 23:59 Singapore time; check later announcements. These requirements come from the earlier handout inspection, not a new announcement check.

## 2. Inputs and verified inventory

Each JSON line is one `(transcript_id, transcript_position)` site, its seven-base sequence, and an `n_reads × 9` matrix. Feature order is:

| Read-vector columns, counted from 1 | Position | Feature order |
|---|---|---|
| 1–3 | −1 neighbour | Dwell time, event current SD, mean current |
| 4–6 | Centre | Dwell time, event current SD, mean current |
| 7–9 | +1 neighbour | Dwell time, event current SD, mean current |

These are event summaries, not raw signal waveforms. Central motif = `sequence[1:6]`. Every site already has a DRACH motif: D=A/G/T, R=A/G, H=A/C/T. Motif identity and flanking bases can vary; DRACH presence itself cannot discriminate these sites.

| Property | data0 | data1 | data2 |
|---|---:|---:|---:|
| Sites | 121,838 | 90,810 | 1,323 |
| Transcript IDs | 5,333 | 4,451 | 7 anonymous IDs |
| Gene IDs supplied | 3,852 | None | None |
| Labels | Binary | Binary | Seven fractional groups |
| Positive sites | 5,475 (4.49%) | 6,593 (7.26%) | 189 rows per label group |
| Coverage median | 47 | 40 | 814 |
| Coverage Q25–Q75 | 32–84 | 27–77 | 440–1,269.5 |
| Coverage range | 20–991 | 20–994 | 26–3,438 |
| Distinct central 5-mers / full 7-mers | 18 / 288 | 18 / 288 | 18 / 139 |

Across 213,971 sites and 20,106,998 site-read entries, all JSON/metadata joins were complete and unique; every read had nine finite, strictly positive measurements; all sequences passed the seven-base/DRACH checks. data1/data2 `n_reads` matched matrix lengths. Site-read entries are not unique molecules: the same molecule may cover multiple positions, and read IDs are unavailable.

The handout identifies the training data as HCT116. data1/data2 sample identity, chemistry, preparation and construction are not established by the supplied files. Structural checks cannot verify alignment accuracy, labels or biological independence.

Binary labels are site-level m6ACE-seq calls. They are not per-read labels. A positive site need not have every molecule modified; label 0 does not prove every molecule is unmodified. A site probability is not automatically modification stoichiometry. Supplied event SD and across-read feature spread are different quantities. Do not use IDs, folds or processing offsets as predictive features; `start/end` are not verified gene-region annotations.

## 3. Findings that should guide model experiments

### Sequence conditioning is the first priority

**Observed:** GGACT had the highest positive-label proportion: 1,440/6,376 (22.58%) in data0 and 1,186/5,415 (21.90%) in data1. Some data0 motifs had very few positives: TAACA 1/4,695, TAACC 2/2,966, AAACC 11/6,502.

For each feature, Member 1 first summarised all reads within each site, then compared sites with equal weight.

| Pooled central feature | data0: label 0 → 1 | data1: label 0 → 1 |
|---|---:|---:|
| Median of site median current | 114 → 118 | 116 → 118 |
| Median of site median event SD | 4.30 → 4.66 | 4.47 → 4.72 |
| Median of within-site current IQR | 3.50 → 4.00 | 3.25 → 4.00 |

However, among motifs with at least 20 sites per label, central current was **lower** for label 1 in 11/15 data0 motifs and 9/17 data1 motifs. Central event SD was lower in 14/15 and 17/17. Within adequately supported motif-by-coverage strata, current was lower in 33/43 data0 strata and 34/58 data1 strata.

**Implication:** pooled comparisons mix sequence compositions. There is no supported universal rule that modification increases current. Test sequence/signal interactions and robust distribution summaries. Sparse motif estimates need shared information or fallbacks. These are descriptive associations; biology, candidate selection and assay effects remain competing explanations.

### Coverage may provide a dataset-specific shortcut

**Observed:** median coverage for labels 0/1 was 47/48 in data0 but 39/47 in data1. data1 positive prevalence rose from 6.28% at 20–49 reads to 10.63% at 500+ reads. The corresponding data0 values were 4.44% and 4.32%, without the same monotonic pattern.

**Implication:** compare models with and without coverage. Test read-subsampling sensitivity. Coverage may reflect abundance, assay detection or processing and affects estimation precision; it does not establish a causal modification effect. No supplied sites have fewer than 20 reads, so behaviour below that depth is unknown. Missing sites are not negatives.

### Unusual distributions require investigation

Examples of large central-current IQR, all label 0:

| Dataset / transcript / position | Reads | IQR | Typical motif IQR in that dataset |
|---|---:|---:|---:|
| data0 / ENST00000592107 / 370 | 28 | 17.75 | 5.00 |
| data0 / ENST00000369075 / 3059 | 29 | 17.00 | 2.65 |
| data1 / ENST00000591247 / 1166 | 23 | 18.55 | 2.60 |

These are mechanically selected broad-spread cases, not model errors. Low coverage, mixed read populations, technical issues and valid biology are hypotheses. No cases were removed or relabelled. Inspect per-read distributions alongside ordinary same-motif, similar-coverage sites before deciding on a quality rule. Broad spread alone does not prove bimodality or modification.

## 4. Dataset overlap and data2: essential split constraints

**data0/data1:** 67,320 site IDs overlap, covering 55.25% of data0 and 74.13% of data1. All paired sequences match. No complete ordered signal matrix is identical, but partial read reuse/common source material was not ruled out.

| data0 label | data1 = 0 | data1 = 1 |
|---|---:|---:|
| 0 | 61,312 | 2,717 |
| 1 | 1,155 | 2,136 |

Thus 3,872 shared sites (5.75%) have different labels. This table compares observed labels, not predictions. Different conditions, assay variation or preparation/annotation mismatch could explain disagreement; provenance is needed. Do not majority-vote or relabel these sites to make them agree.

data1 has 23,490 new site IDs, but these are not necessarily new genes. Mapping through data0 resolves **75,673 data1 sites across 2,508 known genes**. Another **15,137 sites on 1,019 transcripts** lack a gene mapping. Unmapped means unknown, not proven unseen. Obtain the version-matched annotation before a pooled gene split.

**data2:** `tx_id_0` through `tx_id_6` have fixed labels `1, 0.95, 0.75, 0.70, 0.50, 0.25, 0`, respectively. Each has 189 rows at positions `0, 10, …, 1880`. Every matching position has the same 7-mer across all seven groups. This gives 189 repeated positional templates and 139 distinct 7-mers.

Relative to the label-0 row at the same position, median central-current differences across templates are −0.6, −1.9, −2.5, −2.9, −3.0 and −3.0 at labels 0.25, 0.50, 0.70, 0.75, 0.95 and 1. This is consistent with a matched-condition/mixture design, but that interpretation is **unconfirmed**.

Do not round fractional labels, silently drop intermediate groups, use transcript IDs as predictors, or compute ordinary binary ROC/PR AUC across all data2 rows. Do not equate fractions with modification rates until the official semantics are known. The 1,323 rows are not independent biological replicates. A future template split must keep related groups together and account for source reuse; matching positions alone does not establish full independence.

## 5. Recommended development and testing design

| Dataset / design | Recommended use |
|---|---|
| data0 | Development on the exact existing five gene folds. Train on four, validate on one; repeat for k=0…4. Prior tuning means these are development scores, not an untouched test. |
| data1 | Diagnostic evaluation after freezing choices. Report shared-site/new-site strata and gene-overlap limitations. Already exposed historically; do not describe it as blind. |
| data2 | Separate descriptive stress test until labels and intended metrics are clarified. Not the sole ordinary binary test for training on data0+data1. |
| Future official/eligible external data | Potential independent test only if kept out of model selection and verified for appropriate provenance/overlap. None was created by Member 1. |

**Reject random two-thirds/one-third splits within each file:** they distribute related genes/sites/templates across training and testing. A two-thirds/one-third global gene split could be valid with full mapping, but would be a new exploratory design, would replace the team convention and cannot undo prior exposure.

**If adding data1 later:** first confirm sample/assay/reference compatibility and resolve gene mappings. Preserve data0 gene assignments. Every data1 row from a data0 gene inherits that gene's fold. Assign genuinely additional genes once using a documented deterministic five-fold extension, seed 42; export one shared manifest. For round k, exclude all fold-k genes from both datasets' training rows. Compare data0-only versus augmented training on identical data0 validation sites, and report data1 separately. Keep distinct samples and their original labels distinct. Do not substitute transcript grouping for missing gene mapping. No extension or pooled training has been performed.

## 6. Shared implementation settings

- **Use the exact file:** `shared_folds/data0_folds.csv`. Do not independently regenerate it, even with seed 42. Join on transcript ID plus numeric position with unique/complete matches.
- **Verified SHA256:** `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
- **Existing design:** 5 folds, IDs 0–4, grouped by gene; original generation seed 42. All 121,838 sites assigned; no gene crosses folds; both classes appear in every partition.
- **Verification command**, from a project directory containing `data0/` and `shared_folds/`:

```bash
python shared_folds/create_shared_folds.py --labels data0/data.info.labelled --output-dir shared_folds --verify-only
```

- **Preprocessing:** fit learned scaling, motif reference statistics, imputation/feature selection, class weights and calibration using training partitions only. Apply unchanged to held-out data. Never independently normalise each test file to conceal dataset shift.
- **Candidate transforms:** log positive dwell features; `log1p(coverage)`; training-fitted mean/SD or median/IQR scaling where needed. Define zero-scale and sparse/unseen-motif fallbacks. These transforms were proposed, not validated improvements.
- **Tuning/early stopping:** keep genes separate inside outer-training data. Do not early-stop on an outer validation fold and call its score an unbiased final test. Existing outer-fold model selection remains development.
- **Randomness:** seed 42 for new stochastic EDA and reproducible initial comparisons. Optional final robustness runs: training seeds 42, 43, 44 on unchanged folds. These extra repeats are proposals, not existing results.
- **Evaluation:** retain natural label prevalence in validation/testing; apply reweighting/oversampling only in training. Coordinate ROC/PR definitions with Member 3. Save actual per-fold and out-of-fold outputs and relevant subgroup counts. Do not change labels/folds after seeing errors.

## 7. Prioritised experiments and plots

Start by checking what the current pipeline already contains. Use the same eligible sites and folds for paired comparisons, change one main factor at a time, and retain negative results.

| Priority | Proposed experiment | Motivation and check |
|---|---|---|
| 1 | Sequence conditioning or signal-by-motif interactions | Pooled/within-motif directions differ. Compare global and motif-specific behaviour on held-out genes. |
| 2 | Robust read-distribution features: medians, IQRs, quartiles/tails | Positive groups have larger typical current spread. Check benefit beyond existing features, motif and coverage. |
| 3 | Coverage ablation and read-sampling sensitivity | Coverage/label relationships shift. Compare with/without coverage; check low/high-depth subgroups. |
| 4 | data1 augmentation under a shared gene-fold extension | Test sample diversity only after provenance/mapping checks; use identical data0 validation targets. |

Completed plots covered: dataset coverage/prevalence; motif counts/positive rates; within-motif signal differences; label rates by coverage; paired data0/data1 labels/signals; and data2 matched-template trends. Main numerical findings are reproduced above, so images are not needed to understand this handoff.

Useful next plots: (1) exact-context and coverage-matched signal comparisons; (2) read-subsampling stability—same sites with ≥100 reads, sample 20/50/100 without replacement, 100 repeats, seed 42; (3) unusual-case read histograms and neighbouring-feature scatterplots. These were **not performed**. Gene-region plots additionally require correct annotation. Resampling reads measures finite-read stability, not biological replication.

All EDA is descriptive. Correlated sites within genes, rare positives, coverage and sequence selection limit interpretation. No inferential confidence intervals, significance tests or causal conclusions were established. Data2 plot bands were IQRs across templates, not confidence intervals. No universal minimum coverage or outlier-removal rule was validated.

## 8. Additional data, evidence and next action

Possible additional sources were identified, not downloaded/analysed: SG-NEx processed direct-RNA JSONs for Task 2; HEK293T knockout/mixture data cited as ENA PRJEB40872; synthetic Curlcakes cited as GEO GSE124309; and small m6Anet demos for software checks. Compatibility, independent labels and overlap require verification. Synthetic/knockout controls are not automatically representative cellular tests. Unlabelled predictions are not ground truth, and data2 must not be assumed to be one of these experiments.

Original computational inputs are `data0/dataset0.json.gz`, `data0/data.info.labelled`, corresponding `dataset1.json.gz`/`data.info` and `dataset2.json.gz`/`data.info`, plus the exact shared-fold files. Member 2 must also supply the current model code/config/results for model-specific work.

Member 1's supporting archive is named `Member1_Analysis_Package.zip`. It contains full site summaries, source hashes, six figures, motif/coverage/overlap/outlier tables, EDA scripts and unchanged fold files. It is optional for understanding this summary, but needed if the receiving AI wants those particular outputs. Their filenames are references, not evidence of access.

Source context: course handout; course slides pp. 53 and 55 (measurements and split-by-gene guidance); shared-fold README/metadata; and team handoff dated 12 October. External references checked on 13 October:

- m6Anet paper: https://doi.org/10.1038/s41592-022-01666-1
- SG-NEx data: https://github.com/GoekeLab/sg-nex-data
- m6Anet training/demo documentation: https://m6anet.readthedocs.io/en/latest/training.html

**Receiving AI's first response:** briefly state the usable findings and constraints; inventory the files actually available; compare these candidate ideas with the current pipeline; propose the first three controlled experiments and their checks. Ask specifically for missing data/code/folds needed to run them. Investigate data1 provenance, data2 label semantics/read reuse and the annotation version before any pooled-data redesign. Report proposed, running, completed and failed work honestly; do not invent results or promote exploratory datasets to untouched tests.

## 9. Revision 2: implementation-ready improvement plan

The accompanying ZIP now includes `MEMBER2_ACTION_PLAN.md` and `feature_specification.csv`. Read these after this handoff. They specify controlled sequence/coverage comparisons, read-subsampling stability, unusual-case inspection, exact feature definitions and the first three model comparisons. These are **planned follow-ups, not completed analyses or proven improvements**. Original numerical findings are unchanged.

Priority order: (1) inspect the current model to avoid duplicating existing features; (2) refine sequence/coverage-controlled comparisons; (3) measure feature stability using the same high-coverage sites sampled to 20/50/100 reads, 100 repeats, seed 42; (4) inspect individual-read distributions at unusual sites. For each result record the question, observation, possible explanation, limitation and model action.

The specification identifies 36 existing all-read summary columns and distinguishes them from proposed log transforms and training-fitted motif residuals. It defines zero-based matrix columns, quantile interpolation, population SD and training-only fitting requirements. Do not assume the model currently lacks these features.

The receiving AI should read `MEMBER2_ACTION_PLAN.md` before implementing these follow-ups. If only this handoff is uploaded, request the supporting ZIP for the detailed protocols and existing outputs. Raw datasets and the current model code are still separate inputs.
