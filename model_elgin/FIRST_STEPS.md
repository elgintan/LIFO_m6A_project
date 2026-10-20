# Elgin: first modelling step

19 October 2026. Focus: understand the reference model and define one
EDA-motivated experiment. New candidate implementation/training is still
pending; this document does not claim an improvement.

In VS Code choose **File > Open Folder** and open your local
`LIFO_m6A_project` folder. In the left Explorer, expand `model_elgin` and open
this guide. For now, read sections 1 and 3; the reference check in section 2
has already been completed by the assistant, so rerunning it is optional.

## 1. Understand the reference we already have

Open [the archived model](baseline_2026_10_07/code/model.py) and
[data preparation](baseline_2026_10_07/code/data.py) for inspection.

One input example is a transcript-position site. It has a seven-letter
sequence context and multiple reads, each containing nine measurements. The
model predicts one m6A score for the whole site. Individual reads have no
supplied true modification label.

The existing network already combines:

- A numerical encoding learned for the seven-base sequence.
- A small neural network that processes each read alongside that context.
- Attention, a learned weighting for combining read representations, plus
  their mean and spread. Attention is not verified read-level modification.
- 63 site summaries: means, standard deviations and five quantiles of each
  of nine measurements, calculated from all reads. Medians/quartiles exist.
- A final network producing the site score.

Training sampled up to 32 reads in the neural branch; inference used all
reads. The 63 summary features used all reads in both cases. Do not claim
that adding sequence, medians or attention is a new contribution.

The archived training scripts assume their original surrounding folders.
Read them to understand the implementation; do not launch their default
training command from the copied archive. The final saved all-data0 weights
cannot initialise a new held-out-data0 fit.

## 2. Establish a comparable reference

Check the original per-fold prediction files against their combined
out-of-fold (OOF) file and the exact accepted gene assignments. Add the
existing fold ID as metadata without changing scores, then use the shared
scorer. This can reuse valid saved fits rather than repeating training.

An OOF score comes from a model that excluded that site's fold. It differs
from a prediction produced by the final model fitted on all data0.
Historical OOF results remain development evidence: those results helped
select the original architecture. Rechecking them does not create a new test.

**Observed reference check, 19 October:** all 121,838 saved scores matched
their original five fold files and the accepted assignments. The common
scorer reproduced mean-fold ROC AUC **0.93301027**, trapezoidal PR AUC
**0.50388135**, and combined score **0.71844581**. These are the October 7
model's historical predictions rescored, not a newly trained model. Detailed
results and provenance are in `reference_check_2026_10_19/`.

The local exporter is [prepare_reference.py](tools/prepare_reference.py).
It requires the retained original run directory. To reproduce in Elgin's
existing Windows layout, choose **Terminal > New Terminal** in VS Code,
confirm the terminal is in `LIFO_m6A_project`, and use PowerShell:

```powershell
& ..\advanced_model\.venv\Scripts\python.exe -B model_elgin/tools/prepare_reference.py --historical-run ../advanced_model/runs/attention_weighted --output-dir model_elgin/reference_check_2026_10_19
& ..\advanced_model\.venv\Scripts\python.exe -B model_evaluation/evaluate.py --dataset data0 --labels ../data0/data.info.labelled --predictions model_elgin/reference_check_2026_10_19/data0_oof.csv --output model_elgin/reference_check_2026_10_19/data0_cv_metrics.json
```

`&` launches the specified executable; the `.venv` path selects the existing
Python environment with the required libraries; `-B` avoids bytecode-cache
files. These commands export/check saved scores, not train or predict. Expected
scorer output includes `data0: primary score 0.7184458125`. If Python or an
input cannot be found, check the terminal directory and the paths above; do
not regenerate folds or launch the archived trainer to bypass the error.

A public clone on another computer may not contain the original run
directory; the exported reference can be rescored using matching local data0
labels and the common scorer. Original checkpoints/logs remain retained
outside this clean repository.

## 3. First proposed improvement: same-context signal references

Research question: **does adding a signal's deviation from the typical
training signal for its sequence context improve the current network?**

Member 1 found that pooled signal comparisons can point in a different
direction from comparisons within sequence motifs. A high current alone is
therefore not a universal modification rule. The existing sequence embedding
can learn interactions; an explicit context-relative feature is a hypothesis
to test, not an assumed missing capability.

For this experiment, retain the existing inputs and architecture as far as
possible, add training-fitted context reference features, and define a
fallback for contexts with little/no training support. Fit the reference
values only inside the permitted fitting genes, then apply them unchanged
to validation/assessment. Keep original measurements as well.

Do not calculate references using all data0 before splitting. Do not inspect
data1 to choose the reference rule. A context-relative unusual value can be
useful signal or noise; it is not automatically an error to remove.

## 4. Work after this first step

1. Create a portable working trainer/predictor with explicit data, fold and
   output paths, preserving the archive and its saved reference.
2. Implement and check the one added feature family, including sparse-context
   fallback and save/load behaviour. Save references with each fitted model.
3. Screen it using data0 only, then complete the same five outer rounds for
   a nominated candidate. Match non-feature settings for an isolated feature
   comparison, or explicitly describe other changes as pipeline differences.
4. Compare the shared mean-fold score and motif/coverage weaknesses. Retain
   actual logs/checkpoints and gains, failures or inconclusive results.
5. Investigate read-depth/outlier robustness as another controlled experiment.
   Keep valid unusual sites and recompute read-derived inputs consistently in
   subsampling tests. Real variation should not be erased merely to gain score.

Freeze the final data0 recipe before its data1 transfer evaluation. Member 4's
sample inventory and Member 5's interface can progress in parallel. Their
completed biological analysis is not a prerequisite for this modelling work.

## Current boundaries

- [Minimum shared rules](../model_evaluation/SHARED_RULES.md) stay unchanged.
- The [working implementation](context_reference_v1/README.md) is now complete:
  shared gene groups, training-only references/fallback, matched control and
  candidate, checkpoint recovery and prediction-stage checks.
- [Thirty tests and small data0 fits](context_reference_v1/IMPLEMENTATION_CHECK.md)
  passed. The subsequent full five-fold comparison measured lower S with the
  added features (0.708885) than with original features (0.717642). Current
  results and saved-score diagnostics are summarised in [the model status](README.md).
  A new final model and real SG-NEx predictions remain pending.

## Research questions to retain for the report

These are questions to investigate, not findings. The historical reference
has been checked. The first full feature comparison and saved-score subgroup
diagnostics are complete; the added features did not improve mean score.
The read-subsampling diagnostic has now completed; all-read inference performed
best on the matched cohort. See [actual results](read_depth_stability_results/README.md).
The [raw-signal case review](signal_case_review_results/README.md) also completed:
36 Member1 data0 entries, matched high-depth errors and eight read-level panels.
Any newly trained robustness intervention remains pending. A proposed next
single change is training with up to 128 reads per bag rather than 32; this is
a testable hypothesis, not an observed improvement.

1. **Context-relative features:** do training-only, sequence-relative signal
   features improve held-out-gene development performance beyond the existing
   sequence-aware neural network? Evidence: a matched baseline/candidate
   comparison of mean-fold ROC AUC, trapezoidal PR AUC and combined score,
   with per-fold variation and motif-support limitations. Residuals are a
   derived representation of existing measurements, not new biological truth.
2. **Read/outlier robustness:** how stable and reliable are predictions across
   read coverage and unusual valid read distributions, and does a specified
   robustness change help? Evidence: a coverage/performance or read-subsampling
   stability plot plus a few context/coverage-matched unusual-site examples.
   Do not treat repeated subsets as biological replicates or assume unusual
   values are errors. Changes must be trained/tested within the agreed bounds.
3. **Transfer:** after freezing the HCT116/data0 model, what performance and
   subgroup differences appear on HEK293T/data1, given previous exposure and
   overlapping sites/genes? Evidence: frozen-artifact data1 metrics and
   shared-site/new-site diagnostics with exposure, provenance and prevalence
   limitations. Do not use these scores to tune while calling them a blind test.

The linked Task 2 question, coordinated with Member 4, is which predicted m6A
patterns differ across SG-NEx samples and how coverage/replicates support
those observations. The current model does not classify all RNA modification
types or establish true modification fractions.

For an isolated feature-effect claim, match non-feature training settings.
If the new trainer, stopping strategy or settings change materially, fit a
matching control as well as the new candidate. The historical reference alone
cannot isolate the feature's contribution under different training conditions.

Keep the report chain concise: **EDA observation -> research question ->
controlled comparison -> actual result -> interpretation and limitation**.
Report negative or inconclusive results honestly; select the strongest few
measured examples for the five-page report rather than promising every test.
