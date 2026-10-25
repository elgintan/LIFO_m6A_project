# LIFO: m6A prediction and SG-NEx exploration

NUS DSA4262 team project: understand nanopore event data, compare two trained
candidate pipelines using shared gene-grouped validation, and apply one
selected model to investigate predicted m6A patterns across cell lines.

**23 October 2026:** Elgin is consolidating the received work on one laptop.
**Task 1 model selection is complete:** original-feature cap128 with positive
loss weight3 is selected. The fresh 18-epoch all-data0 fit is complete
(11.33 minutes), and the saved artifact and real ten-site example are verified.
Full data0/data1/data2 prediction and frozen data1 evaluation are complete.
Neural data1 S is0.604866 versus LightGBM0.602322; this is a small exposed-data
diagnostic advantage. LightGBM has higher PR AUC and, at0.5, higher precision,
specificity and accuracy. Neither model dominates every metric.
See the [actual results, plots, resource measurements and commands](model_elgin/final_cap128_results/results.md).
The separate external trial has higher ranking S but remains unpromoted after
the documented tradeoff review. See [current stages](CURRENT_STAGE.md) and
[the fixed selection decision](model_elgin/FINAL_MODEL_SELECTION.md).
The [public explorer](https://lifo-sgnex-m6a-explorer.wittylemon1025.chatgpt.site)
now contains **actual scores for all 23 runs and 451,352 sites**, four biological
cases and context/support warnings. See [25 October hosted checks](data_visualisation/hosting_results_2026_10_25/README.md).
The older simulated prototype and received coverage-only dashboard are historical.

**Current stage: Task 2 descriptive analysis and full public actual-score explorer complete; first report draft ready.**
All 23 runs completed and passed verification at 05:46:47 SGT on 23 October.
They contain 2,983,948 scored run-site observations / 232,253,678 reads;
these are not unique sites or assay-confirmed modifications. No training or
prediction needs restarting. The [fixed context QC rules](sgnex_analysis/CROSS_RUN_CONTEXT_QC_PLAN.md)
qualify matching sites before comparisons and preserve conflicts explicitly.
The [completed audit](sgnex_analysis/context_qc_results/README.md) found no
context conflicts across all 451,352 scoreable keys; no scores were excluded.
Member 4's coverage matrix directly checks eligibility and later common-site/
replicate comparisons. See [first-run QC](sgnex_analysis/first_prediction_qc/README.md),
[training-context support](sgnex_analysis/training_context_support/README.md)
and [the resumable run guide](sgnex_analysis/ELGIN_TASK2_RUNNER.md).
The earlier local Docker failure is preserved. A separate hosted Ubuntu 24.04
check now passed with the exact model/pins and verified ten-site numerical parity:
see [actual Linux evidence](model_elgin/ubuntu_prediction_results_2026_10_23/README.md).
**24 October:** the separate user-executed native RONIN/AWS Ubuntu26.04 check
also passed using isolated Python3.12.15 and the same artifact/package pins.
All ten keys/1887reads and model/input/output/source fingerprints matched;
maximum score difference was1.49e-8<3e-6. See [actual AWS evidence](model_elgin/aws_prediction_results_2026_10_24/README.md)
and [prediction/submission readiness](model_elgin/SUBMISSION_READINESS.md).
[Scientific findings, all-pair summaries
and four figure pairs](sgnex_analysis/task2_results_2026_10_23/README.md) are available.
The [first scientific report draft](report/REPORT_DRAFT_2026_10_25.md) and
[evidence/page plan](report/REPORT_EVIDENCE_MAP_2026_10_25.md) are ready for review.
Final Arial 11/five-page rendering and actual new-test submission remain pending.
The user confirmed on 25 October that the new input has not been received.

[Four focused biological cases](sgnex_analysis/biological_case_results_2026_10_23/README.md)
now connect the score comparisons to named transcripts, primary literature and
uncertainty: HNRNPA1/RAB1B contrasts, ACTG1 shared high signal, and G3BP2 group/
coverage limitations. Their training-key exposure and technical confounding are
explicit. These are predicted m6A patterns, not confirmed differential chemistry.

**Deadline update supplied by the user on 22 October:** code repositories and
predictions for the new unlabelled test dataset remain due **28 October**;
the report and interactive visualisation are extended to **8 November**.
The latter's exact time is unconfirmed. See [deadlines and priorities](PROJECT_DEADLINES.md).

## Start here

1. Check [the current stage and next result](CURRENT_STAGE.md), then read
   [current evidence, decisions and remaining gaps](INTEGRATION_STATUS.md).
2. Follow the [minimum shared evaluation rules](model_evaluation/SHARED_RULES.md).
   Keep the exact five data0 gene folds and common scorer; model designs remain
   independent. Data1 is already exposed and is a transfer diagnostic.
3. To run the selected saved model or reproduce its fixed final training,
   follow [Elgin's final-model guide](model_elgin/FINAL_MODEL_USAGE.md).
   [Samuel's example](model_samuel/README.md) retains the LightGBM candidate.
   For the completed neural CV experiment, follow [the development guide](model_elgin/context_reference_v1/README.md).
   The [completed read-depth investigation](model_elgin/read_depth_stability_results/README.md)
   supports retaining all-read prediction; it is a matched-cohort diagnostic,
   not a newly trained model or replacement full-CV score.
   The [completed signal-case review](model_elgin/signal_case_review_results/README.md)
   connects Member1's unusual sites and matched high-coverage errors to raw
   read plots. The [cap128 training experiment](model_elgin/read_cap_results/README.md)
   completed on 21 October: mean-fold S rose from 0.717642 to 0.718715,
   with a positive change in all five folds. This is a small development
   gain; fixed 0.5-cutoff classification metrics were slightly worse.
   The [completed subgroup/Samuel comparison](model_elgin/read_cap_shortfalls_results/README.md)
   supports cap128 as the leading data0 candidate, with remaining high-depth
   misses and differing score reliability. The [recommended next step](model_elgin/SHORTFALL_REVIEW_2026_10_21.md)
   was training-side cutoff validation. The [completed threshold study](model_elgin/THRESHOLD_REVIEW_2026_10_21.md)
   found no convincing F1 gain; 0.5 remains the working reporting cutoff.
   The [completed loss-weight comparison](model_elgin/loss_weight_results/README.md)
   gave mean S0.718381 for weight1 versus0.718715 for weight3. Retain weight3:
   removing the extra positive penalty raised precision but reduced recall
   and F1 at0.5. The [review](model_elgin/LOSS_WEIGHT_REVIEW_2026_10_22.md)
   retains the mixed fold and pooled results; no calibrator was fitted.
4. Continue [SG-NEx analysis](sgnex_analysis/README.md) and the
   [current explorer pipeline](data_visualisation/README.md) after selected-model
   predictions are available. Their supplied scripts are now integrated.

| Folder | Contribution |
|---|---|
| [eda](eda/README.md) | Member 1's findings, source code and exact shared folds |
| [model_elgin](model_elgin/README.md) | Neural candidates, completed matched CV and data0 diagnostics |
| [model_samuel](model_samuel/README.md) | Unpacked sequence-relative LightGBM, saved model and verification |
| [model_evaluation](model_evaluation/README.md) | Common scorer, shared rules and final comparison |
| [sgnex_analysis](sgnex_analysis/README.md) | Member 4's 23-run inventory, coverage and comparison pipeline |
| [data_visualisation](data_visualisation/README.md) | Member 5's validation/build pipeline and coverage-only explorer |

## Scientific story and report

Member 1's EDA -> tested model decisions -> shared candidate comparison -> one
frozen model and calling rule -> real SG-NEx predictions -> replicate-aware
comparisons -> interactive exploration and supported conclusions.

EDA must affect decisions and checks, including cases where a proposed feature
does not improve performance. Keep valid difficult sites; distinguish measured
signals, predictions and biological interpretation. Our scores concern m6A
candidate sites, not other modifications or measured modified-molecule fractions.

Working Task 2 scope is the **23 available processed runs** in the canonical
`sgnex_analysis/manifest.csv`. Missing observations are not unmodified sites.
The hosted explorer may show an explicitly labelled subset, with its selection
rule, displayed population and omissions stated. Static report figures and
interactive views can serve different scientific/exploration purposes while
remaining consistent with the same evidence. See
[project context](PROJECT_CONTEXT.md) and [data access](DATA_ACCESS.md).

Report and interactive visualisation carry 50 percentage points; model
performance carries 5 and leaderboard rank does not determine the grade. The
formal main-report limit remains five pages in Arial 11, with the handout's
permitted exclusions. The new announcement allows an unlimited, **ungraded**
appendix; essential arguments and conclusions must remain in the main body.
The [required simple-baseline/m6Anet comparisons](model_evaluation/benchmark_results_2026_10_22/README.md)
are complete: mean S0.476592 and0.717717 respectively, versus the existing
cap128 control0.718715. The published reference may overlap in pretraining;
its fold-stratified scores are not five-fold refitting. Hosted Ubuntu prediction
and the separate native AWS example have passed. The full explorer is publicly
hosted; final report layout/review and actual new-test submission remain unfinished. Retain a frozen,
runnable inference pipeline and the new unlabelled-test predictions for
28 October, then complete Task 2 analysis/report/explorer for 8 November.
The original 28 October deadline is 23:59 Singapore time; **8 November's exact
time is not confirmed**. See [the supplied deadline update](PROJECT_DEADLINES.md).

Large signals, prediction tables, caches, environments and training checkpoints
stay outside ordinary Git uploads. They remain local or are regenerated through
documented commands. A fresh clone must obtain the documented inputs before
rebuilding the full explorer; it is not shipped as a completed real-score site.
The preserved [source receipt](SOURCE_RECEIPT.json) describes the original
repository setup; each newly integrated handoff records its own provenance.
See [AI assistance](AI_USE.md), [contributing](CONTRIBUTING.md) and
[GitHub/VS Code setup](GITHUB_VSCODE_SETUP.md).
