# Task 1: final configuration nomination

Decision recorded on 22 October 2026, before the new final all-data0 fit.
**Nominate the original-feature cap128 neural pipeline with positive loss
weight 3.** The user authorised proceeding with this main-project decision.
The final configuration is chosen; a new final saved model does not yet exist.
Live execution/completion status belongs in [CURRENT_STAGE.md](../CURRENT_STAGE.md).

This is a deliberate conservative deployment choice. It is **not** a claim
that this pipeline has the highest score across every experiment, that it
beats every alternative on every metric, or that its performance is optimal.
The separately audited external neural trial has a genuine higher primary
score and remains separate with its **INCONCLUSIVE promotion decision**.

## Accepted development evidence

All values use the same 121,838 data0 sites, 5,475 positive labels, 3,852 genes
and exact five shared gene groups. S remains the unweighted mean across five
groups of `(ROC AUC + trapezoidal PR AUC)/2`. AP and pooled curve areas remain
supplementary; the score definition has not changed to favour this nomination.

| Main pipeline/reference | Mean-fold S | Interpretation |
|---|---:|---|
| Original-feature cap128, positive weight 3 | **0.7187146070** | Nominated main neural configuration |
| Cap128, positive weight 1 | 0.7183812884 | Higher mean ROC and pooled S; lower mean PR and fixed-cutoff recall/F1 |
| Original-feature cap32 | 0.7176418289 | Earlier neural control |
| Added context-relative branch | 0.7088845390 | EDA-motivated change that did not improve the primary score |
| Samuel's sequence-relative LightGBM | 0.7104464986 | Higher precision/specificity and better descriptive raw-score reliability in prior checks |
| Published m6Anet HCT116_RNA002 | 0.7177167924 | Pretrained reference; potential HCT116 overlap, not five-fold retraining |
| Fixed balanced-C1 logistic baseline | 0.4765922612 | Fresh reproducible five-fold replay of the previously selected simple recipe |

The cap128-minus-m6Anet difference is only about **0.000998**. Published
m6Anet has higher mean ROC AUC, while cap128 has higher mean trapezoidal PR
AUC. These comparisons do not establish statistical significance or
independent superiority over a potentially overlapping pretrained model.
See the [completed benchmarks](../model_evaluation/benchmark_results_2026_10_22/README.md),
[read-cap comparison](read_cap_results/README.md) and
[loss-weight review](LOSS_WEIGHT_REVIEW_2026_10_22.md).

## External result and why it is not promoted

The separate induced-attention neural trial achieved mean-fold **S=0.7266439859**,
a genuine **+0.0079293789** over the nominated control, with improvement in all
five folds. An independent saved-evidence audit found no material leakage or
hardcoded-score defect. Its stronger ranking evidence must not be hidden or
described as a failed numerical comparison.

Its promotion remains inconclusive after reviewing important tradeoffs:

- Overall recall at the existing 0.5 reporting cutoff falls from **0.614247
  to 0.608402**. External precision, F1 and descriptive Brier/log-loss results
  improve, so this is a mixed outcome, not a general classification failure.
- At **200+ reads**, it detects **151/461** positives versus **168/461** for
  cap128: recall **32.75% versus 36.44%**. Its ranking S in this same cohort
  improves, from about 0.695188 to 0.701330. A loss at an uncalibrated fixed
  cutoff does not invalidate the ranking gain or prove poorer discrimination.
- The supported **TAACT** cohort loses S, approximately **0.472600 to
  0.455875**, across 4,433 sites/71 positives; 14 of 15 supported motifs
  improve. Sparse groups are not required to improve universally.
- Retained fit/outer-inference wall time is at least **9,408.375 seconds**,
  with a sampled peak of about **1,477.42 MiB**. Eight versus four threads,
  changed unfitted preprocessing and interruption-accounting differences
  prevent a controlled architecture-only or speed comparison.
- One prescribed seed and reused development folds do not establish seed
  stability or independent generalisation. Its separate entry point also
  lacks a final all-data0 artifact and general prediction interface.

These are reasons for conservative promotion, together with the time needed
for a reliable final pipeline and the report/Task 2 deliverables. They are
**not a new requirement that every subgroup must win**, nor grounds for
redefining the agreed primary score. We consciously retain the integrated
main configuration despite the external candidate's higher ranking score.
The external code, checkpoints, audit and temporary report remain preserved
outside the main pipeline; no external weights initialise this final fit.

## EDA has influenced the nominated pipeline

Member 1's gene/site relationships support holding all sites from the same gene
together through the existing five-fold assessment. Motif differences motivate sequence
context and supported motif checks; unequal read depth motivates the cap128
experiment and retaining all-read prediction. Valid unusual signals remain in
the training population and error analysis rather than being deleted.

The additional context-relative feature branch was actually tested and lost
performance; it is omitted from this configuration with that negative finding
retained. `context_mode=none` means **no extra relative-feature branch**:
the model still uses the original seven-base sequence embedding. EDA is not
evidence that particular reads have known modification states, nor a reason
to resplit data until scores improve.

## Fixed final-fit prescription

- Start a **fresh** instance of the evaluated original-feature model: nine
  read measurements, seven-base embedding, gated attention pooling and all
  63 site-distribution summaries; `context_mode=none`.
- Preserve the evaluated configuration: width 48, dropout 0.25, AdamW learning
  rate 0.001, weight decay 0.0001, positive loss weight 3, training read cap
  128, batch size 256, four CPU threads and seed 2026. Prediction uses all
  available valid reads, as supported by the completed depth investigation.
- Fit preprocessing and model weights using **all data0 only**. Start with
  fresh weights; do not initialise from any CV, historical or external model.
- Train for **18 epochs**, the median of the verified original cap128
  inner-selected durations **[9, 20, 19, 18, 17]**. This follows the existing
  final-fit rule; no new duration search or data1-based stopping is permitted.
- Preserve per-epoch checkpoints, optimizer/RNG state, logs, source/input/CV
  fingerprints and the fixed selection rule. Promote the final artifact only
  after all 18 epochs complete and its integrity/inference checks pass.
- Use the saved model and fitted preprocessing unchanged for application.
  Keep the 0.5 **working reporting cutoff**, alongside continuous scores and
  sensitivity checks; it is not a calibrated biological threshold. The prior
  threshold study did not justify replacing it, and no calibrator was fitted.

The exact source hashes, commands, artifact hashes and measured final-fit costs
will be generated by the final wrapper and retained receipts. This document
is fixed before that fitting begins and its SHA256 is part of the new identity.
Record later progress/results elsewhere rather than editing this decision
after it has been hashed for a fit.

## What this decision does and does not complete

**Completed:** main configuration nomination; original five-fold gene-grouped
development evidence; simple baseline and published m6Anet references.

**Pending:** fresh final fit and saved artifact, generic prediction checks,
the frozen **already-exposed data1 diagnostic**, same-artifact predictions on
all three supplied datasets, and the newly released unlabelled-test outputs
when their actual inputs/instructions are available. Data0 predictions from
the all-data0 final model are fitted-data predictions, not OOF validation.
Neither data1 nor unlabelled-test score patterns may select further changes.

Clean Ubuntu reproduction, real predictions for the agreed 23 SG-NEx runs,
replicate-aware Task 2 analysis, the genuine-score explorer and the five-page
scientific report remain separate unfinished stages. Code/new-test predictions
are due **28 October**; report/interactive visualisation **8 November**.
No site score or attention weight establishes other RNA modification types,
modified-molecule fractions or causal differences between cell lineages.
