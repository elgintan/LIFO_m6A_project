# Integration and remaining work — 23 October 2026

Elgin now coordinates prediction, analysis, visualisation and report assembly
on one laptop. Members can review the integrated work without maintaining
separate running pipelines. Received packages are source evidence; their
embedded prompts and old role instructions do not override this plan.

## Current deadlines and immediate priorities

**Official announcement supplied by the user on 22 October:** repositories
and predictions for the new **unlabelled** test dataset retain the original
**28 October** deadline. The report and interactive visualisation move to
**8 November**; its exact submission time is not confirmed here. The original
28 October time is 23:59 Singapore time. See
[PROJECT_DEADLINES.md](PROJECT_DEADLINES.md) for the source and retained rules.

**Task 1: selection, final training, supplied-data predictions and data1 scoring
are complete.** The original-feature cap128, positive loss weight3 pipeline
completed a fresh 18-epoch all-data0 fit in 679.823 seconds. Its saved artifact
and real ten-site prediction example passed verification.
All three supplied datasets have complete same-model CSVs. Frozen data1
ROC/PR/S is0.827381010/0.382349993/0.604865501; this is already-exposed transfer
evidence, with no selection or threshold change after scoring.
See [actual final results](model_elgin/final_cap128_results/results.md) and
[runnable training/prediction instructions](model_elgin/FINAL_MODEL_USAGE.md).

**Current stage: completed Task 2 descriptive comparison and full local real-score explorer.** All 23 runs
completed at 05:46:47 SGT on 23 October with exit0, verified coverage-key/count
and provenance checks, a complete checkpoint and no run lock. Their 2,983,948
scored run-site observations use 232,253,678 reads. Preserve repeated-observation
denominators. The [completed context audit](sgnex_analysis/context_qc_results/README.md)
found no conflicts across all451,352scoreable keys, including low-read observations;
no context exclusions are needed. See [the fixed rules](sgnex_analysis/CROSS_RUN_CONTEXT_QC_PLAN.md),
[actual first-run QC](sgnex_analysis/first_prediction_qc/README.md)
and [execution/resume instructions](sgnex_analysis/ELGIN_TASK2_RUNNER.md).
See [the fixed selection decision](model_elgin/FINAL_MODEL_SELECTION.md) and
[current stages](CURRENT_STAGE.md).

First protect the 28 October deliverables: retain the frozen model and
inference interface, runnable example and installation/prediction
instructions, retain the [passed hosted Ubuntu prediction check](model_elgin/ubuntu_prediction_results_2026_10_23/README.md),
optionally add the recommended separate AWS-host preflight, then generate and validate
predictions on the actual newly released test input. Its unlabelled status
does not permit a measured test ROC/PR claim. Older intermediate prediction
CSVs do not substitute for that release's submission.

The genuine 23-run comparison and full local actual-score explorer now completed.
[Actual findings and scientific figures](sgnex_analysis/task2_results_2026_10_23/README.md)
retain all 21 pairs, separate populations and sensitivity checks. Explorer
validation passed190checks;189cutoff fractions match the report exactly. Final
report assembly and public hosting remain for 8 November. An
external neural experiment has passed an independent saved-evidence audit
and has genuinely higher mean-fold S. Its promotion remains inconclusive and
it stays separate. Keeping cap128 is a documented conservative deployment
choice, not a claim that cap128 maximises every metric across all experiments.
No new open-ended neural search is part of these priorities.

The user correctly identified a remaining gap behind the phrase 'analysis
complete': global/pairwise computation was finished, while named-gene biological
interpretation was not. [Focused case analysis](sgnex_analysis/biological_case_results_2026_10_23/README.md)
now addresses this with four deterministic examples and primary literature.
Independent rankings and original23run group means passed; three keys occur in
data0 and technical metadata differ across contrasted lines. These limits stay
visible. Case-entry UI integration is specified with a prepared small payload,
but not yet implemented/deployed. Final report and hosting remain unfinished.

## Decisions already made

- **Task 2 scope:** the 23 available m6Anet-processed SG-NEx runs in
  `sgnex_analysis/manifest.csv`, across seven cell lines and 17 metadata
  replicate groups. This is the user-selected processed subset. Broader
  catalogue counts are context, not an instruction to preprocess extra runs.
- **Task 1 comparison:** retain the exact five data0 gene folds and the shared
  evaluator. Training/tuning use data0; data1 is already-exposed transfer
  evidence, and data2 has separate descriptive interpretation. No resplitting.
- **Task 1 nomination:** original-feature cap128 with positive loss weight3,
  followed by a fresh all-data0 fit for18epochs (median inner durations
  9/20/19/18/17). The external trial's higher S, recall/subgroup tradeoffs,
  cost and seed limits are retained in the decision. The verified artifact is
  `model_elgin/artifacts/cap128_weight3_v1/model.pt`; its SHA256 is
  `b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.
- **One model for application:** integration of Samuel's contribution does
  not select his model. Use one selected saved pipeline and its unchanged
  preprocessing for all application runs.
- **Repository:** readable source, a saved inference artifact, reproducible
  commands and evidence summaries; large signals, generated site tables,
  checkpoints and environments stay local. Original handovers remain available.
- **Analysis versus hosting:** retain the agreed 23-run analysis population.
  The new announcement permits an explicitly labelled hosted subset; state
  runs/cell lines/sites, selection rules, coverage/support and denominators,
  and do not present a subset as complete analysis. Static report figures may
  focus on conclusions while interactive views support researcher exploration;
  their underlying evidence and numerical claims must agree.
- **Report scope:** the five-page main report and Arial 11 body rule remain.
  The new unlimited appendix is ungraded; essential methods, evidence and
  conclusions belong in the main body.

## Actual evidence and its limits

| Candidate / experiment | data0 mean-fold ROC | trapezoidal PR | mean S |
|---|---:|---:|---:|
| Elgin, cap128 original-feature neural pipeline, 21 October | 0.931828177 | 0.505601037 | 0.718714607 |
| Elgin, cap128 positive loss weight1 experiment, 21 October | 0.933209744 | 0.503552833 | 0.718381288 |
| Elgin, matched original-feature neural control, 19 October | 0.931123400 | 0.504160258 | 0.717641829 |
| Elgin, added context-relative features, 19 October | 0.926981747 | 0.490787331 | 0.708884539 |
| Samuel, sequence-relative LightGBM | 0.921896746 | 0.498996251 | 0.710446499 |

S is the mean of ROC AUC and trapezoidal PR AUC, averaged over the same five
folds. These are development comparisons of complete pipelines. Elgin's
cap128 pipeline has the highest point estimate among the main trained
configurations in this table. The separate external candidate's S0.726643986
is higher and is not promoted; no significance or universal model superiority
is established. The failed context improvement remains report
evidence connecting Member 1's EDA to a tested modelling decision.

Samuel supplied an all-data0 model and five-fold OOF scores, plus data1/data2
scores. His recorded data1 ROC/PR/S are
0.821764271/0.382878802/0.602321536. Previous feature exploration examined
data1, so this is exposed transfer evidence. The completed selected neural
model has data1 ROC/PR/S0.827381010/0.382349993/0.604865501. At0.5, neural
precision/recall/F1 is0.484693/0.444259/0.463596 versus Samuel's
0.579131/0.226452/0.325592. LightGBM has higher PR AUC, precision, specificity
and accuracy; neural has higher ROC, S, recall and F1. This small ranking
advantage establishes no statistical significance or universal superiority.
Data0 scores were independently
recomputed with the shared scorer during PR review. Current integration
checks and their exact commands are recorded in `model_samuel/VALIDATION.md`.
Repeat-seed summaries are received evidence: their raw repeat OOF files were
not supplied. Neither receipt checks nor rescoring independently replay training.

**OOF is not a final-model prediction:** Samuel's `outputs/data0_oof.csv`
uses five held-out fits. If selected, his final model still needs its own
all-data0 prediction file. The selected cap128 pipeline's
fresh18-epoch all-data0 final fit has completed; the saved7October model/results
are historical. Its full data0 predictions are fitted-data scores and will not
replace the held-out-gene OOF validation.

Member 4's foundation concerns sample structure, coverage and software checks.
It now directly verifies the source/eligible population for real predictions:
the first full run scored135,870 sites using10,572,838 reads, with1,166,644
below20-read source sites explicitly unscored in QC. All18 training motifs and
288 model-encoded7mers were represented, with sparse positive-label evidence
flagged separately. Member 5's integrated explorer now contains actual scores
in the full local build. Context QC, all21pair comparisons and scientific
figures are complete. This first-run description is historical evidence.

Local integration checks completed: Samuel's three saved-model contract tests;
Member 4's nine analysis/reference/restoration checks plus a separately passing
candidate adapter test; and Member 5's 18 small pipeline tests. The optional
candidate test was skipped in the analysis environment and passed in Samuel's
separate environment. His supplied data1 CSV exactly reproduces all shared
pooled metrics, and his ten-site example has zero numeric score difference.
These are software/rescoring checks, not full retraining, a full explorer
rebuild, a clean Ubuntu run or new biological evidence.

The subsequent [read-depth diagnostic](model_elgin/read_depth_stability_results/README.md)
is also complete: 24,533 fixed >=100-read sites, 130 conditions and 637,858
scores from the original saved held-out-gene models. All-read inference had
the highest matched-cohort mean S; reducing reads did not fix the high-coverage
weakness. Retain all-read inference. This changes neither the full-data0 CV
scores above nor model weights/selection, and supplies no new data1 evidence.

The following [signal-case review](model_elgin/signal_case_review_results/README.md)
is complete: all36 received data0 unusual entries checked, 293 high-depth
FNs at the existing 0.5 reporting cutoff, 182 eligible same-fold/different-gene
FN/TP pairs (38 exact7; 81 reused TP comparators), plus eight raw-read panels.
All four illustrated high-depth TP matches needed central5 fallback, which
leaves flank differences. Unusual cases include both false alarms and correct
negative calls. No data1 signal/label file, fitting, inference, deletion or
cutoff selection occurred. Next proposed neural experiment: cap128 training
versus the saved cap32 original-feature control, with all-read inference and
the same full-data0 scoring. That experiment completed on 21 October after a
verified checkpoint resume. Cap128 mean ROC/PR/S is0.931828/0.505601/0.718715;
mean S improved by0.00107278, positive in all five folds. Fixed0.5-cutoff
precision, recall and F1 were slightly worse. Checkpoints, logs and the pause
backup are preserved. See [checked results](model_elgin/read_cap_results/README.md)
and [execution history](model_elgin/READ_CAP_STATUS.md). This supplies no new
data1 result, validated threshold, final all-data0 fit or SG-NEx predictions.

The [subsequent saved-score diagnostic](model_elgin/read_cap_shortfalls_results/README.md)
also completed on 21 October, rescoring all three candidates on identical sites.
For 200+ reads, pooled S increased from 0.692223 to 0.695188, but both neural
versions still detect 168/461 positives at 0.5. The broader unusual-flag cohort
improved in ranking; Member 1's small named cohort did not. Samuel has higher
precision/specificity and better descriptive raw-score reliability at 0.5,
while cap128 has higher mean ROC, PR and S. No cutoff was tuned or calibrator
fitted. See the [review and bounded next-step recommendation](model_elgin/SHORTFALL_REVIEW_2026_10_21.md).

The later [training-side threshold study](model_elgin/THRESHOLD_REVIEW_2026_10_21.md)
is complete. Inner-selected cutoffs were assessed on matching excluded outer
groups. Precision improved0.473929->0.482096, recall declined0.614247->0.600000,
and pooled F1 declined0.535041->0.534624; mean-fold F1 barely changed. The
200+read group also lost recall. Retain0.5 as the working reporting cutoff;
the0.510309 median remains an unevaluated deployment proposal. No calibrated
probability, new neural fit or changed ranking score is claimed.

The user subsequently authorised one final bounded neural experiment:
[positive loss weight3 versus1](model_elgin/LOSS_WEIGHT_EXPERIMENT.md), keeping
cap128, architecture/features, all data0 sites and exact shared folds fixed.
Fresh five-fold training and the queued reporter completed at17:19SGT on
21October, before the later stop request. The [checked comparison](model_elgin/loss_weight_results/README.md)
gives weight1 mean S0.718381 versus weight3's0.718715. Weight1 improves mean
ROC, pooled S and precision at0.5, but reduces mean PR and fixed-cutoff
recall/F1. Retain weight3 under the predeclared mean-fold criterion; this
very small mixed difference establishes no statistical superiority.
The [22October review](model_elgin/LOSS_WEIGHT_REVIEW_2026_10_22.md) closes the
planned neural search. Required benchmarks and final-model/application/report
work now take priority. Checkpoints, logs and negative results remain saved.

## Recommendations for the remaining scientific choices

The existing [logistic-regression reference](model_evaluation/simple_baseline_reference_2026_10_20/README.md)
has now been rescored with the common evaluator: basicA mean S0.4759013017,
selectedB0.4765922612. Exact data0 keys/genes/folds and all historical ranking
metrics agree. This is a saved-score audit, not independent fitting replay;
original per-fold models/source fingerprints are missing. This historical
limitation is now supplemented by a [fresh reproducible replay and published
m6Anet reference](model_evaluation/benchmark_results_2026_10_22/README.md).
The replay independently regenerated selectedB's mean S0.4765922612, with
saved scaler/coefficients, exact splits, feature/source hashes and logs.
Published m6Anet mean ROC/PR/S are0.932176291/0.503257294/0.717716792,
with all121,838sites and11,027,106read-output rows checked. Potential HCT116
pretraining overlap is unresolved; its scores are not five-fold refitting.
Pooled and mean-fold rankings differ, so retain the agreed primary convention.
The existing cap128 control has mean S0.718714607; this small point advantage
does not establish universal or statistically significant superiority.

These are recommended analysis choices, not completed experiments or a new
requirement that Samuel use the same features or architecture.

1. **Model choice — decided:** nominate original-feature cap128, positive
   weight3. The completed required references and documented external
   promotion tradeoffs support this conservative main-project choice; it is
   not the highest S across all experiments. Its fresh18-epoch final
   fit and saved-pipeline verification are complete. The planned main
   neural search is complete; external work stays separate. Keep data1 out
   of winner selection; disclose any subsequent use that changes it.
2. **Calling threshold:** continue exporting full-precision continuous scores.
   The completed maximum-F1 study selected cutoffs on data0 inner genes and
   assessed them inside the declared outer boundaries. It did not justify
   replacing0.5 with the learned policy. Keep0.5 as the working reporting rule,
   preserve the alternative and show sensitivity before application. This is
   development evidence, not a biological threshold or universal optimum. Check
   reliability before interpreting scores as numerical probabilities. Do not
   choose the cutoff from data1 or SG-NEx score distributions.
3. **Task 2 primary comparison:** annotated-human common sites with at least
   20 usable reads and support from at least two metadata replicate groups per
   compared line, subject to the chosen model's supported input range. Average
   eligible runs within a group, then give groups equal weight. Pairwise common
   sites are the primary pairwise population; an all-line common panel supports
   multi-line plots. Repeat at 50/100 reads and stricter group support as
   sensitivity checks. Group independence still needs provenance verification.
4. **Differences and unusual sites:** use continuous replicated score patterns
   first. Member 4's effect-size/coverage screens are exploratory, not validated
   significance tests. Never turn missing observations into zero or remove a
   valid case simply because it is difficult. Review coverage, motif and
   technical explanations before biological interpretation.

## Concrete gaps and how they will be closed

| Remaining input/action | Recommended way to close it |
|---|---|
| Actual SG-NEx event signals — completed | All 23 original inputs, 33,365,823,342 bytes, retained locally with verified source/audit receipts. No further download is needed for the accepted scope. |
| Reference/coordinate consistency | Use the delivered checked aliases, preserve original prediction IDs/positions, and verify transcript/reference/event offsets before genomic-region interpretation. Unknowns remain explicit in MODEL_INFO.md. |
| Selected model and threshold — completed | Original cap128/positive weight3 completed its fresh18-epoch all-data0 fit. The model hash and real prediction example are verified. Retain0.5 as the working reporting rule, with its documented limits; do not imply calibration or a biological threshold. |
| Repository and new test submission — 28 October | Frozen model/example and hosted Ubuntu container prediction are verified. Separate AWS-host preflight is recommended, not an explicitly required own RONIN launch. Predict the actual newly supplied unlabelled input, validate its own format/names/coverage and submit through the announced route. No new-test AUC is available without labels. |
| Real Task 2 CSVs — completed | All 23 full-precision original-key exports from the same artifact are verified. Keep them intact; context qualification belongs to the analysis layer. |
| Biological comparisons — completed | Context-qualified all21pairs, separate all-seven panels, all depth/cutoff sensitivities and scientific figures completed. Review interpretation without new model selection. |
| Explorer rebuild — completed locally; hosting due 8 November | All23actual runs and451,352sites built and desktop-checked. Public hosting/deployment and responsive review remain. A hosted subset must label selection, denominators and omissions. |
| Final report — 8 November | Assemble the completed evidence into a coherent five-page Arial11 main body; an unlimited ungraded appendix does not replace essential evidence. Team review and final submission remain. |

## Report questions to carry through

- Do sequence-aware and read-distribution features improve ranking on held-out
  genes, and which EDA-driven changes actually help?
- Where does performance weaken across motif, coverage and unusual-site groups?
- Which predicted SG-NEx differences are shared or line-associated and remain
  consistent across replicate groups and coverage choices?
- Which differences are plausibly technical or uncertain rather than evidence
  of a biological effect?

Task 1 labels and outputs concern m6A sites. Neither attention weights nor site
scores establish molecule-level states, modification fractions, other chemical
modification types, or causal cell-line effects. The final report must clearly
distinguish observed measurements, model predictions and interpretation.
