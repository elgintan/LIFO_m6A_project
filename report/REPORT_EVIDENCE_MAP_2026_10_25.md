# Five-page report: requirements, evidence and writing plan

Prepared 25 October 2026 from existing course materials and completed evidence.
This is an assistant-authored planning document for team review, not the final
report, an individual reflection, a new experiment or a contribution statement.
No training, prediction, data rescan or model selection was performed to write it.

**Current stage:** the selected model, development comparisons, required
benchmarks, 23-run predictions, context audit, descriptive Task 2 analysis,
four-case interpretation and full local explorer are complete. The report still
has a [first draft](REPORT_DRAFT_2026_10_25.md) and still needs team checking and
five-page layout verification. The full [public explorer](https://lifo-sgnex-m6a-explorer.wittylemon1025.chatgpt.site)
is deployed; [hosted checks](../data_visualisation/hosting_results_2026_10_25/README.md)
are complete within their stated scope. Do not rerun completed scientific work.

## 1. Official requirements and the corresponding evidence

The primary source is the original [project handout](../../handout_project2_RNAModifications.html),
especially **Project Team Submission Requirements → (1) Report**. The supplied
22 October announcement is recorded in [PROJECT_DEADLINES.md](../PROJECT_DEADLINES.md)
and supersedes the original report/visualisation deadline, not the model or format rules.

| Requirement | Where to satisfy it and what to cite |
|---|---|
| Title; Introduction; Problem statement | Briefly define m6A and the site-level prediction problem, then distinguish model evaluation from exploratory SG-NEx application. The handout and its original m6Anet/SG-NEx references establish motivation. |
| Methods: final model used for submission and analysis | [Actual final model/results](../model_elgin/final_cap128_results/results.md), [fixed selection decision](../model_elgin/FINAL_MODEL_SELECTION.md), [training/prediction interface](../model_elgin/FINAL_MODEL_USAGE.md), and their source/receipt links. Describe the selected pipeline, not every abandoned architecture. |
| Methods: Task 2 datasets and analysis | [Task 2 execution plan](../sgnex_analysis/TASK2_EXECUTION_PLAN.md), [context QC policy](../sgnex_analysis/CROSS_RUN_CONTEXT_QC_PLAN.md), [context results](../sgnex_analysis/context_qc_results/README.md), and [completed analysis](../sgnex_analysis/task2_results_2026_10_23/README.md). |
| Results (1): independent training/test partitions of supplied training data | Exact [five gene-fold assignments](../eda/received/shared_folds/data0_folds.csv), [shared rules](../model_evaluation/SHARED_RULES.md), and [split composition audit](../eda/split_review/README.md). State the fresh inner-selection/refit boundary and repeated development use. |
| Compare final model with a simple baseline and m6Anet | [Four-method benchmark table](../model_evaluation/benchmark_results_2026_10_22/comparison.csv) and [benchmark protocol/limits](../model_evaluation/benchmark_results_2026_10_22/README.md). Published m6Anet is a pretrained reference, not a fresh fold-trained competitor. |
| Optional intermediate-model improvements | [Read-cap comparison](../model_elgin/read_cap_results/README.md), [loss-weight comparison](../model_elgin/loss_weight_results/README.md), [threshold study](../model_elgin/threshold_results/README.md), and [selection decision](../model_elgin/FINAL_MODEL_SELECTION.md). Include negative outcomes and the higher-S unpromoted external trial. |
| Results (2): application to available SG-NEx datasets | [Global findings](../sgnex_analysis/task2_results_2026_10_23/findings.md), [interpretation draft](../sgnex_analysis/task2_results_2026_10_23/INTERPRETATION.md), all aggregate CSVs, and [fixed biological cases](../sgnex_analysis/biological_case_results_2026_10_23/README.md). |
| Discussion | Limit interpretation to uncalibrated candidate-site scores; cover exposure, sparse support, reference/offset uncertainty, technical confounding, metadata-group independence and absent independent SG-NEx assay labels. |
| References | Use primary sources already checked in [case literature notes](../sgnex_analysis/biological_case_results_2026_10_23/LITERATURE.md), plus original m6Anet and SG-NEx papers. Cite each biological claim within its verified boundary. |
| Code Availability | Link [public repository](https://github.com/elgintan/LIFO_m6A_project), [usage documentation](../model_elgin/FINAL_MODEL_USAGE.md), and final verified explorer URL. Prediction instructions must include the model and documented example. |
| AI-use table: tool, prompt/output, use | Adapt the factual evidence in [AI_USE.md](../AI_USE.md); team members confirm actual tool names/versions, prompts and use. Do not invent personal experience or teammate work. |
| At least two wrong/misleading/unverified AI outputs, detection and correction | Two actual candidates are the fold-column/label assumption and premature recommendation of the higher-S external trial; see Section 6 below. Do not replace this with a generic statement that AI was checked. |

The main report is **at most five pages**, excluding an optional title page,
optional contents and references. Body font is **Arial 11**; captions, tables
and references may use **Arial 9–11**. The announcement permits an unlimited
**ungraded** appendix. Essential methods, results and limitations belong in the
main body. Budget the AI table and two error examples in the body rather than
assuming an additional exclusion that the handout does not state.

Code and new unlabelled-test predictions remain due **28 October, 23:59 SGT**.
Report/interactive visualisation are due **8 November**, with exact extended
submission time still unconfirmed here. Report plus interactive visualisation
carries **50 percentage points**, executable/reproducible code five, model
performance five, and individual participation five. Leaderboard rank is not
used for grading. This document does not author the separate confidential
teamwork summary or assign contributions/ratings.

## 2. The scientific story

**Proposed through-line:** sequence and heterogeneous read distributions motivate
a sequence-aware, site-supervised model. Gene-held-out development and explicit
baselines establish useful ranking performance with clear exposure limits.
Applying one frozen model to all 23 SG-NEx runs yields a reproducible,
context-qualified resource: most matched scores are low and broad line shifts
are modest, while selected local contrasts/shared high signals merit follow-up.
Neither global agreement nor persistent case scores establish modification
chemistry, stoichiometry or causal cell-line differences.

The report can support this argument now. More architecture searching is not
needed to make it defensible. Keep future validation proposals distinct from
checks actually completed.

## 3. Claim-to-evidence map

### Data, EDA and evaluation design

| Defensible statement | Exact existing evidence | Boundary to keep beside the claim |
|---|---|---|
| data0: 121,838 sites, 5,475 positives, 3,852 genes; data1: 90,810 sites, 6,593 positives; data2: 1,323 rows with fractional labels | [EDA handover §1](../eda/received/MEMBER1_CONTEXT_2026-10-13.md), [inventory](../eda/received/tables/inventory.json), [actual final results](../model_elgin/final_cap128_results/results.md) | data0 alone fits/tunes the selected final pipeline. data1 was previously explored. Do not binarise data2 or call its groups independent replicates. |
| Context changes apparent signal relationships: pooled data0 central current is 114→118 for labels 0→1, but label-1 current is lower in 11/15 sufficiently supported motifs | [EDA handover §4B](../eda/received/MEMBER1_CONTEXT_2026-10-13.md), [within-motif effects](../eda/received/tables/within_motif_effects.csv), [original signal figure](../eda/received/figures/03_signal_by_motif.png) | Descriptive site-median comparisons; no universal current-change rule or causal effect. This motivated context-aware modelling, not proof of its mechanism. |
| data0/data1 share 67,320 literal site IDs, including 3,872 label disagreements | [overlap table](../eda/received/tables/metadata_overlap.json), [paired counts](../eda/received/tables/paired_label_counts.csv), [EDA handover §4D](../eda/received/MEMBER1_CONTEXT_2026-10-13.md) | A label disagreement table is not a model confusion matrix. Different complete matrices do not prove independent source molecules; data1 is not a blind unseen-gene test. |
| All 121,838 sites have exact assignments; all 3,852 genes stay within one of five folds. Eight of 90 motif/fold groups lack both classes; 38 have fewer than 20 positives | [composition audit](../eda/split_review/composition_audit.json), [motif support](../eda/split_review/motif_support.csv) | Global class balance does not ensure subgroup support. Keep sparse groups; undefined subgroup AUC is not a zero score. Five fold results share training data and are not five biological replicates. |

Fold-file SHA256 is `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
For outer fold `f`, inner fold `(f+1)%5` selects duration using only training
genes; fresh weights then fit all four non-assessment groups. Normalisation is
learned inside each permitted fit. Primary S is the unweighted mean of five
`(ROC AUC + trapezoidal PR AUC)/2` values; average precision and pooled OOF areas
are separate summaries. Historical early screening/October 7 metrics are not
interchangeable with this later strict matched comparison; do not splice them
into one purportedly controlled improvement sequence.

### Model and benchmarks

The selected pipeline combines nine signal measurements per read, a seven-base
embedding, width-48 read encoding, gated attention/mean/SD pooling and 63 all-read
distribution summaries. Training samples at most 128 reads per site; prediction
uses all valid reads. Positive loss weight is three; no probability calibrator
was fitted. `context_mode=none` disables the added relative-reference branch,
**not** the original sequence embedding. Source: [actual model description](../model_elgin/final_cap128_results/results.md).

| Pipeline | Mean-fold ROC AUC | Mean-fold trapezoidal PR AUC | Mean-fold S | Interpretation |
|---|---:|---:|---:|---|
| Fixed balanced-C1 logistic regression | 0.804056 | 0.149129 | 0.476592 | Fresh five-fold simple recipe replay; historical recipe selection disclosed. |
| Samuel LightGBM | 0.921897 | 0.498996 | 0.710446 | Same assessment sites/folds and scorer; a complete-pipeline comparison. |
| Selected cap128/weight3 neural pipeline | 0.931828 | 0.505601 | 0.718715 | Main integrated pipeline; descriptive fold S SD 0.010726. |
| Published m6Anet | 0.932176 | 0.503257 | 0.717717 | Pretrained HCT116_RNA002 model; possible training-source overlap, not five-fold retraining. |

Primary table source: [comparison.csv](../model_evaluation/benchmark_results_2026_10_22/comparison.csv).
Do not say that the neural model independently outperformed m6Anet: the S
difference is about 0.000998, ROC favours m6Anet, and reference overlap remains
unresolved. Do not use pooled-curve legend values as the mean-fold table values.

Retain a short honest development statement: cap32 S 0.717642 → cap128 S
0.718715; added relative-context branch S 0.708885; weight1 S 0.718381. The
training-side threshold study did not establish a useful replacement for 0.5.
Valid unusual signals and difficult high-coverage sites remained in the evidence.

**Required tradeoff disclosure:** the separate external neural trial achieved
S **0.726644**, genuinely higher by **0.007929**, with improvements in all five
folds. Its saved-evidence audit found no material leakage/hardcoded-score defect.
It was not promoted: the recorded decision was inconclusive given mixed
fixed-cutoff/subgroup behaviour, single-seed evidence, different computational
conditions and incomplete final deployment interface/artifact. At 200+ reads,
recall was 151/461 versus 168/461 for cap128 even though ranking improved.
Do not describe it as numerically worse, pretend every subgroup must improve,
or claim the deployed pipeline was globally best. Source: [fixed decision](../model_elgin/FINAL_MODEL_SELECTION.md).

The final selected artifact was fitted **fresh on all data0 only for 18 epochs**
(median inner choices 9/20/19/18/17), SHA256
`b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.
The same artifact generated all supplied-data and Task 2 scores. Final data0
scores are fitted-data outputs, distinct from OOF evidence. Frozen data1
ROC/PR/S are **0.827381/0.382350/0.604866**, versus LightGBM
**0.821764/0.382879/0.602322**: the neural pipeline has higher ROC/S/recall/F1,
while LightGBM has higher PR/precision/specificity/accuracy. Source:
[actual final results and summary](../model_elgin/final_cap128_results/results.md).
Do not reopen model selection using this exposed diagnostic.

Prediction portability is checked on the ten-site/1,887-read example, including
the **user-executed** native AWS Ubuntu 26.04/Python 3.12.15 run and independent
verification; maximum score difference from the pinned example was
**1.4901161193847656e-8**, below 3e-6. Source:
[AWS evidence](../model_elgin/aws_prediction_results_2026_10_24/README.md).
This is software parity, not unseen accuracy, replayed training or submitted new
test data. If runtime is mentioned, use the scoped [final-fit resource report](../model_elgin/final_cap128_results/results.md):
679.823 seconds wall for its wrapper scope, not total historical project cost.

### Task 2: populations, patterns and cases

| Defensible number/claim | Primary source | Essential qualification |
|---|---|---|
| 23 processed runs, seven cell lines, 17 metadata groups; 2,983,948 scored run-site observations using 232,253,678 reads | [context summary](../sgnex_analysis/context_qc_results/summary.json), [analysis receipt](../sgnex_analysis/task2_results_2026_10_23/analysis_receipt.json) | Repeated run-site observations, not unique sites or confirmed modified sites. Metadata groups are not independently verified laboratory preparations. |
| 451,352 scoreable keys; 8,780,071 source observations at those keys, including low-read records; zero encoded context conflicts/exclusions | [QC summary and policy](../sgnex_analysis/context_qc_results/summary.json) | Explicit per-run aliases only; model encoding uppercase/U→T. The 19,890,009 observations outside the scoreable union were counted but not cross-run context-compared. Context agreement is not reference/offset validation. |
| All-seven matched populations: 33,452 at 20 reads, 11,560 at 50, 5,058 at 100 | [population table](../sgnex_analysis/task2_results_2026_10_23/context_population_effects.csv) | Annotated human, primary context eligibility and at least two eligible metadata groups per line. Average eligible runs within group, then groups equally. Pair populations are separate. |
| On the same 33,452-site panel, means span 0.0705–0.0946; 3.76–5.20% meet 0.5; only 15–31 sites per line meet 0.9 | [line/depth/cutoff table](../sgnex_analysis/task2_results_2026_10_23/all_line_score_summary.csv) | These are score distributions/cutoff fractions, not m6A prevalence or molecule fractions. Hct116 is the training cell line; biological, training-domain and technical explanations cannot be separated. |
| At 20 reads, median run-pair Spearman is 0.7904 for six same-group pairs, 0.7934 for 28 other-group same-line pairs, 0.7815 for 219 cross-line pairs | [agreement summary](../sgnex_analysis/task2_results_2026_10_23/agreement_summary.csv), [per-pair denominators](../sgnex_analysis/task2_results_2026_10_23/agreement_by_metadata_relationship.csv) | Overlapping ranges/shared sequence structure; agreement is not assay accuracy. Each pair has its own matched sites. Explorer agreement instead uses mean Pearson in disjoint bands; do not identify the two estimators. |
| All 21 cell-line pairs retained at all three depths; Hct116–HepG2 has 2,331 screened candidates among 120,195 shared sites at 20 reads | [all-pair table](../sgnex_analysis/task2_results_2026_10_23/all_pair_summary.csv) | Screen: absolute mean difference ≥0.2, separated group ranges, depth ratio ≤2. No significance/FDR inference; preserve all denominators, small effects, overlap cases and valid extremes. |
| 22,219/33,452 common 20-read keys have fewer than 20 positive training labels for their seven-base context; 4,290 have zero | [context support table](../sgnex_analysis/task2_results_2026_10_23/common_site_training_context_support.csv) | Support is a warning, not a calibrated uncertainty estimate or eligibility filter. |
| Fixed selection found 1,004 persistent pair-site contrasts, 545 unique keys, 41 shared-high keys and 6,098 inconclusive pair-site candidates | [selection summary](../sgnex_analysis/biological_case_results_2026_10_23/summary.json), [predeclared rules](../sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md), published full ranked pools | Tail-selected illustrations, not representative sampling or discoveries with error-rate control. Persistence across nested thresholds may reuse exactly the same runs. |

The four cases are **HNRNPA1 ENST00000340913:177** (HepG2/K562 contrast),
**RAB1B ENST00000311481:1947** (Hct116/HepG2 and training-line caution),
**ACTG1 ENST00000331925:607** (shared high scores), and
**G3BP2 ENST00000359707:2510** (HEYA8/HepG2 overlap/inconclusive).
Use the [full-precision case tables](../sgnex_analysis/biological_case_results_2026_10_23/case_line_scores.csv),
[original run records](../sgnex_analysis/biological_case_results_2026_10_23/case_run_evidence.csv),
[training-key diagnostics](../sgnex_analysis/biological_case_results_2026_10_23/training_key_diagnostics.csv)
and [case narrative](../sgnex_analysis/biological_case_results_2026_10_23/REPORT_PARAGRAPH.md).

HNRNPA1 pair means are approximately **0.642 versus 0.078**; ACTG1 seven-line
means are **0.942–0.959**. G3BP2's stricter-depth contrast is unavailable when
two groups are not retained; a one-group score remains a diagnostic, not zero
or a qualifying comparison. Across all four cases there are **92 original
run records: 80 scored and 12 below-20-read unscored**, no absent source record.
Three selected literal keys occur in data0 (labels 1/0/1); this is disclosed
training exposure, not independent SG-NEx validation. Published HNRNPA1/ACTG1
assays were not mapped to these exact coordinates. Gene/protein functions do
not establish altered splicing, trafficking or stress-granule activity here.

Depth panels must say **nested sensitivity analysis**: different 20/50/100
populations do not isolate the effect of reading the same sites more deeply.
Stable HNRNPA1/RAB1B/ACTG1 means may simply reuse the same qualifying observations.
The technical metadata table must inform the narrative rather than treating
coverage balancing as adjustment for basecaller/platform/date confounding.

## 4. Proposed five-page body and figures

Use the handout's section names. The allocations below are planning budgets,
not a verified typeset layout; render the actual Word/PDF at Arial 11 before
claiming it fits. Aim for roughly 1,500–1,900 body words after tables/captions.

| Page | Main argument and approximate content | Essential display |
|---|---|---|
| 1 | Introduction/problem; data-role/EDA rationale; final model and gene-held-out inner/refit method. About 300 words. | Small dataset-role table and compact method schematic/text; explain why site labels do not label individual reads. |
| 2 | Results (1): benchmark table, mixed component metrics, honest model progression/external tradeoff; brief frozen data1 result and exposure caveat. About 300 words. | **Figure 1:** [reference_curves.svg](../model_evaluation/benchmark_results_2026_10_22/reference_curves.svg), with the mean-fold table alongside. Caption distinguishes pooled curves from mean-fold S and pretrained m6Anet. |
| 3 | Task 2 methods/population funnel; matched distributions, depth/cutoff counts and Hct116 caution. About 250–300 words. | **Figure 2:** [matched_site_score_patterns.svg](../sgnex_analysis/task2_results_2026_10_23/matched_site_score_patterns.svg). Put 451,352→33,452/11,560/5,058 denominators in a compact table/caption. Summarise the three agreement medians in text/table. |
| 4 | Contrasting biological cases, negative/inconclusive evidence, training exposure and exact-site literature limits. About 200–250 words. | **Figure 3:** [case_group_score_patterns.svg](../sgnex_analysis/biological_case_results_2026_10_23/case_group_score_patterns.svg). Retain all four roles and show that group ranges are not confidence intervals. |
| 5 | Discussion/limits, restrained conclusion, code/explorer availability and factual AI-use table plus two actual correction examples. About 350–450 words including table text. | A concise AI-use/error table; essential limitations remain readable in the body. |

These **three essential figures** cover model assessment, global application and
site-level interpretation. If the actual layout comfortably permits a fourth,
use a compact **agreement** display from
[run_group_agreement.svg](../sgnex_analysis/task2_results_2026_10_23/run_group_agreement.svg),
with per-pair denominators and estimator named. Do not shrink four figures until
their labels are unreadable. The full 21-pair figure, context-population figure,
depth case figure, original EDA panels, extra ablations, all cutoffs and detailed
resources are suitable supporting appendix/explorer material. Their central
methods/results still need a main-body sentence or table because the appendix
is ungraded.

Use existing PNG/SVG figures as checked evidence. Any new multi-panel assembly
must retain scales, populations, caveats and readable labels; it is figure
composition, not permission to alter scores or select more favourable examples.
Do not use final training loss as evidence of unseen performance. Avoid a
dashboard screenshot as the main scientific result when the quantitative
figure is clearer. Insert the verified explorer URL and literal-case links in
Code Availability and explain its intended researcher workflow briefly.

## 5. Suggested language discipline

- Write “predicted site score”, “fraction of measured candidate sites above a
  descriptive cutoff”, “persistent exploratory contrast” and “metadata group”.
- Reserve “independent” for the actual held-out fitting boundary or independent
  software audit, specifying which; do not apply it to unverified laboratory
  preparations, exposed data1, nested thresholds or published-reference training.
- State both numerator and denominator for highlighted screens; do not compare
  all-line and pair-specific populations as if they were identical.
- A site absent/unscored at a depth is not a negative, score zero or proof of
  missing modification. Retain measured scores that become depth-ineligible.
- Do not claim calibrated probability, modification prevalence, molecule
  fraction, causal lineage differences, new RNA-mark identity, significant
  differential m6A or exact-site external validation.

## 6. AI disclosure and remaining actions

The final team AI-use table needs actual tool/model details and prompt/output
use confirmed by the people who used them. [AI_USE.md](../AI_USE.md) already
records assistant implementation, documentation, auditing and figure/narrative
help; it does not replace team confirmation or author anyone's personal reflection.
Two concrete documented correction examples suitable for the report are:

| Actual issue | How it was detected | What changed |
|---|---|---|
| Initial audit code assumed a `fold` column and labels in the fold CSV. | It stopped with KeyError; inspection showed `fold_id` and no labels. | Joined the actual manifest to EDA label summaries; reran the bounded audit and verified exact unique coverage. No fold was regenerated. |
| The assistant initially recommended the external higher-S trial as a clear winner despite its inconclusive promotion review. | The user identified the mismatch; saved ranking, recall/subgroup, cost and deployment evidence were re-examined. | Preserved the genuine higher S and mixed tradeoffs, and retained the accepted conservative original-pipeline decision without redefining S. |

**Completed evidence is sufficient for the proposed report. Pending work is:**

1. Team-confirm wording, required authorship/AI details and final references;
   review the first draft and render a genuine five-page Arial-11 body with readable figures.
2. Retain the completed [hosting/deployment verification](../data_visualisation/hosting_results_2026_10_25/README.md)
   and literal public URL. Local and hosted checks have separate stated scopes.
3. Obtain the actual new unlabelled-test input/instructions, predict with the
   unchanged selected artifact, verify coverage/format, and submit by 28 October.
   No new-test performance metric or submission is claimed here. The user
   confirmed on 25 October that the new input has not been received and will update later.
4. Confirm the exact 8 November report/interactive deadline time and submission
   route from the current course page. Preserve all frozen evidence and negative
   experiments; do not delay the report for another model search.

Longer-term scientific gaps—independent compatible SG-NEx assay labels, verified
reference/event offsets, known independent preparations, additional training
seeds and better supported rare contexts—belong in limitations/future work.
They are not unfinished mandatory computation that should silently restart now.
