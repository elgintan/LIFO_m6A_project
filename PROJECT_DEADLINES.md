# Project deadlines and submission priorities

Updated 22 October 2026. **Source:** the user supplied an official course
announcement in this chat on that date. Its changes supersede the original
[project handout](../handout_project2_RNAModifications.html) for the items
below. This records the supplied announcement; it is not an independent
check of Canvas or later announcements.

| Deliverable | Current deadline | Meaning for our work |
|---|---|---|
| Code repositories | **28 October 2026** — original deadline retained | Freeze a usable model/prediction interface, installation instructions, a small test example and reproducible commands. Verify the documented prediction path on clean Ubuntu. |
| Predictions for the **new unlabelled test dataset** | **28 October 2026** — original deadline retained | Apply the frozen saved model and preprocessing to the actual released input. Validate complete unique site coverage, finite scores and the release's required CSV format/names before submitting. |
| Report and interactive visualisation | **8 November 2026** | Complete the scientific analysis, main report and researcher-facing explorer. The announcement's **exact submission time is not confirmed** in the information supplied here. |

The original handout specifies 28 October at **23:59 Singapore time**. The
new announcement retains that original deadline for code and test predictions;
do not transfer that time to the extended 8 November deadline without checking
the course submission page. Submission routes and any new test-release naming
requirements must follow the actual release instructions.

## First: protect the 28 October deliverables

1. Preserve the completed required references and accepted original
   cap128/weight3 model selection. The higher-S external candidate remains
   unpromoted after the documented tradeoff review.
2. Preserve the completed fresh 18-epoch all-data0 fit and frozen saved artifact,
   inference code, preprocessing, checkpoints and same-model supplied-data CSVs.
   The already-exposed data1 diagnostic is separate from independent testing.
3. Verify a fresh installation, documented training/prediction commands and
   a small runnable input/output example. The hosted Ubuntu24.04 container check
   has passed; the separate user-executed native RONIN/AWS Ubuntu26.04 example
   also passed24October. Retain both evidence packages. Our own AWS test is
   recommended preflight because classmates evaluate on AWS Ubuntu; the handout
   does not explicitly require our own RONIN machine or AWS test receipt.
   Ensure the repository gives access to the required model artifact. Follow
   [the readiness checklist](model_elgin/SUBMISSION_READINESS.md).
4. When the new unlabelled test input is released, predict with that same
   artifact and validate the submission contract. Do not substitute the older
   intermediate dataset CSVs. Labels are unavailable: format/coverage checks
   cannot establish test ROC/PR performance, and test inputs must not guide
   another round of model selection.

These are priorities and pending actions, not claims of completed submission.
Keep actual status in [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md).

## Then: complete the report and explorer for 8 November

Our agreed Task 2 analysis population remains **23 available processed SG-NEx
runs**, seven cell lines and 17 metadata replicate groups. The extension does
not turn predictions into completed biological evidence. All 23 real-signal
audits, frozen-model predictions, cross-run context QC and descriptive comparisons
are complete as of 23 October. Retain group-aware comparisons, denominators,
missingness and coverage sensitivity when assembling the report and hosted view.

The announcement permits hosting an **explicitly labelled subset** in the
interactive dashboard. State which runs/cell lines/sites are displayed, the
selection rule, relevant coverage/support thresholds, denominators and what is
omitted. A hosted subset must not be presented as the full 23-run analysis.

Static report figures and the interactive platform may serve different
purposes: the report develops scientific conclusions; the explorer helps its
intended users investigate the underlying results. Their exact figures need
not match, but their data versions, populations and numerical claims must be
consistent. Keep measured signals, predictions and biological interpretation
distinct; simulated prototype scores are not evidence.

## Report rules retained or clarified

- The main report remains **at most five pages**, with the handout's permitted
  title/contents/reference exclusions. Body text remains **Arial 11**;
  captions, tables and references use the handout's Arial 9–11 range. The
  supplied announcement does not change those rules.
- The announcement allows an **unlimited appendix, which is not graded**.
  Put essential methods, primary results, scientific conclusions and their
  main supporting figures in the five-page body. An appendix can retain
  supporting detail, but cannot rescue a missing graded argument.
- Report plus interactive visualisation carries **50 percentage points**;
  model performance carries **five**. Inter-team leaderboard rank is not used
  for grading. Keep the required code/reproducibility and individual
  contribution components in view.
- Retain the AI-use table and the handout's required examples of incorrect,
  misleading or unverified AI output and how they were checked/corrected.
