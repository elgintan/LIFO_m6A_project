# Historical context: the five initial model candidates

This is a compact source-attributed account of the team's early screening,
not a new model comparison or a change to the selected pipeline.

The preserved 7 October comparison records five candidates: logistic regression,
support vector machine, random forest, XGBoost and LightGBM. It reports training
on data0 with the shared 18 site-level features and gene-separated folds, then
common data1 evaluation. The features summarised the read measurements by
site-level means and standard deviations. Verification depth and tuning budgets
differed between candidates. LightGBM's early values were rounded teammate
summary values at that time; its raw files were not independently replayed in
that original summary-only review.

The early document recommended LightGBM for an intermediate submission and
explicitly said that final team selection was not confirmed at its creation.
That historical recommendation does not supersede the later fixed cap128/weight3
neural selection, fresh all-data0 fit, completed benchmarks or transfer diagnostic.
The early data1-exposed numbers must not be spliced into the later strict shared-
fold comparison as a controlled improvement sequence. No candidate is retrained
or rescored to create this note.

Primary local source: `Team_Project_export/TEAM_MODEL_COMPARISON.md` in the
preserved course workspace, updated 7 October 2026. SHA256:
`c9b2bc4f8e09ea506dd4146174c7158b24cd860f9724e8839d3b9785794c6187`.
The source remains intact outside this repository. This public note includes
only the historical names/protocol/interpretive limits needed by the draft.
Later checked pipeline scores remain in
[the benchmark evidence](../model_evaluation/benchmark_results_2026_10_22/README.md)
and [the fixed selection decision](../model_elgin/FINAL_MODEL_SELECTION.md).
