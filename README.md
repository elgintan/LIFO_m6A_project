# LIFO: m6A prediction and SG-NEx exploration

NUS DSA4262 team project: understand nanopore event data, compare two trained
candidate pipelines using shared gene-grouped validation, and apply one
selected model to investigate predicted m6A patterns across cell lines.

**22 October 2026:** Elgin is consolidating the received work on one laptop.
Both candidates have real data0 validation evidence; final model selection,
validated calling cutoff and real whole-run Task 2 predictions remain pending.
The current explorer is **coverage-only**. The older simulated prototype is
archival and is not biological evidence.

**Deadline update supplied by the user on 22 October:** code repositories and
predictions for the new unlabelled test dataset remain due **28 October**;
the report and interactive visualisation are extended to **8 November**.
The latter's exact time is unconfirmed. See [deadlines and priorities](PROJECT_DEADLINES.md).

## Start here

1. Read [current evidence, decisions and remaining gaps](INTEGRATION_STATUS.md).
2. Follow the [minimum shared evaluation rules](model_evaluation/SHARED_RULES.md).
   Keep the exact five data0 gene folds and common scorer; model designs remain
   independent. Data1 is already exposed and is a transfer diagnostic.
3. For a runnable saved candidate, follow [Samuel's example](model_samuel/README.md).
   For the completed neural CV experiment, follow [Elgin's guide](model_elgin/context_reference_v1/README.md).
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
its fold-stratified scores are not five-fold refitting. Clean Ubuntu reproduction
and the final report/real-result explorer are still unfinished. Prioritise a frozen,
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
