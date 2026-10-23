# Current project stage — 23 October 2026

**Current stage: Task 2 analysis and full local actual-score explorer complete; report assembly and hosting next.**
All 23 runs completed at 05:46:47 Singapore time on 23 October, exit0; the
checkpoint is complete and no run lock remains. The verified exports contain
2,983,948 scored run-site observations / 232,253,678 reads. These are repeated
observations, not unique sites or confirmed modifications. Task 1 final
training, supplied-data predictions and data1 scoring are complete.
The original-feature cap128 neural configuration with positive loss weight 3
completed its fresh **18-epoch all-data0 fit in 679.823 seconds (11.33 minutes)**.
The saved model and a real ten-site prediction example passed verification.
The same artifact produced all 121,838 / 90,810 / 1,323 data0/data1/data2
predictions, with complete unique keys and valid scores. Data1 ROC/PR/S are
0.827381010 / 0.382349993 / 0.604865501. LightGBM's S is 0.602321536;
the neural advantage is small, and LightGBM has higher PR, precision,
specificity and accuracy at the existing 0.5 cutoff.
The [results report](model_elgin/final_cap128_results/results.md) contains the
actual validation/data1 comparisons, figures, measured resources and commands.
See the fixed
[selection and final-fit prescription](model_elgin/FINAL_MODEL_SELECTION.md).

The external trial has genuinely higher mean-fold ranking S (0.726644 versus
0.718715). It remains separate, with an inconclusive promotion decision;
the main nomination is a documented conservative tradeoff, not a claim that
cap128 is globally best. Required simple-baseline and published m6Anet
benchmarks have completed.

| Stage | Actual status | Next concrete result |
|---|---|---|
| Task 1: EDA and shared evaluation | Complete for the current modelling comparison | Retain all original data0 sites, exact five gene folds and checked evidence |
| Task 1: main configuration selection | **Nominated**: original cap128, positive weight 3 | Fixed decision and 18-epoch final-fit prescription |
| Task 1: final model preparation/fitting | **Complete**: fresh 18-epoch fit, saved model and ten-site example | Retain immutable artifact, resumable checkpoints and logs |
| Task 1: frozen data1 diagnostic | **Complete**: S0.604865501 | Retain already-exposed transfer evidence and all metric tradeoffs; no winner selection |
| Task 1: predictions on supplied data0/data1/data2 | **Complete**: 121,838 / 90,810 / 1,323 sites | Preserve CSVs and manifests; fitted-data0 scores are separate from OOF validation |
| Task 1: new unlabelled test submission | Pending actual release/input/instructions | Same frozen artifact, exact coverage/format checks and required submission files; no unavailable label metrics |
| Code reproducibility | **Hosted Ubuntu 24.04 prediction passed**, exact pins and ten-site parity verified; laptop Docker failure preserved | Separate fresh AWS-host verification remains pending; see [actual Linux evidence](model_elgin/ubuntu_prediction_results_2026_10_23/README.md) |
| Task 2: real SG-NEx predictions | **Complete: 23/23 verified** | Preserve same-model exports, full source QC, coverage checks and completion receipts; do not rerun |
| Task 2: biological/data analysis | **Complete descriptive comparison**: no context exclusions; all 21 pairs at 20/50/100 reads, separate all-line panels and 0.5/0.7/0.9 summaries | Team review and concise report narrative; retain all outcomes and limitations |
| Interactive visualisation | **Full local actual-score build complete**, all 23 runs/451,352 sites; 190 validation checks and 189 exact fraction checks passed; desktop Chrome interactions checked | Public hosting/final deployment checks; any hosted subset must be explicitly identified |
| Final scientific report | Evidence available; final five-page report unfinished | Main-body methods, findings, limitations and scientific figures; appendix is unlimited but ungraded |

**Deadlines:** repositories and new unlabelled-test predictions remain due
**28 October 2026** at the original 23:59 Singapore deadline. Report and
interactive visualisation are due **8 November**; its exact time is unconfirmed.
See [the supplied announcement and priorities](PROJECT_DEADLINES.md).

The model is available under `model_elgin/artifacts/cap128_weight3_v1/` with
SHA256 `b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.
Follow [the runnable model guide](model_elgin/FINAL_MODEL_USAGE.md). The public
training interface passed an actual full-input/cache/configuration check
without fitting a second model. The hosted Ubuntu container prediction check
has now passed; this does not establish a separate fresh AWS-host check.
Local predictions and their manifests are retained under
`model_elgin/outputs/final_cap128_v1/`. Independent checks matched every CSV
key to its supplied label file and verified model/input/output/source hashes;
the original CV files remain unchanged. Completion receipts, rather than this
stage tracker alone, establish which commands actually finished.

All 23 runs passed the frozen pipeline's source and export checks. Original
batch completion is recorded in `sgnex_analysis/outputs/elgin_task2_pipeline_v1/`.
Below-20-read source sites remain explicitly unscored in QC.
See [actual first-run evidence](sgnex_analysis/first_prediction_qc/README.md)
and [the sequential-run guide](sgnex_analysis/ELGIN_TASK2_RUNNER.md).
The 23-run predictions and [context audit](sgnex_analysis/context_qc_results/README.md)
are complete. [Actual scientific findings and four figure pairs](sgnex_analysis/task2_results_2026_10_23/README.md)
and the full local actual-score explorer are available. Both context policies
retain the same population, with no exclusions. Final report and public hosting
remain pending. No project computation is intentionally running at handover.
